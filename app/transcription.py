import json
import os
import socket
import urllib.error
import urllib.request
import uuid
from pathlib import Path

from memory.attachments import (
    add_attachment_artifact,
    get_attachment,
    read_attachment_bytes,
)


def _positive_int_env(name, default):
    raw = os.getenv(name)

    if raw is None:
        return default

    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(
            f"{name} must be an integer"
        ) from exc

    if value <= 0:
        raise ValueError(
            f"{name} must be positive"
        )

    return value


STT_BASE_URL = os.getenv(
    "CORVUS_STT_BASE_URL",
    "http://127.0.0.1:8104",
).rstrip("/")

STT_TIMEOUT_SECONDS = _positive_int_env(
    "CORVUS_STT_TIMEOUT_SECONDS",
    60,
)

STT_PROMPT = os.getenv(
    "CORVUS_STT_PROMPT",
    "Corvus Ethan FoxLuma FoxRove PawCareHub",
).strip()

STT_PRODUCER = "whisper.cpp"

STT_PRODUCER_VERSION = os.getenv(
    "CORVUS_STT_PRODUCER_VERSION",
    "small-multilingual",
).strip()


class TranscriptionError(RuntimeError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def _safe_filename(filename):
    filename = Path(
        str(filename)
    ).name.strip()

    if not filename:
        return "audio.bin"

    return (
        filename
        .replace("\\", "_")
        .replace('"', "_")
        .replace("\r", "_")
        .replace("\n", "_")
    )


def _build_multipart_body(
    *,
    audio_bytes,
    filename,
    media_type,
    language,
    prompt,
):
    boundary = (
        "----CorvusSTT"
        + uuid.uuid4().hex
    )

    chunks = []

    def add_field(name, value):
        chunks.extend([
            f"--{boundary}\r\n".encode(),
            (
                f'Content-Disposition: form-data; '
                f'name="{name}"\r\n\r\n'
            ).encode(),
            str(value).encode("utf-8"),
            b"\r\n",
        ])

    add_field(
        "language",
        language,
    )

    add_field(
        "response_format",
        "json",
    )

    if prompt:
        add_field(
            "prompt",
            prompt,
        )

    safe_filename = _safe_filename(
        filename
    )

    chunks.extend([
        f"--{boundary}\r\n".encode(),
        (
            f'Content-Disposition: form-data; '
            f'name="file"; '
            f'filename="{safe_filename}"\r\n'
        ).encode(),
        (
            f"Content-Type: {media_type}\r\n\r\n"
        ).encode(),
        audio_bytes,
        b"\r\n",
        f"--{boundary}--\r\n".encode(),
    ])

    return (
        b"".join(chunks),
        boundary,
    )


def transcribe_attachment(
    attachment_id,
    *,
    language="auto",
    prompt=STT_PROMPT,
    base_url=STT_BASE_URL,
    timeout=STT_TIMEOUT_SECONDS,
    opener=urllib.request.urlopen,
    add_artifact_fn=add_attachment_artifact,
):
    attachment_id = str(
        attachment_id
    ).strip()

    if not attachment_id:
        raise TranscriptionError(
            "TRANSCRIPTION_ATTACHMENT_INVALID",
            "attachment_id must not be empty",
        )

    attachment = get_attachment(
        attachment_id
    )

    if attachment is None:
        raise TranscriptionError(
            "TRANSCRIPTION_ATTACHMENT_NOT_FOUND",
            "attachment not found",
        )

    media_type = (
        attachment["media_type"]
        .strip()
        .lower()
    )

    if not media_type.startswith(
        "audio/"
    ):
        raise TranscriptionError(
            "TRANSCRIPTION_MEDIA_INVALID",
            (
                "attachment media type is not audio: "
                f"{media_type}"
            ),
        )

    try:
        audio_bytes = (
            read_attachment_bytes(
                attachment_id
            )
        )
    except FileNotFoundError as exc:
        raise TranscriptionError(
            "TRANSCRIPTION_AUDIO_UNAVAILABLE",
            "audio attachment is unavailable",
        ) from exc
    except (IOError, ValueError) as exc:
        raise TranscriptionError(
            "TRANSCRIPTION_AUDIO_INVALID",
            "audio attachment failed integrity verification",
        ) from exc

    body, boundary = (
        _build_multipart_body(
            audio_bytes=audio_bytes,
            filename=attachment[
                "original_filename"
            ],
            media_type=media_type,
            language=language,
            prompt=prompt,
        )
    )

    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/inference",
        data=body,
        headers={
            "Content-Type": (
                "multipart/form-data; "
                f"boundary={boundary}"
            ),
        },
        method="POST",
    )

    try:
        with opener(
            request,
            timeout=timeout,
        ) as response:
            raw_response = response.read()

    except (
        socket.timeout,
        TimeoutError,
    ) as exc:
        raise TranscriptionError(
            "TRANSCRIPTION_TIMEOUT",
            "STT request timed out",
        ) from exc

    except urllib.error.HTTPError as exc:
        raise TranscriptionError(
            "TRANSCRIPTION_HTTP_ERROR",
            (
                "STT server returned HTTP "
                f"{exc.code}"
            ),
        ) from exc

    except urllib.error.URLError as exc:
        if isinstance(
            exc.reason,
            (
                socket.timeout,
                TimeoutError,
            ),
        ):
            code = (
                "TRANSCRIPTION_TIMEOUT"
            )
            message = (
                "STT request timed out"
            )
        else:
            code = (
                "TRANSCRIPTION_UNAVAILABLE"
            )
            message = (
                "STT server unavailable: "
                f"{exc.reason}"
            )

        raise TranscriptionError(
            code,
            message,
        ) from exc

    try:
        payload = json.loads(
            raw_response.decode("utf-8")
        )
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:
        raise TranscriptionError(
            "TRANSCRIPTION_RESPONSE_INVALID",
            "STT server returned invalid JSON",
        ) from exc

    transcript = payload.get(
        "text"
    )

    if (
        not isinstance(transcript, str)
        or not transcript.strip()
    ):
        raise TranscriptionError(
            "TRANSCRIPTION_EMPTY",
            "STT server returned no usable transcript",
        )

    transcript = transcript.strip()

    artifact_id = add_artifact_fn(
        attachment_id,
        artifact_kind="TRANSCRIPT",
        content=transcript,
        producer=STT_PRODUCER,
        producer_version=(
            STT_PRODUCER_VERSION
            or None
        ),
    )

    return {
        "attachment_id": attachment_id,
        "artifact_id": artifact_id,
        "transcript": transcript,
        "producer": STT_PRODUCER,
        "producer_version": (
            STT_PRODUCER_VERSION
            or None
        ),
    }
