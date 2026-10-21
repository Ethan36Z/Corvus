/** Focused native-source compilation and transient/reference byte contracts. */
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import vm from 'node:vm';
const require = createRequire(import.meta.url);
const deps = process.env.VISION_NODE_MODULES;
const ts = require(deps + '/typescript/lib/typescript.js');
const lifecycleOnly = process.env.VISION_LIFECYCLE_ONLY === '1';
const svelte = lifecycleOnly ? null : require(deps + '/svelte/compiler.cjs');
const vitePreprocess = lifecycleOnly ? null : (await import(deps + '/@sveltejs/vite-plugin-svelte/src/index.js')).vitePreprocess;
const root = process.env.VISION_PATCHED;
const helper = readFileSync(root + '/src/lib/utils/corvus-vision.ts', 'utf8');
const js = ts.transpileModule(helper,{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS}}).outputText;
const context = { exports:{}, Uint8Array, Blob, atob, AbortController, fetch:undefined };
vm.runInNewContext(js,context);
const { imageDraft,persistentDraft,uploadImage } = context.exports;
const png = Uint8Array.from([137,80,78,71,13,10,26,10,1,2,3]);
const draft = { type:'image',url:'data:image/png;base64,'+Buffer.from(png).toString('base64') };
const large = Buffer.alloc(20*1024*1024); Buffer.from(png).copy(large);
const largeDraft = {type:'image',url:'data:image/png;base64,'+large.toString('base64')};
assert.equal((await imageDraft([largeDraft],false).arrayBuffer()).byteLength,large.length);
assert.throws(()=>imageDraft([{...largeDraft,url:'data:image/png;base64,'+Buffer.concat([large,Buffer.from([0])]).toString('base64')}],false));
const blob = imageDraft([draft],false);
assert.equal(blob.type,'image/png');assert.deepEqual(new Uint8Array(await blob.arrayBuffer()),png);
assert.throws(()=>imageDraft([draft],true));assert.throws(()=>imageDraft([draft,draft],false));
assert.throws(()=>imageDraft([{...draft,url:'data:image/gif;base64,AAAA'}],false));
assert.throws(()=>imageDraft([{...draft,url:'data:image/png;base64,AAAA'}],false));
assert.equal(persistentDraft({prompt:'text',files:[draft]}).files.length,0);
assert.ok(!JSON.stringify(persistentDraft({prompt:'text',files:[draft]})).includes('data:image'));
let calls=0;
context.fetch=async(url,options)=>{
 calls++;assert.equal(options.method,'POST');assert.equal(options.headers['Content-Type'],'image/png');
 assert.deepEqual(new Uint8Array(await options.body.arrayBuffer()),png);
 return {ok:true,json:async()=>({type:'image',corvus_ref:'00000000-0000-0000-0000-000000000001',url:'/api/v1/files/00000000-0000-0000-0000-000000000001/content'})};
};
await uploadImage('synthetic','chat','message',blob,new AbortController().signal);assert.equal(calls,1);
if (!lifecycleOnly) for(const name of ['Chat.svelte','MessageInput.svelte']){
 const source=readFileSync(root+'/src/lib/components/chat/'+name,'utf8');
 const processed=await svelte.preprocess(source,vitePreprocess(),{filename:name});
 svelte.compile(processed.code,{filename:name,generate:'dom'});
 if(name==='Chat.svelte'){
  assert.ok(source.includes('JSON.stringify(persistentDraft(input))'));
  assert.ok(!source.includes("type: 'image_url'"));
  assert.ok(source.includes('const _files = visionDraft ? []'));
  assert.ok(source.indexOf('imageDraft(files, arenaForTurn)')<source.indexOf('let userMessageId = uuidv4()'));
  assert.ok(source.indexOf('uploadImage(localStorage.token')<source.indexOf('\n        await Promise.all('));
  assert.ok(source.includes('imageController?.abort()'));
 }
}
console.log(lifecycleOnly ? 'Installed TypeScript/native function contracts; Svelte compilation not rerun.' : 'Native Svelte compilation and transient/reference contracts passed.');

// Execute the actual native submit/send functions with mocked existing APIs.
// This catches images entering the first-chat/save queues before the upload.
const native=readFileSync(root+'/src/lib/components/chat/Chat.svelte','utf8').match(/<script lang="ts">([\s\S]*?)<\/script>/)[1];
const tree=ts.createSourceFile('Chat.ts',native,ts.ScriptTarget.Latest,true,ts.ScriptKind.TS);
const declarations=[];
for(const statement of tree.statements){
 if(ts.isVariableStatement(statement))for(const declaration of statement.declarationList.declarations){
  if(['submitPrompt','sendPrompt','cancelImageUploadForChat'].includes(declaration.name.getText(tree)))declarations.push('const '+declaration.getText(tree)+';');
 }
}
assert.equal(declarations.length,3);
const executable=ts.transpileModule(declarations.join('\n'),{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.None}}).outputText;
let sequence=0;
async function turn({arena=false,fail=false,cancel=false,otherModel=false,sameChat=false,navigate=false,timeout=false,stateSync=false,nativeOverride=null,referenceSaveFail=false}={}){
 const events=[],errors=[];let stored=null;const display=[];let displayedUrl=null;
 const sandbox={ imageDraft,persistentDraft,Blob,AbortController,setTimeout,clearTimeout,clearInterval,
  imageController:null,imageUploadChatId:'',files:[draft],chatFiles:[],prompt:'Describe image',history:{messages:{},currentId:null},
  arenaEnabled:arena,arenaAvailable:true,selectedModels:['corvus_pipe'],selectedToolIds:[],
  webSearchEnabled:false,imageGenerationEnabled:false,codeInterpreterEnabled:false,
  $temporaryChatEnabled:false,$models:[{id:'corvus_pipe',info:{meta:{capabilities:{vision:true}}}}],
  $settings:{richTextInput:true,memory:false},$config:{},$chatId:'',$currentChatPage:1,
  atSelectedModel:otherModel?{id:'another-model'}:undefined,autoScroll:false,localStorage:{token:'synthetic'},
  document:{getElementById:()=>null},console:{log:()=>{}},toast:{error:(text)=>errors.push(text)},$i18n:{t:(text)=>text},
  uuidv4:()=>`00000000-0000-0000-0000-${String(++sequence).padStart(12,'0')}`,
  tick:async()=>{},saveSessionSelectedModels:()=>{},scrollToBottom:()=>{},getChatEventEmitter:async()=>null,
  getChatList:async()=>[],currentChatPage:{set:()=>{}},chats:{set:()=>{}},
  createMessagesList:(h,id)=>{const out=[];while(id){const m=h.messages[id];if(!m)break;out.unshift(m);id=m.parentId;}return out;},
 };
 if(timeout)sandbox.setTimeout=(callback,ms)=>{assert.equal(ms,30000);queueMicrotask(callback);return 0;};
 const flushNativeImage=()=>{
  const user=Object.values(sandbox.history.messages).find(m=>m.role==='user');
  const ref=user?.files?.[0];
  if(ref && ref.url!==displayedUrl){
   displayedUrl=ref.url;
   // Same membership gate as the existing authenticated content endpoint.
   display.push(stored?.messages?.[user.id]?.files?.[0]?.corvus_ref===ref.corvus_ref?200:404);
  }
 };
 const save=(kind,h)=>{assert.ok(!JSON.stringify(h).includes('data:image'));events.push(kind);};
 sandbox.initChatHandler=async(h)=>{save('create',h);stored=JSON.parse(JSON.stringify(h));sandbox.$chatId='00000000-0000-0000-0000-000000000099';return sandbox.$chatId;};
 sandbox.saveChatHandler=async(id,h)=>save('save',h);
 sandbox.uploadImage=async(token,chat,message,b,signal)=>{
  events.push('upload');assert.equal(b.type,'image/png');assert.deepEqual(new Uint8Array(await b.arrayBuffer()),png);
  assert.ok(sandbox.history.messages[message].corvus_image_pending);
  assert.equal(sandbox.history.messages[message].files,undefined);
  if(fail)throw Error('Synthetic lost response');
  if(sameChat)sandbox.chatChanged(chat);
  if(navigate)sandbox.chatChanged('another-chat');
  if(cancel)sandbox.imageController.abort();
  return {type:'image',corvus_ref:'00000000-0000-0000-0000-000000000001',url:'/api/v1/files/00000000-0000-0000-0000-000000000001/content'};
 };
 sandbox.sendPromptSocket=async(h,model,assistant)=>{
  if(stateSync)flushNativeImage();
  const parent=h.messages[h.messages[assistant].parentId];
  assert.equal(parent.files[0].type,'image');assert.ok(parent.files[0].corvus_ref);
  assert.equal(parent.content,'Describe image');events.push('dispatch');
 };
 let runCode=executable;
 if(stateSync){
  const source=nativeOverride??native,tree=ts.createSourceFile('State.ts',source,ts.ScriptTarget.Latest,true,ts.ScriptKind.TS),nodes=[];
  for(const statement of tree.statements)if(ts.isVariableStatement(statement))for(const d of statement.declarationList.declarations){
   if(['submitPrompt','sendPrompt','cancelImageUploadForChat','persistChatHistory','saveChatHandler'].includes(d.name.getText(tree)))nodes.push('const '+d.getText(tree)+';');
  }
  assert.equal(nodes.length,5);
  runCode=ts.transpileModule(nodes.join('\n'),{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.None}}).outputText;
  Object.assign(sandbox,{params:{},chat:null,persistedArenaTrialIds:new Set(),arenaTrialIdsFromSavedHistory:()=>new Set(),arenaSaves:{save:async(id,callback)=>callback()}});
  sandbox.updateChatById=async(token,id,body)=>{
   events.push('save');flushNativeImage();await Promise.resolve();flushNativeImage();
   assert.ok(!JSON.stringify(body).includes('data:image'));
   if(referenceSaveFail && Object.values(body.history.messages).some(m=>m.files?.length))throw Error('Synthetic reference commit failed');
   stored=JSON.parse(JSON.stringify(body.history));return {id,chat:{history:stored}};
  };
 }
 vm.runInNewContext(runCode+'\nglobalThis.submitNative = submitPrompt;globalThis.chatChanged = cancelImageUploadForChat;'+(stateSync?'globalThis.persistForTest=persistChatHistory;':''),sandbox);
 await sandbox.submitNative('Describe image');
 if(stateSync)flushNativeImage();
 return {events,errors,history:sandbox.history,stored,display,sandbox,getStored:()=>stored};
}
const success=await turn();assert.deepEqual(success.events,['create','save','upload','save','dispatch']);assert.deepEqual(success.errors,[]);
assert.deepEqual((await turn({arena:true})).events,[]);
assert.deepEqual((await turn({fail:true})).events,['create','save','upload']);
console.log('Actual native submit/send: reference-only initial/save queues, upload-before-dispatch, preserved text, Arena zero writes, lost upload no dispatch passed (mocked APIs).');

const cancelled=await turn({cancel:true});assert.deepEqual(cancelled.events,['create','save','upload']);assert.ok(Object.values(cancelled.history.messages).filter(m=>m.role==='assistant').every(m=>m.done));
console.log('Native upload cancellation releases composer and never dispatches a late result.');

assert.deepEqual((await turn({otherModel:true})).events,[]);
console.log('Native @model override rejects image turn before any save/upload.');

// Exercise the actual generated lifecycle dependency gate; unlike extracting only
// submit/send, this reproduces the Svelte dirty-controller flush that caused the
// real upload cancellation. All fetch/provider calls remain mocked.
if (process.env.VISION_COMPILED_BEFORE && process.env.VISION_COMPILED_AFTER) {
 function lifecycle(path) {
  const source=readFileSync(path,'utf8');
  const match=source.match(/o\.\$\$\.dirty\[1\]&([0-9]+)&&C&&\(([^,]+),\(async/);
  assert.ok(match,'Actual chat reactive gate not found');
  const ctx={O:new AbortController(),C:'owned-chat',visionUploadChatId:'owned-chat',o:{$$:{dirty:[0,1<<24]}}};
  const helper=source.match(/const cancelImageUploadForChat=next=>\{[^}]+\};/);
  if(helper)vm.runInNewContext(helper[0],ctx);
  const flush=()=>vm.runInNewContext(`if(o.$$.dirty[1]&${match[1]} && C) {${match[2]};}`,ctx);
  flush();return {ctx,flush,mask:Number(match[1])};
 }
 const original=lifecycle(process.env.VISION_COMPILED_BEFORE);
 assert.equal(original.ctx.O.signal.aborted,true,'Original deployed controller flush must reproduce abort');
 const before=readFileSync(process.env.VISION_COMPILED_BEFORE,'utf8');
 const after=readFileSync(process.env.VISION_COMPILED_AFTER,'utf8');
 for(const anchor of ['ur(()=>{O==null||O.abort(),j==null||j()', 'Qt=async()=>{if(O==null||O.abort(),xe)', 'setTimeout(()=>Lt.abort(),3e4)']) {
  assert.ok(before.includes(anchor) && after.includes(anchor),'Existing cleanup/stop/timeout must remain');
 }
 const fixed=lifecycle(process.env.VISION_COMPILED_AFTER);
 assert.equal(fixed.mask,1<<23);assert.equal(fixed.ctx.O.signal.aborted,false);
 fixed.ctx.o.$$.dirty[1]=1<<23;fixed.flush();assert.equal(fixed.ctx.O.signal.aborted,false,'Same owned chat must not cancel');
 fixed.ctx.C='another-chat';fixed.flush();assert.equal(fixed.ctx.O.signal.aborted,true,'Real chat navigation must cancel');
 console.log('Actual deployed reactive self-abort reproduced; corrected controller flush/same-chat/navigation verified offline.');
}
assert.deepEqual((await turn({sameChat:true})).events,['create','save','upload','save','dispatch']);
for (const settings of [{navigate:true},{timeout:true}]) {
 const result=await turn(settings);assert.deepEqual(result.events,['create','save','upload']);
 assert.ok(Object.values(result.history.messages).filter(m=>m.role==='assistant').every(m=>m.done));
}
console.log('Native functions: same-chat upload completes; navigation/cancellation/timeout signal prevents late save/dispatch, without retries.');

if(process.env.VISION_STATE_BEFORE){
 const before=readFileSync(process.env.VISION_STATE_BEFORE,'utf8').match(/<script lang="ts">([\s\S]*?)<\/script>/)[1];
 const raced=await turn({stateSync:true,nativeOverride:before});
 assert.deepEqual(raced.display,[404],'Original native order must reproduce image GET before saved membership');
 const fixed=await turn({stateSync:true});
 assert.deepEqual(fixed.events,['create','save','upload','save','dispatch']);
 assert.deepEqual(fixed.display,[200],'First native image mount must see committed reference');
 const user=Object.values(fixed.history.messages).find(m=>m.role==='user');
 assert.equal(JSON.stringify(fixed.stored.messages[user.id].files),JSON.stringify(user.files));
 assert.ok(!fixed.stored.messages[user.id].corvus_image_pending);
 // Reopening the same saved history must resolve exactly the displayed URL.
 assert.equal(fixed.stored.messages[user.id].files[0].url,user.files[0].url);
 const failed=await turn({stateSync:true,referenceSaveFail:true});
 assert.deepEqual(failed.events,['create','save','upload','save']);assert.deepEqual(failed.display,[]);
 assert.ok(Object.values(failed.history.messages).filter(m=>m.role==='user').every(m=>!m.files?.length));
 const cancelled=await turn({stateSync:true,navigate:true});assert.deepEqual(cancelled.display,[]);assert.ok(!cancelled.events.includes('dispatch'));
 // Preserve the existing Arena/default save behavior: newest live state wins
 // over an older body snapshot unless this reference commit explicitly opts in.
 const stale=JSON.parse(JSON.stringify(fixed.history));
 fixed.history.messages[fixed.history.currentId].content='latest synthetic event';
 await fixed.sandbox.persistForTest('synthetic',fixed.sandbox.$chatId,{history:stale});
 assert.equal(fixed.getStored().messages[fixed.history.currentId].content,'latest synthetic event');
 console.log('Actual native save functions reproduce pre-commit 404; fixed initial display/reload references agree; save failure/navigation never render or dispatch; default current-history capture preserved.');
}
