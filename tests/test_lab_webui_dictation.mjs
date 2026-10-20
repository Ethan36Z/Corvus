// Synthetic browser contracts against the actual patched native script/functions.
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createRequire, stripTypeScriptTypes } from 'node:module';
import vm from 'node:vm';
import test from 'node:test';
import path from 'node:path';

const root = process.argv[2] || '/tmp/corvus-stt-r4-prepared';
const original = process.argv[3] || '/tmp/corvus-arena-ui1/source';
const require = createRequire('/tmp/corvus-arena-ui1/work/package.json');
const svelte = require('svelte/compiler');
const ts = require('typescript');
const voicePath = 'src/lib/components/chat/MessageInput/VoiceRecording.svelte';
const composerPath = 'src/lib/components/chat/MessageInput.svelte';
const apiPath = 'src/lib/apis/audio/index.ts';
const helper = await readFile(path.join(root, 'src/lib/utils/corvus-dictation.ts'), 'utf8');
const voice = await readFile(path.join(root, voicePath), 'utf8');
const composer = await readFile(path.join(root, composerPath), 'utf8');
const apiSource = await readFile(path.join(root, apiPath), 'utf8');
const js = (text) => stripTypeScriptTypes(text, { mode: 'strip' });
const helperJS = js(helper).replace(/export /g, '') + '\nconst normalizeRecording = (()=>{ ' + js(await readFile(path.join(root, 'src/lib/utils/corvus-normalize.ts'), 'utf8')).replace(/export /g, '') + '; return normalizeRecording; })();';
const own = (value) => JSON.parse(JSON.stringify(value));
const turn = () => new Promise((resolve) => setImmediate(resolve));

function wav(rate = 16000) {
 const b = new ArrayBuffer(364), v = new DataView(b);
 const tag = (at, text) => [...text].forEach((c, i) => v.setUint8(at+i,c.charCodeAt(0)));
 tag(0,'RIFF');v.setUint32(4,356,true);tag(8,'WAVE');tag(12,'fmt ');v.setUint32(16,16,true);
 v.setUint16(20,1,true);v.setUint16(22,1,true);v.setUint32(24,rate,true);v.setUint32(28,rate*2,true);
 v.setUint16(32,2,true);v.setUint16(34,16,true);tag(36,'data');v.setUint32(40,320,true);
 return new Blob([b],{type:'audio/wav'});
}

function environment({ mime='audio/wav', chunk=wav(), answer, permission, decoder, engine='' } = {}) {
 const events=[], calls=[], errors=[], logs=[], tracks=[], contexts=[], recorders=[], pending=[], intervals=new Set(),ticks=[];
 let destroy;
 const stream={ getTracks: () => tracks };
 tracks.push({ stopped:0, stop() {this.stopped++;} });
 class Context {
  constructor() {this.closed=0;contexts.push(this);}
  createMediaStreamSource() {return {connect(){}};}
  createAnalyser() {return {frequencyBinCount:16,fftSize:32};}
  async close() {this.closed++;}
 }
 class Recorder {
  constructor(s) {assert.equal(s,stream);this.mimeType=mime;this.state='inactive';recorders.push(this);}
  start() {this.state='recording';this.onstart?.();}
  stop() {
   assert.notEqual(this.state,'inactive');this.state='inactive';
   queueMicrotask(() => {this.ondataavailable?.({data:chunk});pending.push(Promise.resolve(this.onstop?.()));});
  }
 }
 const settings={speechAutoSend:true};
 class OfflineContext {
  constructor(channels, length, rate) {assert.equal(rate,16000);}
  async decodeAudioData(bytes) {
   if(decoder) return await decoder(bytes);
   const v=new DataView(bytes), channels=v.getUint16(22,true), rate=v.getUint32(24,true);
   const frames=Math.round(v.getUint32(40,true)/(channels*2)*16000/rate);
   return {sampleRate:16000,length:frames,numberOfChannels:channels,getChannelData:()=>new Float32Array(frames)};
  }
 }
 const sandbox={ Blob, File, AbortController, DOMException, DataView, Uint8Array, setTimeout, clearTimeout,
  OfflineAudioContext:OfflineContext,
  createEventDispatcher:()=> (event,detail)=>events.push({event,detail}),
  getContext:()=>({}), onMount:()=>{}, onDestroy:(fn)=>destroy=fn, tick:async()=>{},
  $config:{audio:{stt:{engine}}},$settings:settings,$i18n:{t:(text)=>text},
  toast:{error:(message)=>errors.push(message)},
  blobToFile:(blob,name)=>new File([blob],name,{type:blob.type}),
  transcribeAudio:async (...args)=> {calls.push(args);return answer ? await answer(...args):{text:'中文 English PRIVATE_TRANSCRIPT'};},
  localStorage:{get token(){return 'synthetic-native-token';},setItem(){throw Error('No storage writes');}},
  navigator:{mediaDevices:{getUserMedia:async (options)=> {
   assert.deepEqual(own(options),{audio:{echoCancellation:true,noiseSuppression:true,autoGainControl:true}});
   return permission ? await permission(stream):stream;
  }}}, AudioContext:Context,MediaRecorder:Recorder,
  setInterval:(fn)=> {ticks.push(fn);const n=intervals.size+1;intervals.add(n);return n;},clearInterval:(n)=>intervals.delete(n),
  window:{requestAnimationFrame:()=>0},document:{getElementById:()=>({focus(){}})},
  console:{log:(...v)=>logs.push(v),error:(...v)=>logs.push(v),debug:(...v)=>logs.push(v)},
 };
 const context=vm.createContext(sandbox);
 let script=voice.match(/<script lang="ts">([\s\S]*?)<\/script>/)[1];
 script=script.replace(/\bimport[\s\S]*?;/g,'').replace(/export let /g,'let ');
 script=script.replace(/\$:\s*if \(recording\) \{\s*startRecording\(\);\s*\} else \{\s*stopRecording\(\);\s*\}/,'');
 script=script.replace(/\$:\s*maxVisibleItems =[^;]+;/,'');
 vm.runInContext(helperJS+'\n'+js(script)+`\nglobalThis.component={startRecording,stopRecording,confirmRecording,transcribeHandler,recordingBlob,validateDictationWav,setRecording:(v)=>recording=v};`,context);
 return {component:context.component,events,calls,errors,logs,tracks,contexts,recorders,pending,settings,intervals,ticks,
  destroy:()=>destroy(), async start(){context.component.setRecording(true);await context.component.startRecording();},
  async finish(){await turn();await Promise.all(pending);}};
}

test('both native Svelte components compile; no replacement microphone or composer', async()=>{
 for (const [filename, source] of [[voicePath,voice],[composerPath,composer]]) {
  const preprocessed=source.replace(/(<script[^>]*>)([\s\S]*?)(<\/script>)/,(all,open,body,close)=>open+
    ts.transpileModule(body,{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext,verbatimModuleSyntax:true}}).outputText+close);
  assert.ok(svelte.compile(preprocessed,{filename,generate:'dom'}).js.code.length);
 }
 const prior=await readFile(path.join(original,voicePath),'utf8');
 assert.equal(voice.split('</script>')[1],prior.split('</script>')[1]);
 assert.equal((voice.match(/<button/g)||[]).length,(prior.match(/<button/g)||[]).length);
 assert.ok(composer.includes('<VoiceRecording'));assert.ok(composer.includes("dispatch('submit', prompt)"));
});

test('actual WebM/MP4 MIME and matching extensions preserved; never forged WAV',()=>{
 const {component}=environment();
 for(const [mime,ext] of [['audio/webm;codecs=opus','webm'],['audio/mp4;codecs=mp4a.40.2','m4a']]){
  const result=component.recordingBlob([new Blob(['synthetic'],{type:mime})],mime);
  assert.equal(result.blob.type,mime);assert.equal(result.filename,'recording.'+ext);
 }
 assert.throws(()=>component.recordingBlob([new Blob(['x'],{type:'audio/mp4'})],'audio/webm'));
 assert.throws(()=>component.recordingBlob([new Blob(['x'])],''));
});

test('unsupported compressed/unknown/corrupt WAV fail closed before native API',async()=>{
 for(const [mime,chunk] of [['audio/webm',new Blob(['webm'],{type:'audio/webm'})],
  ['audio/mp4',new Blob(['mp4'],{type:'audio/mp4'})],['audio/wav',new Blob(['not wav'],{type:'audio/wav'})],
  ['audio/wav',wav(192000)]]){
  const e=environment({mime,chunk});await e.start();await e.component.confirmRecording();await e.finish();
  assert.equal(e.calls.length,0);assert.ok(e.errors.length);assert.equal(e.events.filter(x=>x.event==='confirm').length,0);
 }
});

test('canonical synthetic WAV uses native authenticated API and returns text only',async()=>{
 const e=environment();await e.start();await e.component.confirmRecording();await e.finish();
 assert.equal(e.calls.length,1);assert.equal(e.calls[0][0],'synthetic-native-token');
 assert.equal(e.calls[0][1].type,'audio/wav');assert.equal(e.calls[0][1].name,'recording.wav');
 assert.deepEqual(own(e.events),[{event:'confirm',detail:{text:'中文 English PRIVATE_TRANSCRIPT'}}]);
 assert.equal(e.tracks[0].stopped,1);assert.equal(e.contexts[0].closed,1);assert.equal(e.intervals.size,0);
 assert.equal(e.logs.length,0);assert.equal(e.settings.speechAutoSend,true);
});

test('native confirm appends editable composer, never sends even with preference true',async()=>{
 const handler=composer.match(/on:confirm=\{(async \(e\) => \{[\s\S]*?\n[\t ]+\})\}/)[1];
 const settings={speechAutoSend:true}, events=[];let focused=0;
 const context=vm.createContext({$settings:settings,tick:async()=>{},dispatch:(...v)=>events.push(v),
  document:{getElementById:()=>({focus(){focused++;}})}});
 vm.runInContext(`let prompt='existing ';let recording=true;globalThis.confirm=(${handler});globalThis.getPrompt=()=>prompt;`,context);
 await context.confirm({detail:{text:'recognized 中文'}});
 assert.equal(context.getPrompt(),'existing recognized 中文 ');assert.equal(focused,1);assert.equal(events.length,0);
 assert.deepEqual(settings,{speechAutoSend:true});
 const old=await readFile(path.join(original,composerPath),'utf8');
 const auto="if ($settings?.speechAutoSend ?? false) {\n\t\t\t\t\t\t\t\t\tdispatch('submit', prompt);\n\t\t\t\t\t\t\t\t}";
 assert.equal(composer,old.replace(auto,'// Dictation stays editable; retain speechAutoSend for future voice modes.'));
});

test('cancel before stop discards data and releases native tracks',async()=>{
 const e=environment();await e.start();await e.component.stopRecording();await e.finish();
 assert.equal(e.calls.length,0);assert.equal(e.events.length,0);assert.equal(e.tracks[0].stopped,1);
 assert.equal(e.contexts[0].closed,1);assert.equal(e.intervals.size,0);
});

test('cancel during permission acquisition closes late tracks without recorder/API',async()=>{
 let resolve;const e=environment({permission:stream=>new Promise(r=>resolve=()=>r(stream))});
 const starting=e.start();await e.component.stopRecording();resolve();await starting;
 assert.equal(e.tracks[0].stopped,1);assert.equal(e.recorders.length,0);assert.equal(e.calls.length,0);
});

test('cancel during mocked HTTP aborts and suppresses late transcript',async()=>{
 let resolve;const e=environment({answer:()=>new Promise(r=>resolve=r)});
 await e.start();await e.component.confirmRecording();for(let n=0;n<30 && !e.calls.length;n++) await new Promise(r=>setTimeout(r,2));
 assert.equal(e.calls.length,1);const signal=e.calls[0][2];
 await e.component.stopRecording();assert.equal(signal.aborted,true);
 resolve({text:'LATE_PRIVATE_TRANSCRIPT'});await e.finish();
 assert.equal(e.events.length,0);assert.equal(e.logs.length,0);assert.equal(e.errors.length,0);
});

test('component destroy releases microphone/context and never submits',async()=>{
 const e=environment();await e.start();e.destroy();await e.finish();
 assert.equal(e.tracks[0].stopped,1);assert.equal(e.contexts[0].closed,1);assert.equal(e.calls.length,0);
});

test('browser speech recognition override fails closed without permission/API',async()=>{
 const e=environment({engine:'web'});await e.start();
 assert.equal(e.recorders.length,0);assert.equal(e.calls.length,0);assert.equal(e.events[0].event,'cancel');
 assert.equal(e.settings.speechAutoSend,true);
});

test('STT API keeps auth/multipart, rejects redirects, aborts, and never logs provider content',async()=>{
 const source=apiSource.slice(apiSource.indexOf('export const transcribeAudio ='),apiSource.indexOf('export const synthesizeOpenAISpeech ='));
 const calls=[],logs=[];let response={ok:true,json:async()=>({text:'PRIVATE_TRANSCRIPT'})};
 const context=vm.createContext({FormData,File,Error,AUDIO_API_BASE_URL:'/api/v1/audio',
  fetch:async(...args)=>{calls.push(args);return response;},console:{log:(...v)=>logs.push(v)}});
 vm.runInContext(js(source).replace('export const','globalThis.'),context);
 const file=new File([wav()],'recording.wav',{type:'audio/wav'});const controller=new AbortController();
 assert.equal((await context.transcribeAudio('synthetic-token',file,controller.signal)).text,'PRIVATE_TRANSCRIPT');
 assert.equal(calls[0][0],'/api/v1/audio/transcriptions');const options=calls[0][1];
 assert.equal(options.headers.authorization,'Bearer synthetic-token');assert.equal(options.redirect,'error');assert.equal(options.cache,'no-store');
 assert.equal(options.body.get('file').name,'recording.wav');assert.equal(options.signal,controller.signal);
 response={ok:false,json:async()=>({detail:'PRIVATE_ERROR'})};
 await assert.rejects(()=>context.transcribeAudio('synthetic-token',file),/Dictation is unavailable/);
 assert.equal(logs.length,0);
 const prior=await readFile(path.join(original,apiPath),'utf8');
 assert.equal(apiSource.slice(apiSource.indexOf('export const synthesizeOpenAISpeech =')),prior.slice(prior.indexOf('export const synthesizeOpenAISpeech =')));
 assert.ok(!voice.includes('console.'));assert.ok(!source.includes('console.'));assert.ok(!voice.includes("new (window.SpeechRecognition"));
});

test('stale cancelled recorder callbacks cannot release a subsequent recording',async()=>{
 const e=environment();await e.start();const old=e.recorders[0];
 await e.component.stopRecording();await e.start();
 await old.onstop();
 assert.equal(e.recorders[1].state,'recording');assert.equal(e.contexts[1].closed,0);
 assert.equal(e.calls.length,0);
 await e.component.stopRecording();await e.finish();
});


test('supported encoded container reaches same composer contract after mocked normalization',async()=>{
 const fixtures=JSON.parse(await readFile(new URL('fixtures/stt-r4-synthetic.json',import.meta.url),'utf8'));
 for(const [key,mime] of [['webmOpus','audio/webm;codecs=opus'],['unknownClusterWebmOpus','audio/webm;codecs=opus'],['trailingMoov','audio/mp4;codecs=mp4a.40.2']]){
  const e=environment({mime,chunk:new Blob([Buffer.from(fixtures[key],'base64')],{type:mime}),decoder:async()=>({sampleRate:16000,length:160,numberOfChannels:1,getChannelData:()=>new Float32Array(160)})});
  await e.start();await e.component.confirmRecording();await e.finish();assert.equal(e.calls.length,1);
  assert.equal(e.calls[0][1].type,'audio/wav');assert.equal(await e.component.validateDictationWav(e.calls[0][1]),true);
  assert.equal(e.events[0].event,'confirm');assert.equal(e.events.filter(x=>x.event==='submit').length,0);
 }
});
test('cancel while decode is pending drops late PCM and makes no API call',async()=>{
 let resolve;const e=environment({decoder:()=>new Promise(r=>resolve=r)});
 await e.start();await e.component.confirmRecording();await turn();await e.component.stopRecording();
 resolve({sampleRate:16000,length:160,numberOfChannels:1,getChannelData:()=>new Float32Array(160)});await e.finish();
 assert.equal(e.calls.length,0);assert.equal(e.events.length,0);assert.equal(e.logs.length,0);
});
test('encoded accumulation and recording duration caps cancel without submission',async()=>{
 const e=environment();await e.start();e.recorders[0].ondataavailable({data:new Blob([new Uint8Array(8*1024*1024+1)])});await e.finish();
 assert.equal(e.calls.length,0);assert.equal(e.events[0].event,'cancel');assert.equal(e.tracks[0].stopped,1);
 const d=environment();await d.start();for(let i=0;i<120;i++)d.ticks[0]();await d.finish();
 assert.equal(d.calls.length,0);assert.equal(d.events[0].event,'cancel');assert.equal(d.tracks[0].stopped,1);
});
