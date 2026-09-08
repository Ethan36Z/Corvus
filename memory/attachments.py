import hashlib
import io
import os
import uuid
from pathlib import Path

from memory.config import (
    ATTACHMENTS_DIR,
    DATA_DIR,
)
from memory.store import connect


VALID_RETENTION_CLASSES = {
    "PERMANENT",
    "STANDARD",
    "EPHEMERAL",
}

DEFAULT_CHUNK_SIZE = 1024 * 1024


def _validate_text(value, field_name):
    if not isinstance(value, str):
        raise TypeError(
            f"{field_name} must be a string"
        )

    value = value.strip()

    if not value:
        raise ValueError(
            f"{field_name} must not be empty"
        )

    if "\x00" in value:
        raise ValueError(
            f"{field_name} must not contain NUL"
        )

    return value


def _resolve_storage_path(storage_path):
    relative = Path(storage_path)

    if relative.is_absolute():
        raise ValueError(
            "attachment storage_path must be relative"
        )

    data_root = DATA_DIR.resolve()

    resolved = (
        data_root / relative
    ).resolve()

    try:
        resolved.relative_to(data_root)
    except ValueError as exc:
        raise ValueError(
            "attachment storage_path escapes DATA_DIR"
        ) from exc

    return resolved


def _ensure_private_directory(path):
    path.mkdir(
        parents=True,
        exist_ok=True,
        mode=0o700,
    )

    os.chmod(
        path,
        0o700,
    )


def _ensure_attachment_parent(relative_path):
    _ensure_private_directory(
        ATTACHMENTS_DIR
    )

    current = ATTACHMENTS_DIR

    for part in relative_path.parts[1:-1]:
        current = current / part
        _ensure_private_directory(
            current
        )


def _blob_relative_path(sha256):
    return (
        Path("attachments")
        / "blobs"
        / sha256[:2]
        / sha256[2:4]
        / f"{sha256}.blob"
    )


def _verify_blob_file(
    path,
    *,
    expected_sha256,
    expected_size,
):
    if not path.is_file():
        raise FileNotFoundError(
            f"attachment blob missing: {path}"
        )

    if path.stat().st_size != expected_size:
        raise IOError(
            "attachment size mismatch"
        )

    digest = hashlib.sha256()

    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(
                DEFAULT_CHUNK_SIZE
            )

            if not chunk:
                break

            digest.update(chunk)

    if digest.hexdigest() != expected_sha256:
        raise IOError(
            "attachment SHA256 mismatch"
        )


def store_attachment_stream(
    stream,
    *,
    original_filename,
    media_type,
    retention_class="STANDARD",
    max_bytes=None,
    chunk_size=DEFAULT_CHUNK_SIZE,
):
    if not hasattr(stream, "read"):
        raise TypeError(
            "stream must provide read()"
        )

    original_filename = _validate_text(
        original_filename,
        "original_filename",
    )

    media_type = _validate_text(
        media_type,
        "media_type",
    ).lower()

    retention_class = _validate_text(
        retention_class,
        "retention_class",
    ).upper()

    if retention_class not in VALID_RETENTION_CLASSES:
        raise ValueError(
            "invalid retention_class"
        )

    chunk_size = int(chunk_size)

    if chunk_size <= 0:
        raise ValueError(
            "chunk_size must be positive"
        )

    if max_bytes is not None:
        max_bytes = int(max_bytes)

        if max_bytes <= 0:
            raise ValueError(
                "max_bytes must be positive"
            )

    _ensure_private_directory(
        ATTACHMENTS_DIR
    )

    temp_dir = (
        ATTACHMENTS_DIR
        / "tmp"
    )

    _ensure_private_directory(
        temp_dir
    )

    temp_path = (
        temp_dir
        / f"{uuid.uuid4().hex}.part"
    )

    digest = hashlib.sha256()
    size_bytes = 0

    try:
        with open(
            temp_path,
            "xb",
        ) as handle:
            os.chmod(
                temp_path,
                0o600,
            )

            while True:
                chunk = stream.read(
                    chunk_size
                )

                if not chunk:
                    break

                if not isinstance(
                    chunk,
                    (
                        bytes,
                        bytearray,
                        memoryview,
                    ),
                ):
                    raise TypeError(
                        "stream.read() must return bytes"
                    )

                chunk = bytes(chunk)

                size_bytes += len(chunk)

                if (
                    max_bytes is not None
                    and size_bytes > max_bytes
                ):
                    raise ValueError(
                        "attachment exceeds max_bytes"
                    )

                digest.update(chunk)
                handle.write(chunk)

            if size_bytes == 0:
                raise ValueError(
                    "attachment must not be empty"
                )

            handle.flush()
            os.fsync(
                handle.fileno()
            )

        sha256 = digest.hexdigest()

        relative_path = _blob_relative_path(
            sha256
        )

        destination = _resolve_storage_path(
            relative_path
        )

        _ensure_attachment_parent(
            relative_path
        )

        try:
            os.link(
                temp_path,
                destination,
            )
        except FileExistsError:
            _verify_blob_file(
                destination,
                expected_sha256=sha256,
                expected_size=size_bytes,
            )

        temp_path.unlink(
            missing_ok=True
        )

        attachment_id = uuid.uuid4().hex

        with connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO attachment_blobs (
                    sha256,
                    size_bytes,
                    storage_path,
                    blob_status
                )
                VALUES (?, ?, ?, 'PRESENT')
                """,
                (
                    sha256,
                    size_bytes,
                    relative_path.as_posix(),
                ),
            )

            blob = conn.execute(
                """
                SELECT
                    size_bytes,
                    storage_path,
                    blob_status
                FROM attachment_blobs
                WHERE sha256 = ?
                """,
                (sha256,),
            ).fetchone()

            if blob is None:
                raise IOError(
                    "blob metadata registration failed"
                )

            if blob[0] != size_bytes:
                raise IOError(
                    "blob metadata size mismatch"
                )

            if (
                blob[1]
                != relative_path.as_posix()
            ):
                raise IOError(
                    "blob metadata path mismatch"
                )

            if blob[2] != "PRESENT":
                conn.execute(
                    """
                    UPDATE attachment_blobs
                    SET
                        blob_status = 'PRESENT',
                        purged_at = NULL
                    WHERE sha256 = ?
                    """,
                    (sha256,),
                )

            conn.execute(
                """
                INSERT INTO attachments (
                    id,
                    blob_sha256,
                    original_filename,
                    media_type,
                    retention_class
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    attachment_id,
                    sha256,
                    original_filename,
                    media_type,
                    retention_class,
                ),
            )

            conn.commit()

        return get_attachment(
            attachment_id
        )

    finally:
        temp_path.unlink(
            missing_ok=True
        )


def store_attachment_bytes(
    data,
    *,
    original_filename,
    media_type,
    retention_class="STANDARD",
    max_bytes=None,
):
    if not isinstance(
        data,
        (
            bytes,
            bytearray,
            memoryview,
        ),
    ):
        raise TypeError(
            "data must be bytes-like"
        )

    return store_attachment_stream(
        io.BytesIO(
            bytes(data)
        ),
        original_filename=original_filename,
        media_type=media_type,
        retention_class=retention_class,
        max_bytes=max_bytes,
    )


def get_attachment(attachment_id):
    with connect() as conn:
        row = conn.execute(
            """
            SELECT
                a.id,
                b.sha256,
                a.original_filename,
                a.media_type,
                b.size_bytes,
                b.storage_path,
                a.retention_class,
                b.blob_status,
                a.created_at,
                b.created_at,
                b.purged_at
            FROM attachments AS a
            JOIN attachment_blobs AS b
              ON b.sha256 = a.blob_sha256
            WHERE a.id = ?
            """,
            (str(attachment_id),),
        ).fetchone()

    if row is None:
        return None

    return {
        "id": row[0],
        "sha256": row[1],
        "original_filename": row[2],
        "media_type": row[3],
        "size_bytes": row[4],
        "storage_path": row[5],
        "retention_class": row[6],
        "blob_status": row[7],
        "created_at": row[8],
        "blob_created_at": row[9],
        "purged_at": row[10],
    }


def read_attachment_bytes(attachment_id):
    attachment = get_attachment(
        attachment_id
    )

    if attachment is None:
        raise KeyError(
            f"unknown attachment: {attachment_id}"
        )

    if attachment["blob_status"] != "PRESENT":
        raise FileNotFoundError(
            f"attachment blob is "
            f"{attachment['blob_status']}"
        )

    path = _resolve_storage_path(
        attachment["storage_path"]
    )

    _verify_blob_file(
        path,
        expected_sha256=attachment["sha256"],
        expected_size=attachment["size_bytes"],
    )

    return path.read_bytes()


def link_attachment_to_message(
    message_id,
    attachment_id,
    *,
    ordinal=0,
):
    ordinal = int(ordinal)

    if ordinal < 0:
        raise ValueError(
            "ordinal must be non-negative"
        )

    with connect() as conn:
        conn.execute(
            """
            INSERT INTO message_attachments (
                message_id,
                attachment_id,
                ordinal
            )
            VALUES (?, ?, ?)
            """,
            (
                int(message_id),
                str(attachment_id),
                ordinal,
            ),
        )

        conn.commit()


def add_attachment_artifact(
    attachment_id,
    *,
    artifact_kind,
    content,
    producer,
    producer_version=None,
):
    artifact_kind = _validate_text(
        artifact_kind,
        "artifact_kind",
    ).upper()

    content = _validate_text(
        content,
        "content",
    )

    producer = _validate_text(
        producer,
        "producer",
    )

    if producer_version is not None:
        producer_version = _validate_text(
            producer_version,
            "producer_version",
        )

    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO attachment_artifacts (
                attachment_id,
                artifact_kind,
                content,
                producer,
                producer_version
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                str(attachment_id),
                artifact_kind,
                content,
                producer,
                producer_version,
            ),
        )

        conn.commit()

        return cursor.lastrowid
