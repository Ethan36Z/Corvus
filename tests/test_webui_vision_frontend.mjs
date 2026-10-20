/** Focused native-source compilation and transient/reference byte contracts. */
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import vm from 'node:vm';
const require = createRequire(import.meta.url);
const deps = process.env.VISION_NODE_MODULES;
const ts = require(deps + '/typescript/lib/typescript.js');
const svelte = require(deps + '/svelte/compiler.cjs');
const { vitePreprocess } = await import(deps + '/@sveltejs/vite-plugin-svelte/src/index.js');
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
for(const name of ['Chat.svelte','MessageInput.svelte']){
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
console.log('Native Svelte compilation; transient draft, final upload bytes, reference shape, count/type/Arena rejection and save-before-dispatch checks passed. No image build or inference.');

// Execute the actual native submit/send functions with mocked existing APIs.
// This catches images entering the first-chat/save queues before the upload.
const native=readFileSync(root+'/src/lib/components/chat/Chat.svelte','utf8').match(/<script lang="ts">([\s\S]*?)<\/script>/)[1];
const tree=ts.createSourceFile('Chat.ts',native,ts.ScriptTarget.Latest,true,ts.ScriptKind.TS);
const declarations=[];
for(const statement of tree.statements){
 if(ts.isVariableStatement(statement))for(const declaration of statement.declarationList.declarations){
  if(['submitPrompt','sendPrompt'].includes(declaration.name.getText(tree)))declarations.push('const '+declaration.getText(tree)+';');
 }
}
assert.equal(declarations.length,2);
const executable=ts.transpileModule(declarations.join('\n'),{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.None}}).outputText;
let sequence=0;
async function turn({arena=false,fail=false,cancel=false,otherModel=false}={}){
 const events=[],errors=[];
 const sandbox={ imageDraft,persistentDraft,Blob,AbortController,setTimeout,clearTimeout,clearInterval,
  imageController:null,files:[draft],chatFiles:[],prompt:'Describe image',history:{messages:{},currentId:null},
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
 const save=(kind,h)=>{assert.ok(!JSON.stringify(h).includes('data:image'));events.push(kind);};
 sandbox.initChatHandler=async(h)=>{save('create',h);sandbox.$chatId='00000000-0000-0000-0000-000000000099';return sandbox.$chatId;};
 sandbox.saveChatHandler=async(id,h)=>save('save',h);
 sandbox.uploadImage=async(token,chat,message,b,signal)=>{
  events.push('upload');assert.equal(b.type,'image/png');assert.deepEqual(new Uint8Array(await b.arrayBuffer()),png);
  assert.ok(sandbox.history.messages[message].corvus_image_pending);
  assert.equal(sandbox.history.messages[message].files,undefined);
  if(fail)throw Error('Synthetic lost response');
  if(cancel)sandbox.imageController.abort();
  return {type:'image',corvus_ref:'00000000-0000-0000-0000-000000000001',url:'/api/v1/files/00000000-0000-0000-0000-000000000001/content'};
 };
 sandbox.sendPromptSocket=async(h,model,assistant)=>{
  const parent=h.messages[h.messages[assistant].parentId];
  assert.equal(parent.files[0].type,'image');assert.ok(parent.files[0].corvus_ref);
  assert.equal(parent.content,'Describe image');events.push('dispatch');
 };
 vm.runInNewContext(executable+'\nglobalThis.submitNative = submitPrompt;',sandbox);
 await sandbox.submitNative('Describe image');return {events,errors,history:sandbox.history};
}
const success=await turn();assert.deepEqual(success.events,['create','save','upload','save','dispatch']);assert.deepEqual(success.errors,[]);
assert.deepEqual((await turn({arena:true})).events,[]);
assert.deepEqual((await turn({fail:true})).events,['create','save','upload']);
console.log('Actual native submit/send: reference-only initial/save queues, upload-before-dispatch, preserved text, Arena zero writes, lost upload no dispatch passed (mocked APIs).');

const cancelled=await turn({cancel:true});assert.deepEqual(cancelled.events,['create','save','upload']);assert.ok(Object.values(cancelled.history.messages).filter(m=>m.role==='assistant').every(m=>m.done));
console.log('Native upload cancellation releases composer and never dispatches a late result.');

assert.deepEqual((await turn({otherModel:true})).events,[]);
console.log('Native @model override rejects image turn before any save/upload.');
