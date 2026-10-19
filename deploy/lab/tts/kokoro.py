"""Lab-only, transient Read Aloud transport. No conversation/storage imports."""

import asyncio
from contextlib import suppress
import io
import json
import re
import wave

from fastapi import HTTPException, Request
import httpx
from starlette.responses import JSONResponse, Response
from starlette.requests import ClientDisconnect


ENGINE = "corvus-kokoro"
URL = "http://127.0.0.1:8105/v1/audio/speech"
VOICE = "af_mica"
MAX_REQUEST_BYTES = 24 * 1024
MAX_TEXT_CHARS = 4000
MAX_AUDIO_BYTES = 8 * 1024 * 1024
BODY_SECONDS = 5
SYNTHESIS_SECONDS = 60
PRIVATE = {"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"}


def fail(status, detail):
    # Never return upstream bodies, exception strings or submitted text.
    return HTTPException(status, detail, headers=PRIVATE)


def require_enabled(request):
    if request.app.state.config.TTS_ENGINE != ENGINE:
        raise fail(503, "Lab Read Aloud is not enabled.")


async def read_text(request):
    if request.headers.get("content-type", "").split(";", 1)[0].lower() != "application/json":
        raise fail(415, "Read Aloud requires JSON.")
    body = bytearray()
    try:
        async with asyncio.timeout(BODY_SECONDS):
            async for chunk in request.stream():
                if len(body) + len(chunk) > MAX_REQUEST_BYTES:
                    raise fail(413, "Read Aloud request is too large.")
                body.extend(chunk)
    except TimeoutError:
        raise fail(408, "Read Aloud input timed out.") from None
    except ClientDisconnect:
        raise fail(499, "Read Aloud client disconnected.") from None
    try:
        payload = json.loads(body)
    except (ValueError, UnicodeError, RecursionError):
        raise fail(400, "Invalid Read Aloud request.") from None
    if not isinstance(payload, dict) or set(payload) - {"input", "voice", "model"}:
        raise fail(400, "Unsupported Read Aloud fields.")
    text = payload.get("input")
    if not isinstance(text, str) or not 0 < len(text) <= MAX_TEXT_CHARS:
        raise fail(400, "Read Aloud text must contain 1 to 4000 characters.")
    if (payload.get("voice", VOICE) != VOICE
            or payload.get("model", "kokoro") != "kokoro"):
        raise fail(400, "Only the configured Kokoro model and voice are supported.")
    # Same presentation-only whitespace preparation as app/tts.py.
    text = re.sub(r"\s+", " ", text).strip()
    if not text or any(ord(c) < 32 for c in text) or any(0xD800 <= ord(c) <= 0xDFFF for c in text):
        raise fail(400, "Invalid Read Aloud text.")
    return text


def finalize_wav(audio):
    try:
        if audio[:4] != b"RIFF" or audio[8:12] != b"WAVE":
            raise ValueError
        audio = bytearray(audio)
        # The installed Kokoro/PyAV writer emits streaming length sentinels even
        # for stream=false. Finalize only that observed format after full receipt.
        if int.from_bytes(audio[4:8], "little") == 0xFFFFFFFF:
            offset = 12
            while offset + 8 <= len(audio):
                size = int.from_bytes(audio[offset + 4:offset + 8], "little")
                if audio[offset:offset + 4] == b"data":
                    if size != 0xFFFFFFFF:
                        raise ValueError
                    audio[offset + 4:offset + 8] = (len(audio) - offset - 8).to_bytes(4, "little")
                    audio[4:8] = (len(audio) - 8).to_bytes(4, "little")
                    break
                if size == 0xFFFFFFFF:
                    raise ValueError
                offset += 8 + size + size % 2
            else:
                raise ValueError
        if int.from_bytes(audio[4:8], "little") != len(audio) - 8:
            raise ValueError
        with wave.open(io.BytesIO(audio), "rb") as wav:
            if (wav.getcomptype() != "NONE" or wav.getnchannels() not in (1, 2)
                    or wav.getsampwidth() != 2 or wav.getframerate() != 24000
                    or wav.getnframes() <= 0):
                raise ValueError
            expected = wav.getnframes() * wav.getnchannels() * wav.getsampwidth()
            if expected > MAX_AUDIO_BYTES or len(wav.readframes(wav.getnframes() + 1)) != expected:
                raise ValueError
        return bytes(audio)
    except (ValueError, EOFError, wave.Error):
        raise fail(502, "Kokoro returned invalid WAV audio.") from None


async def synthesize(text):
    payload = {"model": "kokoro", "input": text, "voice": VOICE,
               "lang_code": "z", "speed": 0.95, "response_format": "wav",
               "stream": False, "return_download_link": False}
    try:
        async with asyncio.timeout(SYNTHESIS_SECONDS):
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(SYNTHESIS_SECONDS, connect=3),
                follow_redirects=False, trust_env=False,
                transport=httpx.AsyncHTTPTransport(retries=0),
            ) as client:
                async with client.stream(
                    "POST", URL, json=payload,
                    headers={"Accept": "audio/wav", "Accept-Encoding": "identity"},
                ) as response:
                    if response.status_code != 200:
                        raise fail(502, "Kokoro synthesis failed.")
                    if (response.headers.get("content-type", "").split(";", 1)[0].lower() != "audio/wav"
                            or response.headers.get("content-encoding", "identity").lower() != "identity"):
                        raise fail(502, "Kokoro returned an unsupported audio format.")
                    audio = bytearray()
                    async for chunk in response.aiter_raw():
                        if len(audio) + len(chunk) > MAX_AUDIO_BYTES:
                            raise fail(502, "Kokoro audio exceeded the response limit.")
                        audio.extend(chunk)
                    return finalize_wav(audio)
    except (TimeoutError, httpx.TimeoutException):
        raise fail(504, "Kokoro synthesis timed out.") from None
    except httpx.HTTPError:
        raise fail(502, "Kokoro is unavailable.") from None


async def wait_for_disconnect(request):
    while True:
        if (await request.receive())["type"] == "http.disconnect":
            return


async def speech(request: Request):
    # Native audio.py retains its get_verified_user dependency before this call.
    require_enabled(request)
    text = await read_text(request)
    async def render():
        # A debug-mode asyncio Task repr must not contain returned audio bytes.
        return Response(await synthesize(text), media_type="audio/wav", headers=PRIVATE)
    work = asyncio.create_task(render())
    disconnected = asyncio.create_task(wait_for_disconnect(request))
    try:
        done, _ = await asyncio.wait((work, disconnected), return_when=asyncio.FIRST_COMPLETED)
        if disconnected in done:
            raise fail(499, "Read Aloud client disconnected.")
        return await work
    finally:
        for task in (work, disconnected):
            task.cancel()
        # Close transport/watch tasks even when the ASGI request is cancelled.
        with suppress(asyncio.CancelledError):
            await asyncio.gather(work, disconnected, return_exceptions=True)


async def voices(request: Request):
    require_enabled(request)
    # One supported installed voice; no upstream discovery or generic voice API.
    return JSONResponse({"voices": [{"id": VOICE, "name": VOICE}]}, headers=PRIVATE)
