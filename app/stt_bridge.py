"""Standalone stateless Lab bridge, never mounted on the canonical chat API.

The exported ASGI app is unconditionally inert (no token or transcriber). Only
explicit in-process test injection exercises a working request chain at R2.
"""
import hmac
import urllib.request

from fastapi import FastAPI, HTTPException, Request
from starlette.responses import Response

from app.stt_protocol import MAX_AUDIO, MAX_RESPONSE, PRIVATE, REQUEST_SECONDS, fail, read_bounded, text_payload, validate_audio
from app.transcription import transcribe_audio_bytes

WHISPER_BASE = 'http://corvus-whisper:8080'
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
        language='auto', base_url=WHISPER_BASE, timeout=REQUEST_SECONDS, opener=whisper_opener)


def create_app(*, token=None, transcriber=None):
    # No environment enable flag or baked-in credential. Future wiring is a new review.
    if token is not None and (not isinstance(token, bytes) or not 32 <= len(token) <= 128 or not token.isalnum()):
        raise ValueError('invalid bridge credential configuration')
    bridge = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, redirect_slashes=False)

    @bridge.post('/v1/transcribe')
    async def transcribe(request: Request):
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
        audio = validate_audio(await read_bounded(request, MAX_AUDIO))
        try:
            # R1 uses a synchronous bounded urllib call. This worker owns no canonical
            # state. Cancellation cannot kill its Python thread: see the R2 limitations.
            from starlette.concurrency import run_in_threadpool
            text = await run_in_threadpool(transcriber, audio)
            return Response(text_payload(text), media_type='application/json', headers=PRIVATE)
        except HTTPException:
            raise
        except Exception:
            raise fail(502, 'Transcription failed.') from None

    return bridge


app = create_app()  # Always disabled; never register on app.playground_api.
