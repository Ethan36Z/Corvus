import asyncio
import importlib
import os
import shutil
import sqlite3
import tempfile
from pathlib import Path


tmp_root = Path(
    tempfile.mkdtemp(
        prefix="corvus-a3-upload-adapter-"
    )
)

try:
    os.environ[
        "CORVUS_DATA_DIR"
    ] = str(tmp_root)

    import memory.config
    import memory.store
    import memory.attachments

    importlib.reload(memory.config)
    importlib.reload(memory.store)
    importlib.reload(memory.attachments)

    import app.attachment_upload

    importlib.reload(
        app.attachment_upload
    )

    store = memory.store
    upload = app.attachment_upload

    store.init_db()

    payload = (
        b"A" * (1024 * 1024)
        + b"B" * 12345
    )

    async def normal_chunks():
        yield payload[:700000]
        yield payload[700000:]

    attachment = asyncio.run(
        upload.ingest_attachment_chunks(
            normal_chunks(),
            original_filename="large-test.bin",
            media_type=(
                "application/octet-stream"
            ),
            retention_class="STANDARD",
            max_bytes=2 * 1024 * 1024,
        )
    )

    assert attachment["size_bytes"] == len(
        payload
    )

    assert (
        attachment["retention_class"]
        == "STANDARD"
    )

    assert (
        memory.attachments
        .read_attachment_bytes(
            attachment["id"]
        )
        == payload
    )

    async def empty_chunks():
        if False:
            yield b""

    try:
        asyncio.run(
            upload.ingest_attachment_chunks(
                empty_chunks(),
                original_filename="empty.bin",
                media_type=(
                    "application/octet-stream"
                ),
                retention_class="STANDARD",
                max_bytes=1024,
            )
        )
    except upload.AttachmentUploadEmptyError:
        pass
    else:
        raise AssertionError(
            "empty upload was accepted"
        )

    drained_chunks = []

    async def oversized_chunks():
        for chunk in (
            b"1234",
            b"5678",
            b"ABCD",
        ):
            drained_chunks.append(chunk)
            yield chunk

    try:
        asyncio.run(
            upload.ingest_attachment_chunks(
                oversized_chunks(),
                original_filename=(
                    "too-large.bin"
                ),
                media_type=(
                    "application/octet-stream"
                ),
                retention_class="STANDARD",
                max_bytes=7,
            )
        )
    except (
        upload.AttachmentUploadTooLargeError
    ):
        pass
    else:
        raise AssertionError(
            "oversized upload was accepted"
        )

    assert drained_chunks == [
        b"1234",
        b"5678",
        b"ABCD",
    ]

    with sqlite3.connect(
        memory.config.DB_PATH
    ) as conn:
        attachment_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM attachments
            """
        ).fetchone()[0]

        assert attachment_count == 1

    print(
        "ATTACHMENT UPLOAD ADAPTER CONTRACT OK"
    )
    print(
        "UPLOAD >1M STREAMING CONTRACT OK"
    )
    print(
        "UPLOAD EMPTY REJECTION OK"
    )
    print(
        "UPLOAD SIZE LIMIT OK"
    )
    print(
        "OVERSIZE BODY DRAIN CONTRACT OK"
    )

finally:
    shutil.rmtree(
        tmp_root,
        ignore_errors=True,
    )
