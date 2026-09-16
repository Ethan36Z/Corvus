import importlib
import os
import shutil
import sqlite3
import tempfile
from pathlib import Path


tmp_root = Path(
    tempfile.mkdtemp(
        prefix="corvus-web-evidence-batch-"
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

    store = memory.store
    evidence = memory.web_evidence

    store.init_db()

    with store.connect() as conn:
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
                "session-batch",
                "assistant",
                "Grounded answer.",
            ),
        ).lastrowid

        collision_owner_id = (
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
                    "session-collision",
                    "assistant",
                    "Existing grounded answer.",
                ),
            ).lastrowid
        )

        conn.commit()

    existing = (
        evidence.record_web_evidence(
            collision_owner_id,
            ordinal=0,
            source_url=(
                "https://example.org/"
                "existing"
            ),
            source_title=(
                "Existing source"
            ),
            excerpt=(
                "Existing evidence."
            ),
            evidence_id=(
                "webev_collision"
            ),
        )
    )

    assert (
        existing["evidence_id"]
        == "webev_collision"
    )

    success_rows = (
        evidence.record_web_evidence_batch(
            assistant_id,
            [
                {
                    "ordinal": 0,
                    "source_url": (
                        "https://example.com/"
                        "article#section"
                    ),
                    "source_title": (
                        "Example article"
                    ),
                    "excerpt": (
                        "First exact excerpt."
                    ),
                    "evidence_id": (
                        "webev_batch_1"
                    ),
                },
                {
                    "ordinal": 1,
                    "source_url": (
                        "https://example.net/"
                        "news"
                    ),
                    "source_title": (
                        "Example news"
                    ),
                    "excerpt": (
                        "Second exact excerpt."
                    ),
                    "evidence_id": (
                        "webev_batch_2"
                    ),
                },
            ],
        )
    )

    assert [
        row["ordinal"]
        for row in success_rows
    ] == [
        0,
        1,
    ]

    loaded = (
        evidence.load_web_evidence(
            assistant_id
        )
    )

    assert [
        row["evidence_id"]
        for row in loaded
    ] == [
        "webev_batch_1",
        "webev_batch_2",
    ]

    assert (
        loaded[0]["source_url"]
        == "https://example.com/article"
    )

    print(
        "WEB EVIDENCE BATCH SUCCESS CONTRACT OK"
    )

    with store.connect() as conn:
        rollback_target_id = (
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
                    "session-rollback",
                    "assistant",
                    "Rollback target.",
                ),
            ).lastrowid
        )

        conn.commit()

    try:
        evidence.record_web_evidence_batch(
            rollback_target_id,
            [
                {
                    "ordinal": 0,
                    "source_url": (
                        "https://example.com/"
                        "first"
                    ),
                    "excerpt": (
                        "This insert should "
                        "be rolled back."
                    ),
                    "evidence_id": (
                        "webev_before_failure"
                    ),
                },
                {
                    "ordinal": 1,
                    "source_url": (
                        "https://example.com/"
                        "second"
                    ),
                    "excerpt": (
                        "This row collides "
                        "with an existing ID."
                    ),
                    "evidence_id": (
                        "webev_collision"
                    ),
                },
            ],
        )
    except sqlite3.IntegrityError:
        pass
    else:
        raise AssertionError(
            "expected batch persistence failure"
        )

    rolled_back = (
        evidence.load_web_evidence(
            rollback_target_id
        )
    )

    assert rolled_back == []

    with store.connect() as conn:
        leaked = conn.execute(
            """
            SELECT COUNT(*)
            FROM web_evidence
            WHERE id = ?
            """,
            (
                "webev_before_failure",
            ),
        ).fetchone()[0]

    assert leaked == 0

    print(
        "WEB EVIDENCE BATCH ROLLBACK CONTRACT OK"
    )

    with store.connect() as conn:
        validation_target_id = (
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
                    "session-validation",
                    "assistant",
                    "Validation target.",
                ),
            ).lastrowid
        )

        conn.commit()

    try:
        evidence.record_web_evidence_batch(
            validation_target_id,
            [
                {
                    "ordinal": 0,
                    "source_url": (
                        "https://example.com/"
                    ),
                    "excerpt": (
                        "Valid first item."
                    ),
                },
                {
                    "ordinal": 2,
                    "source_url": (
                        "https://example.org/"
                    ),
                    "excerpt": (
                        "Invalid ordinal gap."
                    ),
                },
            ],
        )
    except ValueError as exc:
        assert (
            "contiguous and zero-based"
            in str(exc)
        )
    else:
        raise AssertionError(
            "invalid batch ordinals accepted"
        )

    assert (
        evidence.load_web_evidence(
            validation_target_id
        )
        == []
    )

    print(
        "WEB EVIDENCE PREWRITE VALIDATION CONTRACT OK"
    )

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
                "session-user",
                "user",
                "User evidence.",
            ),
        ).lastrowid

        conn.commit()

    try:
        evidence.record_web_evidence_batch(
            user_id,
            [
                {
                    "ordinal": 0,
                    "source_url": (
                        "https://example.com/"
                    ),
                    "excerpt": (
                        "Must not attach to user."
                    ),
                }
            ],
        )
    except ValueError as exc:
        assert (
            "assistant message"
            in str(exc)
        )
    else:
        raise AssertionError(
            "batch attached to user message"
        )

    assert (
        evidence.load_web_evidence(
            user_id
        )
        == []
    )

    print(
        "WEB EVIDENCE ASSISTANT-ONLY CONTRACT OK"
    )

    empty = (
        evidence.record_web_evidence_batch(
            assistant_id,
            [],
        )
    )

    assert empty == []

    print(
        "WEB EVIDENCE EMPTY-BATCH CONTRACT OK"
    )

    print(
        "A3_4C9D2A_ATOMIC_WEB_EVIDENCE_BATCH_STORE=PASS"
    )

finally:
    shutil.rmtree(
        tmp_root,
        ignore_errors=True,
    )
