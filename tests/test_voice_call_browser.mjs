// Real headless Chrome + native Svelte recorder/converter; synthetic media/API only.
// Uses the existing pinned WebUI compiler/dependencies, not a new test framework.
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { readFile, writeFile, mkdtemp, rm } from 'node:fs/promises';
import { spawn } from 'node:child_process';
import path from 'node:path';
const prepared=path.resolve(process.argv[2] || '');
const require=createRequire(process.env.CORVUS_FRONTEND_PACKAGE);
const {compile,preprocess}=require('svelte/compiler'),ts=require('typescript'),esbuild=require('esbuild');
const tmp=await mkdtemp('/tmp/corvus-call-browser-');
const fixture=JSON.parse(await readFile(new URL('./fixtures/stt-r4-synthetic.json',import.meta.url),'utf8'));
const entry=path.join(tmp,'App.svelte');
await writeFile(entry,`<script>import {setContext} from 'svelte';import {writable} from 'svelte/store';import Call from '${prepared}/src/lib/components/chat/MessageInput/CallOverlay.svelte';setContext('i18n',writable({t:x=>x}));export let history=window.voiceFixture.history;</script><Call eventTarget={window.voiceFixture.target} submitPrompt={window.voiceFixture.submit} {history} modelId="corvus_pipe" chatId="synthetic-chat" files={[]} stopResponse={()=>window.voiceFixture.chatAborts++} />`);
const stub = {
 '$lib/stores':`import {writable} from 'svelte/store';export const config=writable({audio:{stt:{engine:'whisper'},tts:{engine:'corvus-kokoro'}}});export const settings=writable({});export const models=writable([{id:'corvus_pipe'}]);export const showCallOverlay=writable(true);export const TTSWorker=writable(null);`,
 '$lib/apis/audio':`export const transcribeAudio=(...args)=>window.voiceFixture.transcribe(...args);export const synthesizeOpenAISpeech=(...args)=>window.voiceFixture.speech(...args);`,
 '$lib/utils':`export const blobToFile=(blob,name)=>new File([blob],name,{type:blob.type});export const calculateSHA256=()=>'';export const extractCurlyBraceWords=()=>[];`,
 '$lib/components/common/Tooltip.svelte':`export default class {}`,
 '$lib/apis':`export const generateEmoji=()=>{throw Error('Unexpected extra model request')};`,
 '$lib/workers/KokoroWorker':`export class KokoroWorker {constructor(){throw Error('Unexpected browser model')}}`,
 'svelte-sonner':`export const toast={error:()=>window.voiceFixture.errors++};`
};
const built=await esbuild.build({stdin:{contents:`import App from '${entry}';window.callApp=new App({target:document.body});`,resolveDir:tmp},bundle:true,write:false,format:'iife',platform:'browser',define:{'import.meta.env.VITE_CORVUS_VOICE_CALL':JSON.stringify('true')},conditions:['svelte','browser'],nodePaths:[path.join(path.dirname(process.env.CORVUS_FRONTEND_PACKAGE),'node_modules')],plugins:[{name:'native-call-fixture',setup(build){
 build.onResolve({filter:/^\$lib\/|^svelte-sonner$/},args=>stub[args.path]?{path:args.path,namespace:'fixture'}:{path:path.join(prepared,'src/lib',args.path.slice(5)+(args.path.endsWith('.ts')?'':'.ts'))});
 build.onResolve({filter:/(Tooltip|VideoInputMenu)\.svelte$/},args=>({path:args.path,namespace:'dormant-native'}));
 build.onLoad({filter:/.*/,namespace:'dormant-native'},()=>({contents:'export default class {}',loader:'js'}));
 build.onLoad({filter:/.*/,namespace:'fixture'},args=>({contents:stub[args.path],loader:'js',resolveDir:path.dirname(process.env.CORVUS_FRONTEND_PACKAGE)}));
 build.onLoad({filter:/\.svelte$/},async args=>{const text=await readFile(args.path,'utf8');const processed=await preprocess(text,{script:({content,attributes})=>attributes.lang==='ts'?{code:ts.transpileModule(content,{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext,verbatimModuleSyntax:true}}).outputText}:undefined},{filename:args.path});return {contents:compile(processed.code,{filename:args.path,generate:'dom',css:'injected'}).js.code,loader:'js',resolveDir:path.dirname(args.path)};});
}}]});
const setup=`
window.voiceFixture={history:{currentId:null,messages:{}},target:new EventTarget(),sent:[],saved:[],stt:0,tts:0,errors:0,tracks:[],urls:0,chatAborts:0};
const f=window.voiceFixture;let seq=0;
f.submit=async(text)=>{f.sent.push(text);const u='u'+(++seq),a='a'+seq;f.history.messages[u]={id:u,role:'user',content:text};f.history.messages[a]={id:a,parentId:u,model:'corvus_pipe',done:false,content:''};f.history.currentId=a;f.target.dispatchEvent(new CustomEvent('chat:start',{detail:{id:a}}));};
f.complete=()=>{const id=f.history.currentId;const row=f.history.messages[id];row.done=true;row.content='Saved synthetic reply '+seq;f.saved.push(row.content);f.target.dispatchEvent(new CustomEvent('chat:finish',{detail:{id,content:row.content}}));window.callApp.$set({history:f.history});};
f.transcribe=async(token,file,signal)=>{f.stt++;const v=new DataView(await file.arrayBuffer());if(v.getUint32(24,true)!==16000 || file.type!=='audio/wav')throw Error('not normalized');return {text:'Synthetic microphone transcript'};};
f.speech=async(token,voice,text,model,signal)=>{f.tts++;if(!f.saved.includes(text))throw Error('uncommitted speech');if(voice!=='af_mica'||model!=='kokoro')throw Error('wrong voice');const wav=new Uint8Array(4844),v=new DataView(wav.buffer);const tag=(i,t)=>[...t].forEach((c,n)=>v.setUint8(i+n,c.charCodeAt(0)));tag(0,'RIFF');v.setUint32(4,4836,true);tag(8,'WAVE');tag(12,'fmt ');v.setUint32(16,16,true);v.setUint16(20,1,true);v.setUint16(22,1,true);v.setUint32(24,24000,true);v.setUint32(28,48000,true);v.setUint16(32,2,true);v.setUint16(34,16,true);tag(36,'data');v.setUint32(40,4800,true);return new Response(new Blob([wav],{type:'audio/wav'}),{headers:{'Content-Type':'audio/wav'}});};
const original=navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);navigator.mediaDevices.getUserMedia=async(...args)=>{const s=await original(...args);f.tracks.push(...s.getTracks());return s;};
const fixtureBytes=Uint8Array.from(atob('${fixture.webmOpus}'),x=>x.charCodeAt(0));
window.MediaRecorder=class {constructor(stream){this.stream=stream;this.mimeType='audio/webm;codecs=opus';this.state='inactive';(f.recorders??=[]).push(this);}start(){this.state='recording';queueMicrotask(()=>this.onstart?.());}stop(){this.state='inactive';this.ondataavailable?.({data:new Blob([fixtureBytes],{type:this.mimeType})});queueMicrotask(()=>this.onstop?.());}};
HTMLMediaElement.prototype.play=function(){f.playing=this;return Promise.resolve();};HTMLMediaElement.prototype.pause=function(){if(f.playing===this)f.playing=null;};HTMLMediaElement.prototype.load=function(){};
const create=URL.createObjectURL.bind(URL),revoke=URL.revokeObjectURL.bind(URL);URL.createObjectURL=(b)=>{f.urls++;return create(b)};URL.revokeObjectURL=(u)=>{f.urls--;return revoke(u)};
`;
await writeFile(path.join(tmp,'index.html'),`<!doctype html><meta charset="utf-8"><body><script>${setup}</script><script>${built.outputFiles[0].text.replaceAll('</script>','<\\/script>')}</script>`);
const chrome=spawn('/opt/google/chrome/chrome',['--headless=new','--disable-gpu','--disable-background-networking','--disable-component-update','--disable-sync','--no-first-run','--no-default-browser-check','--no-proxy-server','--host-resolver-rules=MAP * ~NOTFOUND','--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream','--remote-debugging-pipe',`--user-data-dir=${tmp}/profile`],{stdio:['ignore','ignore','pipe','pipe','pipe']});
const exited=new Promise(resolve=>chrome.once('exit',resolve));
let id=0,buffer='',errors='';const pending=new Map();
chrome.stderr.on('data',d=>errors+=d.toString());
chrome.stdio[4].on('data',d=>{buffer+=d;let end;while((end=buffer.indexOf('\0'))>=0){const m=JSON.parse(buffer.slice(0,end));buffer=buffer.slice(end+1);if(m.method==='Runtime.exceptionThrown') console.error('Synthetic page exception:',JSON.stringify(m.params.exceptionDetails));if(m.id){const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(Error(JSON.stringify(m.error))):p.resolve(m.result);}}});
const send=(method,params={},sessionId)=>new Promise((resolve,reject)=>{const n=++id;pending.set(n,{resolve,reject});chrome.stdio[3].write(JSON.stringify({id:n,method,params,sessionId})+'\0');});
chrome.on('exit',()=>{for(const p of pending.values())p.reject(Error('Browser exited '+errors.slice(-400)));});
const timeout=setTimeout(()=>chrome.kill(),45000);
try {
 const {targetId}=await send('Target.createTarget',{url:'about:blank'});const {sessionId}=await send('Target.attachToTarget',{targetId,flatten:true});
 await send('Page.enable',{},sessionId);await send('Runtime.enable',{},sessionId);await send('Page.navigate',{url:'file://'+path.join(tmp,'index.html')},sessionId);
 const evaluate=async(expression)=>{const r=await send('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true},sessionId);if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value;};
 const result=await evaluate(`(async()=>{
 const wait=async(fn)=>{for(let i=0;i<400;i++){if(fn())return;await new Promise(r=>setTimeout(r,10));}throw Error('UI timeout: '+document.body.innerText+' '+JSON.stringify({tts:window.voiceFixture?.tts,urls:window.voiceFixture?.urls,saved:window.voiceFixture?.saved.length,errors:window.voiceFixture?.errors,playing:!!window.voiceFixture?.playing}));};
 await wait(()=>window.callApp);const f=window.voiceFixture;
 const button=(label)=>[...document.querySelectorAll('button')].find(x=>x.textContent.trim()===label);
 const state=()=>document.querySelector('[role=status]')?.textContent.trim();
 button('Record a turn').click();await wait(()=>state()==='Listening'&&document.querySelector('[aria-label]'));
 await wait(()=>f.recorders?.at(-1)?.state==='recording');
 // The inherited recorder's confirm control is the final button inside its native bordered container.
 const nativeButtons=[...document.querySelectorAll('button')].filter(x=>x.querySelector('svg'));
 if(!nativeButtons.length)throw Error('Native recorder not mounted');nativeButtons.at(-1).click();
 await wait(()=>state()==='Review');if(f.sent.length)throw Error('Automatic submit');
 const edit=document.querySelector('textarea');edit.value='Edited confirmed turn';edit.dispatchEvent(new Event('input',{bubbles:true}));button('Send this turn').click();
 await wait(()=>state()==='Thinking');if(f.sent.length!==1||f.tts!==0)throw Error('Submit/persistence boundary');
 f.complete();await wait(()=>state()==='Speaking');button('Stop speaking').click();await wait(()=>state()==='Idle');if(f.urls!==0)throw Error('Audio URL leak');
 button('Record a turn').click();await wait(()=>state()==='Listening');await wait(()=>f.recorders?.at(-1)?.state==='recording');[...document.querySelectorAll('button')].filter(x=>x.querySelector('svg')).at(-1).click();await wait(()=>state()==='Review');button('Send this turn').click();await wait(()=>state()==='Thinking');
 const count=f.tts;button('End call').click();f.complete();await new Promise(r=>setTimeout(r,50));
 if(f.sent.length!==2||f.saved.length!==2||f.tts!==count||f.chatAborts!==0)throw Error('Hangup corrupted submitted work');
 window.callApp.$destroy();await new Promise(r=>setTimeout(r,20));if(f.tracks.some(t=>t.readyState!=='ended')||f.urls)throw Error('Media cleanup leak');
 return {native_call_overlay:true,native_recorder_and_normalizer:true,chat_aborts:f.chatAborts,turns:f.sent.length,saved_replies:f.saved.length,tts_requests:f.tts,manual_edit_preserved:f.sent[0]==='Edited confirmed turn',all_tracks_released:true,object_urls_released:true,real_microphone:false,real_model_or_tts:false};})()`);
 assert.equal(result.manual_edit_preserved,true);console.log(JSON.stringify(result));
} finally {clearTimeout(timeout);await send('Browser.close').catch(()=>{});await exited;await rm(tmp,{recursive:true,force:true});}
