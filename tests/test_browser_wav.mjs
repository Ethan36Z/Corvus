// Mock WebAudio allocation/PCM/cancellation contracts. No real codec claims.
import assert from 'node:assert/strict';
import test from 'node:test';
import vm from 'node:vm';
import {readFile} from 'node:fs/promises';
import {stripTypeScriptTypes} from 'node:module';
const source=stripTypeScriptTypes(await readFile(new URL('../deploy/lab/stt/normalize.ts',import.meta.url),'utf8'),{mode:'strip'}).replace(/export /g,'');
const fixtures=JSON.parse(await readFile(new URL('fixtures/stt-r4-synthetic.json',import.meta.url),'utf8'));
const blob=(key='webmOpus',type='audio/webm;codecs=opus')=>new Blob([Buffer.from(fixtures[key],'base64')],{type});
const audio=(values=[[-1,0,1]],rate=16000)=>({sampleRate:rate,length:values[0].length,numberOfChannels:values.length,getChannelData:n=>Float32Array.from(values[n])});
function env(decode=async()=>audio(),clock={setTimeout,clearTimeout}){
 const calls=[];
 class Context {constructor(...args){calls.push(args);}decodeAudioData(bytes){return decode(bytes);}}
 const context=vm.createContext({Blob,DOMException,AbortController,OfflineAudioContext:Context,DataView,Uint8Array,...clock});
 vm.runInContext(source+'\nglobalThis.api={normalizeRecording,encodePcmWav};',context);
 return {...context.api,calls};
}
test('finite mono WAV header and exact clipped PCM frame values',async()=>{
 const e=env(), wav=await e.encodePcmWav(audio([[-2,-1,-.5,0,.5,1,2]]));
 const v=new DataView(await wav.arrayBuffer());assert.equal(wav.type,'audio/wav');assert.equal(wav.size,58);
 for(const [at,value] of [[4,50],[16,16],[24,16000],[28,32000],[40,14]]) assert.equal(v.getUint32(at,true),value);
 for(const [at,value] of [[20,1],[22,1],[32,2],[34,16]]) assert.equal(v.getUint16(at,true),value);
 assert.deepEqual(Array.from({length:7},(_,i)=>v.getInt16(44+i*2,true)),[-32768,-32768,-16384,0,16384,32767,32767]);
});
test('stereo downmix averages channels',async()=>{
 const w=await env().encodePcmWav(audio([[1,-1,.5],[-1,1,.5]])),v=new DataView(await w.arrayBuffer());
 assert.deepEqual([0,1,2].map(i=>v.getInt16(44+i*2,true)),[0,0,16384]);
});
test('output/duration/channel/rate/nonfinite guards reject before PCM allocation',async()=>{
 const e=env();let read=false;
 for(const patch of [{length:0},{length:1920001},{sampleRate:48000},{numberOfChannels:3}]) {
  await assert.rejects(()=>e.encodePcmWav({...audio(),...patch,getChannelData(){read=true;throw Error();}}));
 }
 await assert.rejects(()=>e.encodePcmWav({...audio(),getChannelData(){read=true;throw Error();}},undefined,45));
 assert.equal(read,false);await assert.rejects(()=>e.encodePcmWav(audio([[NaN]])));
});
test('real metadata preserved and decode requested at 16k; output separately encoded',async()=>{
 const e=env();const input=blob();const result=await e.normalizeRecording(input);
 assert.equal(input.type,'audio/webm;codecs=opus');assert.equal(result.type,'audio/wav');
 assert.equal(e.calls[0][0],1);assert.equal(e.calls[0][1],1);assert.equal(e.calls[0][2],16000);
});
test('encoded cap, empty and unsupported MIME reject before decoder construction',async()=>{
 const e=env();for(const b of [new Blob([],{type:'audio/webm'}),new Blob([new Uint8Array(8*1024*1024+1)],{type:'audio/webm'}),blob('webmOpus','audio/ogg')]) await assert.rejects(()=>e.normalizeRecording(b));
 assert.equal(e.calls.length,0);
});
test('corrupt/mislabeled/declared-truncated containers reject before decoder',async()=>{
 const e=env();
 for(const b of [new Blob(['bad'],{type:'audio/webm'}),blob('webmOpus','audio/mp4'),
 new Blob([Buffer.from(fixtures.webmOpus,'base64').subarray(0,-1)],{type:'audio/webm'}),
 new Blob([Buffer.from(fixtures.trailingMoov,'base64').subarray(0,-1)],{type:'audio/mp4'})]) await assert.rejects(()=>e.normalizeRecording(b));
 assert.equal(e.calls.length,0);
});
test('decoder errors are sanitized without including provider content',async()=>{
 const e=env(async()=>{throw Error('PRIVATE_DECODER_CONTENT');});
 await assert.rejects(()=>e.normalizeRecording(blob()),error=>!error.message.includes('PRIVATE')&&/cannot be normalized/.test(error.message));
});
test('excessive decoded duration fails after native allocation, never reaches samples',async()=>{
 let samples=false;const e=env(async()=>({...audio(),length:1920001,getChannelData(){samples=true;throw Error();}}));
 await assert.rejects(()=>e.normalizeRecording(blob()));assert.equal(e.calls.length,1);assert.equal(samples,false);
});
test('cancel pending native decode rejects promptly; latch held until native promise settles',async()=>{
 let finish,count=0;const e=env(()=>count++ ? Promise.resolve(audio()) : new Promise(r=>finish=r)),controller=new AbortController();
 const pending=e.normalizeRecording(blob(),controller.signal);await new Promise(r=>setImmediate(r));controller.abort();
 await assert.rejects(()=>pending,{name:'AbortError'});
 await assert.rejects(()=>e.normalizeRecording(blob()));assert.equal(e.calls.length,1);
 finish(audio());await new Promise(r=>setImmediate(r));
 assert.equal((await e.normalizeRecording(blob())).type,'audio/wav');
 const second=new AbortController();second.abort();await assert.rejects(()=>e.normalizeRecording(blob(),second.signal),{name:'AbortError'});
});
test('logical deadline rejects but does not claim native decoder termination',async()=>{
 let finish,deadline;const e=env(()=>new Promise(r=>finish=r),{setTimeout:(fn,ms)=>{assert.equal(ms,15000);deadline=fn;return 1;},clearTimeout:()=>{}});
 const pending=e.normalizeRecording(blob());await new Promise(r=>setImmediate(r));deadline();await assert.rejects(()=>pending);
 await assert.rejects(()=>e.normalizeRecording(blob()));assert.equal(e.calls.length,1);finish(audio());await new Promise(r=>setImmediate(r));
});
test('cancel during chunked PCM encoding drops output',async()=>{
 const controller=new AbortController(),e=env();const pending=e.encodePcmWav(audio([new Array(100000).fill(.2)]),controller.signal);
 controller.abort();await assert.rejects(()=>pending,{name:'AbortError'});
});

// Structural cases use the existing mocked decoder, not codec-acceptance claims.
const ebml = (...parts) => Uint8Array.from(parts.flatMap(part => Array.from(part)));
const ebmlHeader = [0x1a,0x45,0xdf,0xa3,0x80];
const segment = [0x18,0x53,0x80,0x67,0xff];
const cluster = [0x1f,0x43,0xb6,0x75,0xff];
const block = [0xa3,0x84,0x81,0,0,0];
const webm = (...parts) => new Blob([ebml(ebmlHeader,...parts)],{type:'audio/webm'});

test('unknown-sized Cluster fixture reaches existing decoder; finite fixture stays accepted',async()=>{
 const e=env();
 for(const key of ['webmOpus','unknownClusterWebmOpus']) {
  const wav=await e.normalizeRecording(blob(key));assert.equal(wav.type,'audio/wav');
 }
 assert.equal(e.calls.length,2);
});
test('streaming Clusters terminate at siblings and finite parent end without growing nesting',async()=>{
 const e=env();
 // More than eight siblings must not be interpreted as recursive Clusters.
 await e.normalizeRecording(webm(segment,...Array.from({length:20},()=>ebml(cluster,block)),[0x1c,0x53,0xbb,0x6b,0x80]));
 const payload=ebml(cluster,block);
 await e.normalizeRecording(webm([0x18,0x53,0x80,0x67,0x80+payload.length],payload));
 assert.equal(e.calls.length,2);
});
test('unknown sizes outside Segment/its Cluster, truncated payloads and parent escapes reject',async()=>{
 const e=env();
 for(const input of [webm(segment,cluster,[0xa3,0xff]),
   webm(segment,[0x15,0x49,0xa9,0x66,0xff],block),
   webm(cluster,block),webm(segment,[0xae,0x80+cluster.length+block.length],cluster,block),
   webm(segment,cluster,[0xa3,0x85,0x81,0,0,0]),
   webm([0x18,0x53,0x80,0x67,0x80+cluster.length+block.length-1],cluster,block),
   blob('unknownClusterWebmOpus').slice(0,-1,'audio/webm')]) {
  await assert.rejects(()=>e.normalizeRecording(input));
 }
 assert.equal(e.calls.length,0);
});
test('streaming Cluster keeps depth and element-count limits',async()=>{
 const e=env();let nested=ebml(block);
 for(let i=0;i<10;i++)nested=ebml([0xae,0x80+nested.length],nested);
 await assert.rejects(()=>e.normalizeRecording(webm(segment,cluster,nested)));
 await assert.rejects(()=>e.normalizeRecording(webm(segment,cluster,block,new Uint8Array(200002).map((_,i)=>i%2 ? 0x80 : 0xec))));
 assert.equal(e.calls.length,0);
});
