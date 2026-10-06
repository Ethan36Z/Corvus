"""Lab-only, comparison-only recall after a confirmed text reply is sent.

This module never writes to the memory bank. If a later experiment adds bank
writes, recall must complete before that turn's write to avoid self-leakage.
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
import fcntl
import json
import logging
import math
import os
from pathlib import Path
import stat
import time

import httpx
from starlette.concurrency import run_in_threadpool

from memory.config import DATA_DIR, PROJECT_ROOT


LAB_PROJECT_ROOT = Path("/home/ethan/srv/apps/corvus-lab")
LAB_DATA_DIR = Path("/home/ethan/srv/data/corvus/lab")
BASE_URL = "http://127.0.0.1:8888"
BANK = "corvus-hindsight-lab-v1"
DEADLINE_SECONDS = 10
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
    """Append one derived record; flock prevents interleaved partial writes."""
    if not lab_shadow_enabled() or DATA_DIR.resolve() != LAB_DATA_DIR:
        raise ValueError("shadow log is Lab only")
    data = (json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
    fd = os.open(
        DATA_DIR / LOG_NAME,
        os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_CLOEXEC | os.O_NOFOLLOW,
        0o600,
    )
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError("shadow log must be a regular file")
        fcntl.flock(fd, fcntl.LOCK_EX)
        remaining = memoryview(data)
        while remaining:
            written = os.write(fd, remaining)
            if written <= 0:
                raise OSError("shadow log write failed")
            remaining = remaining[written:]
    finally:
        os.close(fd)


async def run_shadow_recall(turn):
    """Contain all shadow failures; never receives or mutates the API reply."""
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
        }
        await run_in_threadpool(append_observation, record)
    except Exception:
        logger.warning("H1 shadow recall observation could not be recorded")


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
