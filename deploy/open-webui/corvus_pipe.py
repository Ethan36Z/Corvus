"""
title: Corvus OW1
description: Text-only adapter to the authoritative Corvus conversation runtime.
version: 0.2.0
required_open_webui_version: 0.6.5
"""

import asyncio
import hashlib
import json
import math
import re
from typing import Literal
from uuid import UUID

import httpx
from pydantic import BaseModel, Field, StrictBool, field_validator


CORVUS_CHAT_URL = "http://127.0.0.1:8096/api/chat"
UNCERTAIN_RESULT = (
    "Corvus did not confirm this turn. It may already have been saved. "
    "Check Corvus before sending again; do not retry or regenerate automatically."
)


def arena_ui_payload(result):
    """Whitelist display data only; callers contain every comparison-only failure."""
    trial_id = result["trial_id"]
    if str(UUID(trial_id)) != trial_id or result["fairness"] != "BEST_EFFORT_PRE_TURN":
        raise ValueError("Invalid Arena identity")

    def elapsed(value):
        if value is None:
            return None
        if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
            raise ValueError("Invalid Arena timing")
        return value

    def evidence(rows, shadow=False):
        if not isinstance(rows, list) or len(rows) > 100:
            raise ValueError("Invalid Arena evidence")
        output = []
        for row in rows:
            text = row["text" if shadow else "content"]
            if not isinstance(text, str) or len(text) > 200000:
                raise ValueError("Invalid Arena evidence text")
            if shadow:
                source_id = row["source_id"]
                if not isinstance(source_id, str) or not source_id or len(source_id) > 256:
                    raise ValueError("Invalid Arena source ID")
                output.append({"source_id": "hindsight:" + source_id, "text": text})
            else:
                message_id = row["id"]
                if type(message_id) is not int or message_id < 1:
                    raise ValueError("Invalid canonical message ID")
                output.append({"message_id": message_id, "text": text})
        return output

    main, shadow = result["main"], result["shadow"]
    recall = shadow["recall"]
    error = shadow.get("error")
    if error not in (None, "HINDSIGHT_RECALL_UNAVAILABLE", "CANONICAL_CONTEXT_UNAVAILABLE",
                     "SHADOW_GENERATION_FAILED", "CANONICAL_TURN_FAILED"):
        error = "COMPARISON_UNAVAILABLE"
    payload = {
        "version": 1, "trial_id": trial_id, "fairness": result["fairness"],
        "main": {"status": main["status"]["overall"],
                 "retrieval_status": main["status"]["retrieval"],
                 "retrieval_ms": elapsed(main.get("historical_recall_elapsed_ms")),
                 "generation_ms": elapsed(main.get("generation_elapsed_ms")),
                 "evidence": evidence(main.get("retrieved_memories", []))},
        "shadow": {"status": shadow["status"], "recall_status": recall["status"],
                   "reply": shadow.get("reply"), "error_code": error,
                   "retrieval_ms": elapsed(recall.get("elapsed_ms")),
                   "generation_ms": elapsed(shadow.get("generation_elapsed_ms")),
                   "evidence": evidence(shadow.get("evidence", []), shadow=True)},
        "evaluation": {"status": result["evaluation"]["status"],
                       "votable": result["evaluation"]["votable"]},
    }
    if len(json.dumps(payload, allow_nan=False).encode("utf-8")) > 1000000:
        raise ValueError("Arena display payload too large")
    return payload


def validate_corvus_chat_url(value):
    """Accept only a literal loopback HTTP chat endpoint; never normalize URLs."""
    match = re.fullmatch(
        r"http://127\.0\.0\.1:([1-9][0-9]{0,4})/api/chat", value
    ) if isinstance(value, str) else None
    if match is None or int(match.group(1)) > 65535:
        raise ValueError(
            "Corvus endpoint must be http://127.0.0.1:<port>/api/chat "
            "with a port from 1 to 65535."
        )
    return value


def _identity(value):
    return isinstance(value, str) and bool(value) and value == value.strip()


def corvus_session_id(instance_id, user_id, chat_id):
    """Versioned, unambiguous mapping; never accept a socket session ID."""
    if not all(_identity(value) for value in (instance_id, user_id, chat_id)):
        raise ValueError("OW1 requires INSTANCE_ID, an authenticated user, and a saved chat.")
    try:
        # v0.6.5 saved chats use canonical UUIDs; local/temporary IDs fail closed.
        saved_chat = str(UUID(chat_id)) == chat_id
    except ValueError:
        saved_chat = False
    if not saved_chat:
        raise ValueError("OW1 requires a saved chat; temporary/local chats are unsupported.")
    identity = json.dumps(
        [instance_id, user_id, chat_id], ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    return "ow1:" + hashlib.sha256(identity).hexdigest()


def _reject_unsupported(source):
    # Inspect both the body and retained metadata: v0.6.5 pops feature/file/tool
    # fields before invoking a Pipe, and may already have transformed messages.
    for key in (
        "files", "attachments", "attachment_id", "images", "audio", "video",
        "tools", "tool_ids", "tool_servers", "tool_calls", "functions",
        "function_call", "function_calling", "tool_choice", "operation", "action",
        "regenerate", "branch", "parent_id", "parent_message_id", "continue",
    ):
        if source.get(key) not in (None, False, "", [], {}):
            raise ValueError("OW1 supports ordinary text turns only; this operation is unsupported.")
    features = source.get("features")
    if features is not None and (
        not isinstance(features, dict) or any(features.values())
    ):
        raise ValueError("OW1 does not support Open WebUI search, media, or tool features.")
    if source.get("modalities") not in (None, [], ["text"]):
        raise ValueError("OW1 supports text only.")
    if source.get("n", 1) != 1:
        raise ValueError("OW1 supports one response per turn.")


class Pipe:
    class Valves(BaseModel):
        CORVUS_CHAT_URL: str = Field(
            default=CORVUS_CHAT_URL,
            description="Admin-only HTTP loopback chat endpoint; use port 18096 for isolated acceptance.",
        )
        INSTANCE_ID: str = Field(
            default="", description="Required stable unique ID for this Open WebUI installation."
        )
        WEB_MODE: Literal["off", "on", "auto"] = Field(
            default="auto", description="Corvus web mode, controlled by the administrator."
        )
        TIMEOUT_SECONDS: float = Field(default=300, ge=1, le=600)
        ARENA_ENABLED: StrictBool = Field(
            default=False, description="Enable Memory A/B only in the isolated Lab installation."
        )

        @field_validator("CORVUS_CHAT_URL")
        @classmethod
        def validate_endpoint(cls, value):
            return validate_corvus_chat_url(value)

    def __init__(self):
        self.valves = self.Valves()

    async def pipe(
        self,
        body: dict,
        __user__: dict = None,
        __chat_id__: str = None,
        __metadata__: dict = None,
        __task__: str = None,
        __task_body__: dict = None,
        __files__: list = None,
        __tools__: dict = None,
        __event_emitter__=None,
    ) -> str:
        if not isinstance(body, dict):
            raise ValueError("OW1 requires a text chat request.")
        metadata_sources = [__metadata__, body.get("metadata")]
        for metadata in metadata_sources:
            if metadata is not None and not isinstance(metadata, dict):
                raise ValueError("OW1 requires valid chat metadata.")
        sources = [body] + [item for item in metadata_sources if item is not None]

        # Suppress *all* tasks, including unknown future task labels, before
        # identity validation or I/O. Empty output is local to Open WebUI.
        if __task__ is not None or __task_body__ is not None or any(
            source.get("task") is not None or source.get("task_body") is not None
            for source in sources
        ):
            return ""

        for source in sources:
            _reject_unsupported(source)
        if __files__ or __tools__:
            raise ValueError("OW1 does not support files or tools.")
        params = body.get("params")
        if params is not None:
            if not isinstance(params, dict):
                raise ValueError("OW1 requires valid request parameters.")
            _reject_unsupported(params)

        user_id = (__user__ or {}).get("id") if isinstance(__user__, dict) else None
        chat_ids = [__chat_id__] + [source.get("chat_id") for source in sources]
        chat_ids = [value for value in chat_ids if value is not None]
        chat_id = chat_ids[0] if chat_ids else None
        if any(value != chat_id for value in chat_ids) or any(
            source.get("user_id", user_id) != user_id for source in sources
        ):
            raise ValueError("OW1 received inconsistent chat identity.")
        session_id = corvus_session_id(self.valves.INSTANCE_ID, user_id, chat_id)
        if self.valves.WEB_MODE not in {"off", "on", "auto"}:
            raise ValueError("OW1 WEB_MODE must be off, on, or auto.")
        # Validate again because direct assignment can bypass Pydantic validators.
        # Request fields, metadata, and user valves never select a destination.
        chat_url = validate_corvus_chat_url(self.valves.CORVUS_CHAT_URL)
        arena_flag = (__metadata__ or {}).get("corvus_arena", False)
        if type(arena_flag) is not bool:
            raise ValueError("Memory A/B requires a boolean opt-in.")
        if arena_flag and (self.valves.ARENA_ENABLED is not True
                           or chat_url != "http://127.0.0.1:18096/api/chat"):
            raise ValueError("Memory A/B is not enabled for this Lab installation.")

        messages = body.get("messages")
        if not isinstance(messages, list) or not messages:
            raise ValueError("OW1 requires a current user text message.")
        for message in messages:
            if (
                not isinstance(message, dict)
                or message.get("role") not in ("system", "user", "assistant")
                or not isinstance(message.get("content"), str)
            ):
                raise ValueError("OW1 does not support media or tool messages.")
            _reject_unsupported(message)
        current = messages[-1]
        if current["role"] != "user" or not current["content"].strip():
            raise ValueError("OW1 requires a new, nonempty user text turn.")

        payload = {
            "session_id": session_id,
            "message": current["content"],
            "web_mode": self.valves.WEB_MODE,
        }
        if arena_flag:
            chat_url = "http://127.0.0.1:18096/api/arena/chat"
            payload.pop("web_mode")
        # No redirects, environment proxies, or HTTP transport retries. Corvus
        # can persist before the caller times out; OW1 has no idempotency key.
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(self.valves.TIMEOUT_SECONDS, connect=5),
                follow_redirects=False,
                trust_env=False,
                transport=httpx.AsyncHTTPTransport(retries=0),
            ) as client:
                response = await client.post(chat_url, json=payload)
        except httpx.TimeoutException:
            raise ValueError("Corvus request timed out. " + UNCERTAIN_RESULT) from None
        except httpx.HTTPError:
            raise ValueError("Corvus request failed. " + UNCERTAIN_RESULT) from None

        if response.status_code != 200:
            # Never include response.text, exception strings, or backend error fields.
            raise ValueError("Corvus returned an unsuccessful response. " + UNCERTAIN_RESULT)
        try:
            result = response.json()
        except (ValueError, UnicodeError):
            raise ValueError("Corvus returned an invalid response. " + UNCERTAIN_RESULT) from None
        if not isinstance(result, dict):
            raise ValueError("Corvus returned an invalid response. " + UNCERTAIN_RESULT)
        arena_result = result
        if arena_flag:
            result = result.get("main", {})
            if not isinstance(result, dict):
                raise ValueError("Corvus returned an invalid response. " + UNCERTAIN_RESULT)
        status = result.get("status")
        reply = result.get("reply")
        # Deterministic Web fallbacks are canonical replies without generation.
        # They still require this session, a confirmed assistant commit and NORMAL persistence.
        fallback_confirmed = (
            isinstance(status, dict)
            and not arena_flag
            and result.get("web_presentation_outcome") in ("SOURCES_WITH_LIMITATIONS", "SEARCH_FAILED")
            and result.get("web_acceptance_status") == "EVIDENCE_INSUFFICIENT"
            and status.get("model") == "NOT_CALLED"
        )
        if (
            result.get("session_id") != session_id
            or not isinstance(status, dict)
            or status.get("overall") not in ("OK", "DEGRADED")
            or (status.get("model") != "OK" and not fallback_confirmed)
            or status.get("persistence") != "NORMAL"
            or (fallback_confirmed and (type(result.get("assistant_message_id")) is not int
                                        or result["assistant_message_id"] <= 0))
            or not isinstance(reply, str)
            or not reply.strip()
        ):
            raise ValueError("Corvus did not return a confirmed reply. " + UNCERTAIN_RESULT)
        if arena_flag:
            # This side channel must never invalidate a successful canonical turn.
            # One emission attempt only; never retry the event or the chat POST.
            try:
                if __event_emitter__ is not None:
                    await asyncio.wait_for(__event_emitter__(
                        {"type": "corvus:arena:v1", "data": arena_ui_payload(arena_result)}
                    ), timeout=1.0)
            except (Exception, asyncio.CancelledError):
                pass
        return reply
