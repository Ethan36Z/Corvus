import hashlib
import uuid

from app.web_security import (
    validate_public_url,
)
from memory.store import connect


def _new_evidence_id():
    return (
        "webev_"
        + uuid.uuid4().hex
    )


def _required_text(
    value,
    name,
):
    if not isinstance(value, str):
        raise ValueError(
            f"{name} must be text"
        )

    value = value.strip()

    if not value:
        raise ValueError(
            f"{name} must not be empty"
        )

    return value


def _optional_text(
    value,
):
    if value is None:
        return None

    value = str(value).strip()

    return value or None


def _normalize_assistant_message_id(
    assistant_message_id,
):
    try:
        assistant_message_id = int(
            assistant_message_id
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise ValueError(
            "assistant_message_id "
            "must be an integer"
        ) from exc

    return assistant_message_id


def _prepare_web_evidence_batch_item(
    item,
    expected_ordinal,
):
    if not isinstance(
        item,
        dict,
    ):
        raise ValueError(
            "web evidence item must be a dict"
        )

    if "ordinal" not in item:
        raise ValueError(
            "web evidence item requires ordinal"
        )

    try:
        ordinal = int(
            item["ordinal"]
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise ValueError(
            "ordinal must be an integer"
        ) from exc

    if ordinal < 0:
        raise ValueError(
            "ordinal must be >= 0"
        )

    if ordinal != expected_ordinal:
        raise ValueError(
            "web evidence ordinals must be "
            "contiguous and zero-based"
        )

    if "source_url" not in item:
        raise ValueError(
            "web evidence item requires source_url"
        )

    if "excerpt" not in item:
        raise ValueError(
            "web evidence item requires excerpt"
        )

    validated_url = (
        validate_public_url(
            item["source_url"]
        )["url"]
    )

    excerpt = _required_text(
        item["excerpt"],
        "excerpt",
    )

    source_title = _optional_text(
        item.get(
            "source_title"
        )
    )

    excerpt_sha256 = (
        hashlib.sha256(
            excerpt.encode("utf-8")
        )
        .hexdigest()
    )

    evidence_id = item.get(
        "evidence_id"
    )

    if evidence_id is None:
        evidence_id = (
            _new_evidence_id()
        )
    else:
        evidence_id = (
            _required_text(
                evidence_id,
                "evidence_id",
            )
        )

    return {
        "evidence_id": evidence_id,
        "ordinal": ordinal,
        "source_url": validated_url,
        "source_title": source_title,
        "excerpt": excerpt,
        "excerpt_sha256": (
            excerpt_sha256
        ),
    }


def record_web_evidence_batch(
    assistant_message_id,
    evidence_items,
):
    """
    Persist one complete Used Web Evidence set atomically.

    All item normalization and public-URL validation happen before
    database writes begin.

    Once the transaction starts, every evidence row is committed
    together or the complete batch is rolled back.
    """
    assistant_message_id = (
        _normalize_assistant_message_id(
            assistant_message_id
        )
    )

    try:
        evidence_items = tuple(
            evidence_items
        )
    except TypeError as exc:
        raise ValueError(
            "evidence_items must be iterable"
        ) from exc

    if not evidence_items:
        return []

    prepared = [
        _prepare_web_evidence_batch_item(
            item,
            expected_ordinal=ordinal,
        )
        for ordinal, item in enumerate(
            evidence_items
        )
    ]

    evidence_ids = [
        item["evidence_id"]
        for item in prepared
    ]

    if len(
        set(evidence_ids)
    ) != len(evidence_ids):
        raise ValueError(
            "duplicate evidence_id in batch"
        )

    conn = connect()

    try:
        conn.execute(
            "BEGIN"
        )

        message = conn.execute(
            """
            SELECT role
            FROM messages
            WHERE id = ?
            """,
            (
                assistant_message_id,
            ),
        ).fetchone()

        if message is None:
            raise ValueError(
                "assistant message "
                "does not exist"
            )

        if message[0] != "assistant":
            raise ValueError(
                "web evidence may only "
                "attach to an assistant message"
            )

        for item in prepared:
            conn.execute(
                """
                INSERT INTO web_evidence (
                    id,
                    assistant_message_id,
                    ordinal,
                    source_url,
                    source_title,
                    excerpt,
                    excerpt_sha256
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item["evidence_id"],
                    assistant_message_id,
                    item["ordinal"],
                    item["source_url"],
                    item["source_title"],
                    item["excerpt"],
                    item["excerpt_sha256"],
                ),
            )

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()

    return [
        {
            "evidence_id": item[
                "evidence_id"
            ],
            "assistant_message_id": (
                assistant_message_id
            ),
            "ordinal": item[
                "ordinal"
            ],
            "source_url": item[
                "source_url"
            ],
            "source_title": item[
                "source_title"
            ],
            "excerpt": item[
                "excerpt"
            ],
            "excerpt_sha256": item[
                "excerpt_sha256"
            ],
        }
        for item in prepared
    ]


def record_web_evidence(
    assistant_message_id,
    *,
    ordinal,
    source_url,
    excerpt,
    source_title=None,
    evidence_id=None,
):
    try:
        assistant_message_id = int(
            assistant_message_id
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise ValueError(
            "assistant_message_id "
            "must be an integer"
        ) from exc

    try:
        ordinal = int(
            ordinal
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise ValueError(
            "ordinal must be an integer"
        ) from exc

    if ordinal < 0:
        raise ValueError(
            "ordinal must be >= 0"
        )

    validated_url = (
        validate_public_url(
            source_url
        )["url"]
    )

    excerpt = _required_text(
        excerpt,
        "excerpt",
    )

    source_title = _optional_text(
        source_title
    )

    excerpt_sha256 = (
        hashlib.sha256(
            excerpt.encode("utf-8")
        )
        .hexdigest()
    )

    if evidence_id is None:
        evidence_id = (
            _new_evidence_id()
        )
    else:
        evidence_id = (
            _required_text(
                evidence_id,
                "evidence_id",
            )
        )

    with connect() as conn:
        message = conn.execute(
            """
            SELECT role
            FROM messages
            WHERE id = ?
            """,
            (
                assistant_message_id,
            ),
        ).fetchone()

        if message is None:
            raise ValueError(
                "assistant message "
                "does not exist"
            )

        if message[0] != "assistant":
            raise ValueError(
                "web evidence may only "
                "attach to an assistant message"
            )

        conn.execute(
            """
            INSERT INTO web_evidence (
                id,
                assistant_message_id,
                ordinal,
                source_url,
                source_title,
                excerpt,
                excerpt_sha256
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                evidence_id,
                assistant_message_id,
                ordinal,
                validated_url,
                source_title,
                excerpt,
                excerpt_sha256,
            ),
        )

        conn.commit()

    return {
        "evidence_id": evidence_id,
        "assistant_message_id": (
            assistant_message_id
        ),
        "ordinal": ordinal,
        "source_url": validated_url,
        "source_title": source_title,
        "excerpt": excerpt,
        "excerpt_sha256": (
            excerpt_sha256
        ),
    }


def load_web_evidence(
    assistant_message_id,
):
    assistant_message_id = int(
        assistant_message_id
    )

    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                id,
                assistant_message_id,
                ordinal,
                source_url,
                source_title,
                excerpt,
                excerpt_sha256,
                fetched_at
            FROM web_evidence
            WHERE assistant_message_id = ?
            ORDER BY ordinal ASC
            """,
            (
                assistant_message_id,
            ),
        ).fetchall()

    return [
        {
            "evidence_id": row[0],
            "assistant_message_id": (
                row[1]
            ),
            "ordinal": row[2],
            "source_url": row[3],
            "source_title": row[4],
            "excerpt": row[5],
            "excerpt_sha256": row[6],
            "fetched_at": row[7],
        }
        for row in rows
    ]
