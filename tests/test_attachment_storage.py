import hashlib
import importlib
import io
import os
import shutil
import sqlite3
import tempfile
from pathlib import Path


tmp_root = Path(
    tempfile.mkdtemp(
        prefix="corvus-a3-attachment-contract-"
    )
)

try:
    os.environ["CORVUS_DATA_DIR"] = str(
        tmp_root
    )

    import memory.config
    import memory.store
    import memory.attachments

    importlib.reload(memory.config)
    importlib.reload(memory.store)
    importlib.reload(memory.attachments)

    config = memory.config
    store = memory.store
    attachments = memory.attachments

    payload = (
        b"Corvus A3 attachment regression test\n"
    )

    store.init_db()

    message_id = store.add_message(
        "attachment-test",
        "user",
        "I attached a test file.",
    )

    first = attachments.store_attachment_stream(
        io.BytesIO(payload),
        original_filename="test.txt",
        media_type="text/plain",
        retention_class="STANDARD",
        max_bytes=1024,
    )

    second = attachments.store_attachment_bytes(
        payload,
        original_filename="copy.txt",
        media_type="text/plain",
        retention_class="EPHEMERAL",
        max_bytes=1024,
    )

    assert first["id"] != second["id"]
    assert first["sha256"] == second["sha256"]
    assert (
        first["storage_path"]
        == second["storage_path"]
    )

    attachments.link_attachment_to_message(
        message_id,
        first["id"],
        ordinal=0,
    )

    artifact_id = (
        attachments.add_attachment_artifact(
            first["id"],
            artifact_kind="DOCUMENT_TEXT",
            content=payload.decode().strip(),
            producer="contract-test",
            producer_version="0.2",
        )
    )

    expected_sha = hashlib.sha256(
        payload
    ).hexdigest()

    assert first["sha256"] == expected_sha
    assert first["size_bytes"] == len(payload)
    assert first["blob_status"] == "PRESENT"
    assert not first["storage_path"].startswith("/")

    assert (
        attachments.read_attachment_bytes(
            first["id"]
        )
        == payload
    )

    blob_path = (
        config.DATA_DIR
        / first["storage_path"]
    )

    assert blob_path.is_file()

    assert (
        blob_path.stat().st_mode & 0o777
    ) == 0o600

    current = blob_path.parent

    while current != config.DATA_DIR:
        assert (
            current.stat().st_mode & 0o777
        ) == 0o700

        if current == config.ATTACHMENTS_DIR:
            break

        current = current.parent

    with sqlite3.connect(
        config.DB_PATH
    ) as conn:
        blob_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM attachment_blobs
            """
        ).fetchone()[0]

        attachment_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM attachments
            """
        ).fetchone()[0]

        assert blob_count == 1
        assert attachment_count == 2

        linked = conn.execute(
            """
            SELECT COUNT(*)
            FROM message_attachments
            WHERE message_id = ?
              AND attachment_id = ?
            """,
            (
                message_id,
                first["id"],
            ),
        ).fetchone()[0]

        assert linked == 1

        artifact = conn.execute(
            """
            SELECT
                artifact_kind,
                content,
                producer,
                producer_version
            FROM attachment_artifacts
            WHERE id = ?
            """,
            (artifact_id,),
        ).fetchone()

        assert artifact == (
            "DOCUMENT_TEXT",
            "Corvus A3 attachment regression test",
            "contract-test",
            "0.2",
        )

    blob_files = list(
        config.ATTACHMENTS_DIR.glob(
            "blobs/*/*/*.blob"
        )
    )

    assert len(blob_files) == 1

    #
    # Same-size tampering must be detected by SHA256.
    #
    blob_path.write_bytes(
        b"X" * len(payload)
    )

    try:
        attachments.read_attachment_bytes(
            first["id"]
        )
    except IOError as exc:
        assert (
            "sha256"
            in str(exc).lower()
        )
    else:
        raise AssertionError(
            "tampered attachment was accepted"
        )

    #
    # Path traversal must be rejected.
    #
    try:
        attachments._resolve_storage_path(
            "../../escape.bin"
        )
    except ValueError:
        pass
    else:
        raise AssertionError(
            "path traversal was accepted"
        )

    #
    # Streaming size cap must stop oversized input.
    #
    try:
        attachments.store_attachment_stream(
            io.BytesIO(b"123456"),
            original_filename="too-large.bin",
            media_type="application/octet-stream",
            max_bytes=5,
        )
    except ValueError as exc:
        assert (
            "max_bytes"
            in str(exc)
        )
    else:
        raise AssertionError(
            "oversized attachment was accepted"
        )

    leftovers = list(
        (
            config.ATTACHMENTS_DIR
            / "tmp"
        ).glob("*.part")
    )

    assert leftovers == []

    print(
        "ATTACHMENT STORAGE CONTRACT OK"
    )
    print(
        "CONTENT ADDRESSED DEDUP OK"
    )
    print(
        "STREAMING INGESTION OK"
    )

finally:
    shutil.rmtree(
        tmp_root,
        ignore_errors=True,
    )
