"""Authorized Lab activation wrapper around the existing R6 bridge."""
from starlette.responses import JSONResponse
from app.stt_bridge import create_app, whisper_text
from app.stt_protocol import service_token, admissions_open, PRIVATE


class Admissions:
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        if scope['type'] == 'http' and not admissions_open():
            await JSONResponse({'detail': 'Lab transcription is disabled.'}, status_code=503,
                               headers=PRIVATE)(scope, receive, send)
            return
        await self.inner(scope, receive, send)


def build_app():
    return Admissions(create_app(token=service_token(), transcriber=whisper_text))


app = build_app()
