import sys,pathlib,json,time,io,wave,asyncio,os,re,contextlib
import httpx
sys.path.insert(0,os.environ.get('CORVUS_STT_OPERATIONS_DIR','/tmp/corvus-stt-retry3'));import runtime as r
NATIVE='http://127.0.0.1:3003/api/v1/audio/transcriptions'
def headers():return {'Authorization':'Bearer '+(r.REC/'native-acceptance.token').read_text().strip()}
def post(c,audio,mime='audio/wav',auth=True):return c.post(NATIVE,headers=headers() if auth else {},files={'file':('synthetic.wav',audio,mime)})
def metrics():
 out={}
 for name in ['corvus-whisper-dictation','corvus-stt-bridge']:
  o=r.guard(name)
  raw=r.run(['docker','exec',o['Id'],'/bin/sh','-c','cat /sys/fs/cgroup/memory.current /sys/fs/cgroup/memory.peak /sys/fs/cgroup/memory.swap.current /sys/fs/cgroup/cpu.stat']).decode().splitlines()
  out[name]={'current_bytes':int(raw[0]),'peak_bytes':int(raw[1]),'swap_current':int(raw[2]),**{x.split()[0]:int(x.split()[1]) for x in raw[3:]}}
 return out

def cache():
 # Metadata-only inventory, never open historical audio, names never printed.
 code="""import pathlib,json
out={}
for name in ['cache/audio','uploads']:
 p=pathlib.Path('/app/backend/data')/name
 out[name]={str(x.relative_to(p)):[x.stat().st_size,x.stat().st_mtime_ns] for x in p.rglob('*') if x.is_file()} if p.exists() else {}
print(json.dumps(out))"""
 return json.loads(r.run(['docker','exec','corvus-lab-open-webui','python','-B','-c',code]))
def fixture(name):return (pathlib.Path('/tmp/corvus-stt-lab-activation')/('public-'+name+'.wav')).read_bytes()

def before():
 (r.REC/'cache-before.json').write_text(json.dumps(cache()));(r.REC/'resource-before.json').write_text(json.dumps(metrics()));print('Metadata-only cache and owned-resource baselines captured; no audio inspected')

def speech(name):
 audio=fixture(name);a=metrics();start=time.monotonic()
 with httpx.Client(trust_env=False,follow_redirects=False,timeout=40) as c:response=post(c,audio)
 elapsed=time.monotonic()-start;b=metrics()
 record={'fixture':name,'status':response.status_code,'seconds':round(elapsed,3),'before':a,'after':b}
 (r.REC/('speech-'+name+'.json')).write_text(json.dumps(record,indent=2))
 assert response.status_code==200, 'Synthetic '+name+' failed HTTP '+str(response.status_code)
 text=response.json()['text'];assert isinstance(text,str) and text.strip() and len(text)<=16384
 if name=='chinese':semantic=any(w in text for w in ['天气','天氣','测试','測試'])
 elif name=='english':semantic='test' in text.lower() and any(w in text.lower() for w in ['hello','dictation','public'])
 else:semantic=any(w in text for w in ['你好','Hello','hello']) and any(w in text.lower() for w in ['test','voice','public'])
 # Mixed-language keyword misses are quality findings, never system exceptions.
 if name=='mixed':
  normalized=re.sub(r'[^\w\u4e00-\u9fff]','',text.lower()).translate(str.maketrans('這個語聲測試開妳','这个语声测试开你'))
  concepts={'greeting':any(w in normalized for w in ['你好','您好','hello','nihao']),
            'public':any(w in normalized for w in ['public','公共','公开','公用']),
            'voice':any(w in normalized for w in ['voice','语音','声音']),
            'test':any(w in normalized for w in ['test','测试'])}
  equivalents={'你好thisisapublicvoicetest','hellothisisapublicvoicetest',
   '你好这是一个公共语音测试','你好这是一个公开的语音测试','你好这是一个公共的语音测试',
   '你好这是一个公开语音测试','你好这是公共语音测试','你好这是一个公用语音测试'}
  if normalized in equivalents:quality='ACCEPTED';reason='public_phrase_or_equivalent_translation'
  elif normalized in {'谢谢观看','感谢观看','thanksforwatching'}:quality='QUALITY_FAIL';reason='unrelated_outro_instead_of_public_voice_test'
  else:quality='QUALITY_REVIEW_REQUIRED';reason='meaning_not_confirmed_by_existing_fixture_check'
  record.update(quality_status=quality,semantic_evidence=concepts,quality_reason=reason)
 else:
  assert semantic,'Primary-language transcription quality failed'
  record.update(quality_status='ACCEPTED',quality_reason='existing_public_fixture_check')
 assert response.headers.get('cache-control')=='private, no-store' and len(response.content)<=65536
 record.update(nonempty=True,expected_public_words=bool(semantic),chars=len(text),no_store=True)
 for service in a:
  record.setdefault('cpu_seconds',{})[service]=round((b[service]['usage_usec']-a[service]['usage_usec'])/1e6,3)
 (r.REC/('speech-'+name+'.json')).write_text(json.dumps(record,indent=2))
 print(json.dumps(record))

def invalids():
 out={}
 with httpx.Client(trust_env=False,follow_redirects=False,timeout=10) as c:
  out['native_unauth']=post(c,b'bad',auth=False).status_code;assert out['native_unauth']==403
  out['bridge_unauth']=c.post('http://127.0.0.1:18106/v1/transcribe',content=b'bad').status_code;assert out['bridge_unauth']==401
  for name,data,mime,status in [('corrupt',b'not wave','audio/wav',400),('wrong_format',b'not wave','audio/webm',400),('oversize',b'0'*(8*1024*1024+16385),'audio/wav',413)]:
   res=post(c,data,mime=mime);assert res.status_code==status,(name,res.status_code);out[name]=status
  bio=io.BytesIO()
  with wave.open(bio,'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000);w.writeframes(b'\0\0'*(120*16000+1))
  res=post(c,bio.getvalue());assert res.status_code==400;out['duration_over_120s']=res.status_code
 assert cache()==json.loads((r.REC/'cache-before.json').read_text()),'Audio/upload metadata changed'
 (r.REC/'bounds-auth-cache.json').write_text(json.dumps(out));print(json.dumps({**out,'cache_upload_metadata_unchanged':True}))


def native_config(client):
 # Pinned 0.6.5 /api/config reads the native token cookie, not Bearer.
 # Without it the public response correctly omits audio/permission fields.
 response=client.get('/api/config',cookies={'token':(r.REC/'native-acceptance.token').read_text().strip()})
 assert response.status_code==200
 config=response.json()
 assert config['audio']['stt']['engine']!='web'
 assert config['permissions']['chat']['stt'] is True
 return {'native_cookie_config':True,'native_stt_permission':True}

def bridge_probe():
 # Credential stays inside the existing WebUI container; probe cannot infer.
 code="""import urllib.request,urllib.error
from open_webui.routers.corvus_stt_protocol import service_token
request=urllib.request.Request('http://127.0.0.1:18106/v1/transcribe',data=b'not a WAV',headers={'Authorization':'Bearer '+service_token().decode(),'Content-Type':'audio/wav'})
try:
 with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(request,timeout=3) as response:print(response.status)
except urllib.error.HTTPError as e:print(e.code)
"""
 return int(r.run(['docker','exec','corvus-lab-open-webui','python','-B','-c',code]).strip())

def faults():
 result={};engine=r.guard('corvus-whisper-dictation')['Id']
 # Intentional fault only in the owned new engine, never a shared service.
 r.run(['docker','stop','--time','10',engine])
 try:
  start=time.monotonic()
  with httpx.Client(trust_env=False,follow_redirects=False,timeout=10) as c:response=post(c,fixture('chinese'))
  assert response.status_code==502 and response.json()=={'detail':'Transcription failed.'}
  result['provider_unavailable']={'status':502,'seconds':round(time.monotonic()-start,3),'sanitized':True}
 finally:
  r.guard('corvus-whisper-dictation');r.run(['docker','start',engine]);r.health(engine)
 r.guard('corvus-whisper-dictation');r.run(['docker','pause',engine])
 try:
  start=time.monotonic()
  with httpx.Client(trust_env=False,follow_redirects=False,timeout=35) as c:response=post(c,fixture('english'))
  elapsed=time.monotonic()-start
  assert response.status_code in (502,504) and response.json() in ({'detail':'Transcription failed.'},{'detail':'Transcription timed out.'})
  assert 23<=elapsed<32
  result['provider_deadline']={'native_status':response.status_code,'seconds':round(elapsed,3),'sanitized':True}
 finally:
  o=r.guard('corvus-whisper-dictation')
  if o['State']['Paused']:r.run(['docker','unpause',engine])
  r.health(engine)
 # A timed-out caller does not prove server work ended. Allow this short
 # synthetic late request to settle; no synchronous cancellation claim.
 time.sleep(5)
 end=time.monotonic()+30
 while True:
  code=bridge_probe()
  if code==400:break
  assert code in (429,503) and time.monotonic()<end
  time.sleep(.5)
 result['admission_recovered']=True
 (r.REC/'live-faults.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))

async def cancellation():
 start=time.monotonic();result={}
 async with httpx.AsyncClient(trust_env=False,follow_redirects=False,timeout=40) as c:
  task=asyncio.create_task(c.post(NATIVE,headers=headers(),files={'file':('synthetic.wav',fixture('english'),'audio/wav')}))
  await asyncio.sleep(.8)
  assert not task.done(),'Cancellation fixture finished before cancellation'
  task.cancel()
  try:await task
  except asyncio.CancelledError:result['client_cancelled']=True
 assert result['client_cancelled']
 codes=[];deadline=time.monotonic()+30
 while True:
  code=await asyncio.to_thread(bridge_probe);codes.append(code)
  if code==400:break
  assert code in (429,503) and time.monotonic()<deadline
  await asyncio.sleep(.5)
 result.update(seconds_to_admission_recovery=round(time.monotonic()-start,3),probe_statuses=sorted(set(codes)),synchronous_worker_termination_claimed=False)
 (r.REC/'live-cancellation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))

if __name__=='__main__':
 try:
  mode=sys.argv[1]
  if mode=='before':before()
  elif mode=='invalids':invalids()
  elif mode=='faults':faults()
  elif mode=='cancellation':asyncio.run(cancellation())
  else:speech(mode)
 except BaseException as e:
  r.close();r.note('ACCEPTANCE_FAILED',{'classification':'SYSTEM_FAILURE','kind':type(e).__name__,'stage':sys.argv[1]});print('CRITICAL ACCEPTANCE FAILURE; admission closed; scoped rollback starting',flush=True);r.rollback();raise
