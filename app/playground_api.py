from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.conversation_runtime import process_turn
from app.attachment_upload import (
    AttachmentUploadEmptyError,
    AttachmentUploadTooLargeError,
    ingest_attachment_chunks,
)
from app.runtime_config import (
    ATTACHMENT_DEFAULT_RETENTION,
    ATTACHMENT_MAX_BYTES,
)
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


@app.post(
    "/api/attachments",
    status_code=201,
)
async def post_attachment(
    request: Request,
    filename: str = Query(
        ...,
        min_length=1,
        max_length=255,
    ),
):
    filename = filename.strip()

    if not filename:
        raise HTTPException(
            status_code=400,
            detail="filename must not be empty",
        )

    raw_content_length = request.headers.get(
        "content-length"
    )

    if raw_content_length is not None:
        try:
            content_length = int(
                raw_content_length
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail="invalid Content-Length",
            ) from exc

        if content_length < 0:
            raise HTTPException(
                status_code=400,
                detail="invalid Content-Length",
            )

        if content_length == 0:
            raise HTTPException(
                status_code=400,
                detail="attachment must not be empty",
            )

    media_type = (
        request.headers.get(
            "content-type",
            "application/octet-stream",
        )
        .split(";", 1)[0]
        .strip()
        .lower()
    )

    if not media_type:
        media_type = (
            "application/octet-stream"
        )

    if len(media_type) > 255:
        raise HTTPException(
            status_code=400,
            detail="Content-Type too long",
        )

    try:
        attachment = (
            await ingest_attachment_chunks(
                request.stream(),
                original_filename=filename,
                media_type=media_type,
                retention_class=(
                    ATTACHMENT_DEFAULT_RETENTION
                ),
                max_bytes=(
                    ATTACHMENT_MAX_BYTES
                ),
            )
        )

    except AttachmentUploadEmptyError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except AttachmentUploadTooLargeError as exc:
        raise HTTPException(
            status_code=413,
            detail=str(exc),
        ) from exc

    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return {
        "attachment_id": attachment["id"],
        "original_filename": attachment[
            "original_filename"
        ],
        "media_type": attachment[
            "media_type"
        ],
        "size_bytes": attachment[
            "size_bytes"
        ],
        "sha256": attachment[
            "sha256"
        ],
        "retention_class": attachment[
            "retention_class"
        ],
        "blob_status": attachment[
            "blob_status"
        ],
    }


class ChatRequest(BaseModel):
    session_id: str = "default"
    message: str
    attachment_id: str | None = None


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
        "attachment_id": result.get(
            "attachment_id"
        ),
        "attachment_status": result.get(
            "attachment_status",
            "NOT_REQUESTED",
        ),
        "recent_message_ids": result[
            "recent_message_ids"
        ],
        "historical_message_ids": historical_ids,
        "retrieved_memories": retrieved_memories,
        "input_tokens": result["input_tokens"],
        "status": {
            "overall": overall,
            "attachment": result.get(
                "attachment_status",
                "NOT_REQUESTED",
            ),
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
        "attachment_error": result.get(
            "attachment_error"
        ),
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
        "attachment_id": None,
        "attachment_status": "NOT_RUN",
        "recent_message_ids": [],
        "historical_message_ids": [],
        "retrieved_memories": [],
        "input_tokens": None,
        "status": {
            "overall": "FAILED",
            "attachment": "NOT_RUN",
            "retrieval": "NOT_RUN",
            "model": "NOT_CALLED",
            "persistence": "USER_PERSISTENCE_FAILED",
            "dense": "NOT_RUN",
        },
        "retrieval_error": None,
        "attachment_error": None,
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

    attachment_id = request.attachment_id

    if attachment_id is not None:
        attachment_id = attachment_id.strip()

        if not attachment_id:
            return JSONResponse(
                status_code=400,
                content=build_hard_failure_response(
                    session_id,
                    "attachment_id must not be empty",
                ),
            )

    try:
        result = process_turn(
            session_id=session_id,
            user_content=request.message,
            attachment_id=attachment_id,
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


def build_session_title(content, max_length=36):
    normalized = " ".join(
        (content or "").split()
    )

    if not normalized:
        return "New conversation"

    if len(normalized) <= max_length:
        return normalized

    return normalized[:max_length].rstrip() + "…"


@app.get("/api/sessions")
def get_sessions(
    limit: int = Query(
        default=50,
        ge=1,
        le=100,
    ),
):
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                m.session_id,
                COUNT(*) AS message_count,
                MIN(m.id) AS first_message_id,
                MAX(m.id) AS last_message_id,
                MIN(m.created_at) AS created_at,
                MAX(m.created_at) AS updated_at,
                (
                    SELECT first_user.content
                    FROM messages AS first_user
                    WHERE
                        first_user.session_id = m.session_id
                        AND first_user.role = 'user'
                    ORDER BY first_user.id ASC
                    LIMIT 1
                ) AS title_source
            FROM messages AS m
            GROUP BY m.session_id
            ORDER BY last_message_id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [
        {
            "session_id": row[0],
            "message_count": row[1],
            "first_message_id": row[2],
            "last_message_id": row[3],
            "created_at": row[4],
            "updated_at": row[5],
            "title": build_session_title(row[6]),
        }
        for row in rows
    ]


@app.get("/api/sessions/{session_id}")
def get_session(
    session_id: str,
    limit: int = Query(
        default=200,
        ge=1,
        le=500,
    ),
):
    session_id = session_id.strip()

    if not session_id:
        return JSONResponse(
            status_code=400,
            content={
                "error": "session_id must not be empty",
            },
        )

    with connect() as conn:
        total = conn.execute(
            """
            SELECT COUNT(*)
            FROM messages
            WHERE session_id = ?
            """,
            (session_id,),
        ).fetchone()[0]

        if total == 0:
            return JSONResponse(
                status_code=404,
                content={
                    "session_id": session_id,
                    "error": "session not found",
                },
            )

        rows = conn.execute(
            """
            SELECT
                id,
                session_id,
                role,
                content,
                created_at
            FROM messages
            WHERE session_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (
                session_id,
                limit,
            ),
        ).fetchall()

    rows.reverse()

    messages = [
        {
            "id": row[0],
            "session_id": row[1],
            "role": row[2],
            "content": row[3],
            "created_at": row[4],
        }
        for row in rows
    ]

    return {
        "session_id": session_id,
        "message_count": total,
        "returned_count": len(messages),
        "has_more": total > len(messages),
        "messages": messages,
    }


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
