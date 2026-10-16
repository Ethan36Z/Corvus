/** Run against a checksum-verified, prepared --arena-ui1 source tree. No HTTP. */
import assert from 'node:assert/strict';
import { test } from 'node:test';
import vm from 'node:vm';
import { createRequire } from 'node:module';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { resolve, join } from 'node:path';
import { pathToFileURL } from 'node:url';

const root = resolve(process.argv[2]);
const require = createRequire(join(root, 'package.json'));
const ts = require('typescript');
const svelte = require('svelte/compiler');
const output = join(root, '.arena-ui1-tests');
await mkdir(output, { recursive: true });
const read = (p) => readFile(join(root, p), 'utf8');
const transpile = (code) => ts.transpileModule(code, {
 compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext, verbatimModuleSyntax: true }
}).outputText;
await writeFile(join(output, 'arena.mjs'), transpile(await read('src/lib/corvus-arena.ts')));
const { arenaMetadata, validArenaPayload, acceptArenaEvent, preserveArena, hasArena, createArenaSaveQueue } =
 await import(pathToFileURL(join(output, 'arena.mjs')));
const trial = '25415702-8bac-4f1a-9dd8-5eba47de0ff4';
const fixture = () => ({ version: 1, trial_id: trial, fairness: 'BEST_EFFORT_PRE_TURN',
 main: { status: 'OK', retrieval_status: 'OK', retrieval_ms: 10, generation_ms: 20,
  evidence: [{ message_id: 1, text: 'RAG evidence <script>unsafe()</script>' }] },
 shadow: { status: 'OK', recall_status: 'OK', reply: 'Shadow fixture', error_code: null,
  retrieval_ms: 30, generation_ms: 40, evidence: [{ source_id: 'hindsight:fact-1', text: 'Hindsight evidence' }] },
 evaluation: { status: 'STORED', votable: true } });
const history = () => ({ currentId: 'assistant', messages: {
 user: { id: 'user', role: 'user', content: 'Question' },
 assistant: { id: 'assistant', role: 'assistant', model: 'corvus_pipe', content: '', corvus_arena_requested: true }
} });
const event = (data = fixture()) => ({ chat_id: 'chat', message_id: 'assistant', data: { type: 'corvus:arena:v1', data } });
const copy = (v) => JSON.parse(JSON.stringify(v));

test('OFF default produces byte-identical request payload; saved panels do not opt in', () => {
 const normal = { stream: true, messages: [{ role: 'user', content: 'Question' }], chat_id: 'chat' };
 assert.equal(JSON.stringify({ ...normal, ...arenaMetadata() }), JSON.stringify(normal));
 assert.deepEqual(arenaMetadata(false), {});
 assert.deepEqual(arenaMetadata(true), { metadata: { corvus_arena: true } });
 assert.deepEqual(arenaMetadata('true'), {});
 const restored = history(); restored.messages.assistant.corvus_arena = fixture();
 assert.ok(hasArena(restored)); assert.deepEqual(arenaMetadata(), {});
});

test('valid event attaches only to the requested canonical assistant, separately from content', () => {
 const h = history(), e = event(); assert.ok(validArenaPayload(e.data.data));
 assert.ok(acceptArenaEvent(h, e, 'chat'));
 assert.equal(h.messages.assistant.content, '');
 assert.equal(h.messages.assistant.corvus_arena.trial_id, trial);
 e.data.data.shadow.reply = 'mutated';
 assert.equal(h.messages.assistant.corvus_arena.shadow.reply, 'Shadow fixture');
 assert.ok(!acceptArenaEvent(h, event(), 'chat')); // duplicate
 const different = fixture(); different.trial_id = 'ae03ed9d-94d2-4e5e-a104-2b5520530e07';
 assert.ok(!acceptArenaEvent(h, event(different), 'chat')); // no replacement
});

test('reject wrong chat, message, role, model, missing opt-in, schema and namespace', () => {
 for (const mutate of [
  (h,e) => e.chat_id = 'other', (h,e) => e.message_id = 'missing',
  h => h.messages.assistant.role = 'user', h => h.messages.assistant.model = 'other',
  h => delete h.messages.assistant.corvus_arena_requested,
  (h,e) => e.data.data.version = 2, (h,e) => e.data.data.trial_id = 'invalid',
  (h,e) => e.data.data.personality = 'unexpected',
  (h,e) => e.data.data.shadow.evidence[0].source_id = '17',
  (h,e) => e.data.data.main.retrieval_ms = NaN,
  (h,e) => e.data.data.evaluation.votable = 'true'
 ]) { const h=history(), e=event(); mutate(h,e); assert.equal(acceptArenaEvent(h,e,'chat'),false); }
});

test('event before stale completion survives; event after completion also attaches', () => {
 const h = history(), stale = copy(h.messages.assistant);
 assert.ok(acceptArenaEvent(h,event(),'chat'));
 stale.content = 'Canonical RAG reply'; stale.done = true;
 h.messages.assistant = preserveArena(stale,h.messages.assistant);
 assert.equal(h.messages.assistant.corvus_arena.trial_id,trial);
 const later = history(); later.messages.assistant.content='Canonical RAG reply'; later.messages.assistant.done=true;
 assert.ok(acceptArenaEvent(later,event(),'chat'));
 assert.equal(later.messages.assistant.content,'Canonical RAG reply');
});

test('full chat-history save/reload restores the panel without including it in provider content', () => {
 const h=history(); acceptArenaEvent(h,event(),'chat');
 const restored=JSON.parse(JSON.stringify({history:h})).history;
 assert.ok(validArenaPayload(restored.messages.assistant.corvus_arena));
 const provider = Object.values(restored.messages).map(m=>({role:m.role,content:m.content}));
 assert.ok(!JSON.stringify(provider).includes(trial));
 assert.deepEqual(arenaMetadata(),{});
});

test('queued writes never overlap or persist stale event/completion ordering', async () => {
 const queue=createArenaSaveQueue(), h=history(), writes=[];
 let release; const gate=new Promise(r=>release=r); let active=0;
 const first=queue.save('chat',async()=>{ assert.equal(active++,0); writes.push(copy(h)); await gate; active--; });
 await Promise.resolve(); assert.ok(queue.pending('chat'));
 acceptArenaEvent(h,event(),'chat');
 const second=queue.save('chat',async()=>{ assert.equal(active++,0); writes.push(copy(h)); active--; });
 h.messages.assistant.content='Canonical RAG reply'; h.messages.assistant.done=true;
 release(); await Promise.all([first,second]);
 assert.equal(writes.length,2); assert.equal(writes.at(-1).messages.assistant.content,'Canonical RAG reply');
 assert.equal(writes.at(-1).messages.assistant.corvus_arena.trial_id,trial);
});

test('failed write does not poison later saves or block another chat', async () => {
 const q=createArenaSaveQueue();
 await assert.rejects(q.save('a',async()=>{throw Error('disk');}));
 assert.equal(await q.save('a',async()=>42),42);
 assert.equal(await q.save('b',async()=>43),43);
});

async function compileSSR(source, name) {
 const processed=await svelte.preprocess(source,{script:({content,attributes})=>
  attributes.lang==='ts'?{code:transpile(content)}:undefined});
 const compiled=svelte.compile(processed.code,{generate:'ssr',filename:name});
 const file=join(output,name+'.mjs'); await writeFile(file,compiled.js.code);
 return (await import(pathToFileURL(file))).default;
}
await writeFile(join(output,'StubContentRenderer.mjs'), `import {create_ssr_component,escape} from 'svelte/internal';
export default create_ssr_component(($$result,props)=>'<div data-candidate="true">'+escape(props.content)+'</div>');`);
const panelSource=await read('src/lib/components/chat/Messages/ArenaPanel.svelte');
const Panel=await compileSSR(panelSource.replace("'./ContentRenderer.svelte'","'./StubContentRenderer.mjs'"),'ArenaPanel');
const render=(arena)=>Panel.render({arena,id:'assistant',history:history(),model:null}).html;

test('ArenaPanel success, escaped evidence, collapsed details, and no duplicate main or voting',()=>{
 const html=render(fixture());
 for(const label of ['Memory A/B','Hindsight candidate','Shadow fixture','Evidence &amp; timing','Corvus RAG','BEST_EFFORT_PRE_TURN']) assert.ok(html.includes(label),label);
 assert.ok(html.includes('&lt;script')); assert.ok(!html.includes('<script>'));
 assert.ok(!/<details[^>]*\bopen/.test(html)); assert.ok(!html.includes('Canonical RAG reply'));
 assert.ok(!/<button/.test(html)); assert.ok(!panelSource.includes('/api/'));
 assert.ok(panelSource.includes('floatingButtons={false} save={false}'));
});

test('ArenaPanel provider failure, empty evidence, unavailable comparison/evaluation',()=>{
 const a=fixture(); a.shadow.status='ERROR'; a.shadow.reply=null; a.shadow.error_code='SHADOW_GENERATION_FAILED';
 a.main.evidence=[]; a.shadow.evidence=[]; a.evaluation={status:'UNAVAILABLE',votable:false};
 const html=render(a); assert.ok(html.includes('Hindsight candidate unavailable'));
 assert.ok(html.includes('Evaluation record unavailable')); assert.equal((html.match(/No historical evidence/g)||[]).length,2);
 assert.ok(render(undefined).includes('Comparison unavailable'));
});

const inputSource=await read('src/lib/components/chat/MessageInput.svelte');
const toggle=inputSource.match(/\{#if arenaAvailable\}[\s\S]*?\{\/if\}/)[0];
const Toggle=await compileSSR('<script>export let arenaAvailable=true; export let arenaEnabled=false;</script>'+toggle,'Toggle');
test('actual input toggle markup defaults OFF, refresh creates OFF, and ON is accessible',()=>{
 for(let i=0;i<2;i++) assert.ok(Toggle.render().html.includes('aria-checked="false"'));
 assert.ok(Toggle.render({arenaEnabled:true}).html.includes('aria-checked="true"'));
 assert.ok(!Toggle.render({arenaAvailable:false}).html.includes('Memory A/B'));
});

test('pinned Chat wiring captures per submission, strips display data from messages, and serializes all writes',async()=>{
 const c=await read('src/lib/components/chat/Chat.svelte');
 assert.ok(c.includes('let arenaEnabled = false;'));
 assert.equal((c.match(/bind:arenaEnabled/g)||[]).length,2); // existing and fresh-chat inputs
 const placeholder=await read('src/lib/components/chat/Placeholder.svelte');
 assert.ok(placeholder.includes('bind:arenaEnabled'));
 assert.ok(c.includes('const arenaForTurn = arenaEnabled && arenaAvailable;'));
 assert.ok(c.includes('corvusArena: arenaForTurn'));
 assert.ok(c.includes('...arenaMetadata(arenaForTurn)'));
 assert.ok(c.includes('arenaForTurn = false) =>'));
 assert.ok(c.includes('preserveArena(message, history.messages[message.id])'));
 assert.equal((c.match(/await persistChatHistory\(/g)||[]).length,3);
 assert.equal((c.match(/await updateChatById\(/g)||[]).length,1);
 assert.ok(!/localStorage[^\n]*arenaEnabled|sessionStorage[^\n]*arenaEnabled/.test(c));
 assert.ok(!c.includes('corvus_arena: m.corvus_arena'));
 assert.ok(c.includes('saveHistory={saveChatHandler}'));
 const child=await read('src/lib/components/chat/Messages.svelte');
 assert.ok(!child.includes('updateChatById'));
});

test('pinned modified Svelte components compile with original compiler',async()=>{
 const { default: config } = await import(pathToFileURL(join(root,'svelte.config.js')));
 for(const name of ['Chat.svelte','MessageInput.svelte','Placeholder.svelte','Messages/ResponseMessage.svelte','Messages.svelte']) {
  const source=await read('src/lib/components/chat/'+name);
  const processed=await svelte.preprocess(source,config.preprocess,{filename:join(root,'src/lib/components/chat',name)});
  assert.doesNotThrow(()=>svelte.compile(processed.code,{generate:'ssr',filename:name}));
 }
});

// Execute declarations extracted from the actual patched Svelte scripts, including
// the parent/child integration. No reimplementation of the writer under test.
function declarations(source, names) {
 const script=source.match(/<script[^>]*>([\s\S]*?)<\/script>/)[1];
 const tree=ts.createSourceFile('component.ts',script,ts.ScriptTarget.Latest,true,ts.ScriptKind.TS);
 return names.map(name=>{
  const statement=tree.statements.find(n=>ts.isVariableStatement(n)&&n.declarationList.declarations.some(d=>d.name.getText(tree)===name));
  assert.ok(statement, name);
  return transpile(statement.getText(tree).replace(/^export /,''))+'\n';
 }).join('');
}
const chatSource=await read('src/lib/components/chat/Chat.svelte');
const messagesSource=await read('src/lib/components/chat/Messages.svelte');
function integration() {
 const stored=new Map(), requests=[];
 let hold, fail=false;
 const ctx=vm.createContext({ history:history(), $chatId:'chat', chat:{id:'chat'},
  $temporaryChatEnabled:false, localStorage:{token:'test'}, selectedModels:['corvus_pipe'],
  params:{},chatFiles:[], $currentChatPage:1,
  currentChatPage:{set(){}},chats:{set(){}},getChatList:async()=>[],
  createMessagesList:h=>Object.values(h.messages),createArenaSaveQueue,acceptArenaEvent,preserveArena,
  tick:async()=>{},$settings:{},$config:{},navigator:{},autoScroll:false,
  getMessageContentParts:()=>[],eventTarget:{dispatchEvent(){}},CustomEvent:class {},
  $models:[{id:'corvus_pipe'}],$socket:{id:'socket'},chatCompleted:async()=>null,
  toast:{error:message=>{throw Error(message);}},console:{log(){}},taskIds:null,
  updateChatById:async(token,id,body)=>{
   const snapshot=copy(body); requests.push({id,snapshot});
   if(hold){const gate=hold;hold=null;await gate;}
   if(fail){fail=false;throw Error('save failed');}
   stored.set(id,copy(snapshot));return {id,chat:copy(snapshot)};
  }
 });
 vm.runInContext('const arenaSaves=createArenaSaveQueue();'+declarations(chatSource,['persistChatHistory','saveChatHandler','chatCompletedHandler','chatCompletionEventHandler','chatEventHandler'])+
  ';globalThis.save=saveChatHandler;globalThis.persist=persistChatHistory;globalThis.onEvent=chatEventHandler;globalThis.complete=chatCompletionEventHandler;',ctx);
 const child=vm.createContext({history:ctx.history,chatId:'chat',$temporaryChatEnabled:false,
  saveHistory:(...args)=>ctx.save(...args),tick:async()=>{},uuidv4:()=> 'copy',sendPrompt:async()=>{throw Error('unexpected generation');}});
 vm.runInContext(declarations(messagesSource,['updateChat','editMessage','rateMessage','saveMessage'])+
  ';globalThis.save=updateChat;globalThis.edit=editMessage;globalThis.rate=rateMessage;globalThis.saveMessage=saveMessage;',child);
 return {ctx,child,stored,requests,holdNext(){let release;hold=new Promise(r=>release=r);return release;},failNext(){fail=true;}};
}
const flush=async()=>{for(let i=0;i<8;i++)await Promise.resolve();};

test('A: old OFF save finishes before queued Arena event/completion save; newest state survives reload',async()=>{
 const x=integration(), release=x.holdNext();
 delete x.ctx.history.messages.assistant.corvus_arena_requested;
 const old=x.ctx.save('chat',x.ctx.history);await flush();
 assert.equal(x.requests.length,1);
 x.ctx.history.messages.assistant.corvus_arena_requested=true;
 acceptArenaEvent(x.ctx.history,event(),'chat');x.ctx.history.messages.assistant.content='Latest canonical reply';
 const newer=x.ctx.save('chat',x.ctx.history);await flush();
 assert.equal(x.requests.length,1);release();await Promise.all([old,newer]);
 const reloaded=copy(x.stored.get('chat')).history;
 assert.equal(reloaded.messages.assistant.content,'Latest canonical reply');
 assert.equal(reloaded.messages.assistant.corvus_arena.trial_id,trial);
});

test('B: actual Messages delegate shares parent writer with event/completion saves',async()=>{
 const x=integration(),release=x.holdNext();
 const childSave=x.child.save();await flush();
 acceptArenaEvent(x.ctx.history,event(),'chat');x.ctx.history.messages.assistant.content='Completed';
 const completion=x.ctx.save('chat',x.ctx.history);await flush();assert.equal(x.requests.length,1);
 release();await Promise.all([childSave,completion]);
 assert.equal(x.stored.get('chat').history.messages.assistant.content,'Completed');
 assert.equal(x.stored.get('chat').history.messages.assistant.corvus_arena.trial_id,trial);
});

test('C: navigation does not retarget queued snapshots or apply old response to active chat',async()=>{
 const x=integration(),release=x.holdNext();
 const old=x.ctx.save('chat',x.ctx.history);await flush();
 acceptArenaEvent(x.ctx.history,event(),'chat');x.ctx.history.messages.assistant.content='Old chat final';
 const queued=x.ctx.save('chat',x.ctx.history);
 x.ctx.$chatId='other';x.ctx.history={currentId:'b',messages:{b:{id:'b',content:'Other chat'}}};x.ctx.chat={id:'other'};
 const other=x.ctx.save('other',x.ctx.history);await other;
 await x.ctx.save('chat',{messages:{bad:{content:'wrong chat'}}});
 release();await Promise.all([old,queued]);
 assert.equal(x.stored.get('chat').history.messages.assistant.content,'Old chat final');
 assert.equal(x.stored.get('other').history.messages.b.content,'Other chat');
 assert.equal(x.ctx.chat.id,'other');assert.equal(x.ctx.history.messages.b.content,'Other chat');
});

test('D/E: actual assistant copy/edit invalidates trial; normal rating preserves it',async()=>{
 const x=integration();acceptArenaEvent(x.ctx.history,event(),'chat');
 x.ctx.history.messages.assistant.parentId='user';x.ctx.history.messages.user.childrenIds=['assistant'];
 await x.child.edit('assistant','Copied answer',true);
 assert.equal(x.ctx.history.messages.copy.corvus_arena,undefined);
 assert.equal(x.ctx.history.messages.copy.corvus_arena_requested,undefined);
 assert.equal(x.ctx.history.messages.assistant.corvus_arena.trial_id,trial);
 await x.child.rate('assistant',1);
 assert.equal(x.stored.get('chat').history.messages.assistant.corvus_arena.trial_id,trial);
 await x.child.edit('assistant','Edited answer',false);
 assert.equal(x.stored.get('chat').history.messages.assistant.corvus_arena,undefined);
 assert.equal(x.stored.get('chat').history.messages.assistant.corvus_arena_requested,undefined);
 assert.equal(x.stored.get('chat').history.messages.assistant.content,'Edited answer');
});

test('actual parent writer recovers after failure without retry',async()=>{
 const x=integration();x.failNext();await assert.rejects(x.ctx.save('chat',x.ctx.history));
 x.ctx.history.messages.assistant.content='Recovered';await x.ctx.save('chat',x.ctx.history);
 assert.equal(x.requests.length,2);assert.equal(x.stored.get('chat').history.messages.assistant.content,'Recovered');
});

test('other assistant content-save and inline code edits also invalidate association',async()=>{
 const x=integration();acceptArenaEvent(x.ctx.history,event(),'chat');
 await x.child.saveMessage('assistant',{...x.ctx.history.messages.assistant,content:'Changed through content-save'});
 assert.equal(x.stored.get('chat').history.messages.assistant.corvus_arena,undefined);
 x.ctx.history.messages.assistant.corvus_arena_requested=true;
 acceptArenaEvent(x.ctx.history,event(),'chat');
 const response=await read('src/lib/components/chat/Messages/ResponseMessage.svelte');
 const callback=response.match(/on:update=\{(\(e\) => \{[\s\S]*?)\}\}\s*on:select/)[1]+'}';
 const context=vm.createContext({history:x.ctx.history,message:{id:'assistant'},updateChat:()=>x.child.save()});
 const apply=vm.runInContext('('+callback+')',context);
 apply({detail:{raw:'Changed through content-save',oldContent:'Changed',newContent:'Inline edited'}});
 await flush();await x.ctx.save('chat',x.ctx.history);
 assert.equal(x.stored.get('chat').history.messages.assistant.corvus_arena,undefined);
 assert.equal(x.stored.get('chat').history.messages.assistant.corvus_arena_requested,undefined);
 assert.equal(x.stored.get('chat').history.messages.assistant.content,'Inline edited through content-save');
});

// Actual Arena dispatch + actual completion + actual completion-save integration.
test('pre-completion Arena event attaches locally without enqueueing a history write',async()=>{
 const x=integration();await x.ctx.onEvent(event());await flush();
 assert.equal(x.ctx.history.messages.assistant.corvus_arena.trial_id,trial);
 assert.equal(x.ctx.history.messages.assistant.content,'');assert.equal(x.requests.length,0);
 // A terminal but empty/error placeholder must not originate an Arena save either.
 const empty=integration();empty.ctx.history.messages.assistant.done=true;
 await empty.ctx.onEvent(event());assert.equal(empty.requests.length,0);
});

test('event then actual completion persists finished canonical reply with attached Arena',async()=>{
 const x=integration();await x.ctx.onEvent(event());assert.equal(x.requests.length,0);
 await x.ctx.complete({content:'Completed canonical reply',done:true},x.ctx.history.messages.assistant,'chat');
 assert.equal(x.requests.length,1);
 const saved=x.stored.get('chat').history.messages.assistant;
 assert.equal(saved.content,'Completed canonical reply');assert.equal(saved.done,true);
 assert.equal(saved.corvus_arena.trial_id,trial);
});

test('server completion before Arena persistence is never replaced by an event placeholder',async()=>{
 const x=integration();await x.ctx.onEvent(event());
 const serverHistory=copy(x.ctx.history);serverHistory.messages.assistant.content='Server-completed reply';
 x.stored.set('chat',{history:serverHistory});await flush();
 assert.equal(x.requests.length,0);assert.equal(x.stored.get('chat').history.messages.assistant.content,'Server-completed reply');
 await x.ctx.complete({content:'Server-completed reply',done:true},x.ctx.history.messages.assistant,'chat');
 assert.ok(x.requests.every(r=>r.snapshot.history.messages.assistant.done===true&&r.snapshot.history.messages.assistant.content==='Server-completed reply'));
 assert.equal(x.stored.get('chat').history.messages.assistant.corvus_arena.trial_id,trial);
});

test('actual completion then Arena event saves the same finished reply plus comparison',async()=>{
 const x=integration();await x.ctx.complete({content:'Canonical complete first',done:true},x.ctx.history.messages.assistant,'chat');
 assert.equal(x.requests.length,1);assert.equal(x.stored.get('chat').history.messages.assistant.corvus_arena,undefined);
 await x.ctx.onEvent(event());assert.equal(x.requests.length,2);
 const saved=x.stored.get('chat').history.messages.assistant;
 assert.equal(saved.content,'Canonical complete first');assert.equal(saved.corvus_arena.trial_id,trial);
 await x.ctx.onEvent(event());assert.equal(x.requests.length,2); // no duplicate save
});

test('navigation after local Arena event cannot overwrite upstream completed reply',async()=>{
 const x=integration();await x.ctx.onEvent(event());assert.equal(x.requests.length,0);
 x.ctx.$chatId='other';x.ctx.history={currentId:'b',messages:{b:{content:'Other chat'}}};x.ctx.chat={id:'other'};
 const serverHistory=history();serverHistory.messages.assistant.content='Server canonical reply';serverHistory.messages.assistant.done=true;
 x.stored.set('chat',{history:copy(serverHistory)});
 await x.ctx.onEvent({chat_id:'chat',message_id:'assistant',data:{type:'chat:completion',data:{content:'Server canonical reply',done:true}}});
 await flush();assert.equal(x.requests.length,0);
 assert.equal(x.stored.get('chat').history.messages.assistant.content,'Server canonical reply');
 assert.equal(x.stored.get('chat').history.messages.assistant.corvus_arena,undefined);
 assert.equal(x.ctx.history.messages.b.content,'Other chat');assert.equal(x.ctx.chat.id,'other');
});
