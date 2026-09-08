import base64
import importlib
import os
import shutil
import sqlite3
import tempfile
from pathlib import Path


tmp_root = Path(
    tempfile.mkdtemp(
        prefix=(
            "corvus-a3-vision-input-contract-"
        )
    )
)

try:
    os.environ[
        "CORVUS_DATA_DIR"
    ] = str(tmp_root)

    import memory.config
    import memory.store
    import memory.attachments

    importlib.reload(
        memory.config
    )
    importlib.reload(
        memory.store
    )
    importlib.reload(
        memory.attachments
    )

    import app.vision_input
    importlib.reload(
        app.vision_input
    )

    store = memory.store
    attachments = memory.attachments
    vision = app.vision_input

    store.init_db()

    png = (
        b"\x89PNG\r\n\x1a\n"
        b"CORVUS-VISION-TEST"
    )

    image = (
        attachments.store_attachment_bytes(
            png,
            original_filename="vision.png",
            media_type="image/png",
            retention_class="STANDARD",
            max_bytes=1024,
        )
    )

    source_messages = [
        {
            "role": "system",
            "content": "system",
        },
        {
            "role": "user",
            "content": (
                "What is in this image?"
            ),
        },
    ]

    result = vision.build_vision_messages(
        source_messages,
        image["id"],
        max_bytes=1024,
    )

    model_messages = result[
        "messages"
    ]

    assert (
        source_messages[-1]["content"]
        == "What is in this image?"
    )

    assert (
        model_messages[-1]["role"]
        == "user"
    )

    parts = model_messages[-1][
        "content"
    ]

    assert parts[0] == {
        "type": "text",
        "text": "What is in this image?",
    }

    assert (
        parts[1]["type"]
        == "image_url"
    )

    url = parts[1][
        "image_url"
    ]["url"]

    prefix = (
        "data:image/png;base64,"
    )

    assert url.startswith(prefix)

    decoded = base64.b64decode(
        url[len(prefix):]
    )

    assert decoded == png

    assert (
        result["attachment"]["id"]
        == image["id"]
    )

    print(
        "VISION MULTIMODAL MESSAGE CONTRACT OK"
    )

    #
    # A declared image type must agree
    # with the actual bytes.
    #
    mislabeled = (
        attachments.store_attachment_bytes(
            b"not-an-image",
            original_filename="fake.png",
            media_type="image/png",
            retention_class="STANDARD",
            max_bytes=1024,
        )
    )

    try:
        vision.load_vision_attachment(
            mislabeled["id"],
            max_bytes=1024,
        )
    except (
        vision.VisionAttachmentTypeError
    ):
        pass
    else:
        raise AssertionError(
            "mislabeled image was accepted"
        )

    print(
        "VISION IMAGE SIGNATURE CHECK OK"
    )

    #
    # Non-image attachment types are
    # not silently passed to vision.
    #
    text_attachment = (
        attachments.store_attachment_bytes(
            b"hello",
            original_filename="note.txt",
            media_type="text/plain",
            retention_class="STANDARD",
            max_bytes=1024,
        )
    )

    try:
        vision.load_vision_attachment(
            text_attachment["id"],
            max_bytes=1024,
        )
    except (
        vision.VisionAttachmentTypeError
    ):
        pass
    else:
        raise AssertionError(
            "non-image attachment was accepted"
        )

    print(
        "VISION MEDIA TYPE GATE OK"
    )

    #
    # Unknown attachment IDs fail
    # without creating anything.
    #
    try:
        vision.load_vision_attachment(
            "missing-attachment",
            max_bytes=1024,
        )
    except (
        vision.VisionAttachmentNotFoundError
    ):
        pass
    else:
        raise AssertionError(
            "missing attachment was accepted"
        )

    print(
        "VISION MISSING ATTACHMENT CHECK OK"
    )

    #
    # Vision has a separate model-facing
    # size boundary from raw upload.
    #
    try:
        vision.load_vision_attachment(
            image["id"],
            max_bytes=4,
        )
    except (
        vision.VisionAttachmentTooLargeError
    ):
        pass
    else:
        raise AssertionError(
            "vision size limit was ignored"
        )

    print(
        "VISION SIZE LIMIT OK"
    )

    #
    # PURGED evidence identity remains,
    # but raw bytes cannot be used.
    #
    with sqlite3.connect(
        memory.config.DB_PATH
    ) as conn:
        conn.execute(
            """
            UPDATE attachment_blobs
            SET blob_status = 'PURGED'
            WHERE sha256 = ?
            """,
            (image["sha256"],),
        )
        conn.commit()

    try:
        vision.load_vision_attachment(
            image["id"],
            max_bytes=1024,
        )
    except (
        vision.VisionAttachmentUnavailableError
    ):
        pass
    else:
        raise AssertionError(
            "purged image was accepted"
        )

    print(
        "VISION PURGED BLOB CHECK OK"
    )

    print(
        "A3 VISION INPUT ADAPTER: PASS"
    )

finally:
    shutil.rmtree(
        tmp_root,
        ignore_errors=True,
    )
