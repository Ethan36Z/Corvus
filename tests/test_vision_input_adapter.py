import base64
import importlib
import io
import os
import shutil
import sqlite3
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw


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

    with io.BytesIO() as buffer:
        Image.new("RGB", (16, 12), "red").save(buffer, format="PNG")
        png = buffer.getvalue()

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

    # Exercise the real attachment/read/model-message boundary with synthetic
    # originals. No inference copy may become an attachment or canonical row.
    for image_format, size, orientation in [
        ("PNG", (1024, 512), None),
        ("JPEG", (640, 480), 6),
        ("PNG", (1536, 2048), None),
        ("JPEG", (2048, 1536), 6),
        ("PNG", (4096, 512), None),
    ]:
        mode = "RGBA" if image_format == "PNG" else "RGB"
        with Image.new(mode, size, "red") as generated, io.BytesIO() as buffer:
            ImageDraw.Draw(generated).rectangle((size[0]//2, 0, size[0], size[1]), fill="blue")
            options = {}
            if orientation:
                exif = Image.Exif(); exif[274] = orientation
                options["exif"] = exif
            generated.save(buffer, format=image_format, **options)
            original = buffer.getvalue()
        mime = "image/png" if image_format == "PNG" else "image/jpeg"
        attachment = attachments.store_attachment_bytes(
            original, original_filename="synthetic", media_type=mime,
            retention_class="STANDARD", max_bytes=20*1024*1024,
        )
        before_meta = attachments.get_attachment(attachment["id"])
        with sqlite3.connect(memory.config.DB_PATH) as conn:
            before_counts = [conn.execute("SELECT COUNT(*) FROM " + t).fetchone()[0]
                             for t in ["attachments", "attachment_blobs", "messages"]]
        output = vision.build_vision_messages(source_messages, attachment["id"])
        url = output["messages"][-1]["content"][1]["image_url"]["url"]
        assert url.startswith("data:" + mime + ";base64,")
        resized = base64.b64decode(url.split(",", 1)[1])
        assert attachments.read_attachment_bytes(attachment["id"]) == original
        assert attachments.get_attachment(attachment["id"]) == before_meta
        assert output["attachment"] == before_meta
        with sqlite3.connect(memory.config.DB_PATH) as conn:
            assert before_counts == [conn.execute("SELECT COUNT(*) FROM " + t).fetchone()[0]
                                     for t in ["attachments", "attachment_blobs", "messages"]]
        with Image.open(io.BytesIO(resized)) as decoded:
            assert decoded.format == image_format
            if max(size) <= 1024:
                assert resized == original
                assert decoded.size == size
            else:
                assert resized != original
                expected = ((768, 1024) if size in [(1536, 2048), (2048, 1536)]
                            else (1024, 128))
                assert decoded.size == expected
                assert decoded.getexif().get(274, 1) == 1
                if image_format == "PNG":
                    assert decoded.mode == "RGBA"
                if orientation == 6:
                    # EXIF clockwise rotation: old left red half becomes top.
                    top = decoded.getpixel((decoded.width//2, decoded.height//4))
                    bottom = decoded.getpixel((decoded.width//2, 3*decoded.height//4))
                    assert top[0] > top[2] + 100 and bottom[2] > bottom[0] + 100
    corrupt = b"\x89PNG\r\n\x1a\nnot-a-decodable-image"
    reads = []
    try:
        vision.build_vision_messages(
            source_messages, "synthetic-corrupt",
            get_attachment_fn=lambda _: {"media_type": "image/png", "blob_status": "PRESENT",
                                          "size_bytes": len(corrupt)},
            read_attachment_fn=lambda aid: (reads.append(aid), corrupt)[1],
        )
    except vision.VisionInputError as exc:
        assert str(exc) == "Vision inference image processing failed."
    else:
        raise AssertionError("Corrupted image was accepted")
    assert reads == ["synthetic-corrupt"], "No automatic reread/retry"
    assert source_messages[-1]["content"] == "What is in this image?"
    assert vision.DEFAULT_MAX_VISION_BYTES == 20*1024*1024
    print("VISION IN-MEMORY RESIZE: small bytes unchanged; proportional bounds; EXIF direction; PNG/JPEG MIME; originals/DB unchanged; sanitized failure OK")

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
