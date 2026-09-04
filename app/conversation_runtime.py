from app.model_client import (
    ModelClientError,
    count_input_tokens,
    generate_chat_completion,
)
from app.working_context import build_working_context
from memory.dense_index import sync_dense_message_ids
from memory.store import add_message


SYSTEM_PROMPT = (
    "You are Corvus, a persistent personal AI. "
    "Use relevant historical evidence when it helps answer the user. "
    "Do not claim memories that are not present in the provided context."
)


def process_turn(
    session_id,
    user_content,
    add_message_fn=add_message,
    build_context_fn=build_working_context,
    count_tokens_fn=count_input_tokens,
    generate_fn=generate_chat_completion,
    dense_sync_fn=sync_dense_message_ids,
):
    """
    Execute one SQLite-first persistent conversation turn.
    """
    result = {
        "session_id": session_id,
        "user_message_id": None,
        "assistant_message_id": None,
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

    # 2. Build this turn's temporary Working Context.
    try:
        context = build_context_fn(
            session_id=session_id,
            current_user_message_id=user_message_id,
            current_user_content=user_content,
            system_prompt=SYSTEM_PROMPT,
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

    # 3. Ask the local model.
    try:
        reply = generate_fn(
            context["messages"]
        )
    except ModelClientError as exc:
        result["model_status"] = exc.code
        result["error"] = str(exc)
        return result

    result["model_status"] = "OK"
    result["reply"] = reply

    # 4. Assistant text becomes canonical only after SQLite commit.
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

    # 5. Dense state is derived and happens last.
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
