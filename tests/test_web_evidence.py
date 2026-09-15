import hashlib
import importlib
import os
import shutil
import sqlite3
import tempfile
from pathlib import Path


tmp_root = Path(
    tempfile.mkdtemp(
        prefix="corvus-web-evidence-"
    )
)

try:
    os.environ[
        "CORVUS_DATA_DIR"
    ] = str(tmp_root)

    import memory.config
    import memory.store

    importlib.reload(
        memory.config
    )

    importlib.reload(
        memory.store
    )

    import memory.web_evidence

    importlib.reload(
        memory.web_evidence
    )

    from app.web_security import (
        WebSecurityError,
    )

    store = memory.store
    evidence = memory.web_evidence

    store.init_db()

    with store.connect() as conn:
        user_id = conn.execute(
            """
            INSERT INTO messages (
                session_id,
                role,
                content
            )
            VALUES (?, ?, ?)
            """,
            (
                "session-test",
                "user",
                "What happened today?",
            ),
        ).lastrowid

        assistant_id = conn.execute(
            """
            INSERT INTO messages (
                session_id,
                role,
                content
            )
            VALUES (?, ?, ?)
            """,
            (
                "session-test",
                "assistant",
                "According to the source...",
            ),
        ).lastrowid

        conn.commit()

    excerpt_one = (
        "This exact text was selected "
        "for the model context."
    )

    first = (
        evidence.record_web_evidence(
            assistant_id,
            ordinal=0,
            source_url=(
                "https://example.com/"
                "article#section"
            ),
            source_title=(
                "Example article"
            ),
            excerpt=excerpt_one,
            evidence_id="webev_test_1",
        )
    )

    assert first["source_url"] == (
        "https://example.com/article"
    )

    assert (
        first["excerpt_sha256"]
        == hashlib.sha256(
            excerpt_one.encode(
                "utf-8"
            )
        ).hexdigest()
    )

    evidence.record_web_evidence(
        assistant_id,
        ordinal=1,
        source_url=(
            "https://example.org/news"
        ),
        excerpt=(
            "Second selected evidence."
        ),
        evidence_id="webev_test_2",
    )

    loaded = (
        evidence.load_web_evidence(
            assistant_id
        )
    )

    assert [
        item["ordinal"]
        for item in loaded
    ] == [
        0,
        1,
    ]

    assert loaded[0]["excerpt"] == (
        excerpt_one
    )

    try:
        evidence.record_web_evidence(
            user_id,
            ordinal=0,
            source_url=(
                "https://example.com/"
            ),
            excerpt="not allowed",
        )
    except ValueError as exc:
        assert (
            "assistant message"
            in str(exc)
        )
    else:
        raise AssertionError(
            "web evidence attached "
            "to user message"
        )

    try:
        evidence.record_web_evidence(
            assistant_id,
            ordinal=2,
            source_url=(
                "http://127.0.0.1/"
            ),
            excerpt="blocked",
        )
    except WebSecurityError as exc:
        assert exc.code == (
            "WEB_ADDRESS_BLOCKED"
        )
    else:
        raise AssertionError(
            "blocked URL accepted"
        )

    with sqlite3.connect(
        memory.config.DB_PATH
    ) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                """
            ).fetchall()
        }

        assert "web_searches" not in tables
        assert (
            "web_search_results"
            not in tables
        )
        assert "web_fetches" not in tables

        evidence_count = (
            conn.execute(
                """
                SELECT COUNT(*)
                FROM web_evidence
                """
            ).fetchone()[0]
        )

        assert evidence_count == 2

        message_count = (
            conn.execute(
                """
                SELECT COUNT(*)
                FROM messages
                """
            ).fetchone()[0]
        )

        assert message_count == 2

    print(
        "WEB USED-EVIDENCE "
        "PERSISTENCE CONTRACT OK"
    )
    print(
        "WEB RETRIEVAL "
        "NON-PERSISTENCE CONTRACT OK"
    )
    print(
        "WEB USER-EVIDENCE "
        "SEPARATION CONTRACT OK"
    )
    print(
        "WEB SOURCE SAFETY "
        "CONTRACT OK"
    )

finally:
    shutil.rmtree(
        tmp_root,
        ignore_errors=True,
    )
