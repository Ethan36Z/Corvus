"""Backend-only contexts, exact R7 native route; no frontend regeneration."""
import hashlib
from pathlib import Path
import shutil
import sys
ROOT=Path(__file__).resolve().parents[4]
WEBUI='sha256:6a1d1843c52be7b5a1a66d503a8c16514f617d4a478ddd9dc6e09b45858487db'
BRIDGE='sha256:538fbebfc017b2cd628e540cb4a537aee99b7704cc637e9932f1801d1e4a997b'

def prepare(audio, output):
    audio,output=Path(audio).resolve(),Path(output).resolve()
    assert not output.exists()
    text=audio.read_text()
    assert hashlib.sha256(text.encode()).hexdigest()=='b9f10084b5b1cd75f5c9ba915cb2af3d0136eb925d15e9c98835ab81549d6ca7'
    old='from open_webui.routers.corvus_stt import transcription as handle'
    assert text.count(old)==1
    patched=text.replace(old,'from open_webui.routers.corvus_stt_active import transcription as handle')
    for part in ['webui','bridge']:(output/part).mkdir(parents=True)
    w=output/'webui';b=output/'bridge'
    (w/'audio.py').write_text(patched)
    shutil.copyfile(ROOT/'app/stt_protocol.py',w/'corvus_stt_protocol.py')
    shutil.copyfile(ROOT/'deploy/lab/stt/activation/webui_active.py',w/'corvus_stt_active.py')
    (w/'Dockerfile').write_text(f'FROM {WEBUI}\nCOPY audio.py corvus_stt_protocol.py corvus_stt_active.py /app/backend/open_webui/routers/\nLABEL io.corvus.stt="lab-active-wired" io.corvus.scope="lab"\n')
    shutil.copyfile(ROOT/'app/stt_protocol.py',b/'stt_protocol.py');shutil.copyfile(ROOT/'app/stt_active.py',b/'stt_active.py')
    (b/'Dockerfile').write_text(f'''FROM {BRIDGE}
COPY stt_protocol.py stt_active.py /opt/corvus/app/
CMD ["exec python -B -m uvicorn app.stt_active:app --host 0.0.0.0 --port 8106 --workers 1 --no-access-log --log-level critical --lifespan off --limit-concurrency 2 --timeout-keep-alive 2 >/dev/null 2>&1"]
LABEL io.corvus.stt="lab-active-wired" io.corvus.scope="lab"
''')
if __name__=='__main__':prepare(*sys.argv[1:])
