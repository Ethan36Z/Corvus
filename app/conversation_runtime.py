from app.model_client import (
    ModelClientError,
    count_input_tokens,
    generate_chat_completion,
)
from app.working_context import build_working_context
from app.vision_input import (
    VisionInputError,
    build_vision_messages,
)
from memory.attachments import (
    link_attachment_to_message,
)
from memory.dense_index import sync_dense_message_ids
from memory.store import add_message
from personality.runtime import compile_personality_system_prompt


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
):
    """
    Execute one SQLite-first persistent conversation turn.
    """
    if attachment_id is not None:
        attachment_id = str(
            attachment_id
        ).strip()

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
        "recent_message_ids": [],
        "historical_message_ids": [],
        "input_tokens": None,
        "retrieval_status": "NOT_RUN",
        "retrieval_error": None,
        "model_status": "NOT_CALLED",
        "dense_status": "NOT_RUN",
        "persistence_status": "NORMAL",
        "reply": None,
        "error": None,
    }

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

    # 3. Build this turn's temporary Working Context.
    try:
        system_prompt = system_prompt_fn()
        context = build_context_fn(
            session_id=session_id,
            current_user_message_id=user_message_id,
            current_user_content=user_content,
            system_prompt=system_prompt,
            count_tokens=count_tokens_fn,
        )
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

    # 4. Keep retrieval/context text-only. Only
    # the final model-facing current user message
    # becomes multimodal.
    model_messages = context["messages"]

    if attachment_id is not None:
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
    try:
        reply = generate_fn(
            model_messages
        )
    except ModelClientError as exc:
        result["model_status"] = exc.code
        result["error"] = str(exc)
        return result

    result["model_status"] = "OK"
    result["reply"] = reply

    if attachment_id is not None:
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

    # 7. Dense state is derived and happens last.
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
