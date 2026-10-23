// Existing Node test runner; synthetic native chat events and media, no network/storage.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { stripTypeScriptTypes } from 'node:module';
const source = await readFile(new URL('../deploy/lab/voice-call/call-loop.ts', import.meta.url), 'utf8');
const { CallLoop, callSession } = await import('data:text/javascript;base64,' + Buffer.from(stripTypeScriptTypes(source, {mode:'strip'})).toString('base64'));
const tick = async () => { for (let i=0;i<8;i++) await Promise.resolve(); };
const event = (target,type,detail) => target.dispatchEvent(new CustomEvent(type,{detail}));
const deferred = () => { let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});return {promise,resolve,reject}; };
function fixture(options={}) {
 const target=new EventTarget(), timers=new Set(), calls=[], sounds=[], stopped=[], views=[];
 const history={currentId:null,messages:{}};let seq=0;
 const ports={history:()=>history,ready:()=>true,
  submit:(text)=>{calls.push(text);const u='u'+(++seq),a='a'+seq;history.messages[u]={id:u,role:'user',content:text};history.messages[a]={id:a,parentId:u,model:'corvus_pipe',role:'assistant',done:false,content:''};history.currentId=a;event(target,'chat:start',{id:a});},
  synthesize:async(text,signal)=>{sounds.push({text,signal});return {ok:true,blob:async()=>new Blob(['synthetic PCM'],{type:'audio/wav'})};},
  play:async(blob,started)=>started(),stopAudio:()=>stopped.push(true),...options};
 const loop=new CallLoop(target,{setTimer:f=>(timers.add(f),f),clearTimer:f=>timers.delete(f)});
 const detach=loop.attach(ports,s=>views.push(s));
 const send=(text='confirmed synthetic text')=>{assert.equal(loop.listening(),true);loop.transcribing();loop.transcribed(text);return loop.send(text);};
 const finish=(text='saved synthetic reply',extra={})=>{const id=history.currentId;Object.assign(history.messages[id],{done:true,content:text},extra);event(target,'chat:finish',{id,content:text});};
 return {loop,target,history,ports,calls,sounds,stopped,timers,views,detach,send,finish};
}
test('two full call turns reuse native submit, committed completion and speech',async()=>{
 const f=fixture();f.send();assert.equal(f.loop.state.phase,'Thinking');assert.equal(f.sounds.length,0);assert.equal(f.loop.listening(),false);
 event(f.target,'chat',{id:f.history.currentId,content:'partial'});await tick();assert.equal(f.sounds.length,0);
 f.finish();await tick();assert.equal(f.loop.state.phase,'Idle');assert.equal(f.sounds.length,1);assert.equal(f.timers.size,0);
 f.send('second edited turn');f.finish('second saved reply');await tick();assert.deepEqual(f.calls,['confirmed synthetic text','second edited turn']);assert.equal(f.sounds.length,2);
});
test('transcription remains reviewable; edited send is exactly once',()=>{
 const f=fixture();f.loop.listening();f.loop.transcribed('draft');assert.equal(f.calls.length,0);assert.equal(f.loop.state.phase,'Review');
 assert.equal(f.loop.send('edited'),true);assert.equal(f.loop.send('edited'),false);assert.deepEqual(f.calls,['edited']);
});
test('cancelled transcription cannot auto-submit or restore a stale draft',()=>{
 const f=fixture();f.loop.listening();f.loop.transcribing();f.loop.cancelRecording();f.loop.transcribed('late');assert.equal(f.loop.state.phase,'Idle');assert.equal(f.calls.length,0);assert.equal(f.loop.state.draft,'');
});
test('busy native chat is rejected before submit without losing review text',()=>{
 const f=fixture();f.loop.listening();f.loop.transcribed('draft');f.ports.ready=()=>false;assert.equal(f.loop.send('edited'),false);assert.equal(f.calls.length,0);assert.equal(f.loop.state.phase,'Review');
});
test('foreign start and finish events cannot authorize speech',async()=>{
 const f=fixture();f.send();event(f.target,'chat:finish',{id:'foreign',content:'not ours'});await tick();assert.equal(f.sounds.length,0);assert.equal(f.loop.state.pending,true);
});
test('a matching finish without done/commit evidence is unknown, not speech',async()=>{
 const f=fixture();f.send();const id=f.history.currentId;f.history.messages[id].content='partial';event(f.target,'chat:finish',{id,content:'partial'});await tick();assert.equal(f.loop.state.phase,'Unknown');assert.equal(f.sounds.length,0);
});
test('error or mismatched content cannot be spoken',async()=>{
 for(const extra of [{error:{content:'failure'}},{model:'other'}]){const f=fixture();f.send();f.finish('not confirmed',extra);await tick();assert.equal(f.loop.state.phase,'Unknown');assert.equal(f.sounds.length,0);}
 const f=fixture();f.send();f.history.messages[f.history.currentId].done=true;event(f.target,'chat:finish',{id:f.history.currentId,content:'different'});await tick();assert.equal(f.sounds.length,0);
});
test('failed submit is unknown and never retried',async()=>{
 const f=fixture({submit:()=>Promise.reject(new Error('unknown transport outcome'))});f.send();await tick();assert.equal(f.loop.state.phase,'Unknown');assert.equal(f.loop.send(),false);assert.equal(f.loop.listening(),false);assert.equal(f.sounds.length,0);
});
test('timeout locks the turn; late completion is saved without surprise playback',async()=>{
 const f=fixture();f.send();[...f.timers][0]();assert.equal(f.loop.state.phase,'Unknown');assert.equal(f.loop.listening(),false);f.finish();await tick();assert.equal(f.loop.state.pending,false);assert.equal(f.loop.state.phase,'Idle');assert.equal(f.sounds.length,0);assert.equal(f.calls.length,1);
});
test('hangup does not abort submitted chat; later completion is not spoken',async()=>{
 const f=fixture();f.send();f.detach();f.finish();await tick();assert.equal(f.calls.length,1);assert.equal(f.loop.state.pending,false);assert.equal(f.loop.state.reply,'saved synthetic reply');assert.equal(f.sounds.length,0);
});
test('layout remount reuses pending identity instead of creating another turn',()=>{
 const target=new EventTarget();const a=callSession(target);const b=callSession(target);assert.equal(a,b);
 const f=fixture();f.send();f.detach();f.loop.attach(f.ports,()=>{});assert.equal(f.loop.send('duplicate'),false);assert.equal(f.calls.length,1);
});
test('stop during TTS download aborts media and suppresses late playback',async()=>{
 const d=deferred();let signal,plays=0;const f=fixture({synthesize:async(text,s)=>{signal=s;return d.promise;},play:async()=>{plays++;}});f.send();f.finish();await tick();assert.equal(f.loop.state.phase,'Synthesizing');f.loop.stopSpeaking();assert.equal(signal.aborted,true);d.resolve({ok:true,blob:async()=>new Blob(['audio'],{type:'audio/wav'})});await tick();assert.equal(plays,0);assert.equal(f.calls.length,1);assert.equal(f.loop.state.reply,'saved synthetic reply');
});
test('stop during playback preserves reply and allows next turn',async()=>{
 const d=deferred();const f=fixture({play:async(blob,started)=>{started();return d.promise;},stopAudio:()=>d.resolve()});f.send();f.finish();await tick();assert.equal(f.loop.state.phase,'Speaking');assert.equal(f.loop.listening(),false);f.loop.stopSpeaking();await tick();assert.equal(f.loop.state.phase,'Idle');assert.equal(f.calls.length,1);assert.equal(f.loop.listening(),true);
});
test('TTS failure is recoverable by replay only, not chat resubmission',async()=>{
 let n=0;const f=fixture({synthesize:async()=>{if(!n++)throw Error('speech');return {ok:true,blob:async()=>new Blob(['audio'],{type:'audio/wav'})};}});f.send();f.finish();await tick();assert.equal(f.loop.state.phase,'Error');assert.match(f.loop.state.notice,/saved/);await f.loop.speak();assert.equal(f.loop.state.phase,'Idle');assert.equal(f.calls.length,1);assert.equal(n,2);
});
test('playback rejection and malformed media become visible errors',async()=>{
 for(const ports of [{play:async()=>{throw Error('autoplay denied');}},{synthesize:async()=>({ok:true,blob:async()=>new Blob(['bad'],{type:'text/html'})})}]){const f=fixture(ports);f.send();f.finish();await tick();assert.equal(f.loop.state.phase,'Error');assert.equal(f.calls.length,1);}
});
test('native history error is surfaced before the long wait timer',()=>{const f=fixture();f.send();f.history.messages[f.history.currentId].error={};f.loop.observe();assert.equal(f.loop.state.phase,'Unknown');assert.equal(f.timers.size,0);});
test('stale rejection/timer from completed turn cannot poison a new turn',async()=>{
 const old=deferred();const f=fixture();const native=f.ports.submit;f.ports.submit=text=>{native(text);return old.promise;};f.send();const timer=[...f.timers][0];f.finish();await tick();f.ports.submit=native;f.send('next');old.reject(Error('late'));timer();await tick();assert.equal(f.loop.state.phase,'Thinking');f.finish();await tick();assert.equal(f.loop.state.phase,'Idle');
});
