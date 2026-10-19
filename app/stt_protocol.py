"""Shared, bounded in-memory STT envelope; no persistence or transport imports."""
import asyncio
import io
import os
import stat
import json
import wave

from fastapi import HTTPException
from starlette.requests import ClientDisconnect

MAX_AUDIO = 8 * 1024 * 1024
MAX_REQUEST = MAX_AUDIO + 16 * 1024
MAX_RESPONSE = 64 * 1024
MAX_TEXT = 16 * 1024
BODY_SECONDS = 5
REQUEST_SECONDS = 30
PRIVATE = {'Cache-Control': 'private, no-store', 'X-Content-Type-Options': 'nosniff'}


def fail(status, message):
    return HTTPException(status, message, headers=PRIVATE)


async def read_bounded(request, maximum):
    if request.headers.get('content-encoding', 'identity').lower() != 'identity':
        raise fail(415, 'Unsupported audio request.')
    length = request.headers.get('content-length')
    if length is not None:
        if not length.isascii() or not length.isdecimal():
            raise fail(400, 'Invalid audio request.')
        if len(length) > 12 or int(length) > maximum:
            raise fail(413, 'Audio request is too large.')
    data = bytearray()
    try:
        async with asyncio.timeout(BODY_SECONDS):
            async for chunk in request.stream():
                if len(data) + len(chunk) > maximum:
                    raise fail(413, 'Audio request is too large.')
                data.extend(chunk)
    except TimeoutError:
        raise fail(408, 'Audio upload timed out.') from None
    except ClientDisconnect:
        raise fail(499, 'Audio upload disconnected.') from None
    return bytes(data)


def validate_audio(data):
    # This checkpoint deliberately supports canonical PCM WAV only, no converter.
    if len(data) > MAX_AUDIO:
        raise fail(413, 'Audio request is too large.')
    try:
        if data[:4] != b'RIFF' or data[8:12] != b'WAVE' or int.from_bytes(data[4:8], 'little') != len(data)-8:
            raise ValueError
        with wave.open(io.BytesIO(data), 'rb') as audio:
            channels, width, rate, frames = (audio.getnchannels(), audio.getsampwidth(),
                                            audio.getframerate(), audio.getnframes())
            if (channels not in (1, 2) or width != 2 or rate != 16000
                    or audio.getcomptype() != 'NONE' or not 0 < frames <= 120 * rate):
                raise ValueError
            expected = frames * channels * width
            if expected > MAX_AUDIO or len(audio.readframes(frames+1)) != expected:
                raise ValueError
    except (ValueError, EOFError, wave.Error):
        raise fail(400, 'Invalid or unsupported PCM WAV audio.') from None
    return data


def text_payload(text):
    if (not isinstance(text, str) or not text.strip() or len(text) > MAX_TEXT
            or any(0xD800 <= ord(c) <= 0xDFFF for c in text)):
        raise fail(502, 'Transcription failed.')
    data = json.dumps({'text': text.strip()}, ensure_ascii=False).encode('utf-8')
    if len(data) > MAX_RESPONSE:
        raise fail(502, 'Transcription response is too large.')
    return data


# Fixed operator-owned, read-only container mounts. Never request/env controlled.
SERVICE_SECRET = '/run/secrets/corvus_stt_bridge'
ADMISSIONS = '/run/secrets/corvus_stt_admissions'

def service_token():
    try:
        descriptor = os.open(SERVICE_SECRET, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            metadata = os.fstat(descriptor)
            if (not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != 10001
                    or stat.S_IMODE(metadata.st_mode) != 0o400 or metadata.st_size != 64):
                raise ValueError
            token = os.read(descriptor, 65)
            if len(token) != 64 or any(c not in b'0123456789abcdef' for c in token):
                raise ValueError
            return token
        finally:
            os.close(descriptor)
    except Exception:
        raise fail(503, 'Lab transcription is unavailable.') from None


def admissions_open():
    try:
        descriptor = os.open(ADMISSIONS, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            metadata = os.fstat(descriptor)
            return (stat.S_ISREG(metadata.st_mode) and metadata.st_size == 5
                    and os.read(descriptor, 16) == b'open\n')
        finally:
            os.close(descriptor)
    except Exception:
        return False
