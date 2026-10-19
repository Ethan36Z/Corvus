"""Standalone stateless Lab bridge, never mounted on the canonical chat API.

The exported ASGI app is unconditionally inert (no token or transcriber). Only
explicit in-process test injection exercises a working request chain at R2.
"""
import asyncio
import contextlib
import hmac
import urllib.request

from fastapi import FastAPI, HTTPException, Request
from starlette.responses import Response

from app.stt_protocol import MAX_AUDIO, MAX_RESPONSE, PRIVATE, REQUEST_SECONDS, fail, read_bounded, text_payload, validate_audio
from app.transcription import transcribe_audio_bytes

WHISPER_BASE = 'http://corvus-whisper-dictation:8080'
INFERENCE_SECONDS = 25
WHISPER_URL = WHISPER_BASE + '/inference'


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class BoundedReply:
    def __init__(self, response):
        self.response = response

    def __enter__(self):
        return self

    def __exit__(self, *unused):
        self.response.close()

    def read(self):
        data = self.response.read(MAX_RESPONSE + 1)
        if len(data) > MAX_RESPONSE:
            raise ValueError('bounded upstream response')
        return data


def whisper_opener(request, timeout):
    if request.full_url != WHISPER_URL or request.method != 'POST':
        raise ValueError('fixed upstream target required')
    # Reuse R1 multipart; change only transport policy via its existing opener seam.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    response = opener.open(request, timeout=timeout)
    try:
        if (response.status != 200 or response.geturl() != WHISPER_URL
                or response.headers.get_content_type() != 'application/json'
                or response.headers.get('Content-Encoding', 'identity').lower() != 'identity'):
            raise ValueError('unsupported upstream response')
    except BaseException:
        response.close()
        raise
    return BoundedReply(response)


def whisper_text(audio):
    return transcribe_audio_bytes(audio, filename='dictation.wav', media_type='audio/wav',
        language='auto', base_url=WHISPER_BASE, timeout=INFERENCE_SECONDS, opener=whisper_opener)


def create_app(*, token=None, transcriber=None):
    # No environment enable flag or baked-in credential. Future wiring is a new review.
    if token is not None and (not isinstance(token, bytes) or not 32 <= len(token) <= 128 or not token.isalnum()):
        raise ValueError('invalid bridge credential configuration')
    bridge = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, redirect_slashes=False)

    # One event-loop worker / one in-flight body+inference. No admission queue.
    # Keep ownership until the real synchronous worker settles, even on timeout.
    slot = None

    @bridge.post('/v1/transcribe')
    async def transcribe(request: Request):
        nonlocal slot
        if token is None:
            raise fail(503, 'Lab transcription is disabled.')
        auth = request.headers.getlist('authorization')
        try:
            allowed = len(auth) == 1 and hmac.compare_digest(auth[0].encode('ascii'), b'Bearer '+token)
        except UnicodeError:
            allowed = False
        if not allowed:
            raise fail(401, 'Bridge authentication required.')
        if transcriber is None:
            raise fail(503, 'Lab transcription is disabled.')
        if request.url.query or request.headers.get('content-type', '').lower() != 'audio/wav':
            raise fail(415, 'Unsupported audio request.')
        if slot is not None:
            raise fail(429, 'Transcription is busy.')
        owner = object()
        slot = owner
        worker = None
        disconnect = None
        stop_polling = asyncio.Event()

        def release(task):
            nonlocal slot
            if slot is owner:
                slot = None
            # Consume late exceptions without logging provider text.
            if not task.cancelled():
                task.exception()

        async def disconnected():
            while not stop_polling.is_set():
                if await request.is_disconnected():
                    return
                await asyncio.sleep(0.1)

        try:
            audio = validate_audio(await read_bounded(request, MAX_AUDIO))
            from starlette.concurrency import run_in_threadpool
            worker = asyncio.create_task(run_in_threadpool(transcriber, audio))
            disconnect = asyncio.create_task(disconnected())
            done, _ = await asyncio.wait({worker, disconnect}, timeout=INFERENCE_SECONDS,
                                         return_when=asyncio.FIRST_COMPLETED)
            if disconnect in done:
                raise fail(499, 'Transcription cancelled.')
            if worker not in done:
                raise fail(504, 'Transcription timed out.')
            return Response(text_payload(worker.result()), media_type='application/json', headers=PRIVATE)
        except HTTPException:
            raise
        except Exception:
            raise fail(502, 'Transcription failed.') from None
        finally:
            if disconnect is not None:
                stop_polling.set()
                disconnect.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await disconnect
            if worker is not None and not worker.done():
                worker.add_done_callback(release)
            else:
                if worker is not None:
                    release(worker)
                elif slot is owner:
                    slot = None

    return bridge


app = create_app()  # Always disabled; never register on app.playground_api.
