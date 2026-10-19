"""Minimal activation wiring/auth contracts; synthetic credentials/WAV only."""
import asyncio,ast,io,importlib.util,os,stat,sys,types,unittest,wave
from pathlib import Path
from unittest.mock import Mock,patch
import httpx
from app import stt_protocol as protocol
from app import stt_bridge as bridge
ROOT=Path(__file__).resolve().parents[1]
TOKEN=b'a'*64

def wav():
 b=io.BytesIO()
 with wave.open(b,'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000);w.writeframes(b'\0\0'*160)
 return b.getvalue()

def active_module():
 m=types.ModuleType('synthetic_active')
 source=(ROOT/'app/stt_active.py').read_text();tree=ast.parse(source)
 tree.body=[n for n in tree.body if not isinstance(n,ast.Assign) or not any(isinstance(t,ast.Name) and t.id=='app' for t in n.targets)]
 exec(compile(tree,'activation-wrapper','exec'),m.__dict__)
 return m

class ActivationContracts(unittest.IsolatedAsyncioTestCase):
 def test_credential_restricted_and_sanitized(self):
  flags=[]
  def opened(path,options):self.assertEqual(path,'/run/secrets/corvus_stt_bridge');flags.append(options);return 42
  metadata=types.SimpleNamespace(st_mode=stat.S_IFREG|0o400,st_uid=10001,st_size=64)
  with patch.object(protocol.os,'open',opened),patch.object(protocol.os,'close'),patch.object(protocol.os,'fstat',return_value=metadata),patch.object(protocol.os,'read',return_value=TOKEN):
   self.assertEqual(protocol.service_token(),TOKEN)
   self.assertTrue(flags[0]&os.O_NOFOLLOW)
   for field,value in [('st_mode',stat.S_IFREG|0o644),('st_uid',0),('st_size',65)]:
    old=getattr(metadata,field);setattr(metadata,field,value)
    with self.assertRaises(Exception) as e:protocol.service_token()
    self.assertEqual(e.exception.status_code,503);setattr(metadata,field,old)
  with patch.object(protocol.os,'open',side_effect=OSError('PRIVATE_CONTENT')):
   with self.assertRaises(Exception) as e:protocol.service_token()
   self.assertNotIn('PRIVATE_CONTENT',e.exception.detail)

 def test_admission_missing_or_malformed_fails_closed(self):
  with patch.object(protocol.os,'open',side_effect=FileNotFoundError):self.assertFalse(protocol.admissions_open())
  meta=types.SimpleNamespace(st_mode=stat.S_IFREG|0o444,st_size=5)
  with patch.object(protocol.os,'open',return_value=42),patch.object(protocol.os,'close'),patch.object(protocol.os,'fstat',return_value=meta),patch.object(protocol.os,'read',return_value=b'open\n'):
   self.assertTrue(protocol.admissions_open())
   with patch.object(protocol.os,'read',return_value=b'bad\n'):self.assertFalse(protocol.admissions_open())

 async def test_closed_admission_rejects_before_body_and_provider(self):
  m=active_module();call=Mock(return_value='text')
  with patch.object(m,'service_token',return_value=TOKEN),patch.object(m,'whisper_text',call):app=m.build_app()
  consumed=[]
  async def body():consumed.append(True);yield wav()
  with patch.object(m,'admissions_open',return_value=False):
   async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://synthetic') as c:r=await c.post('/v1/transcribe',content=body())
  self.assertEqual(r.status_code,503);self.assertEqual(consumed,[]);call.assert_not_called()

 async def test_open_auth_validated_wav_and_existing_r6_transport(self):
  m=active_module();call=Mock(return_value='中文 English')
  with patch.object(m,'service_token',return_value=TOKEN),patch.object(m,'whisper_text',call):app=m.build_app()
  with patch.object(m,'admissions_open',return_value=True):
   async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://synthetic') as c:
    self.assertEqual((await c.post('/v1/transcribe',content=wav())).status_code,401)
    headers={'authorization':'Bearer '+TOKEN.decode(),'content-type':'audio/wav'}
    self.assertEqual((await c.post('/v1/transcribe',headers=headers,content=b'bad')).status_code,400)
    r=await c.post('/v1/transcribe',headers=headers,content=wav())
    self.assertEqual(r.status_code,200);self.assertEqual(r.json(),{'text':'中文 English'})
    self.assertEqual(r.headers['cache-control'],'private, no-store');call.assert_called_once_with(wav())

 async def test_native_delegates_only_after_admission_and_uses_fixed_credential(self):
  m=types.ModuleType('native_active');fake=types.ModuleType('open_webui.routers.corvus_stt')
  seen=[]
  async def core(request,*,bridge):return await bridge(wav())
  async def text(audio,*,token):seen.append((audio,token));return 'recognized'
  fake.transcription=core;fake.bridge_text=text
  with patch.dict(sys.modules,{'open_webui':types.ModuleType('open_webui'),'open_webui.routers':types.ModuleType('open_webui.routers'),'open_webui.routers.corvus_stt':fake,'open_webui.routers.corvus_stt_protocol':protocol}):
   exec((ROOT/'deploy/lab/stt/activation/webui_active.py').read_text(),m.__dict__)
  with patch.object(m,'service_token',return_value=TOKEN),patch.object(m,'admissions_open',return_value=False):
   with self.assertRaises(Exception) as e:await m.transcription(object())
   self.assertEqual(e.exception.status_code,503);self.assertEqual(seen,[])
  with patch.object(m,'service_token',return_value=TOKEN),patch.object(m,'admissions_open',return_value=True):
   self.assertEqual(await m.transcription(object()),'recognized');self.assertEqual(seen,[(wav(),TOKEN)])

 def test_backend_patch_preserves_native_auth_and_every_other_handler(self):
  p=ROOT/'deploy/lab/stt/activation/prepare.py';spec=importlib.util.spec_from_file_location('prepare_active',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  source=Path('/tmp/corvus-stt-r7-package/webui/audio.py').read_text();prepared=Path('/tmp/corvus-stt-lab-activation/context/webui/audio.py').read_text()
  old='from open_webui.routers.corvus_stt import transcription as handle'
  self.assertEqual(prepared,source.replace(old,'from open_webui.routers.corvus_stt_active import transcription as handle'))
  node=next(n for n in ast.parse(prepared).body if isinstance(n,ast.AsyncFunctionDef) and n.name=='transcription')
  self.assertEqual(ast.unparse(node.args),'request: Request, user=Depends(get_verified_user)')
  self.assertEqual(bridge.WHISPER_BASE,'http://corvus-whisper-dictation:8080')

if __name__=='__main__':unittest.main(verbosity=2)
