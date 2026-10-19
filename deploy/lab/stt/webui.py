"""Native WebUI STT adapter; no Corvus Python imports across containers."""
import asyncio
from email import policy
from email.parser import BytesParser
import json
import re

from fastapi import HTTPException
import httpx
from starlette.responses import Response
from open_webui.routers.corvus_stt_protocol import (
    MAX_AUDIO, MAX_REQUEST, MAX_RESPONSE, PRIVATE, REQUEST_SECONDS,
    fail, read_bounded, text_payload, validate_audio,
)

BRIDGE_URL = 'http://corvus-stt-bridge:8106/v1/transcribe'


async def bridge_text(audio, *, token):
    if not isinstance(token, bytes) or not 32 <= len(token) <= 128 or not token.isalnum():
        raise fail(503, 'Lab transcription is disabled.')
    try:
        async with asyncio.timeout(REQUEST_SECONDS):
            async with httpx.AsyncClient(timeout=httpx.Timeout(REQUEST_SECONDS, connect=3),
                    follow_redirects=False, trust_env=False,
                    transport=httpx.AsyncHTTPTransport(retries=0)) as client:
                async with client.stream('POST', BRIDGE_URL, content=audio, headers={
                        'Authorization': 'Bearer '+token.decode('ascii'), 'Content-Type': 'audio/wav',
                        'Accept': 'application/json', 'Accept-Encoding': 'identity'}) as reply:
                    if (reply.status_code != 200 or reply.headers.get('content-type', '').split(';')[0].lower() != 'application/json'
                            or reply.headers.get('content-encoding', 'identity').lower() != 'identity'):
                        raise fail(502, 'Transcription failed.')
                    data = bytearray()
                    async for chunk in reply.aiter_raw():
                        if len(data)+len(chunk) > MAX_RESPONSE:
                            raise fail(502, 'Transcription response is too large.')
                        data.extend(chunk)
                    payload = json.loads(data)
                    if not isinstance(payload, dict) or set(payload) != {'text'}:
                        raise ValueError
                    return json.loads(text_payload(payload['text']))['text']
    except (TimeoutError, httpx.TimeoutException):
        raise fail(504, 'Transcription timed out.') from None
    except HTTPException:
        raise
    except Exception:
        raise fail(502, 'Transcription failed.') from None


async def transcription(request, *, bridge=None):
    # The pinned native route retains Depends(get_verified_user) before this call.
    # No env/header/query setting enables dispatch. Tests inject a bridge callable.
    if bridge is None:
        raise fail(503, 'Lab transcription is disabled.')
    header = request.headers.get('content-type', '')
    if request.url.query or len(header) > 200 or '\r' in header or '\n' in header:
        raise fail(400, 'Invalid audio request.')
    try:
        envelope = BytesParser(policy=policy.default).parsebytes(('Content-Type: '+header+'\r\n\r\n').encode('ascii')
            + await read_bounded(request, MAX_REQUEST))
        if envelope.get_content_type() != 'multipart/form-data' or not envelope.is_multipart() or envelope.defects:
            raise ValueError
        if not re.fullmatch(r"[A-Za-z0-9'()+_,./:=?-]{1,70}", envelope.get_boundary() or ''):
            raise ValueError
        parts = list(envelope.iter_parts())
        if len(parts) != 1:
            raise ValueError
        part = parts[0]
        if (part.is_multipart() or part.defects or part.get_content_disposition() != 'form-data'
                or part.get_param('name', header='content-disposition') != 'file'
                or not part.get_filename() or len(part.get_filename()) > 255
                or part.get('Content-Transfer-Encoding') is not None
                or part.get_content_type() not in {'audio/wav', 'audio/x-wav'}):
            raise ValueError
        audio = validate_audio(part.get_payload(decode=True))
    except HTTPException:
        raise
    except Exception:
        raise fail(400, 'Invalid audio request.') from None
    try:
        return Response(text_payload(await bridge(audio)), media_type='application/json', headers=PRIVATE)
    except HTTPException:
        raise
    except Exception:
        raise fail(502, 'Transcription failed.') from None
