import {spawn} from 'node:child_process';
import {mkdtemp,readFile,writeFile,rm} from 'node:fs/promises';
import {stripTypeScriptTypes} from 'node:module';
const root=new URL('../',import.meta.url).pathname.replace(/\/$/,'');
const profile=await mkdtemp('/tmp/corvus-stt-r4-chrome-');
const chrome=spawn('/opt/google/chrome/chrome',['--headless=new','--disable-gpu','--disable-background-networking','--disable-component-update','--disable-sync','--disable-default-apps','--no-first-run','--no-default-browser-check','--no-proxy-server','--host-resolver-rules=MAP * ~NOTFOUND','--autoplay-policy=no-user-gesture-required','--remote-debugging-pipe',`--user-data-dir=${profile}`],{stdio:['ignore','ignore','pipe','pipe','pipe']});
const exited=new Promise(resolve=>chrome.once('exit',resolve));
let pending=new Map(),id=0,buffer='',errors='';chrome.stderr.on('data',d=>errors+=d.toString());
chrome.stdio[4].on('data',d=>{buffer+=d;let end;while((end=buffer.indexOf('\0'))>=0){const message=JSON.parse(buffer.slice(0,end));buffer=buffer.slice(end+1);if(message.id){const p=pending.get(message.id);pending.delete(message.id);message.error?p.reject(Error(JSON.stringify(message.error))):p.resolve(message.result);}}});
const send=(method,params={},sessionId)=>new Promise((resolve,reject)=>{const key=++id;pending.set(key,{resolve,reject});chrome.stdio[3].write(JSON.stringify({id:key,method,params,sessionId})+'\0');});
chrome.on('exit',()=>{for(const p of pending.values())p.reject(Error('Chrome exited: '+errors.slice(-1500)));});
chrome.stdio[4].on('error',()=>{for(const p of pending.values())p.reject(Error('Isolated browser pipe failed'));});
const timeout=setTimeout(()=>{chrome.kill();},45000);
try {
 const version=await send('Browser.getVersion');
 const {targetId}=await send('Target.createTarget',{url:'about:blank'});
 const {sessionId}=await send('Target.attachToTarget',{targetId,flatten:true});
 await send('Network.enable',{},sessionId);await send('Network.setBlockedURLs',{urls:['*']},sessionId);
 const source=stripTypeScriptTypes(await readFile(root+'/deploy/lab/stt/normalize.ts','utf8'),{mode:'strip'}).replace(/export /g,'');
 const helper=stripTypeScriptTypes(await readFile(root+'/deploy/lab/stt/dictation.ts','utf8'),{mode:'strip'}).replace(/export /g,'');
 const fixtures=JSON.parse(await readFile(root+'/tests/fixtures/stt-r4-synthetic.json','utf8'));
 const expression=`(async()=>{${source}\n${helper}\n
 const results=[],canonicalWavs=[]; let pcmDiagnostic; const fixtures=${JSON.stringify(fixtures)};
 const check=(value)=>{if(!value)throw Error('Synthetic contract assertion failed');};
 const fixture=(key,type)=>new Blob([Uint8Array.from(atob(fixtures[key]),c=>c.charCodeAt(0))],{type});
 const run=async(name,fn)=>{try{const detail=await fn();results.push({name,pass:true,...detail});}catch{results.push({name,pass:false});}};
 const rejected=async(fn)=>{try{await fn();return false;}catch{return true;}};
 const inspect=async(blob)=>{check(await validateDictationWav(blob));const v=new DataView(await blob.arrayBuffer());check(v.getUint16(22,true)===1);canonicalWavs.push(btoa(String.fromCharCode(...new Uint8Array(await blob.arrayBuffer()))));return {bytes:blob.size,frames:v.getUint32(40,true)/2,rate:v.getUint32(24,true)};};
 await run('WebM/Opus complete synthetic fixture',async()=>inspect(await normalizeRecording(fixture('webmOpus','audio/webm;codecs=opus'))));
 await run('MP4/AAC trailing-moov complete synthetic fixture',async()=>{
  const input=fixture('trailingMoov','audio/mp4;codecs=mp4a.40.2'),bytes=new Uint8Array(await input.arrayBuffer());
  const text=String.fromCharCode(...bytes);check(text.indexOf('moov')>text.indexOf('mdat'));
  return inspect(await normalizeRecording(input));
 });
 let pcm;
 await run('48kHz stereo PCM WAV -> 16kHz mono finite PCM frames',async()=>{
  const b=new ArrayBuffer(44+4800*4),v=new DataView(b),tag=(at,s)=>[...s].forEach((c,i)=>v.setUint8(at+i,c.charCodeAt(0)));
  tag(0,'RIFF');v.setUint32(4,b.byteLength-8,true);tag(8,'WAVE');tag(12,'fmt ');v.setUint32(16,16,true);v.setUint16(20,1,true);v.setUint16(22,2,true);v.setUint32(24,48000,true);v.setUint32(28,192000,true);v.setUint16(32,4,true);v.setUint16(34,16,true);tag(36,'data');v.setUint32(40,4800*4,true);
  for(let i=0;i<4800;i++){v.setInt16(44+i*4,8192,true);v.setInt16(46+i*4,24576,true);}
  pcm=new Blob([b],{type:'audio/wav'});const wav=await normalizeRecording(pcm),detail=await inspect(wav);pcmDiagnostic={...detail,sample:new DataView(await wav.arrayBuffer()).getInt16(44+1000*2,true)};check(detail.frames===1600);
  const out=new DataView(await wav.arrayBuffer());check(Math.abs(out.getInt16(44+1000*2,true)-16384)<=8);return detail;
 });
 await run('corrupt, unsupported, mislabeled and declared-truncated inputs reject',async()=>{
  for(const b of [new Blob(['bad'],{type:'audio/wav'}),fixture('webmOpus','audio/ogg'),fixture('webmOpus','audio/mp4'),fixture('webmOpus','audio/webm').slice(0,-1,'audio/webm'),fixture('trailingMoov','audio/mp4').slice(0,-1,'audio/mp4')])check(await rejected(()=>normalizeRecording(b)));
 });
 await run('excessive decoded duration and output allocation guard',async()=>{
  const frames=1920001,b=new ArrayBuffer(44+frames*2),v=new DataView(b);new Uint8Array(b,0,44).set(new Uint8Array(await pcm.slice(0,44).arrayBuffer()));
  v.setUint32(4,b.byteLength-8,true);v.setUint16(22,1,true);v.setUint32(24,16000,true);v.setUint32(28,32000,true);v.setUint16(32,2,true);v.setUint32(40,frames*2,true);
  check(await rejected(()=>normalizeRecording(new Blob([b],{type:'audio/wav'}))));
  check(await rejected(()=>encodePcmWav(new AudioBuffer({length:160,sampleRate:16000,numberOfChannels:1}),undefined,44)));
 });
 await run('pre-cancelled decode and cancelled PCM produce no result',async()=>{
  const c=new AbortController();c.abort();check(await rejected(()=>normalizeRecording(pcm,c.signal)));
  const audio=new AudioBuffer({length:100000,sampleRate:16000,numberOfChannels:1}),next=new AbortController();const pending=encodePcmWav(audio,next.signal);next.abort();check(await rejected(()=>pending));
 });
 return {results,canonicalWavs,pcmDiagnostic,recordingSupport:{webm:MediaRecorder.isTypeSupported('audio/webm;codecs=opus'),aac:MediaRecorder.isTypeSupported('audio/mp4;codecs=mp4a.40.2')}};})()`;
 const response=await send('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true},sessionId);
 if(response.exceptionDetails)throw Error(JSON.stringify(response.exceptionDetails));
 const value=response.result.value;await writeFile('/tmp/corvus-stt-r4-browser-results.json',JSON.stringify({version,...value},null,2));
 console.log(JSON.stringify({version:version.product,results:value.results,pcmDiagnostic:value.pcmDiagnostic,recordingSupport:value.recordingSupport}));if(value.results.some(r=>!r.pass))process.exitCode=1;
} finally {clearTimeout(timeout);chrome.kill('SIGTERM');await exited;if(!profile.startsWith('/tmp/corvus-stt-r4-chrome-'))throw Error('Profile cleanup identity failed');await rm(profile,{recursive:true,force:true});}
