import base64
import io
import warnings

from PIL import Image, ImageOps

from memory.attachments import (
    get_attachment,
    read_attachment_bytes,
)


SUPPORTED_VISION_MEDIA_TYPES = {
    "image/png",
    "image/jpeg",
}

DEFAULT_MAX_VISION_BYTES = (
    20 * 1024 * 1024
)
INFERENCE_IMAGE_MAX_SIZE = (1024, 1024)


class VisionInputError(ValueError):
    pass


class VisionAttachmentNotFoundError(
    VisionInputError
):
    pass


class VisionAttachmentUnavailableError(
    VisionInputError
):
    pass


class VisionAttachmentTypeError(
    VisionInputError
):
    pass


class VisionAttachmentTooLargeError(
    VisionInputError
):
    pass


def _detect_image_media_type(data):
    if data.startswith(
        b"\x89PNG\r\n\x1a\n"
    ):
        return "image/png"

    if data.startswith(
        b"\xff\xd8\xff"
    ):
        return "image/jpeg"

    return None


def load_vision_attachment(
    attachment_id,
    *,
    max_bytes=DEFAULT_MAX_VISION_BYTES,
    get_attachment_fn=get_attachment,
    read_attachment_fn=read_attachment_bytes,
):
    attachment_id = str(
        attachment_id
    ).strip()

    if not attachment_id:
        raise VisionAttachmentNotFoundError(
            "attachment_id must not be empty"
        )

    max_bytes = int(max_bytes)

    if max_bytes <= 0:
        raise ValueError(
            "max_bytes must be positive"
        )

    attachment = get_attachment_fn(
        attachment_id
    )

    if attachment is None:
        raise VisionAttachmentNotFoundError(
            f"unknown attachment: {attachment_id}"
        )

    media_type = str(
        attachment["media_type"]
    ).strip().lower()

    if (
        media_type
        not in SUPPORTED_VISION_MEDIA_TYPES
    ):
        raise VisionAttachmentTypeError(
            "Vision v1 supports only "
            "image/png and image/jpeg"
        )

    if (
        attachment["blob_status"]
        != "PRESENT"
    ):
        raise VisionAttachmentUnavailableError(
            "attachment raw blob is not present"
        )

    if (
        int(attachment["size_bytes"])
        > max_bytes
    ):
        raise VisionAttachmentTooLargeError(
            "image exceeds Vision v1 size limit"
        )

    try:
        data = read_attachment_fn(
            attachment_id
        )
    except FileNotFoundError as exc:
        raise VisionAttachmentUnavailableError(
            "attachment raw blob is unavailable"
        ) from exc
    except IOError as exc:
        raise VisionAttachmentUnavailableError(
            "attachment raw blob failed "
            "integrity verification"
        ) from exc

    if len(data) > max_bytes:
        raise VisionAttachmentTooLargeError(
            "image exceeds Vision v1 size limit"
        )

    detected_media_type = (
        _detect_image_media_type(data)
    )

    if detected_media_type is None:
        raise VisionAttachmentTypeError(
            "attachment bytes are not a "
            "supported PNG or JPEG image"
        )

    if detected_media_type != media_type:
        raise VisionAttachmentTypeError(
            "attachment media type does not "
            "match image bytes"
        )

    return {
        "attachment": attachment,
        "data": data,
        "media_type": detected_media_type,
    }


def _inference_image_bytes(data, media_type):
    """Keep attachment evidence unchanged; resize only the in-memory model input."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            image_format = {"image/png": "PNG", "image/jpeg": "JPEG"}[media_type]
            with io.BytesIO(data) as source, Image.open(source, formats=[image_format]) as image:
                if image.width <= 1024 and image.height <= 1024:
                    return data
                ImageOps.exif_transpose(image, in_place=True)
                image.thumbnail(INFERENCE_IMAGE_MAX_SIZE, Image.Resampling.LANCZOS)
                with io.BytesIO() as output:
                    image.save(output, format=image_format)
                    return output.getvalue()
    except Exception:
        # No source bytes, filenames or decoder details enter the API error.
        raise VisionInputError("Vision inference image processing failed.") from None


def build_vision_messages(
    messages,
    attachment_id,
    *,
    max_bytes=DEFAULT_MAX_VISION_BYTES,
    get_attachment_fn=get_attachment,
    read_attachment_fn=read_attachment_bytes,
):
    if (
        not isinstance(messages, list)
        or not messages
    ):
        raise VisionInputError(
            "messages must be a non-empty list"
        )

    current = messages[-1]

    if (
        not isinstance(current, dict)
        or current.get("role") != "user"
        or not isinstance(
            current.get("content"),
            str,
        )
    ):
        raise VisionInputError(
            "final message must be a "
            "text user message"
        )

    loaded = load_vision_attachment(
        attachment_id,
        max_bytes=max_bytes,
        get_attachment_fn=get_attachment_fn,
        read_attachment_fn=read_attachment_fn,
    )

    encoded = base64.b64encode(
        _inference_image_bytes(loaded["data"], loaded["media_type"])
    ).decode("ascii")

    data_url = (
        f"data:{loaded['media_type']};"
        f"base64,{encoded}"
    )

    model_messages = [
        dict(message)
        for message in messages
    ]

    model_messages[-1] = {
        **model_messages[-1],
        "content": [
            {
                "type": "text",
                "text": current["content"],
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": data_url,
                },
            },
        ],
    }

    return {
        "messages": model_messages,
        "attachment": loaded[
            "attachment"
        ],
    }
