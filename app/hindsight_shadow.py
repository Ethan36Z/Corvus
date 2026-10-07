"""Lab-only derived recall/retain after a confirmed text reply is sent.

One background task recalls, durably records the comparison, then retains the
canonical completed turn. Nothing here enters active retrieval or the reply.
"""

import asyncio
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
import fcntl
import json
import logging
import math
import os
from pathlib import Path
import sqlite3
import stat
import time

import httpx
from starlette.concurrency import run_in_threadpool

from memory.config import DATA_DIR, PROJECT_ROOT
from memory import store


LAB_PROJECT_ROOT = Path("/home/ethan/srv/apps/corvus-lab")
LAB_DATA_DIR = Path("/home/ethan/srv/data/corvus/lab")
BASE_URL = "http://127.0.0.1:8888"
BANK = "corvus-hindsight-lab-v1"
DEADLINE_SECONDS = 10
# Provisional: two local 180s LLM calls (modest chunking) + 30s DB/embedding
# overhead. Bulk benchmark ingestion took 2027s/18 operations, not a turn SLA.
# This bounds our wait; a timeout cannot prove the server stopped writing.
RETAIN_DEADLINE_SECONDS = 390
LOG_NAME = "h1-shadow-recall.jsonl"
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ShadowTurn:
    session_id: str
    user_message_id: int
    assistant_message_id: int
    query: str
    historical_message_ids: tuple[int, ...]


def lab_shadow_enabled():
    return PROJECT_ROOT == LAB_PROJECT_ROOT and DATA_DIR == LAB_DATA_DIR


def _normalize(body):
    if not isinstance(body, dict) or not isinstance(body.get("results"), list):
        raise ValueError("invalid response")
    normalized = []
    for rank, row in enumerate(body["results"], start=1):
        if (
            not isinstance(row, dict)
            or not isinstance(row.get("id"), str)
            or not row["id"]
            or not isinstance(row.get("text"), str)
        ):
            raise ValueError("invalid result")
        scores = row.get("scores")
        score = None
        if scores is not None:
            if not isinstance(scores, dict):
                raise ValueError("invalid scores")
            score = scores.get("final")
            if (
                isinstance(score, bool)
                or not isinstance(score, (int, float))
                or not math.isfinite(score)
            ):
                raise ValueError("invalid final score")
        metadata = {
            key: row[key]
            for key in (
                "type", "context", "entities", "document_id", "chunk_id",
                "mentioned_at", "occurred_start", "occurred_end", "tags",
                "source_fact_ids", "metadata", "scores",
            )
            if key in row
        }
        normalized.append({
            "rank": rank,
            "text": row["text"],
            "score": score,
            "source_id": row["id"],
            "metadata": metadata,
        })
    return normalized


async def recall(query):
    """One real-contract request, with no retries and a total HTTP deadline."""
    started = time.perf_counter()
    result = {
        "provider": "hindsight",
        "bank": BANK,
        "status": "ERROR",
        "elapsed_ms": 0,
        "results": [],
        "error": None,
    }
    try:
        async with asyncio.timeout(DEADLINE_SECONDS):
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(DEADLINE_SECONDS, connect=2),
                trust_env=False,
                follow_redirects=False,
                transport=httpx.AsyncHTTPTransport(retries=0),
            ) as client:
                response = await client.post(
                    f"{BASE_URL}/v1/default/banks/{BANK}/memories/recall",
                    json={
                        "query": query,
                        "budget": "mid",
                        "max_tokens": 4096,
                        "trace": False,
                        "include": {"entities": None, "chunks": None, "source_facts": None},
                    },
                )
                response.raise_for_status()
                results = _normalize(response.json())
            if time.perf_counter() - started >= DEADLINE_SECONDS:
                raise TimeoutError
        result["status"] = "OK"
        result["results"] = results
    except (TimeoutError, httpx.TimeoutException):
        result["status"] = "TIMEOUT"
        result["error"] = "DEADLINE_EXCEEDED"
    except httpx.HTTPStatusError as exc:
        result["error"] = f"HTTP_{exc.response.status_code}"
    except httpx.RequestError:
        result["error"] = "TRANSPORT_ERROR"
    except ValueError:
        result["error"] = "INVALID_RESPONSE"
    except Exception:
        result["error"] = "UNEXPECTED_ERROR"
    result["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 3)
    return result


def append_observation(record):
    """Durably append one derived record under flock, including its directory."""
    if not lab_shadow_enabled() or DATA_DIR.resolve() != LAB_DATA_DIR:
        raise ValueError("shadow log is Lab only")
    data = (json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
    fd = os.open(
        DATA_DIR / LOG_NAME,
        os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_CLOEXEC | os.O_NOFOLLOW,
        0o600,
    )
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError("shadow log must be a regular file")
        fcntl.flock(fd, fcntl.LOCK_EX)
        initial_size = os.fstat(fd).st_size
        if initial_size and os.pread(fd, 1, initial_size - 1) != b"\n":
            raise ValueError("shadow log has an incomplete record")
        try:
            remaining = memoryview(data)
            while remaining:
                written = os.write(fd, remaining)
                if written <= 0:
                    raise OSError("shadow log write failed")
                remaining = remaining[written:]
            os.fsync(fd)
            directory_fd = os.open(DATA_DIR, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except Exception:
            # A failed partial append must not corrupt the next mutation's gate.
            os.ftruncate(fd, initial_size)
            os.fsync(fd)
            raise
    finally:
        os.close(fd)


def _retain_observation(turn, status="SKIPPED", error=None):
    return {
        "status": status,
        "elapsed_ms": 0,
        "document_id": f"corvus-lab:turn:{turn.user_message_id}:{turn.assistant_message_id}",
        "error": error,
    }


def _load_retain_item(turn):
    """Read canonical rows only; never create a database or change history."""
    if (
        any(type(value) is not int or value <= 0
            for value in (turn.user_message_id, turn.assistant_message_id))
        or turn.user_message_id >= turn.assistant_message_id
        or not isinstance(turn.session_id, str)
        or not turn.session_id.strip()
    ):
        return None
    with closing(sqlite3.connect(f"{store.DB_PATH.resolve().as_uri()}?mode=ro", uri=True)) as conn:
        rows = conn.execute(
            "SELECT id, session_id, role, content, created_at FROM messages WHERE id IN (?, ?)",
            (turn.user_message_id, turn.assistant_message_id),
        ).fetchall()
    by_id = {row[0]: row for row in rows}
    user = by_id.get(turn.user_message_id)
    assistant = by_id.get(turn.assistant_message_id)
    if any(
        row is None or row[1] != turn.session_id or row[2] != role
        or not isinstance(row[3], str) or not row[3].strip()
        for row, role in ((user, "user"), (assistant, "assistant"))
    ):
        return None
    # SQLite CURRENT_TIMESTAMP is UTC without an offset. Preserve that meaning,
    # and validate both timestamps rather than silently substituting ingest time.
    timestamps = []
    for row in (user, assistant):
        timestamp = datetime.fromisoformat(row[4])
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        timestamps.append(timestamp.astimezone(timezone.utc).isoformat())
    return {
        "content": f"User:\n{user[3]}\n\nAssistant:\n{assistant[3]}",
        "timestamp": timestamps[1],
        "document_id": _retain_observation(turn)["document_id"],
        "metadata": {
            "source": "corvus-lab",
            "session_id": turn.session_id,
            "user_message_id": str(turn.user_message_id),
            "assistant_message_id": str(turn.assistant_message_id),
        },
    }


async def retain_completed_turn(turn):
    """One synchronous-contract HTTP retain; no retry, including after timeout."""
    started = time.perf_counter()
    result = _retain_observation(turn)
    if (
        not lab_shadow_enabled() or DATA_DIR.resolve() != LAB_DATA_DIR
        or store.DB_PATH.resolve() != LAB_DATA_DIR / "corvus.db"
    ):
        result["error"] = "RETAIN_NOT_ELIGIBLE"
        return result
    try:
        item = await run_in_threadpool(_load_retain_item, turn)
    except Exception:
        item = None
    if item is None:
        result["error"] = "MISSING_CANONICAL_TURN_DATA"
        result["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 3)
        return result
    result["status"] = "ERROR"
    try:
        async with asyncio.timeout(RETAIN_DEADLINE_SECONDS):
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(RETAIN_DEADLINE_SECONDS, connect=2),
                trust_env=False,
                follow_redirects=False,
                transport=httpx.AsyncHTTPTransport(retries=0),
            ) as client:
                response = await client.post(
                    f"{BASE_URL}/v1/default/banks/{BANK}/memories",
                    json={"items": [item], "async": False},
                )
                response.raise_for_status()
                body = response.json()
                if (
                    not isinstance(body, dict) or body.get("success") is not True
                    or body.get("bank_id") != BANK or body.get("async") is not False
                    or type(body.get("items_count")) is not int or body["items_count"] != 1
                ):
                    raise ValueError("invalid retain response")
            result["status"] = "OK"
    except (TimeoutError, httpx.TimeoutException):
        result["status"] = "TIMEOUT"
        result["error"] = "DEADLINE_EXCEEDED_WRITE_COMPLETION_UNKNOWN"
    except httpx.HTTPStatusError as exc:
        result["error"] = f"HTTP_{exc.response.status_code}"
    except httpx.RequestError:
        result["error"] = "TRANSPORT_ERROR"
    except ValueError:
        result["error"] = "INVALID_RESPONSE"
    except Exception:
        result["error"] = "UNEXPECTED_ERROR"
    result["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 3)
    return result


async def run_shadow_recall(turn):
    """Sequential recall -> durable comparison -> retain -> linked outcome."""
    if not lab_shadow_enabled():
        return
    started = time.perf_counter()
    try:
        observation = await recall(turn.query)
    except Exception:
        observation = {
            "provider": "hindsight", "bank": BANK, "status": "ERROR",
            "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
            "results": [], "error": "UNEXPECTED_ERROR",
        }
    try:
        record = {
            "schema_version": 1,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "session_id": turn.session_id,
            "user_message_id": turn.user_message_id,
            "assistant_message_id": turn.assistant_message_id,
            "query": turn.query,
            "corvus": {"historical_message_ids": list(turn.historical_message_ids)},
            "hindsight": observation,
            "retain": _retain_observation(turn, error="RETAIN_NOT_STARTED"),
        }
        await run_in_threadpool(append_observation, record)
    except Exception:
        logger.warning(
            "H1 shadow retain SKIPPED: COMPARISON_APPEND_FAILED user=%s assistant=%s",
            turn.user_message_id, turn.assistant_message_id,
        )
        return
    try:
        retain = await retain_completed_turn(turn)
    except Exception:
        retain = _retain_observation(turn, "ERROR", "UNEXPECTED_ERROR")
    try:
        # Append-only completion event: linkage instead of another copy of query
        # or recalled text. The preceding comparison remains the mutation gate.
        await run_in_threadpool(append_observation, {
            "schema_version": 1,
            "record_type": "retain_outcome",
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "session_id": turn.session_id,
            "user_message_id": turn.user_message_id,
            "assistant_message_id": turn.assistant_message_id,
            "retain": retain,
        })
    except Exception:
        logger.warning(
            "H1 shadow retain outcome could not be recorded: status=%s error=%s user=%s assistant=%s",
            retain["status"], retain["error"], turn.user_message_id, turn.assistant_message_id,
        )


def schedule_shadow_recall(background_tasks, response, query):
    """Capture immutable linkage only; HTTP/log work starts after transmission."""
    try:
        if not lab_shadow_enabled() or not isinstance(query, str) or not query.strip():
            return
        status = response["status"]
        if (
            status["overall"] not in ("OK", "DEGRADED")
            or status["model"] != "OK"
            or status["persistence"] != "NORMAL"
            or not isinstance(response["reply"], str)
            or not response["reply"].strip()
            or any(type(response[key]) is not int or response[key] <= 0
                   for key in ("user_message_id", "assistant_message_id"))
        ):
            return
        turn = ShadowTurn(
            session_id=response["session_id"],
            user_message_id=response["user_message_id"],
            assistant_message_id=response["assistant_message_id"],
            query=query,
            historical_message_ids=tuple(response["historical_message_ids"]),
        )
        background_tasks.add_task(run_shadow_recall, turn)
    except Exception:
        logger.warning("H1 shadow recall could not be scheduled")
