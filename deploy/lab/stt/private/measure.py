"""Isolated synthetic no-convert model measurement; never touch existing services."""
import subprocess,json,uuid,pathlib,time,io,wave,math,sys
IMAGE='sha256:caf0cd77c922e9c53f10a9bc17c2f74cc2295d12e7b0f96b630fb3b3c55a0026'
MODEL=str(pathlib.Path(sys.argv[1]).resolve(strict=True))
assert pathlib.Path(MODEL).is_file() and pathlib.Path(MODEL).name=='ggml-small.bin'
assert pathlib.Path(MODEL).stat().st_size==487601967
name='corvus-stt-r6-measure-'+uuid.uuid4().hex[:12];label='corvus.stt-r6-measure='+uuid.uuid4().hex
cid=None
result={'image':IMAGE,'validated_memory_ceiling':1140850688,'cpus':8,'threads':8,'cases':[]}
def d(*a,timeout=10,input=None):
 return subprocess.run(['docker',*a],input=input,capture_output=True,timeout=timeout,check=True).stdout
info=json.loads(d('image','inspect','--format','{{json .}}',IMAGE))
assert info['Id']==IMAGE and not info['Config'].get('Volumes')
# Confirm the candidate limit derived from prior observed peak 712343552 bytes:
# 1.5x rounded up to 64 MiB = 1088 MiB. Baseline layer changes are Docker mount setup.
command='exec /app/build/bin/whisper-server --host 0.0.0.0 --port 8080 -m /models/ggml-small.bin -t 8 -l auto --no-gpu >/dev/null 2>&1'
cid=d('create','--pull=never','--name',name,'--label',label,'--network=none','--read-only',
 '--user','10001:10001','--cap-drop=ALL','--security-opt=no-new-privileges','--pids-limit=64',
 '--memory=1088m','--memory-swap=1088m','--cpus=8','--ulimit=core=0:0','--log-driver=none',
 '--mount','type=bind,src='+MODEL+',dst=/models/ggml-small.bin,readonly',
 '--entrypoint=/bin/sh',IMAGE,'-c',command).decode().strip()
def guard():
 o=json.loads(d('inspect','--format','{{json .}}',cid))
 assert o['Id']==cid and o['Image']==IMAGE and o['Config']['Labels'][label.split('=')[0]]==label.split('=')[1]
 assert o['HostConfig']['NetworkMode']=='none' and o['HostConfig']['ReadonlyRootfs'] and not o['HostConfig']['PortBindings']
 assert o['HostConfig']['LogConfig']['Type']=='none' and len(o['Mounts'])==1
 m=o['Mounts'][0];assert m['Source']==MODEL and m['Destination']=='/models/ggml-small.bin' and not m['RW']
 return o
HTTP_SCRIPT='exec 3<>/dev/tcp/127.0.0.1/8080; cat >&3; cat <&3'
def request(path,body=b'',timeout=30,ctype='application/octet-stream'):
 head=('POST' if body else 'GET')+' '+path+' HTTP/1.1\r\nHost: isolated-test\r\nConnection: close\r\nContent-Type: '+ctype+'\r\nContent-Length: '+str(len(body))+'\r\n\r\n'
 data=d('exec','-i',cid,'/bin/bash','-c',HTTP_SCRIPT,input=head.encode()+body,timeout=timeout)
 header,payload=data.split(b'\r\n\r\n',1);status=int(header.split(b' ',2)[1]);return status,payload
METRICS='cat /sys/fs/cgroup/memory.current /sys/fs/cgroup/memory.peak /sys/fs/cgroup/memory.swap.max /sys/fs/cgroup/memory.swap.current; cat /sys/fs/cgroup/cpu.stat /sys/fs/cgroup/memory.events'
def metrics():
 lines=d('exec',cid,'/bin/sh','-c',METRICS).decode().splitlines()
 return {'memory_current':int(lines[0]),'memory_peak':int(lines[1]),'swap_max':lines[2],'swap_current':int(lines[3]),'counters':{k:int(v) for k,v in (line.split() for line in lines[4:])}}
try:
 guard();result['baseline_layer_diff']=d('diff',cid).decode().splitlines();start=time.monotonic();d('start',cid)
 deadline=start+25
 while True:
  assert time.monotonic()<deadline,'isolated model startup deadline exceeded'
  assert guard()['State']['Running'],'isolated server exited'
  try:
   status,payload=request('/health',timeout=2)
   if status==200 and json.loads(payload).get('status')=='ok':break
  except (subprocess.CalledProcessError,subprocess.TimeoutExpired,ValueError):pass
  time.sleep(.2)
 result['startup_seconds']=round(time.monotonic()-start,3);result['after_startup']=metrics();print('Isolated model ready',flush=True)
 for seconds in [1,120]:
  b=io.BytesIO()
  with wave.open(b,'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000);w.writeframes(b'\0\0'*(seconds*16000))
  # Synthetic silence only; no prompt or source content ever printed.
  boundary='CorvusR6Synthetic'
  body=(('--'+boundary+'\r\nContent-Disposition: form-data; name="response_format"\r\n\r\njson\r\n--'+boundary+'\r\nContent-Disposition: form-data; name="language"\r\n\r\nauto\r\n--'+boundary+'\r\nContent-Disposition: form-data; name="file"; filename="dictation.wav"\r\nContent-Type: audio/wav\r\n\r\n').encode()+b.getvalue()+('\r\n--'+boundary+'--\r\n').encode())
  before=metrics();t=time.monotonic()
  result['current_case_seconds']=seconds;pathlib.Path('/tmp/corvus-stt-r6-measure-partial.json').write_text(json.dumps(result,indent=2));print('Measuring synthetic WAV duration '+str(seconds),flush=True)
  status,payload=request('/inference',body,timeout=55,ctype='multipart/form-data; boundary='+boundary)
  elapsed=time.monotonic()-t;after=metrics()
  assert status==200,'synthetic inference failed'
  answer=json.loads(payload);assert isinstance(answer.get('text'),str)
  result['cases'].append({'synthetic_seconds':seconds,'wav_bytes':len(b.getvalue()),'http_status':status,'response_bytes':len(payload),'wall_seconds':round(elapsed,3),'cpu_seconds':round((after['counters']['usage_usec']-before['counters']['usage_usec'])/1e6,3),'metrics':after})
 guard()
 # No writable audio path exists. Check layer diff metadata without inspecting data.
 result['final_layer_diff']=d('diff',cid).decode().splitlines();result['layer_diff_only_model_scaffolding']=set(result['final_layer_diff']) <= {'A /models','A /models/ggml-small.bin'}
 result['final']=metrics();assert result['final']['swap_max']=='0' and result['final']['swap_current']==0
 assert result['final']['counters']['oom_kill']==0 and result['layer_diff_only_model_scaffolding']
 result['peak_bytes']=result['final']['memory_peak']
 result['proposed_memory_bytes']=math.ceil(result['peak_bytes']*1.5/(64*1024*1024))*(64*1024*1024)+64*1024*1024
 pathlib.Path('/tmp/corvus-stt-r6-measure-results.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(result,indent=2))
finally:
 if cid:
  try:result['final_attempt']=metrics();pathlib.Path('/tmp/corvus-stt-r6-measure-partial.json').write_text(json.dumps(result,indent=2))
  except Exception:pass
  o=guard()
  if o['State']['Running']:d('kill',cid);d('wait',cid)
  guard();d('rm',cid)
  p=subprocess.run(['docker','inspect',cid],capture_output=True,text=True)
  assert p.returncode==1 and 'no such' in p.stderr.lower()
  print('Exact isolated measurement container removed')
