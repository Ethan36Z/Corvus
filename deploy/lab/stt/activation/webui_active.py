"""Native verified-user route delegates here; preserve its R2 parser/transport."""
from open_webui.routers.corvus_stt import transcription as core, bridge_text
from open_webui.routers.corvus_stt_protocol import service_token, admissions_open, fail


async def transcription(request):
    if not admissions_open():
        raise fail(503, 'Lab transcription is disabled.')
    token = service_token()

    async def dispatch(audio):
        return await bridge_text(audio, token=token)

    return await core(request, bridge=dispatch)
