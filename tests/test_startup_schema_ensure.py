import asyncio
import sqlite3
import tempfile
from pathlib import Path
from types import SimpleNamespace

import memory.store as store

from app.runtime_lifecycle import (
    prepare_runtime_startup,
)


#
# Contract 1:
# A legacy DB that predates Web evidence must gain
# the additive table without losing canonical data.
#

with tempfile.TemporaryDirectory() as tmp:
    original_db_path = store.DB_PATH

    legacy_db = (
        Path(tmp)
        / "legacy-corvus.db"
    )

    store.DB_PATH = legacy_db

    try:
        with sqlite3.connect(
            legacy_db
        ) as conn:
            conn.execute(
                """
                CREATE TABLE messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                        DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            conn.execute(
                """
                INSERT INTO messages (
                    session_id,
                    role,
                    content
                )
                VALUES (?, ?, ?)
                """,
                (
                    "legacy-session",
                    "user",
                    "preserve this canonical message",
                ),
            )

        #
        # Must be safe to run repeatedly.
        #
        store.init_db()
        store.init_db()

        with sqlite3.connect(
            legacy_db
        ) as conn:
            integrity = conn.execute(
                "PRAGMA integrity_check"
            ).fetchone()[0]

            tables = {
                row[0]
                for row
                in conn.execute(
                    """
                    SELECT name
                    FROM sqlite_master
                    WHERE type = 'table'
                    """
                ).fetchall()
            }

            row = conn.execute(
                """
                SELECT
                    session_id,
                    role,
                    content
                FROM messages
                WHERE id = 1
                """
            ).fetchone()

            web_columns = {
                item[1]
                for item
                in conn.execute(
                    """
                    PRAGMA table_info(
                        web_evidence
                    )
                    """
                ).fetchall()
            }

        assert integrity == "ok"

        assert (
            "web_evidence"
            in tables
        )

        assert row == (
            "legacy-session",
            "user",
            "preserve this canonical message",
        )

        assert {
            "id",
            "assistant_message_id",
            "ordinal",
            "source_url",
            "source_title",
            "excerpt",
            "excerpt_sha256",
            "fetched_at",
        }.issubset(
            web_columns
        )

    finally:
        store.DB_PATH = (
            original_db_path
        )


print(
    "STARTUP SCHEMA LEGACY-DB UPGRADE CONTRACT OK"
)

print(
    "STARTUP SCHEMA IDEMPOTENCE CONTRACT OK"
)

print(
    "STARTUP SCHEMA CANONICAL-DATA PRESERVATION CONTRACT OK"
)


#
# Contract 2:
# canonical schema ensure must happen before dense
# recovery.
#

events = []

recovery_result = {
    "status": "OK",
    "caught_up": True,
    "batches": 0,
    "indexed": 0,
    "progress_after": None,
    "error": None,
}


def ensure_schema():
    events.append(
        "schema"
    )


def recover_dense():
    events.append(
        "dense"
    )

    return recovery_result


result = prepare_runtime_startup(
    schema_ensure_fn=ensure_schema,
    recovery_fn=recover_dense,
)

assert events == [
    "schema",
    "dense",
]

assert result is recovery_result

print(
    "STARTUP SCHEMA-BEFORE-DENSE ORDER CONTRACT OK"
)


#
# Contract 3:
# canonical schema failure must block dense recovery
# and fail startup instead of serving against an
# invalid canonical DB.
#

failure_events = []


def fail_schema():
    failure_events.append(
        "schema"
    )

    raise RuntimeError(
        "synthetic schema failure"
    )


def must_not_recover():
    failure_events.append(
        "dense"
    )

    raise AssertionError(
        "dense recovery must not run "
        "after schema failure"
    )


try:
    prepare_runtime_startup(
        schema_ensure_fn=fail_schema,
        recovery_fn=must_not_recover,
    )
except RuntimeError as exc:
    assert (
        "synthetic schema failure"
        in str(exc)
    )
else:
    raise AssertionError(
        "schema failure must propagate"
    )


assert failure_events == [
    "schema",
]

print(
    "STARTUP SCHEMA FAILURE FAIL-CLOSED CONTRACT OK"
)


#
# Contract 4:
# FastAPI lifespan must use the coordinator result
# as the existing startup_recovery health payload.
#

import app.playground_api as api


original_prepare = (
    api.prepare_runtime_startup
)

lifespan_result = {
    "status": "OK",
    "caught_up": True,
    "batches": 1,
    "indexed": 2,
    "progress_after": 2,
    "error": None,
}

lifespan_events = []


def fake_prepare():
    lifespan_events.append(
        "prepare"
    )

    return lifespan_result


async def exercise_lifespan():
    fake_app = SimpleNamespace(
        state=SimpleNamespace()
    )

    async with api.lifespan(
        fake_app
    ):
        assert (
            fake_app.state.startup_recovery
            is lifespan_result
        )

        lifespan_events.append(
            "serve"
        )


try:
    api.prepare_runtime_startup = (
        fake_prepare
    )

    asyncio.run(
        exercise_lifespan()
    )

finally:
    api.prepare_runtime_startup = (
        original_prepare
    )


assert lifespan_events == [
    "prepare",
    "serve",
]

print(
    "FASTAPI STARTUP COORDINATOR WIRING CONTRACT OK"
)

print(
    "A3_4_STARTUP_SCHEMA_ENSURE=PASS"
)
