"""Lab-only human evaluation; canonical turns and the H1 lifecycle stay separate."""

from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
from inspect import signature
import json
from time import perf_counter
from typing import Literal
from uuid import UUID, uuid4

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, StrictStr, field_validator
from starlette.concurrency import run_in_threadpool

from app import hindsight_shadow
from app.conversation_runtime import process_turn
from app.durable_jsonl import append_jsonl
from app.foreground_activity import track_foreground_generation
from app.model_client import count_input_tokens, generate_chat_completion
from app.working_context import _compose_working_messages, build_working_context
from personality.runtime import compile_personality_system_prompt


FAIRNESS = "BEST_EFFORT_PRE_TURN"
LOG_NAME = "memory-arena-v0.jsonl"
CHOICES = {"rag", "hindsight", "tie", "neither"}
_CONTEXT_SIGNATURE = signature(build_working_context)


class ArenaChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: StrictStr
    message: StrictStr

    @field_validator("session_id", "message")
    @classmethod
    def nonempty_text(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("must not be empty")
        return value


class ArenaVoteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    trial_id: UUID
    choice: Literal["rag", "hindsight", "tie", "neither"]


def require_lab_arena():
    # Reuse H1's exact Lab/canonical-store eligibility check, including resolution.
    if not hindsight_shadow._retain_eligible():
        raise HTTPException(status_code=404, detail="Arena is Lab only")


def _now():
    return datetime.now(timezone.utc).isoformat()


def _hash(value):
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False)
    return sha256(encoded.encode("utf-8")).hexdigest()


def _trial_states(records):
    """Validate the small derived event stream; never repair damaged history."""
    trials = {}
    for record in records:
        if record.get("schema_version") != 1:
            raise ValueError("unsupported Arena record")
        trial_id = record["trial_id"]
        if str(UUID(trial_id)) != trial_id:
            raise ValueError("invalid trial ID")
        if record.get("record_type") == "trial":
            if trial_id in trials or type(record.get("votable")) is not bool:
                raise ValueError("invalid trial record")
            trials[trial_id] = record
        elif record.get("record_type") == "vote":
            if (trial_id not in trials or not trials[trial_id]["votable"]
                    or record.get("choice") not in CHOICES):
                raise ValueError("invalid vote record")
        else:
            raise ValueError("unknown Arena record")
    return trials


def append_arena_trial(record):
    require_lab_arena()
    append_jsonl(hindsight_shadow.DATA_DIR / LOG_NAME, record,
                 validate_records=_trial_states)


def record_arena_vote(request):
    require_lab_arena()
    record = {"schema_version": 1, "record_type": "vote",
              "trial_id": str(request.trial_id), "choice": request.choice,
              "recorded_at": _now()}

    def validate(records):
        trials = _trial_states(records[:-1])
        trial = trials.get(record["trial_id"])
        if trial is None:
            raise HTTPException(status_code=404, detail="Unknown Arena trial")
        if not trial["votable"]:
            raise HTTPException(status_code=409, detail="Arena trial is not votable")
        _trial_states(records)

    try:
        append_jsonl(hindsight_shadow.DATA_DIR / LOG_NAME, record, validate_records=validate)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=503, detail="Arena evaluation storage unavailable") from None
    return {key: record[key] for key in ("trial_id", "choice", "recorded_at")}


def build_shadow_messages(system_prompt, recent_messages, query, evidence, *,
                          count_tokens, historical_token_budget, input_token_budget):
    """Compose without I/O except the supplied tokenizer; never trim recent context."""
    def compose(selected, recent):
        # These IDs exist only inside prompt rendering. They cannot be confused
        # with canonical integer IDs, hydrated, or passed to canonical retention.
        rows = [{"id": f"hindsight:{item['source_id']}", "role": "derived",
                 "content": item["text"]} for item in selected]
        return _compose_working_messages(system_prompt, rows, recent, query)

    baseline = count_tokens(compose([], []))
    selected = []
    for item in evidence:
        candidate = [*selected, item]
        if max(0, count_tokens(compose(candidate, [])) - baseline) > historical_token_budget:
            break
        selected = candidate
    messages = compose(selected, recent_messages)
    tokens = count_tokens(messages)
    while tokens > input_token_budget and selected:
        selected.pop()
        messages = compose(selected, recent_messages)
        tokens = count_tokens(messages)
    if tokens > input_token_budget:
        raise ValueError("frozen recent context exceeds input budget")
    return messages, deepcopy(selected), tokens


def _successful_main(main):
    status = main["status"]
    return (status["overall"] in {"OK", "DEGRADED"} and status["model"] == "OK"
            and status["persistence"] == "NORMAL" and bool(main["reply"]))


def _generate_shadow(shadow, captured, prompt, query):
    try:
        messages, evidence, tokens = build_shadow_messages(
            prompt, captured["context"]["recent_messages"], query,
            shadow["recall"]["results"], count_tokens=count_input_tokens,
            historical_token_budget=captured["historical_token_budget"],
            input_token_budget=captured["input_token_budget"],
        )
        shadow.update(evidence=evidence, input_tokens=tokens)
        started = perf_counter()
        try:
            with track_foreground_generation():
                shadow["reply"] = generate_chat_completion(messages)
        finally:
            shadow["generation_elapsed_ms"] = round((perf_counter() - started) * 1000, 3)
        shadow.update(status="OK", error=None)
    except Exception:
        shadow.update(status="ERROR", reply=None, error="SHADOW_GENERATION_FAILED")


async def run_arena_turn(request, *, build_response):
    require_lab_arena()
    trial_id = str(uuid4())
    prompt = compile_personality_system_prompt()
    personality_hash = sha256(prompt.encode("utf-8")).hexdigest()
    try:
        observation = await hindsight_shadow.recall(request.message)
    except Exception:
        observation = {"provider": "hindsight", "status": "ERROR", "results": [],
                       "elapsed_ms": None, "error": "UNEXPECTED_ERROR"}
    captured = {}
    generation = {}

    def capture_context(**kwargs):
        context = build_working_context(**kwargs)
        bound = _CONTEXT_SIGNATURE.bind(**kwargs)
        bound.apply_defaults()
        captured.update(context=deepcopy(context), **{
            name: bound.arguments[name]
            for name in ("historical_token_budget", "input_token_budget")
        })
        return context  # Return the original object without changing RAG behavior.

    def generate_main(messages):
        started = perf_counter()
        try:
            return generate_chat_completion(messages)
        finally:
            generation["elapsed_ms"] = round((perf_counter() - started) * 1000, 3)

    def canonical_turn():
        result = process_turn(
            session_id=request.session_id, user_content=request.message, web_mode="off",
            system_prompt_fn=lambda: prompt, build_context_fn=capture_context,
            count_tokens_fn=count_input_tokens, generate_fn=generate_main,
        )
        return build_response(result)

    main = await run_in_threadpool(canonical_turn)
    shadow = {"provider": "hindsight", "canonical": False, "status": "SKIPPED",
              "reply": None, "recall": observation, "evidence": [], "input_tokens": None,
              "generation_elapsed_ms": None, "error": "CANONICAL_TURN_FAILED"}
    if _successful_main(main):
        if observation["status"] != "OK":
            shadow["error"] = "HINDSIGHT_RECALL_UNAVAILABLE"
        elif "context" not in captured:
            shadow["error"] = "CANONICAL_CONTEXT_UNAVAILABLE"
        else:
            await run_in_threadpool(_generate_shadow, shadow, captured, prompt, request.message)
    response = {"trial_id": trial_id, "fairness": FAIRNESS,
                "main": dict(main, provider="rag", canonical=True,
                             generation_elapsed_ms=generation.get("elapsed_ms")),
                "shadow": shadow, "personality_sha256": personality_hash,
                "evaluation": {"status": "UNAVAILABLE", "votable": False}}
    # Every evaluation-only operation is contained after the canonical result.
    # Its failure must never turn a persisted successful reply into a failed chat.
    try:
        context = captured.get("context", {})
        votable = _successful_main(main) and shadow["status"] == "OK"
        record = {"schema_version": 1, "record_type": "trial", "trial_id": trial_id,
                  "recorded_at": _now(), "fairness": FAIRNESS,
                  "personality_sha256": personality_hash, "query": request.message,
                  "recent_message_ids": context.get("recent_message_ids", []),
                  "recent_messages_sha256": _hash(context.get("recent_messages", [])),
                  "rag_evidence": context.get("historical_evidence", []),
                  "main": response["main"], "shadow": shadow, "votable": votable}
        await run_in_threadpool(append_arena_trial, record)
        response["evaluation"] = {"status": "STORED", "votable": votable}
    except Exception:
        pass
    return response
