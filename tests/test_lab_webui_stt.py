"""R2 ASGI contracts with synthetic credentials/audio and mocked Whisper only."""
import ast
from contextlib import ExitStack
from email.message import Message
import hashlib
import importlib.util
import io
import json
import logging
from pathlib import Path
import socket
import sqlite3
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import urllib.error
import wave

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
import httpx
from app import stt_bridge as bridge
from app import stt_protocol as protocol

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path('/tmp/corvus-stt-r2-source')
TOKEN = b'OnlySyntheticBridgeCredentialForOfflineTests123456789'
RealClient = httpx.AsyncClient


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def wav_bytes():
    data = io.BytesIO()
    with wave.open(data, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
        w.writeframes(b'\0\0'*160)
    return data.getvalue()


class Reply:
    status = 200
    def __init__(self, data=b'{"text":"recognized text"}', **kwargs):
        self.data = data
        self.closed = False
        self.headers = Message(); self.headers['Content-Type'] = 'application/json'
        self.__dict__.update(kwargs)
    def geturl(self): return bridge.WHISPER_URL
    def read(self, count): return self.data[:count]
    def close(self): self.closed = True


class STTContracts(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.prepare = load('stt_r2_patch', ROOT/'deploy/lab/stt/prepare_audio.py')
        cls.source = (SOURCE/'audio.py').read_text()
        cls.patched = cls.prepare.patch_audio(cls.source)
        cls.modules = patch.dict(sys.modules, {'open_webui': ModuleType('open_webui'),
            'open_webui.routers': ModuleType('open_webui.routers'),
            'open_webui.routers.corvus_stt_protocol': protocol})
        cls.modules.start(); cls.addClassCleanup(cls.modules.stop)
        cls.webui = load('stt_r2_webui', ROOT/'deploy/lab/stt/webui.py')
        sys.modules['open_webui.routers.corvus_stt'] = cls.webui
        cls.addClassCleanup(sys.modules.pop, 'open_webui.routers.corvus_stt', None)
        async def current_user(request: Request):
            role = request.headers.get('x-synthetic-role')
            if not role: raise HTTPException(401, 'Not authenticated')
            return SimpleNamespace(role=role)
        namespace = {'Depends': Depends, 'get_current_user': current_user, 'HTTPException': HTTPException,
            'status': SimpleNamespace(HTTP_401_UNAUTHORIZED=401),
            'ERROR_MESSAGES': SimpleNamespace(ACCESS_PROHIBITED='Access prohibited')}
        native = next(n for n in ast.parse((SOURCE/'auth.py').read_text()).body
                      if isinstance(n, ast.FunctionDef) and n.name=='get_verified_user')
        exec(compile(ast.Module(body=[native],type_ignores=[]),'native-verified-user','exec'),namespace)
        router = APIRouter()
        namespace.update(router=router, Request=Request)
        route = next(n for n in ast.parse(cls.patched).body
                     if isinstance(n,ast.AsyncFunctionDef) and n.name=='transcription')
        exec(compile(ast.Module(body=[route],type_ignores=[]),'native-stt-route','exec'),namespace)
        cls.native = FastAPI(); cls.native.include_router(router,prefix='/api/v1/audio')

    async def request(self, *, audio=None, role='user', headers=None, raw=None, bridge_app=None):
        h={'x-synthetic-role':role} if role else {}
        h.update(headers or {})
        app=bridge_app or bridge.create_app(token=TOKEN, transcriber=bridge.whisper_text)
        async def dispatch(audio): return await self.webui.bridge_text(audio,token=TOKEN)
        actual=self.webui.transcription
        async def handler(request): return await actual(request,bridge=dispatch)
        with patch.object(self.webui,'transcription',handler), \
             patch.object(httpx,'AsyncHTTPTransport',return_value=httpx.ASGITransport(app=app)) as transport:
            async with RealClient(transport=httpx.ASGITransport(app=self.native),base_url='http://native-test') as client:
                if raw is not None:
                    reply=await client.post('/api/v1/audio/transcriptions',headers=h,content=raw)
                else:
                    reply=await client.post('/api/v1/audio/transcriptions',headers=h,
                        files={'file':('recording.wav',wav_bytes() if audio is None else audio,'audio/wav')})
        return reply,transport

    async def test_native_verified_auth_and_single_r1_transport(self):
        reply=Reply(json.dumps({'text':'中文 English transcript'}).encode())
        opener=Mock(); opener.open.return_value=reply
        with patch.object(bridge.urllib.request,'build_opener',return_value=opener) as builder:
            r,factory=await self.request(headers={'Authorization':'Bearer synthetic-browser-JWT'})
        self.assertEqual(r.status_code,200); self.assertEqual(r.json(),{'text':'中文 English transcript'})
        self.assertEqual(r.headers['cache-control'],'private, no-store')
        opener.open.assert_called_once(); factory.assert_called_once_with(retries=0)
        req=opener.open.call_args.args[0]
        self.assertEqual(req.full_url,bridge.WHISPER_URL)
        self.assertIsNone(req.get_header('Authorization'))
        self.assertIn(b'name="file"',req.data); self.assertIn(b'dictation.wav',req.data)
        self.assertIn(wav_bytes(),req.data); self.assertTrue(reply.closed)
        self.assertIsInstance(builder.call_args.args[0],bridge.urllib.request.ProxyHandler)
        self.assertEqual(builder.call_args.args[0].proxies,{})
        self.assertIsInstance(builder.call_args.args[1],bridge.NoRedirect)

    async def test_native_unauthenticated_and_unverified_rejected(self):
        for role in (None,'pending','blocked'):
            with self.subTest(role=role),patch.object(bridge,'whisper_text') as call:
                r,_=await self.request(role=role)
                self.assertEqual(r.status_code,401); call.assert_not_called()
        with patch.object(bridge.urllib.request,'build_opener',return_value=Mock(open=Mock(return_value=Reply()))):
            self.assertEqual((await self.request(role='admin'))[0].status_code,200)

    async def test_bridge_credential_required_before_body_read(self):
        call=Mock(return_value='text'); app=bridge.create_app(token=TOKEN,transcriber=call)
        for auth in (None,'Bearer wrong','Bearer '+TOKEN.decode()+'x'):
            consumed=[]
            async def chunks(): consumed.append(True); yield wav_bytes()
            async with RealClient(transport=httpx.ASGITransport(app=app),base_url='http://bridge-test') as c:
                r=await c.post('/v1/transcribe',headers={} if auth is None else {'authorization':auth},content=chunks())
            self.assertEqual(r.status_code,401); self.assertEqual(consumed,[])
        call.assert_not_called()
        with self.assertRaises(ValueError): bridge.create_app(token=b'weak',transcriber=call)

    async def test_exported_entry_points_always_disabled(self):
        async with RealClient(transport=httpx.ASGITransport(app=bridge.app),base_url='http://bridge-test') as c:
            self.assertEqual((await c.post('/v1/transcribe',content=wav_bytes())).status_code,503)
            self.assertEqual((await c.get('/docs')).status_code,404)
            self.assertEqual((await c.post('/v1/transcribe/')).status_code,404)
        async with RealClient(transport=httpx.ASGITransport(app=self.native),base_url='http://native-test') as c:
            r=await c.post('/api/v1/audio/transcriptions',headers={'x-synthetic-role':'user'},content=b'not read')
        self.assertEqual(r.status_code,503)

    async def test_invalid_and_oversized_audio(self):
        for data,code in ((b'not audio',400),(b'RIFF'+b'\0'*64,400),
                (wav_bytes()[:-2],400),(b'x'*(protocol.MAX_AUDIO+1),413)):
            with self.subTest(code=code),patch.object(bridge,'whisper_text') as call:
                r,_=await self.request(audio=data)
                self.assertEqual(r.status_code,code); call.assert_not_called()

    async def test_request_envelope_limits_and_fields(self):
        for content,headers,code in (
            (b'',{'content-type':'multipart/form-data; boundary=x','content-length':str(protocol.MAX_REQUEST+1)},413),
            (b'bad multipart',{'content-type':'multipart/form-data; boundary=x'},400),
            (b'{}',{'content-type':'application/json'},400),
            (b'x'*(protocol.MAX_REQUEST+1),{'content-type':'multipart/form-data; boundary=x'},413),
            (b'',{'content-type':'multipart/form-data; boundary=x','content-encoding':'gzip'},415)):
            with self.subTest(code=code): self.assertEqual((await self.request(raw=content,headers=headers))[0].status_code,code)

    async def test_storage_canonical_and_logging_guards(self):
        records=[]
        class Capture(logging.Handler):
            def emit(self,r): records.append(r.getMessage())
        capture=Capture(); logging.getLogger().addHandler(capture)
        try:
            opener=Mock(open=Mock(return_value=Reply(b'{"text":"PRIVATE_TRANSCRIPT_SENTINEL"}')))
            with ExitStack() as stack:
                for target in ('builtins.open','os.open','pathlib.Path.open','sqlite3.connect',
                    'tempfile.SpooledTemporaryFile','app.transcription.get_attachment',
                    'app.transcription.read_attachment_bytes','app.transcription.add_attachment_artifact',
                    'memory.attachments.store_attachment_bytes','memory.attachments.store_attachment_stream',
                    'memory.store.add_message','memory.store.connect'):
                    stack.enter_context(patch(target,side_effect=AssertionError('no persistence/cache')))
                stack.enter_context(patch.object(bridge.urllib.request,'build_opener',return_value=opener))
                r,_=await self.request()
                self.assertEqual(r.status_code,200)
            self.assertNotIn('PRIVATE_TRANSCRIPT_SENTINEL','\n'.join(records))
        finally:logging.getLogger().removeHandler(capture)

    async def test_whisper_errors_and_invalid_output_sanitized(self):
        for error in (urllib.error.URLError('PRIVATE_SENTINEL'),socket.timeout('PRIVATE_SENTINEL'),
                      urllib.error.HTTPError('http://private.invalid',302,'PRIVATE_SENTINEL',{},None)):
            with self.subTest(error=type(error).__name__):
                opener=Mock(open=Mock(side_effect=error))
                with patch.object(bridge.urllib.request,'build_opener',return_value=opener):r,_=await self.request()
                self.assertEqual(r.status_code,502); self.assertNotIn('PRIVATE_SENTINEL',r.text)
                opener.open.assert_called_once()
        for raw in (b'PRIVATE_SENTINEL',b'[]',b'{"text":""}',b'x'*(protocol.MAX_RESPONSE+1),
                    json.dumps({'text':'x'*(protocol.MAX_TEXT+1)}).encode()):
            with self.subTest(size=len(raw)):
                reply=Reply(raw)
                with patch.object(bridge.urllib.request,'build_opener',return_value=Mock(open=Mock(return_value=reply))):
                    r,_=await self.request()
                self.assertEqual(r.status_code,502); self.assertNotIn('PRIVATE_SENTINEL',r.text)
                self.assertTrue(reply.closed)

    async def test_bridge_redirect_timeout_and_response_bounds(self):
        for status,raw,code in ((302,b'PRIVATE_SENTINEL',502),(500,b'PRIVATE_SENTINEL',502),
                               (200,b'x'*(protocol.MAX_RESPONSE+1),502),(200,b'{}',502)):
            seen=[]
            def handler(request):
                seen.append(request)
                self.assertEqual(str(request.url),self.webui.BRIDGE_URL)
                self.assertEqual(request.headers['authorization'],'Bearer '+TOKEN.decode())
                return httpx.Response(status,content=raw,headers={'content-type':'application/json','location':'http://external.invalid'})
            with patch.object(httpx,'AsyncHTTPTransport',return_value=httpx.MockTransport(handler)) as factory:
                with self.assertRaises(HTTPException) as caught:await self.webui.bridge_text(wav_bytes(),token=TOKEN)
            self.assertEqual(caught.exception.status_code,code); self.assertNotIn('PRIVATE_SENTINEL',caught.exception.detail)
            self.assertEqual(len(seen),1); factory.assert_called_once_with(retries=0)
        def timedout(request):raise httpx.ReadTimeout('PRIVATE_SENTINEL')
        with patch.object(httpx,'AsyncHTTPTransport',return_value=httpx.MockTransport(timedout)):
            with self.assertRaises(HTTPException) as caught:await self.webui.bridge_text(wav_bytes(),token=TOKEN)
        self.assertEqual(caught.exception.status_code,504)

    def test_fixed_upstream_and_redirect_policy(self):
        self.assertIsNone(bridge.NoRedirect().redirect_request(None,None,302,'private',{},'http://external.invalid'))
        request=bridge.urllib.request.Request('http://external.invalid/inference',data=b'x')
        with self.assertRaises(ValueError):bridge.whisper_opener(request,30)

    def test_exact_patch_preserves_every_other_handler(self):
        def unchanged(source):
            return [ast.dump(n,include_attributes=False) for n in ast.parse(source).body
                    if not isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) or n.name!='transcription']
        self.assertEqual(unchanged(self.source),unchanged(self.patched))
        route=next(n for n in ast.parse(self.patched).body if isinstance(n,ast.AsyncFunctionDef) and n.name=='transcription')
        self.assertEqual(ast.unparse(route.args),'request: Request, user=Depends(get_verified_user)')
        self.assertNotIn('UploadFile',ast.unparse(route)); self.assertNotIn('File(',ast.unparse(route))
        with self.assertRaises(ValueError):self.prepare.patch_audio(self.source+'\n')
        webui=(ROOT/'deploy/lab/stt/webui.py').read_text()
        self.assertNotIn('from app',webui)
        self.assertNotIn('transcribe_attachment',webui)
        self.assertNotIn('process_turn',webui)


if __name__=='__main__':unittest.main(verbosity=2)
