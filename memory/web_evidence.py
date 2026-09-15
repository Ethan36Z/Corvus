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
