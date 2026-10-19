"""Credential-only tests; container modes use real mounts, synthetic WAV/mock R1."""
import ast
import asyncio
import importlib.util
import io
import json
import logging
import os
from pathlib import Path
import resource
import sys
import unittest
import wave

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('credential_repair', ROOT/'deploy/lab/stt/activation/credential_repair.py')
repair = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(repair)


class RepairContracts(unittest.TestCase):
    def test_only_fixed_owner_changes(self):
        original = (ROOT/'app/stt_protocol.py').read_bytes()
        self.assertEqual(repair.webui_protocol(), original.replace(b'metadata.st_uid != 10001', b'metadata.st_uid != 0'))
        before, after = ast.parse(original), ast.parse(repair.webui_protocol())
        old = next(n for n in ast.walk(before) if isinstance(n, ast.Compare) and ast.unparse(n)=='metadata.st_uid != 10001')
        old.comparators[0].value = 0
        self.assertEqual(ast.dump(before), ast.dump(after))

    def test_compose_distinct_readonly_consumers(self):
        import yaml
        config = yaml.safe_load((ROOT/'deploy/lab/stt/activation/compose.yml').read_text())['services']
        w, b = config['open-webui']['volumes'], config['corvus-stt-bridge']['volumes']
        self.assertIn('CORVUS_STT_WEBUI_SECRET_FILE', w[0]['source'])
        self.assertIn('CORVUS_STT_BRIDGE_SECRET_FILE', b[0]['source'])
        self.assertNotIn('CORVUS_STT_SECRET_FILE', str(config))
        for item in w+b:
            self.assertTrue(item['read_only'])
            self.assertFalse(item['bind']['create_host_path'])
        self.assertEqual(w[-1]['target'], '/app/backend/open_webui/routers/corvus_stt_protocol.py')
        self.assertEqual(config['open-webui']['environment']['USER_PERMISSIONS_CHAT_STT'], '${CORVUS_STT_PERMISSION:-false}')


def security(uid):
    assert os.getuid()==uid
    status=Path('/proc/self/status').read_text()
    assert next(x for x in status.splitlines() if x.startswith('CapEff:')).split()[1]=='0000000000000000'
    assert next(x for x in status.splitlines() if x.startswith('NoNewPrivs:')).split()[1]=='1'
    assert resource.getrlimit(resource.RLIMIT_CORE)==(0,0)


def protocol(consumer):
    if consumer=='webui':
        sys.path.insert(0,'/app/backend')
        from open_webui.routers import corvus_stt_protocol as p
    else:
        from app import stt_protocol as p
    return p


def negative(consumer):
    security(0 if consumer=='webui' else 10001)
    p=protocol(consumer)
    try:p.service_token()
    except Exception as exc:assert exc.status_code==503 and exc.detail=='Lab transcription is unavailable.'
    else:raise AssertionError('Credential must fail closed')
    if consumer=='bridge':
        # Actual startup cannot construct the exported app with a bad secret.
        try:__import__('app.stt_active')
        except Exception as exc:assert exc.status_code==503
        else:raise AssertionError('Bridge initialization must fail closed')
    print(json.dumps({'consumer':consumer,'credential_failure':503,'uid':os.getuid(),'zero_capabilities':True}))


def wav():
    b=io.BytesIO()
    with wave.open(b,'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000);w.writeframes(b'\0\0'*160)
    return b.getvalue()


def serve_bridge():
    security(10001)
    from app import stt_bridge as b
    from unittest.mock import patch
    from email.message import Message
    class Reply:
        def __enter__(self):return self
        def __exit__(self,*unused):return False
        def read(self):return json.dumps({'text':'中文 English synthetic'}).encode()
    def mocked(request, timeout):
        assert request.full_url==b.WHISPER_URL=='http://corvus-whisper-dictation:8080/inference'
        assert request.method=='POST' and b'filename="dictation.wav"' in request.data and wav() in request.data
        assert timeout==25
        return Reply()
    b.whisper_opener=mocked
    from app.stt_active import app
    import sqlite3,uvicorn
    # Any canonical write path is a test failure; never import/start canonical API.
    with patch.object(sqlite3,'connect',side_effect=AssertionError('No database access')):
        uvicorn.run(app,host='127.0.0.1',port=18106,workers=1,access_log=False,log_level='critical',lifespan='off',limit_concurrency=2,timeout_keep_alive=2)


async def webui(stage):
    import httpx
    from fastapi import FastAPI,Depends,HTTPException,Request
    from unittest.mock import patch
    import sqlite3
    security(0)
    p=protocol('webui');token=p.service_token();assert len(token)==64
    assert p.admissions_open()==(stage=='open')
    async def verified(request:Request):
        if request.headers.get('x-synthetic-user')!='verified':raise HTTPException(403,'Not authenticated')
        return object()
    # Use exact image native handler/signature without starting WebUI or its DB.
    tree=ast.parse(Path('/app/backend/open_webui/routers/audio.py').read_text())
    node=next(n for n in tree.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='transcription')
    assert ast.unparse(node.args)=='request: Request, user=Depends(get_verified_user)'
    assert ast.unparse(node.body[0])=='from open_webui.routers.corvus_stt_active import transcription as handle'
    node.decorator_list=[]
    ns={'Request':Request,'Depends':Depends,'get_verified_user':verified}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),'native-handler','exec'),ns)
    app=FastAPI();app.post('/api/v1/audio/transcriptions')(ns['transcription'])
    from open_webui.routers.corvus_stt import BRIDGE_URL
    assert BRIDGE_URL=='http://127.0.0.1:18106/v1/transcribe'
    with patch.object(sqlite3,'connect',side_effect=AssertionError('No database access')):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://isolated') as c:
            path='/api/v1/audio/transcriptions'
            assert (await c.post(path,content=b'bad')).status_code==403
            r=await c.post(path,headers={'x-synthetic-user':'verified'},files={'file':('synthetic.wav',wav(),'audio/wav')})
            assert r.status_code==(200 if stage=='open' else 503)
            if stage=='open':assert r.json()=={'text':'中文 English synthetic'} and r.headers['cache-control']=='private, no-store'
        async with httpx.AsyncClient(trust_env=False,follow_redirects=False,timeout=5) as c:
            if stage=='closed':
                assert (await c.post(BRIDGE_URL,content=b'bad')).status_code==503
            else:
                assert (await c.post(BRIDGE_URL,content=b'bad')).status_code==401
                wrong=bytes([ord('b') if token[0]==ord('a') else ord('a')])+token[1:]
                for key,expected in [(wrong,401),(token,200)]:
                    r=await c.post(BRIDGE_URL,content=wav(),headers={'Authorization':'Bearer '+key.decode(),'Content-Type':'audio/wav'})
                    assert r.status_code==expected
    print(json.dumps({'consumer':'webui','uid':0,'zero_capabilities':True,'stage':stage,'native_auth':403,'assigned_secret_read':True,'fixed_dispatch_mocked':stage=='open','bridge_auth_checked':stage=='open','database_accesses':0}))


if __name__=='__main__':
    logging.disable(logging.CRITICAL)
    if len(sys.argv)==1:unittest.main()
    elif sys.argv[1]=='serve-bridge':serve_bridge()
    elif sys.argv[1]=='webui':asyncio.run(webui(sys.argv[2]))
    elif sys.argv[1]=='negative':negative(sys.argv[2])
