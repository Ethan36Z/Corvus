from time import perf_counter

from app.model_client import (
    ModelClientError,
    count_input_tokens,
    generate_chat_completion,
    take_last_generation_timings,
)
from app.foreground_activity import track_foreground_generation
from app.working_context import build_working_context
from app.vision_input import (
    VisionInputError,
    build_vision_messages,
)
from app.transcription import (
    TranscriptionError,
    transcribe_attachment,
)
from app.web_evidence_prompt import (
    WebEvidencePromptError,
    pack_web_evidence,
)
from app.web_orchestration import (
    prepare_web_grounding,
)
from app.web_query_rewrite import (
    rewrite_web_query,
)
from app.web_intent_gate import (
    decide_web_intent,
)
from app.searxng_provider import (
    SearXNGProvider,
)
from app.ddgs_provider import (
    DDGSProvider,
)
from app.runtime_config import (
    TIMEZONE,
    WEB_MVP_ENABLED,
    WEB_PROVIDER,
)
from datetime import datetime
from app.web_mvp import prepare_web_mvp, failed_preparation, present_grounded_answer, grounded_citation_counts

from memory.attachments import (
    link_attachment_to_message,
)
from memory.dense_index import sync_dense_message_ids
from memory.web_evidence import (
    record_web_evidence_batch,
)
from memory.store import add_message
from personality.runtime import compile_personality_system_prompt


VOICE_TRANSCRIPT_SYSTEM_NOTE = (
    "The current user turn was received by Corvus as spoken audio. "
    "The user-facing text for this turn is an STT transcript produced "
    "by the speech-recognition layer. Respond to the spoken content "
    "normally, but allow for possible transcription errors. Do not "
    "claim that Corvus cannot process audio merely because this model "
    "component receives the transcript as text."
)


def _current_time():
    return datetime.now(TIMEZONE)


def current_date_note(now):
    """One line of request-time date context; computed per turn, never cached."""
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("current time must be timezone-aware")
    offset = now.strftime("%z")
    zone = getattr(now.tzinfo, "key", None) or now.tzname() or "UTC"
    return (
        f"Current date: {now.strftime('%Y-%m-%d')} ({now.strftime('%A')}), "
        f"time zone {zone} (UTC{offset[:3]}:{offset[3:]}). "
        "Use it to judge recency. When web evidence is supplied, prefer it "
        "over your training knowledge about what is current; do not claim "
        "that something is unreleased or the latest unless evidence supports it."
    )


def _build_default_web_provider(
    attempt,
):
    if WEB_PROVIDER == "SEARXNG":
        return SearXNGProvider(
            category=attempt.category,
            language=attempt.language,
            engine_bang=attempt.engine_bang,
            time_range=attempt.time_range,
        )

    region = (
        "cn-zh"
        if (
            attempt.language is not None
            and str(
                attempt.language
            ).lower().startswith("zh")
        )
        else "us-en"
    )

    return DDGSProvider(
        category=attempt.category,
        region=region,
        time_range=attempt.time_range,
    )


def process_turn(
    session_id,
    user_content,
    add_message_fn=add_message,
    build_context_fn=build_working_context,
    count_tokens_fn=count_input_tokens,
    generate_fn=generate_chat_completion,
    dense_sync_fn=sync_dense_message_ids,
    system_prompt_fn=compile_personality_system_prompt,
    attachment_id=None,
    link_attachment_fn=link_attachment_to_message,
    build_vision_messages_fn=build_vision_messages,
    model_user_content=None,
    attachment_mode="vision",
    transcribe_attachment_fn=transcribe_attachment,
    used_web_evidence=None,
    pack_web_evidence_fn=pack_web_evidence,
    record_web_evidence_batch_fn=(
        record_web_evidence_batch
    ),
    web_mode="off",
    prepare_web_grounding_fn=(
        prepare_web_grounding
    ),
    web_provider_builder_fn=(
        _build_default_web_provider
    ),
    web_query_rewrite_fn=(
        rewrite_web_query
    ),
    web_intent_decide_fn=(
        decide_web_intent
    ),
    web_mvp_enabled=WEB_MVP_ENABLED,
    web_requirements=None,
    web_source_facts_fn=lambda page: None,
    prepare_web_mvp_fn=prepare_web_mvp,
    now_fn=_current_time,
):
    """
    Execute one SQLite-first persistent conversation turn.
    """
    turn_started = perf_counter()
    stage_ms = {}  # W2-a diagnostics; reported for Web turns only

    if attachment_id is not None:
        attachment_id = str(
            attachment_id
        ).strip()

    if model_user_content is None:
        model_user_content = user_content

    attachment_mode = str(
        attachment_mode
    ).strip().lower()

    if attachment_mode not in {
        "vision",
        "voice",
        "provenance_only",
    }:
        raise ValueError(
            "invalid attachment_mode"
        )

    web_mode = str(
        web_mode
    ).strip().lower()

    if web_mode not in {
        "off",
        "on",
        "auto",
    }:
        raise ValueError(
            "invalid web_mode"
        )

    if (
        attachment_mode == "voice"
        and attachment_id is None
    ):
        raise ValueError(
            "voice mode requires attachment_id"
        )

    result = {
        "session_id": session_id,
        "user_message_id": None,
        "assistant_message_id": None,
        "attachment_id": attachment_id,
        "attachment_status": (
            "NOT_REQUESTED"
            if attachment_id is None
            else "NOT_RUN"
        ),
        "attachment_error": None,
        "transcription_status": (
            "NOT_RUN"
            if attachment_mode == "voice"
            else "NOT_REQUESTED"
        ),
        "transcription_error": None,
        "transcript_artifact_id": None,
        "transcript": None,
        "web_mode": web_mode,
        "web_intent_decision": (
            "WEB"
            if web_mode == "on"
            else (
                "NO_WEB"
                if web_mode == "off"
                else "NOT_RUN"
            )
        ),
        "web_intent_source": (
            "FORCED_ON"
            if web_mode == "on"
            else (
                "FORCED_OFF"
                if web_mode == "off"
                else "NOT_RUN"
            )
        ),
        "web_intent_signal": None,
        "web_intent_error": None,
        "web_query_rewrite_status": (
            "NOT_REQUESTED"
            if web_mode == "off"
            else "NOT_RUN"
        ),
        "web_query_rewrite_error": None,
        "web_search_query": None,
        "web_grounding_status": (
            "NOT_REQUESTED"
            if web_mode == "off"
            else "NOT_RUN"
        ),
        "web_grounding_error": None,
        "web_grounding_selected_result_id": None,
        "web_evidence_status": "NOT_REQUESTED",
        "web_evidence_error": None,
        "web_evidence_refs": [],
        "web_evidence_prompt_chars": 0,
        "web_evidence_persisted_count": 0,
        "recent_message_ids": [],
        "historical_message_ids": [],
        "historical_recall_elapsed_ms": None,
        "input_tokens": None,
        "retrieval_status": "NOT_RUN",
        "retrieval_error": None,
        "model_status": "NOT_CALLED",
        "dense_status": "NOT_RUN",
        "persistence_status": "NORMAL",
        "reply": None,
        "error": None,
    }

    mvp_active = bool(web_mvp_enabled) and attachment_id is None
    mvp_prepared = None
    deterministic_reply = None

    # 1. Canonical user evidence comes first.
    user_message_id = add_message_fn(
        session_id,
        "user",
        user_content,
    )

    result["user_message_id"] = user_message_id

    # 2. Link attachment provenance only after the
    # canonical user message exists.
    if attachment_id is not None:
        try:
            link_attachment_fn(
                user_message_id,
                attachment_id,
                ordinal=0,
            )
        except Exception as exc:
            result["attachment_status"] = (
                "LINK_FAILED"
            )
            result["attachment_error"] = str(
                exc
            )
            result["error"] = str(exc)
            return result

        result["attachment_status"] = "LINKED"

    # 3. Voice perception happens only after the
    # canonical message and raw attachment provenance
    # are safely persisted.
    if (
        attachment_id is not None
        and attachment_mode == "voice"
    ):
        try:
            transcription = (
                transcribe_attachment_fn(
                    attachment_id
                )
            )
        except TranscriptionError as exc:
            result["transcription_status"] = (
                exc.code
            )
            result["transcription_error"] = str(
                exc
            )
            result["error"] = str(exc)
            return result
        except Exception as exc:
            result["transcription_status"] = (
                "TRANSCRIPTION_FAILED"
            )
            result["transcription_error"] = str(
                exc
            )
            result["error"] = str(exc)
            return result

        model_user_content = transcription[
            "transcript"
        ]

        result["transcription_status"] = "OK"
        result["transcript"] = (
            transcription["transcript"]
        )
        result["transcript_artifact_id"] = (
            transcription["artifact_id"]
        )

    # 4. Resolve Web intent exactly once for this turn.
    #
    # Forced modes bypass the classifier entirely.
    # Auto mode uses deterministic high-confidence
    # signals first and invokes the model only when
    # the request remains ambiguous.
    if web_mode == "on":
        web_should_ground = True

    elif web_mode == "off":
        web_should_ground = False

    else:
        try:
            web_intent = (
                web_intent_decide_fn(
                    model_user_content
                )
            )

            decision = str(
                web_intent.decision
            ).strip().upper()

            source = str(
                web_intent.source
            ).strip()

            signal = getattr(
                web_intent,
                "signal",
                None,
            )

            intent_error = getattr(
                web_intent,
                "error",
                None,
            )

            if decision not in {
                "WEB",
                "NO_WEB",
            }:
                raise ValueError(
                    "invalid Web intent decision"
                )

        except Exception as exc:
            decision = "NO_WEB"
            source = "DECISION_FAILED"
            signal = None
            intent_error = str(exc)

        result[
            "web_intent_decision"
        ] = decision

        result[
            "web_intent_source"
        ] = source

        result[
            "web_intent_signal"
        ] = signal

        result[
            "web_intent_error"
        ] = intent_error

        web_should_ground = (
            decision == "WEB"
        )

        if not web_should_ground:
            result[
                "web_query_rewrite_status"
            ] = "NOT_REQUESTED"

            result[
                "web_grounding_status"
            ] = "NOT_REQUESTED"

            result[
                "web_evidence_status"
            ] = "NOT_REQUESTED"

    # 5. Normalize optional preselected Web evidence.
    # Existing callers may still provide an already
    # selected evidence tuple directly.
    try:
        used_web_evidence = tuple(
            used_web_evidence or ()
        )
    except TypeError as exc:
        result["web_evidence_status"] = (
            "WEB_EVIDENCE_INPUT_INVALID"
        )
        result["web_evidence_error"] = str(exc)
        result["error"] = str(exc)
        return result

    # 5. Explicit Web mode performs discovery only
    # after canonical user evidence is safe.
    #
    # For voice turns, model_user_content is the STT
    # derived perception, while the canonical message
    # remains the raw-audio marker.
    if web_should_ground or (mvp_active and result["web_intent_source"] == "DECISION_FAILED"):
        if used_web_evidence:
            message = (
                "Web grounding mode cannot be combined "
                "with preselected used_web_evidence"
            )

            result["web_grounding_status"] = (
                "WEB_GROUNDING_INPUT_CONFLICT"
            )
            result["web_grounding_error"] = (
                message
            )
            result["web_evidence_status"] = (
                "WEB_EVIDENCE_INPUT_CONFLICT"
            )
            result["error"] = message
            return result

        search_query = model_user_content

        if mvp_active:
            result["web_query_rewrite_status"] = "NOT_REQUESTED"
        else:
            try:
                rewritten_query = (
                    web_query_rewrite_fn(
                        model_user_content
                    )
                )

                if not isinstance(
                    rewritten_query,
                    str,
                ):
                    raise ValueError(
                        "Web query rewrite must "
                        "return text"
                    )

                rewritten_query = " ".join(
                    rewritten_query.split()
                )

                if not rewritten_query:
                    raise ValueError(
                        "Web query rewrite must "
                        "not be empty"
                    )

                search_query = (
                    rewritten_query
                )

                result[
                    "web_query_rewrite_status"
                ] = "OK"

            except Exception as exc:
                result[
                    "web_query_rewrite_status"
                ] = "FALLBACK_ORIGINAL"

                result[
                    "web_query_rewrite_error"
                ] = str(exc)

                search_query = (
                    model_user_content
                )

        result["web_search_query"] = (
            search_query
        )

        try:
            if mvp_active:
                if result["web_intent_source"] == "DECISION_FAILED":
                    result["web_intent_error"] = "WEB_INTENT_FAILED"
                    mvp_prepared = failed_preparation(search_query, "WEB_INTENT_FAILED")
                else:
                    try:
                        mvp_prepared = prepare_web_mvp_fn(
                            search_query, provider_builder=web_provider_builder_fn,
                            requirements=web_requirements, source_facts=web_source_facts_fn,
                        )
                    except Exception:
                        # No backend exception text or private data enters the reply.
                        mvp_prepared = failed_preparation(search_query)
                grounding = mvp_prepared
                deterministic_reply = mvp_prepared.deterministic_reply
                result["web_answer_basis"] = mvp_prepared.answer_basis
                result["web_acceptance_status"] = mvp_prepared.evidence_status
                result["web_coverage_missing"] = list(mvp_prepared.missing)
                result["web_discovery_status"] = mvp_prepared.retrieval_status
                result["web_sources"] = [
                    {"url": source.url, "identity": source.identity,
                     "refs": list(source.refs), "verification": source.verification}
                    for source in mvp_prepared.sources
                ]
            else:
                grounding = prepare_web_grounding_fn(
                    search_query, provider_builder=web_provider_builder_fn,
                )

            grounding_status = str(
                grounding.status
            )

            grounding_selected_result_id = (
                grounding.selected_result_id
            )

            grounding_evidence = tuple(
                grounding.used_web_evidence
            )

        except Exception as exc:
            result["web_grounding_status"] = (
                "WEB_GROUNDING_FAILED"
            )
            result["web_grounding_error"] = str(
                exc
            )
            result["web_evidence_status"] = (
                "NOT_AVAILABLE"
            )
            result["error"] = str(exc)
            return result

        result["web_grounding_status"] = (
            grounding_status
        )
        result[
            "web_grounding_selected_result_id"
        ] = grounding_selected_result_id

        if (
            deterministic_reply is None
            and (grounding_status != "READY" or not grounding_evidence)
        ):
            message = (
                "Web grounding did not produce "
                "usable evidence: "
                f"{grounding_status}"
            )

            result["web_grounding_error"] = (
                message
            )
            result["web_evidence_status"] = (
                "NOT_AVAILABLE"
            )
            result["error"] = message
            return result

        used_web_evidence = (
            grounding_evidence
        )

    # 6. Pack optional current-turn Web evidence.
    web_evidence_content = None

    if used_web_evidence:
        try:
            packed_web_evidence = (
                pack_web_evidence_fn(
                    used_web_evidence
                )
            )
        except WebEvidencePromptError as exc:
            result["web_evidence_status"] = (
                exc.code
            )
            result["web_evidence_error"] = str(
                exc
            )
            result["error"] = str(exc)
            return result
        except Exception as exc:
            result["web_evidence_status"] = (
                "WEB_EVIDENCE_PACKING_FAILED"
            )
            result["web_evidence_error"] = str(
                exc
            )
            result["error"] = str(exc)
            return result

        web_evidence_content = (
            packed_web_evidence.content
        )

        result["web_evidence_status"] = (
            "PREPARED"
        )
        result["web_evidence_refs"] = list(
            packed_web_evidence.evidence_refs
        )
        result[
            "web_evidence_prompt_chars"
        ] = packed_web_evidence.packed_chars

    if deterministic_reply is None:
        # 5. Build this turn's temporary Working Context.
        try:
            system_prompt = (
                f"{system_prompt_fn()}\n\n"
                f"{current_date_note(now_fn())}"
            )

            if attachment_mode == "voice":
                system_prompt = (
                    f"{system_prompt}\n\n"
                    f"{VOICE_TRANSCRIPT_SYSTEM_NOTE}"
                )

            context_kwargs = {
                "session_id": session_id,
                "current_user_message_id": (
                    user_message_id
                ),
                "current_user_content": (
                    model_user_content
                ),
                "system_prompt": system_prompt,
                "count_tokens": count_tokens_fn,
            }

            if web_evidence_content:
                context_kwargs[
                    "web_evidence_content"
                ] = web_evidence_content
                # Web source boundary: prior model output (direct or
                # derived) never enters a web-grounded turn as history.
                context_kwargs["web_grounded"] = True

            context_started = perf_counter()
            context = build_context_fn(
                **context_kwargs
            )
            stage_ms["context_ms"] = round((perf_counter() - context_started) * 1000, 1)
        except ModelClientError as exc:
            result["model_status"] = exc.code
            result["error"] = str(exc)
            return result
        except ValueError as exc:
            result["model_status"] = "CONTEXT_INVALID"
            result["error"] = str(exc)
            return result
        except Exception as exc:
            result["model_status"] = "CONTEXT_FAILED"
            result["error"] = str(exc)
            return result

        result["recent_message_ids"] = context[
            "recent_message_ids"
        ]
        result["historical_message_ids"] = context[
            "historical_message_ids"
        ]
        result["input_tokens"] = context[
            "input_tokens"
        ]
        result["retrieval_status"] = context.get(
            "retrieval_status",
            "OK",
        )
        result["retrieval_error"] = context.get(
            "retrieval_error"
        )
        result["historical_recall_elapsed_ms"] = context.get(
            "historical_recall_elapsed_ms"
        )

        # 4. Keep retrieval/context text-only. Only
        # the final model-facing current user message
        # becomes multimodal.
        model_messages = context["messages"]

        if (
            attachment_id is not None
            and attachment_mode == "vision"
        ):
            try:
                vision_input = (
                    build_vision_messages_fn(
                        model_messages,
                        attachment_id,
                    )
                )
            except VisionInputError as exc:
                result["attachment_status"] = (
                    "VISION_INPUT_FAILED"
                )
                result["attachment_error"] = str(
                    exc
                )
                result["model_status"] = (
                    "VISION_INPUT_INVALID"
                )
                result["error"] = str(exc)
                return result
            except Exception as exc:
                result["attachment_status"] = (
                    "VISION_INPUT_FAILED"
                )
                result["attachment_error"] = str(
                    exc
                )
                result["model_status"] = (
                    "VISION_INPUT_FAILED"
                )
                result["error"] = str(exc)
                return result

            model_messages = vision_input[
                "messages"
            ]

            result["attachment_status"] = "READY"

        # 5. Ask the existing local model.
        take_last_generation_timings()  # never attribute a stale value
        generation_started = perf_counter()
        try:
            with track_foreground_generation():
                reply = generate_fn(
                    model_messages
                )
        except ModelClientError as exc:
            result["model_status"] = exc.code
            result["error"] = str(exc)
            return result
        finally:
            stage_ms["generation_ms"] = round((perf_counter() - generation_started) * 1000, 1)
        server = take_last_generation_timings()
        if server:
            compute = float(server.get("prompt_ms") or 0) + float(server.get("predicted_ms") or 0)
            stage_ms["model_compute_ms"] = round(compute, 1)
            # Wall time not spent computing: queueing behind other users of
            # the shared llama server (e.g. Hindsight), HTTP and decoding.
            stage_ms["model_wait_ms"] = round(max(0.0, stage_ms["generation_ms"] - compute), 1)
            stage_ms["prompt_tokens"] = server.get("prompt_n")
            stage_ms["completion_tokens"] = server.get("predicted_n")

    else:
        reply = deterministic_reply

    if mvp_prepared is not None and deterministic_reply is None:
        try:
            citation_counts = grounded_citation_counts(reply, mvp_prepared)
            # The user's own words in this turn's context may support
            # personal anchors (e.g. their hardware); nothing else may.
            user_texts = [model_user_content, user_content] + [
                row.get("content", "")
                for key in ("historical_evidence", "recent_messages")
                for row in (context.get(key) or [])
                if isinstance(row, dict) and row.get("role") == "user"
            ]
            support = {}
            reply = present_grounded_answer(
                reply, mvp_prepared, chinese=any('\u3400' <= ch <= '\u9fff' for ch in user_content),
                user_texts=user_texts, diagnostics=support,
            )
            citation_counts.update(support)
        except Exception:
            result["model_status"] = "WEB_PRESENTATION_FAILED"
            result["error"] = "Web source presentation failed; no automatic retry."
            return result
        result.update(citation_counts)
    if mvp_prepared is not None:
        result["web_timings_ms"] = {
            **(getattr(mvp_prepared, "timings", None) or {}),
            **stage_ms,
            # Until the reply is ready, before the canonical commit.
            "answer_ready_ms": round((perf_counter() - turn_started) * 1000, 1),
        }
    result["model_status"] = "OK" if deterministic_reply is None else "NOT_CALLED"
    result["reply"] = reply

    if used_web_evidence:
        result["web_evidence_status"] = "USED"
    elif deterministic_reply is not None:
        result["web_evidence_status"] = "NOT_USED"

    if (
        attachment_id is not None
        and attachment_mode == "vision"
    ):
        result["attachment_status"] = "USED"

    # 6. Assistant text becomes canonical only after SQLite commit.
    try:
        assistant_message_id = add_message_fn(
            session_id,
            "assistant",
            reply,
        )
    except Exception as exc:
        result["persistence_status"] = (
            "ASSISTANT_PERSISTENCE_FAILED"
        )
        result["error"] = str(exc)
        return result

    result["assistant_message_id"] = (
        assistant_message_id
    )
    # Presentation outcome is confirmed only after the canonical assistant commit.
    if mvp_prepared is not None:
        result["web_presentation_outcome"] = mvp_prepared.outcome

    # 7. Persist exactly the same Used Web Evidence
    # set that was supplied to the successful model
    # call. Assistant canonical evidence remains
    # committed if provenance persistence degrades.
    if used_web_evidence:
        try:
            evidence_items = [
                {
                    "ordinal": item.ordinal,
                    "source_url": (
                        item.source_url
                    ),
                    "source_title": (
                        item.source_title
                    ),
                    "excerpt": item.excerpt,
                }
                for item in used_web_evidence
            ]

            persisted_web_evidence = (
                record_web_evidence_batch_fn(
                    assistant_message_id,
                    evidence_items,
                )
            )
        except Exception as exc:
            result["web_evidence_status"] = (
                "USED_PERSISTENCE_FAILED"
            )
            result["web_evidence_error"] = str(
                exc
            )
            result["persistence_status"] = (
                "WEB_EVIDENCE_PERSISTENCE_DEGRADED"
            )
            result["error"] = str(exc)
        else:
            result["web_evidence_status"] = (
                "PERSISTED"
            )
            result[
                "web_evidence_persisted_count"
            ] = len(
                persisted_web_evidence
            )

    # 8. Dense state is derived and happens last.
    try:
        dense_sync_fn(
            [
                user_message_id,
                assistant_message_id,
            ]
        )
    except Exception as exc:
        result["dense_status"] = "DEGRADED"
        result["error"] = str(exc)
        return result

    result["dense_status"] = "OK"

    return result
