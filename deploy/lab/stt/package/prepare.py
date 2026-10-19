"""Build isolated offline contexts from verified cached sources; never touch runtime."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[4]
BASE='sha256:72252f095805fa8aebb6ed17e7fb44c3746e9d2a289ec3ff395769aad0c44e3b'

def load(path):
    spec=importlib.util.spec_from_file_location('package_'+path.stem,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def prepare(source, public_base, output):
    source,public_base,output=(Path(p).resolve() for p in (source,public_base,output))
    assert not output.exists(), 'Require a fresh output tree'
    assert all(output!=p and output not in p.parents and p not in output.parents for p in (source,public_base,ROOT))
    branding=load(ROOT/'deploy/open-webui/branding/verify_branding.py')
    branding.source_checks(source,arena_ui2=True)
    frontend=load(ROOT/'deploy/lab/stt/prepare_frontend.py')
    native=load(ROOT/'deploy/lab/stt/prepare_audio.py')
    transformed=frontend.patch_sources({p:(source/p).read_text() for p in frontend.PINS})
    audio=(public_base/'audio.py').read_text()
    patched=native.patch_audio(audio) # Exact current TTS-enabled source, native auth retained.
    assert json.loads((public_base/'package.json').read_text())['version']=='0.6.5'
    assert (public_base/'corvus_tts.py').read_bytes()==(ROOT/'deploy/lab/tts/kokoro.py').read_bytes()
    response='src/lib/components/chat/Messages/ResponseMessage.svelte'
    old=(source/response).read_text()
    assert hashlib.sha256(old.encode()).hexdigest()=='48cfca12c0e8fc857a3078a5c0f7e7abda6616f82ac704c1ee037c184cac409b'
    debug="\t\t\tconsole.debug('Prepared message content for TTS', messageContentParts);\n"
    assert old.count(debug)==1
    transformed[response]=old.replace(debug,'') # Preserve the active TTS privacy patch during rebuild.
    output.mkdir()
    src=output/'source'
    shutil.copytree(source,src,ignore=shutil.ignore_patterns('node_modules','.svelte-kit','build','.git'))
    for name,text in transformed.items():
        path=src/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)
    shutil.copytree(ROOT/'deploy/open-webui/branding/assets',src/'static/static',dirs_exist_ok=True)
    shutil.copyfile(ROOT/'deploy/open-webui/branding/assets/favicon.png',src/'static/favicon.png')
    shutil.copytree(public_base/'pyodide',src/'static/pyodide',dirs_exist_ok=True)
    web=output/'webui';web.mkdir()
    (web/'audio.py').write_text(patched)
    shutil.copyfile(ROOT/'deploy/lab/stt/webui.py',web/'corvus_stt.py')
    shutil.copyfile(ROOT/'app/stt_protocol.py',web/'corvus_stt_protocol.py')
    (web/'Dockerfile').write_text(f'''FROM {BASE}
COPY audio.py corvus_stt.py corvus_stt_protocol.py /app/backend/open_webui/routers/
RUN rm -rf /app/build
COPY build/ /app/build/
LABEL io.corvus.scope="lab" io.corvus.stt="r7-disabled" io.corvus.stt.base="{BASE}"
''')
    bridge=output/'bridge';bridge.mkdir()
    files=['app/stt_bridge.py','app/stt_protocol.py','app/transcription.py','memory/attachments.py','memory/store.py','memory/config.py']
    for name in files:
        path=bridge/name;path.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,path)
    (bridge/'Dockerfile').write_text(f'''FROM {BASE}
WORKDIR /opt/corvus
COPY app/ /opt/corvus/app/
COPY memory/ /opt/corvus/memory/
ENV PYTHONPATH=/opt/corvus PYTHONDONTWRITEBYTECODE=1 CORVUS_DATA_DIR=/nonexistent-canonical-data
USER 10001:10001
ENTRYPOINT ["/bin/sh", "-c"]
CMD ["exec python -B -m uvicorn app.stt_bridge:app --host 0.0.0.0 --port 8106 --workers 1 --no-access-log --log-level critical --lifespan off --limit-concurrency 2 --timeout-keep-alive 2 >/dev/null 2>&1"]
LABEL io.corvus.scope="lab" io.corvus.stt="r7-disabled" io.corvus.stt.base="{BASE}"
''')
    proof={'runtime_image':BASE,'source_version':'0.6.5','modified_frontend':{p:hashlib.sha256(text.encode()).hexdigest() for p,text in transformed.items()},'backend_audio_sha256':hashlib.sha256(patched.encode()).hexdigest(),'source_checks':'117 original branding/Arena files verified before isolated edits','gates':'both disabled; no token or callable wired','bridge_modules':files}
    (output/'proof.json').write_text(json.dumps(proof,indent=2)+'\n')
    return proof

if __name__=='__main__':print(json.dumps(prepare(*sys.argv[1:]),indent=2))
