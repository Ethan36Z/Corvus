import json
import os
import re
import socket
import urllib.error
import urllib.request


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


def _positive_float_env(name, default):
    raw = os.getenv(name)

    if raw is None:
        return default

    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(
            f"{name} must be a number"
        ) from exc

    if value <= 0:
        raise ValueError(
            f"{name} must be positive"
        )

    return value


TTS_BASE_URL = os.getenv(
    "CORVUS_TTS_BASE_URL",
    "http://127.0.0.1:8105",
).rstrip("/")

TTS_TIMEOUT_SECONDS = _positive_int_env(
    "CORVUS_TTS_TIMEOUT_SECONDS",
    60,
)

TTS_MODEL = os.getenv(
    "CORVUS_TTS_MODEL",
    "kokoro",
).strip()

TTS_VOICE = os.getenv(
    "CORVUS_TTS_VOICE",
    "af_mica",
).strip()

TTS_LANGUAGE = os.getenv(
    "CORVUS_TTS_LANGUAGE",
    "z",
).strip()

TTS_SPEED = _positive_float_env(
    "CORVUS_TTS_SPEED",
    0.95,
)

TTS_RESPONSE_FORMAT = "wav"


class TTSError(RuntimeError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def prepare_speech_text(text):
    """
    Convert canonical assistant text into derived presentation text.

    This function must never modify the canonical conversation record.
    It exists only to prepare text for speech synthesis.
    """
    if not isinstance(text, str):
        raise TTSError(
            "TTS_TEXT_INVALID",
            "speech text must be a string",
        )

    prepared = re.sub(
        r"\s+",
        " ",
        text,
    ).strip()

    if not prepared:
        raise TTSError(
            "TTS_TEXT_EMPTY",
            "speech text must not be empty",
        )

    return prepared


def synthesize_speech(
    text,
    *,
    base_url=TTS_BASE_URL,
    timeout=TTS_TIMEOUT_SECONDS,
    model=TTS_MODEL,
    voice=TTS_VOICE,
    language=TTS_LANGUAGE,
    speed=TTS_SPEED,
    opener=urllib.request.urlopen,
):
    speech_text = prepare_speech_text(
        text
    )

    payload = json.dumps(
        {
            "model": model,
            "input": speech_text,
            "voice": voice,
            "response_format": (
                TTS_RESPONSE_FORMAT
            ),
            "speed": speed,
            "lang_code": language,
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        (
            f"{base_url.rstrip('/')}"
            "/v1/audio/speech"
        ),
        data=payload,
        headers={
            "Content-Type": (
                "application/json"
            ),
            "Accept": "audio/wav",
        },
        method="POST",
    )

    try:
        with opener(
            request,
            timeout=timeout,
        ) as response:
            audio_bytes = response.read()

    except (
        socket.timeout,
        TimeoutError,
    ) as exc:
        raise TTSError(
            "TTS_TIMEOUT",
            "TTS request timed out",
        ) from exc

    except urllib.error.HTTPError as exc:
        raise TTSError(
            "TTS_HTTP_ERROR",
            (
                "TTS server returned HTTP "
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
            code = "TTS_TIMEOUT"
            message = (
                "TTS request timed out"
            )
        else:
            code = "TTS_UNAVAILABLE"
            message = (
                "TTS server unavailable: "
                f"{exc.reason}"
            )

        raise TTSError(
            code,
            message,
        ) from exc

    if (
        not audio_bytes
        or len(audio_bytes) < 12
        or audio_bytes[:4] != b"RIFF"
        or audio_bytes[8:12] != b"WAVE"
    ):
        raise TTSError(
            "TTS_RESPONSE_INVALID",
            (
                "TTS server returned "
                "invalid WAV audio"
            ),
        )

    return {
        "audio": audio_bytes,
        "media_type": "audio/wav",
        "speech_text": speech_text,
        "model": model,
        "voice": voice,
        "language": language,
        "speed": speed,
    }
