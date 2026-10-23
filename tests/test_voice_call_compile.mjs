// Use the existing locked WebUI Svelte/TypeScript packages; no network/install/build.
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {readFile} from 'node:fs/promises';
import path from 'node:path';
const require=createRequire(process.env.CORVUS_FRONTEND_PACKAGE);
const {compile,preprocess}=require('svelte/compiler'),ts=require('typescript');
const prepared=path.resolve(process.argv[2]);
const files=['src/lib/components/chat/MessageInput/CorvusCall.svelte','src/lib/components/chat/MessageInput/CallOverlay.svelte','src/lib/components/chat/MessageInput/VoiceRecording.svelte','src/lib/components/chat/ChatControls.svelte','src/lib/components/chat/MessageInput.svelte'];
const warnings=[];
for(const filename of files){
 const source=await readFile(path.join(prepared,filename),'utf8');
 const processed=await preprocess(source,{script:({content,attributes})=>attributes.lang==='ts'?{code:ts.transpileModule(content,{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext,verbatimModuleSyntax:true}}).outputText}:undefined},{filename});
 const result=compile(processed.code,{filename,generate:'dom'});assert.ok(result.js.code.length);
 for(const w of result.warnings){assert.equal(filename.endsWith('/CallOverlay.svelte')&&w.code==='a11y-media-has-caption',true,w.message);warnings.push({filename,code:w.code});}
}
const core=new URL('../deploy/lab/voice-call/call-loop.ts',import.meta.url).pathname;
const program=ts.createProgram([core],{strict:true,noEmit:true,target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext,lib:['lib.es2022.d.ts','lib.dom.d.ts'],types:[],skipLibCheck:true});
const diagnostics=ts.getPreEmitDiagnostics(program);
assert.equal(diagnostics.length,0,ts.formatDiagnosticsWithColorAndContext(diagnostics,{getCurrentDirectory:()=>process.cwd(),getCanonicalFileName:x=>x,getNewLine:()=> '\n'}));
console.log(JSON.stringify({svelte_components_compiled:files.length,strict_call_types:'PASS',existing_native_warnings:warnings}));
