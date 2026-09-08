import tempfile

from memory.attachments import (
    store_attachment_stream,
)


SPOOL_MEMORY_BYTES = 1024 * 1024


class AttachmentUploadError(ValueError):
    pass


class AttachmentUploadEmptyError(
    AttachmentUploadError
):
    pass


class AttachmentUploadTooLargeError(
    AttachmentUploadError
):
    pass


async def ingest_attachment_chunks(
    chunks,
    *,
    original_filename,
    media_type,
    retention_class,
    max_bytes,
    store_fn=store_attachment_stream,
):
    max_bytes = int(max_bytes)

    if max_bytes <= 0:
        raise ValueError(
            "max_bytes must be positive"
        )

    total_bytes = 0
    too_large = False

    with tempfile.SpooledTemporaryFile(
        max_size=min(
            SPOOL_MEMORY_BYTES,
            max_bytes,
        ),
        mode="w+b",
    ) as spool:
        async for chunk in chunks:
            if not isinstance(
                chunk,
                (
                    bytes,
                    bytearray,
                    memoryview,
                ),
            ):
                raise TypeError(
                    "upload chunks must be bytes"
                )

            chunk = bytes(chunk)

            if not chunk:
                continue

            total_bytes += len(chunk)

            if total_bytes > max_bytes:
                too_large = True
                continue

            spool.write(chunk)

        if total_bytes == 0:
            raise AttachmentUploadEmptyError(
                "attachment must not be empty"
            )

        if too_large:
            raise AttachmentUploadTooLargeError(
                "attachment exceeds maximum size"
            )

        spool.seek(0)

        return store_fn(
            spool,
            original_filename=original_filename,
            media_type=media_type,
            retention_class=retention_class,
            max_bytes=max_bytes,
        )
