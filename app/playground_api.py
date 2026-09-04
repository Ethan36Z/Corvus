from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.conversation_runtime import process_turn
from app.model_client import (
    ModelClientError,
    check_model_health,
)
from app.runtime_lifecycle import recover_dense_tail
from memory.store import connect


@asynccontextmanager
async def lifespan(app):
    app.state.startup_recovery = recover_dense_tail()
    yield


app = FastAPI(
    title="Corvus Playground API",
    lifespan=lifespan,
)


def build_health_status(
    app,
    model_health_fn=check_model_health,
):
    recovery = getattr(
        app.state,
        "startup_recovery",
        {
            "status": "NOT_RUN",
            "caught_up": False,
            "batches": 0,
            "indexed": 0,
            "progress_after": None,
            "error": None,
        },
    )

    try:
        model_health_fn()
    except ModelClientError as exc:
        model = {
            "status": exc.code,
            "error": str(exc),
        }
    else:
        model = {
            "status": "OK",
            "error": None,
        }

    if (
        model["status"] == "OK"
        and recovery["status"] == "OK"
    ):
        status = "OK"
    else:
        status = "DEGRADED"

    return {
        "status": status,
        "service": "OK",
        "model": model,
        "dense_recovery": recovery,
    }


@app.get("/api/health")
def get_health():
    return build_health_status(app)


class ChatRequest(BaseModel):
    session_id: str = "default"
    message: str


def load_messages_by_ids(message_ids):
    message_ids = [
        int(message_id)
        for message_id in message_ids
    ]

    if not message_ids:
        return []

    placeholders = ",".join(
        "?"
        for _ in message_ids
    )

    with connect() as conn:
        rows = conn.execute(
            f"""
            SELECT
                id,
                session_id,
                role,
                content,
                created_at
            FROM messages
            WHERE id IN ({placeholders})
            """,
            message_ids,
        ).fetchall()

    by_id = {
        row[0]: {
            "id": row[0],
            "session_id": row[1],
            "role": row[2],
            "content": row[3],
            "created_at": row[4],
        }
        for row in rows
    }

    return [
        by_id[message_id]
        for message_id in message_ids
        if message_id in by_id
    ]


def build_chat_response(
    result,
    load_messages_fn=load_messages_by_ids,
):
    historical_ids = result[
        "historical_message_ids"
    ]

    inspection_error = None

    try:
        retrieved = load_messages_fn(
            historical_ids
        )
    except Exception as exc:
        retrieved = []
        inspection_error = str(exc)

    retrieved_memories = [
        {
            "rank": rank,
            **row,
        }
        for rank, row in enumerate(
            retrieved,
            start=1,
        )
    ]

    assistant_persisted = (
        result["assistant_message_id"]
        is not None
    )

    if not assistant_persisted:
        overall = "FAILED"
    elif (
        result["retrieval_status"] != "OK"
        or result["model_status"] != "OK"
        or result["persistence_status"] != "NORMAL"
        or result["dense_status"] != "OK"
        or inspection_error is not None
    ):
        overall = "DEGRADED"
    else:
        overall = "OK"

    return {
        "reply": result["reply"],
        "session_id": result["session_id"],
        "user_message_id": result[
            "user_message_id"
        ],
        "assistant_message_id": result[
            "assistant_message_id"
        ],
        "recent_message_ids": result[
            "recent_message_ids"
        ],
        "historical_message_ids": historical_ids,
        "retrieved_memories": retrieved_memories,
        "input_tokens": result["input_tokens"],
        "status": {
            "overall": overall,
            "retrieval": result[
                "retrieval_status"
            ],
            "model": result["model_status"],
            "persistence": result[
                "persistence_status"
            ],
            "dense": result["dense_status"],
            "inspection": (
                "DEGRADED"
                if inspection_error is not None
                else "OK"
            ),
        },
        "inspection_error": inspection_error,
        "retrieval_error": result[
            "retrieval_error"
        ],
        "error": result["error"],
    }


def build_hard_failure_response(
    session_id,
    error,
):
    return {
        "reply": None,
        "session_id": session_id,
        "user_message_id": None,
        "assistant_message_id": None,
        "recent_message_ids": [],
        "historical_message_ids": [],
        "retrieved_memories": [],
        "input_tokens": None,
        "status": {
            "overall": "FAILED",
            "retrieval": "NOT_RUN",
            "model": "NOT_CALLED",
            "persistence": "USER_PERSISTENCE_FAILED",
            "dense": "NOT_RUN",
        },
        "retrieval_error": None,
        "error": str(error),
    }


@app.post("/api/chat")
def post_chat(request: ChatRequest):
    session_id = request.session_id.strip()

    if not session_id:
        return JSONResponse(
            status_code=400,
            content=build_hard_failure_response(
                "",
                "session_id must not be empty",
            ),
        )

    if not request.message.strip():
        return JSONResponse(
            status_code=400,
            content=build_hard_failure_response(
                session_id,
                "message must not be empty",
            ),
        )

    try:
        result = process_turn(
            session_id=session_id,
            user_content=request.message,
        )
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=build_hard_failure_response(
                session_id,
                exc,
            ),
        )

    return build_chat_response(
        result
    )


@app.get("/api/evidence")
def get_evidence():
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT id, session_id, role, content, created_at
            FROM messages
            ORDER BY id DESC
            LIMIT 100
            """
        ).fetchall()

    return [
        {
            "id": row[0],
            "session_id": row[1],
            "role": row[2],
            "content": row[3],
            "created_at": row[4],
        }
        for row in rows
    ]

from memory.assertion_store import load_unsuperseded_assertions


@app.get("/api/assertions")
def get_assertions():
    with connect() as conn:
        rows = load_unsuperseded_assertions(conn)

    return [
        {
            "id": row[0],
            "subject": row[1],
            "predicate": row[2],
            "object": row[3],
            "provenance": row[4],
            "authority": row[5],
            "modality": row[6],
            "temporal_kind": row[7],
            "time_start": row[8],
            "time_end": row[9],
            "temporal_granularity": row[10],
            "recorded_at": row[11],
        }
        for row in rows
    ]
