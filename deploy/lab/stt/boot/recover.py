"""Exact retained Lab repair, no build/pull, no second container supervisor.

Private runtime snapshots/configuration live outside Git. prepare is read-only
with respect to runtime. material provisioning is a separate local sudo step.
"""
import copy, hashlib, http.client, importlib.util, io, json, os
from pathlib import Path
import subprocess, sys, time, uuid, wave
os.umask(0o077)
ROOT=Path(__file__).resolve().parents[4]
STATE=Path('/home/ethan/.config/corvus-lab/stt-runtime')
BACKUP=Path('/home/ethan/corvus-vision-recovery.7lm0_3t8/rollback-compose.json')
WEB='corvus-lab-open-webui';BRIDGE='corvus-lab-open-webui-corvus-stt-bridge-1';ENGINE='corvus-lab-open-webui-corvus-whisper-dictation-1'
IMAGES={WEB:'sha256:4b0451913d93774af57defe40873f29323239ef83ed7dfd8f405abe7b4f7ad17',BRIDGE:'sha256:5d3cd6aff2db1a9712ce98669942d093858640298e9c04903f3cee3b510dc6b2',ENGINE:'sha256:caf0cd77c922e9c53f10a9bc17c2f74cc2295d12e7b0f96b630fb3b3c55a0026'}
SOURCES={'/run/secrets/corvus_stt_bridge':{'open-webui':'/etc/corvus-lab/stt/webui/credential','corvus-stt-bridge':'/etc/corvus-lab/stt/bridge/credential'},'/run/secrets/corvus_stt_admissions':'/etc/corvus-lab/stt/stt-admissions','/app/backend/open_webui/routers/corvus_stt_protocol.py':'/etc/corvus-lab/stt/webui-protocol.py'}
def run(args,body=None,timeout=180):
 p=subprocess.run(args,input=body,capture_output=True,timeout=timeout)
 if p.returncode:raise RuntimeError('Command failed; private details withheld: '+args[0])
 return p.stdout

def inspect(name):return json.loads(run(['docker','inspect',name]))[0]
def write(name,obj):
 p=STATE/name
 if p.exists():raise RuntimeError('Existing checkpoint; resume, do not overwrite')
 p.write_text(json.dumps(obj,indent=2));p.chmod(0o600)
def escape(value):
 if isinstance(value,str):return value.replace('$','$$')
 if isinstance(value,list):return [escape(x) for x in value]
 if isinstance(value,dict):return {k:escape(v) for k,v in value.items()}
 return value

def prepare():
 assert os.getuid()==1000 and not STATE.exists(),'Prepare only once as ethan; preserve prior checkpoint'
 old={n:inspect(n) for n in IMAGES}
 for n,o in old.items():
  assert o['Image']==IMAGES[n]
  assert json.loads(run(['docker','image','inspect',IMAGES[n]]))[0]['Id']==IMAGES[n]
 assert old[WEB]['State']['Status']=='exited' and old[BRIDGE]['State']['Status']=='exited'
 assert old[ENGINE]['State']['Running'] and old[ENGINE]['State']['Health']['Status']=='healthy'
 assert not any(x.startswith('CORVUS_SINGLE_STORE_VISION=') for x in old[WEB]['Config']['Env'])
 assert run(['systemctl','is-enabled','docker.service']).strip()==b'enabled'
 config=json.loads(BACKUP.read_text())
 assert set(config['services'])=={'open-webui','corvus-stt-bridge','corvus-whisper-dictation'}
 for service,name in [('open-webui',WEB),('corvus-stt-bridge',BRIDGE),('corvus-whisper-dictation',ENGINE)]:
  s=config['services'][service];o=old[name];s['image']=IMAGES[name];s['pull_policy']='never';s.pop('build',None)
  s['environment']=dict(x.split('=',1) for x in o['Config']['Env']);s['user']=o['Config']['User'];s['restart']='unless-stopped'
  for key,value in list(s.get('ulimits',{}).items()):
   if value is None or value=={}:s['ulimits'][key]=0
  for mount in s.get('volumes',[]):
   assert any(m['Destination']==mount['target'] for m in o['Mounts'])
   if mount['type']=='bind':
    prior=next(m for m in o['Mounts'] if m['Destination']==mount['target']);assert mount['source']==prior['Source']
    target=SOURCES.get(mount['target'])
    if target:mount['source']=target[service] if isinstance(target,dict) else target
    assert not mount['source'].startswith('/tmp/') and not mount['source'].startswith('/run/')
    mount['read_only']=True;mount['bind']={'create_host_path':False}
 for service,s in config['services'].items():
  o=old[{'open-webui':WEB,'corvus-stt-bridge':BRIDGE,'corvus-whisper-dictation':ENGINE}[service]];h=o['HostConfig']
  assert s.get('network_mode', 'default')==h['NetworkMode'] if service=='open-webui' else True
  assert s.get('cap_drop')==h['CapDrop'] and not h['CapAdd']
  assert s.get('security_opt')==h['SecurityOpt']
  assert s.get('read_only',False)==h['ReadonlyRootfs']
  assert int(s.get('mem_limit') or 0)==h['Memory'] and int(s.get('memswap_limit') or 0)==h['MemorySwap']
  assert s.get('logging',{}).get('driver')==h['LogConfig']['Type']
 STATE.mkdir(mode=0o700)
 write('before-containers.json',old);write('compose.json',escape(config))
 all_before={}
 for cid in run(['docker','ps','-aq']).decode().split():
  o=inspect(cid);all_before[o['Id']]={'image':o['Image'],'started':o['State']['StartedAt'],'name':o['Name']}
 write('other-containers.json',all_before)
 parsed=json.loads(run(compose()+['config','--format','json']))
 for service in config['services']:
  assert parsed['services'][service]['environment']==config['services'][service]['environment']
 write('prepared.json',{'images':IMAGES,'boot_manager':'existing enabled Docker service','root_material_required':True})
 print('PERSISTENT_REPAIR_PREPARED: private snapshot/config validated; no runtime changes')

def compose():return ['docker','compose','-p','corvus-lab-open-webui','-f',str(STATE/'compose.json'),'--profile','stt-private-review']
def consumer_checks():
 # Use the actual image UIDs/capabilities. No network, model, data or host ports.
 for consumer,name,uid in [('webui',WEB,'0:0'),('bridge',BRIDGE,'10001:10001')]:
  code="""import os,stat,importlib.util,hashlib
assert next(x for x in open('/proc/self/status') if x.startswith('CapEff:')).split()[1]=='0000000000000000'
assert next(x for x in open('/proc/self/status') if x.startswith('NoNewPrivs:')).split()[1]=='1'
"""
  if consumer=='webui':
   spec=importlib.util.spec_from_file_location('repair',ROOT/'deploy/lab/stt/activation/credential_repair.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);expected=hashlib.sha256(m.webui_protocol()).hexdigest()
   code+="p='/app/backend/open_webui/routers/corvus_stt_protocol.py'\nassert hashlib.sha256(open(p,'rb').read()).hexdigest()=="+repr(expected)+"\ns=importlib.util.spec_from_file_location('p',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)\n"
  else:code+='from app import stt_protocol as m\n'
  code+="assert len(m.service_token())==64 and m.admissions_open()\nprint('CONSUMER_READ_VALIDATION_PASS')"
  label=uuid.uuid4().hex
  args=['docker','create','--pull=never','--network=none','--read-only','--user',uid,'--cap-drop=ALL','--security-opt=no-new-privileges','--memory=256m','--memory-swap=256m','--cpus=1','--pids-limit=64','--ulimit=core=0:0','--log-driver=none','--label','corvus.stt.boot-check='+label,'--tmpfs=/tmp:rw,noexec,nosuid,nodev,size=16m','--tmpfs=/app/backend/data:rw,noexec,nosuid,nodev,size=16m']
  mounts=[('/etc/corvus-lab/stt/'+consumer+'/credential','/run/secrets/corvus_stt_bridge'),('/etc/corvus-lab/stt/stt-admissions','/run/secrets/corvus_stt_admissions')]
  if consumer=='webui':mounts.append(('/etc/corvus-lab/stt/webui-protocol.py','/app/backend/open_webui/routers/corvus_stt_protocol.py'))
  for source,target in mounts:args+=['--mount','type=bind,src='+source+',dst='+target+',readonly']
  args+=['--entrypoint','python',IMAGES[name],'-B','-c',code]
  cid=run(args).decode().strip()
  def owned():
   o=inspect(cid);assert o['Id']==cid and o['Image']==IMAGES[name] and o['Config']['Labels']['corvus.stt.boot-check']==label and o['HostConfig']['NetworkMode']=='none';return o
  try:
   owned();output=run(['docker','start','-a',cid],timeout=40)
   assert run(['docker','wait',cid]).strip()==b'0' and b'CONSUMER_READ_VALIDATION_PASS' in output
  finally:
   o=owned()
   if o['State']['Running']:run(['docker','kill',cid]);run(['docker','wait',cid])
   owned();run(['docker','rm',cid])
 print('EXACT_CONSUMER_MOUNTS_PASS: same credential validation; zero capabilities, no network')

def unchanged_others(old):
 for cid,b in json.loads((STATE/'other-containers.json').read_text()).items():
  if cid in {old[WEB]['Id'],old[BRIDGE]['Id']}:continue
  o=inspect(cid);assert o['Image']==b['image'] and o['State']['StartedAt']==b['started'],'Unexpected unrelated service restart'

def restore():
 old=json.loads((STATE/'before-containers.json').read_text());assert not (STATE/'restore-attempt.json').exists(),'Already attempted; reconcile checkpoint before another attempt'
 for n,b in old.items():
  o=inspect(n);assert o['Id']==b['Id'] and o['Image']==b['Image'] and o['Config']==b['Config'] and o['HostConfig']==b['HostConfig'],'Runtime drift'
 consumer_checks();unchanged_others(old)
 write('restore-attempt.json',{'started':True,'only_recreate':[WEB,BRIDGE]})
 run(compose()+['up','-d','--no-deps','--no-build','--pull','never','corvus-stt-bridge','open-webui'])
 # Metadata update only. The healthy existing Whisper process is NOT restarted.
 run(['docker','update','--restart','unless-stopped',old[ENGINE]['Id']])
 for _ in range(90):
  o=inspect(WEB)
  if o['State'].get('Health',{}).get('Status')=='healthy':break
  time.sleep(2)
 else:raise RuntimeError('WebUI health check failed; preserve checkpoint')
 for n,b in old.items():
  o=inspect(n);assert o['Image']==b['Image'] and dict(x.split('=',1) for x in o['Config']['Env'])==dict(x.split('=',1) for x in b['Config']['Env']) and o['Config']['User']==b['Config']['User']
  for key in ['Memory','MemorySwap','NanoCpus','CapAdd','CapDrop','SecurityOpt','ReadonlyRootfs','LogConfig','PortBindings','NetworkMode']:
   assert o['HostConfig'][key]==b['HostConfig'][key],key
  assert o['HostConfig']['RestartPolicy']['Name']=='unless-stopped'
  assert o['State']['Running']
  assert len(o['Mounts'])==len(b['Mounts'])
  for mount in o['Mounts']:
   prior=next(m for m in b['Mounts'] if m['Destination']==mount['Destination']);assert mount['Type']==prior['Type'] and mount['RW']==prior['RW']
   if mount['Type']=='volume':assert mount['Name']==prior['Name']
   else:assert not mount['Source'].startswith(('/tmp/','/run/'))
 unchanged_others(old);write('restored.json',{'restored':True,'whisper_not_restarted':True});print('WEBUI_BRIDGE_RESTORED: persistent binds and Docker unless-stopped; Whisper process unchanged')

def http(path,body=None,headers=None):
 c=http.client.HTTPConnection('127.0.0.1',3003,timeout=45)
 try:
  c.request('POST' if body is not None else 'GET',path,body,headers or {});r=c.getresponse();data=r.read(65537);assert len(data)<=65536 or path=='/health';return r.status,dict(r.getheaders()),data
 finally:c.close()

def verify():
 assert (STATE/'restored.json').exists() and not (STATE/'live-test-attempt.json').exists(),'Verify only once; no automatic STT retries'
 assert http('/health')[0]==200
 assert http('/api/v1/audio/transcriptions',b'bad')[0]==403
 # Reuse the public synthetic TTS fixture already retained in protected recovery.
 fixture=Path('/home/ethan/corvus-tts22-recovery.ew92qsh5/synthetic-acceptance.wav')
 import audioop
 with wave.open(str(fixture),'rb') as w:
  assert (w.getnchannels(),w.getsampwidth(),w.getframerate())==(1,2,24000)
  assert w.getnframes()<=24000*15
  pcm,_=audioop.ratecv(w.readframes(w.getnframes()),2,1,24000,16000,None)
 audio=io.BytesIO()
 with wave.open(audio,'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000);w.writeframes(pcm)
 # Existing native authentication, short-lived token kept only in memory.
 code="""import sqlite3,jwt,os,time
c=sqlite3.connect('file:/app/backend/data/webui.db?mode=ro',uri=True);u=c.execute('select user_id from function where id=?',('corvus_pipe',)).fetchone()[0];assert c.execute('select role from user where id=?',(u,)).fetchone()[0]=='admin';c.close()
print(jwt.encode({'id':u,'exp':int(time.time())+300},os.environ['WEBUI_SECRET_KEY'],algorithm='HS256'))"""
 token=run(['docker','exec',WEB,'python','-B','-c',code]).decode().strip()
 boundary='CorvusPublicSyntheticBootCheck'
 body=('--'+boundary+'\r\nContent-Disposition: form-data; name="file"; filename="public-synthetic.wav"\r\nContent-Type: audio/wav\r\n\r\n').encode()+audio.getvalue()+('\r\n--'+boundary+'--\r\n').encode()
 write('live-test-attempt.json',{'attempts':1,'fixture':'known public synthetic TTS22; in-memory stdlib fixture resampling only'})
 start=time.monotonic();status,headers,data=http('/api/v1/audio/transcriptions',body,{'Authorization':'Bearer '+token,'Content-Type':'multipart/form-data; boundary='+boundary})
 assert status==200,'Synthetic STT failed HTTP '+str(status)+'; no automatic retry'
 text=json.loads(data).get('text','');assert isinstance(text,str) and text.strip()
 semantic=any(word in text.lower() for word in ['test','hello','public','测试','測試','语音','語音']);assert semantic,'Public sample quality requires review; transcript withheld'
 assert headers.get('cache-control')=='private, no-store'
 old=json.loads((STATE/'before-containers.json').read_text());unchanged_others(old)
 for n in IMAGES:
  o=inspect(n);assert o['State']['Running'] and o['HostConfig']['RestartPolicy']['Name']=='unless-stopped'
 assert inspect(ENGINE)['State']['Health']['Status']=='healthy'
 out={'health_http':200,'authenticated_stt_http':status,'seconds':round(time.monotonic()-start,3),'nonempty_public_quality_check':True,'all_mounts_persistent':True,'policies':'Docker unless-stopped','actual_reboot_test':'NOT_PERFORMED','vision_untouched':True,'whisper_not_restarted':True,'private_data_or_snapshot_restored':False}
 write('acceptance.json',out);print(json.dumps(out))

if __name__=='__main__':
 try:
  action=sys.argv[1]
  if action=='prepare':prepare()
  elif action=='consumer-checks':consumer_checks()
  elif action=='restore':restore()
  elif action=='verify':verify()
  else:raise RuntimeError('Unknown action')
 except Exception as error:
  message=str(error) if isinstance(error,(AssertionError,RuntimeError)) else 'Private details withheld'
  print('STOP: '+message+'; preserve checkpoint, do not retry or rotate credentials automatically',file=sys.stderr);sys.exit(1)
