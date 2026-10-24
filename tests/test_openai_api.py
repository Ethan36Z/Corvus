"""API-1 contracts. Synthetic credentials, fake inference, no service calls."""
import asyncio
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import threading
import unittest
from unittest.mock import patch

import httpx
from app.openai_api import create_app, strict_json, ChatRequest
from app.foreground_activity import ForegroundActivityTracker
from app.foreground_registry import ForegroundRegistry, RegistryState
from app.model_client import ModelClientError

ROOT=Path(__file__).resolve().parents[1]
KEY='SyntheticApiKeyForOfflineTests_'+'A'*32
OTHER='SyntheticApiKeyForOfflineTests_'+'B'*32
HEADERS={'Authorization':'Bearer '+KEY}
BODY={'model':'corvus','messages':[{'role':'user','content':'hello'}]}


def response(content=' hello ',reason='stop'):
    return {'id':'chatcmpl-synthetic','object':'chat.completion','created':1700000000,'model':'corvus',
            'choices':[{'index':0,'message':{'role':'assistant','content':content},'finish_reason':reason}],
            'usage':{'prompt_tokens':10,'completion_tokens':3,'total_tokens':13}}


class APIContracts(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.directory=Path(self.tmp.name)
        self.keys=self.directory/'keys.sha256';self.write_keys(KEY);self.calls=[]
        def generator(payload,timeout):
            self.calls.append((deepcopy(payload),timeout));return response()
        self.generator=generator
        self.app=self.make_app()

    def write_keys(self,*keys):
        p=self.directory/'new-keys';p.write_text(''.join(hashlib.sha256(x.encode()).hexdigest()+'\n' for x in keys));p.chmod(0o600);os.replace(p,self.keys)

    def make_app(self,**kw):
        return create_app(enabled=True,key_file=self.keys,generator=kw.pop('generator',self.generator),rate_limit=1000,**kw)

    async def request(self,path='/v1/chat/completions',body=None,headers=None,method='POST',app=None,**kwargs):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app or self.app),base_url='http://synthetic') as client:
            return await client.request(method,path,headers=HEADERS if headers is None else headers,
                                        json=BODY if body is None and method=='POST' and 'content' not in kwargs else body,**kwargs)

    async def test_standard_envelope_exact_content_usage_and_no_cookies(self):
        r=await self.request();self.assertEqual(r.status_code,200);self.assertEqual(r.json(),response())
        self.assertEqual(len(self.calls),1);self.assertEqual(self.calls[0][0]['messages'],BODY['messages'])
        self.assertEqual(r.headers['cache-control'],'no-store');self.assertEqual(r.headers['x-content-type-options'],'nosniff')

    async def test_discovery_schema_auth_and_route_isolation(self):
        r=await self.request('/v1/models',method='GET');self.assertEqual(r.json()['data'][0]['id'],'corvus');self.assertEqual(self.calls,[])
        schema=await self.request('/openapi.json',method='GET');self.assertEqual(schema.status_code,200);s=schema.json()
        self.assertEqual(set(s['paths']),{'/v1/models','/v1/chat/completions'})
        self.assertIn('HTTPBearer',s['components']['securitySchemes'])
        self.assertIn('ChatRequest',s['components']['schemas']);self.assertIn('developer',s['components']['schemas']['Message']['properties']['role']['enum'])
        self.assertIn('401',s['paths']['/v1/chat/completions']['post']['responses'])
        def refs(value):
            if isinstance(value,dict):
                if '$ref' in value:
                    p=value['$ref'];self.assertTrue(p.startswith('#/components/schemas/'));self.assertIn(p.split('/')[-1],s['components']['schemas'])
                for v in value.values():refs(v)
            elif isinstance(value,list):
                for v in value:refs(v)
        refs(s)
        for path in ['/docs','/redoc','/api/chat','/api/sessions','/api/evidence','/slots','/health']:
            self.assertEqual((await self.request(path,method='GET')).status_code,404)
        self.assertEqual((await self.request('/openapi.json',method='GET',headers={})).status_code,401)

    async def test_auth_missing_wrong_malformed_duplicate_and_query(self):
        for headers in [{},{'Authorization':'Bearer '+OTHER},{'Authorization':'Basic private'},
                        {'Authorization':'Bearer short'},[('Authorization','Bearer '+KEY),('authorization','Bearer '+KEY)]]:
            with self.subTest(headers_type=type(headers)):
                r=await self.request(headers=headers);self.assertEqual(r.status_code,401);self.assertEqual(r.headers['www-authenticate'],'Bearer')
        self.assertEqual((await self.request('/v1/models?api_key=synthetic',method='GET')).status_code,400)
        self.assertEqual(self.calls,[])
        self.assertEqual((await self.request('/v1/models',method='GET',headers={'Authorization':'bearer '+KEY})).status_code,200)

    async def test_rotation_and_independent_revocation_without_restart(self):
        self.write_keys(KEY,OTHER)
        for key in [KEY,OTHER]:self.assertEqual((await self.request('/v1/models',method='GET',headers={'Authorization':'Bearer '+key})).status_code,200)
        self.write_keys(OTHER)
        self.assertEqual((await self.request('/v1/models',method='GET')).status_code,401)
        self.assertEqual((await self.request('/v1/models',method='GET',headers={'Authorization':'Bearer '+OTHER})).status_code,200)
        self.write_keys(KEY)
        self.assertEqual((await self.request('/v1/models',method='GET',headers={'Authorization':'Bearer '+OTHER})).status_code,401)

    async def test_invalid_key_files_fail_closed_without_cached_keys(self):
        self.assertEqual((await self.request('/v1/models',method='GET')).status_code,200)
        for data in ['', 'not a digest\n','a'*64+'\n'+'a'*64+'\n','a'*2100]:
            self.keys.write_text(data);self.assertEqual((await self.request('/v1/models',method='GET')).status_code,503)
        self.write_keys(KEY);self.keys.chmod(0o644)
        self.assertEqual((await self.request('/v1/models',method='GET')).status_code,503)
        self.write_keys(KEY);self.directory.chmod(0o755)
        self.assertEqual((await self.request('/v1/models',method='GET')).status_code,503);self.directory.chmod(0o700)
        self.keys.unlink();self.assertEqual((await self.request('/v1/models',method='GET')).status_code,503)
        self.keys.symlink_to(self.directory/'target');self.assertEqual((await self.request('/v1/models',method='GET')).status_code,503)

    async def test_key_hardlinks_fifos_and_symlink_parent_rejected(self):
        os.link(self.keys,self.directory/'hardlink');self.assertEqual((await self.request('/v1/models',method='GET')).status_code,503)
        self.keys.unlink();os.mkfifo(self.keys,0o600)
        self.assertEqual((await self.request('/v1/models',method='GET')).status_code,503)
        self.keys.unlink();self.write_keys(KEY)
        with TemporaryDirectory() as outer:
            alias=Path(outer)/'alias';alias.symlink_to(self.directory,target_is_directory=True)
            self.assertEqual((await self.request('/v1/models',method='GET',app=create_app(enabled=True,key_file=alias/'keys.sha256'))).status_code,503)

    async def test_exported_defaults_disabled_and_bad_limits_rejected(self):
        with patch.dict(os.environ,{},clear=True):app=create_app()
        self.assertEqual((await self.request(app=app)).status_code,503)
        for kw in [{'request_seconds':0},{'body_seconds':-1},{'rate_limit':True}]:
            with self.assertRaises(ValueError):create_app(**kw)

    async def test_developer_prefix_and_supported_parameters(self):
        body=dict(BODY,messages=[{'role':'system','content':' first '},{'role':'developer','content':'second'},
            {'role':'user','content':'one'},{'role':'assistant','content':'two'},{'role':'user','content':'three'}],
            max_completion_tokens=42,temperature=0,top_p=0.5,stop=['END'],n=1,stream=False)
        self.assertEqual((await self.request(body=body)).status_code,200)
        p=self.calls[0][0];self.assertEqual(p['messages'][0],{'role':'system','content':' first \n\nsecond'})
        self.assertEqual(p['max_tokens'],42);self.assertEqual(p['temperature'],0);self.assertEqual(p['stop'],['END'])

    async def test_unsupported_invalid_parameters_and_messages(self):
        changes=[{'stream':True},{'stream':0},{'tools':[]},{'user':'not supported'},{'n':True},{'n':2},
                 {'chat_template_kwargs':{}},{'cache_prompt':True},{'max_tokens':1025},{'max_tokens':True},
                 {'max_tokens':10,'max_completion_tokens':10},{'temperature':float('nan')},{'top_p':0},
                 {'stop':[]},{'stop':['']},{'response_format':{'type':'json_schema'}},
                 {'messages':[]},{'messages':[{'role':'tool','content':'x'}]},
                 {'messages':[{'role':'user','content':[{'type':'image_url','image_url':{'url':'http://private'}}]}]},
                 {'messages':[{'role':'user','content':'x'},{'role':'developer','content':'x'}]},
                 {'messages':[{'role':'assistant','content':'x'}]}, {'messages':[{'role':'user','content':'\ud800'}]},
                 {'messages':[{'role':'user','content':'x','tool_calls':[]}]},
                 {'messages':[{'role':'user','content':'x'}]*65}]
        for change in changes:
            content=json.dumps(dict(BODY,**change)).encode()
            with self.subTest(fields=list(change)):
                r=await self.request(content=content,headers=dict(HEADERS,**{'Content-Type':'application/json'}));self.assertEqual(r.status_code,400,r.text)
        self.assertEqual(self.calls,[])
        self.assertEqual((await self.request(body=dict(BODY,model='unknown'))).status_code,404)

    async def test_malformed_duplicate_deep_and_oversized_json(self):
        for raw in [b'[]',b'null',b'{',b'{"model":"a","model":"b"}',b'['*2000+b']'*2000,b'\xff']:
            self.assertEqual((await self.request(content=raw,headers=dict(HEADERS,**{'Content-Type':'application/json'}))).status_code,400)
        self.assertEqual((await self.request(content=b'x'*131073,headers=dict(HEADERS,**{'Content-Type':'application/json'}))).status_code,413)
        async def chunks():
            for _ in range(33):yield b'x'*4096
        self.assertEqual((await self.request(content=chunks(),headers=dict(HEADERS,**{'Content-Type':'application/json','Content-Length':'1'}))).status_code,413)
        self.assertEqual((await self.request(content=b'{}',headers=HEADERS)).status_code,415)
        for value in ['9'*5000, '-1', 'not-a-number']:
            r=await self.request(content=b'{}',headers=dict(HEADERS,**{'Content-Type':'application/json','Content-Length':value}))
            self.assertEqual(r.status_code,413 if value[0]=='9' else 400)
        self.assertEqual(self.calls,[])

    async def test_json_object_verification_and_truncation(self):
        for content,reason,status in [(' {"ok":true,"n":2} ','stop',200),('[]','stop',502),('plain','stop',502),
                                      ('{"x":NaN}','stop',502),('{"x":1e999}','stop',502),('{"x":1,"x":2}','stop',502),
                                      ('{"x":','length',502),('{"x":1}','length',200)]:
            app=self.make_app(generator=lambda *_a,**_kw:response(content,reason))
            r=await self.request(body=dict(BODY,response_format={'type':'json_object'}),app=app)
            self.assertEqual(r.status_code,status,r.text)
            if status==200:self.assertEqual(r.json()['choices'][0]['message']['content'],content)
        r=await self.request(app=self.make_app(generator=lambda *_a,**_kw:response('', 'length')))
        self.assertEqual(r.status_code,200);self.assertEqual(r.json()['choices'][0]['finish_reason'],'length')

    async def test_invalid_upstream_and_safe_failures(self):
        bad=[]
        for edit in [('model','private/path'),('id','private-id'),('usage',{'prompt_tokens':1,'completion_tokens':1,'total_tokens':9}),('choices',[])]:
            raw=response();raw[edit[0]]=edit[1];bad.append(raw)
        raw=response();raw['choices'][0]['message']['tool_calls']=[{}];bad.append(raw)
        raw=response();raw['usage']['completion_tokens']=True;bad.append(raw)
        for raw in bad:
            r=await self.request(app=self.make_app(generator=lambda *_a,**_kw:raw));self.assertEqual(r.status_code,502)
        for error,status in [(ModelClientError('MODEL_TIMEOUT','PRIVATE_SECRET'),504),
                             (ModelClientError('MODEL_UNAVAILABLE','PRIVATE_SECRET'),503),
                             (ModelClientError('MODEL_HTTP_ERROR','PRIVATE_SECRET'),502),
                             (ModelClientError('INPUT_TOO_LONG','PRIVATE_SECRET'),400),(RuntimeError('PRIVATE_SECRET'),500)]:
            def generator(*_a,**_kw):raise error
            r=await self.request(app=self.make_app(generator=generator));self.assertEqual(r.status_code,status)
            self.assertNotIn('PRIVATE_SECRET',r.text);self.assertEqual(set(r.json()),{'error'})
        r=await self.request(body=dict(BODY,temperature='PRIVATE_SECRET'));self.assertNotIn('PRIVATE_SECRET',r.text)

    async def test_rate_window_is_bounded_and_explicit(self):
        clock=[100]
        app=create_app(enabled=True,key_file=self.keys,generator=self.generator,rate_limit=1,clock=lambda:clock[0])
        self.assertEqual((await self.request(app=app)).status_code,200)
        r=await self.request(app=app);self.assertEqual(r.status_code,429);self.assertEqual(r.headers['retry-after'],'60')
        clock[0]+=60;self.assertEqual((await self.request(app=app)).status_code,200)

    async def test_timeout_and_cancelled_request_keep_real_worker_ownership(self):
        for cancel in [False,True]:
            started,release,finished=threading.Event(),threading.Event(),threading.Event()
            def generator(*_a,**_kw):
                started.set();release.wait(3);finished.set();return response()
            tracker=ForegroundActivityTracker();app=self.make_app(generator=generator,tracker=tracker,request_seconds=0.03)
            async with app.router.lifespan_context(app):
                task=asyncio.create_task(self.request(app=app))
                try:
                    await asyncio.to_thread(started.wait,1)
                    if cancel:
                        task.cancel()
                        with self.assertRaises(asyncio.CancelledError):await task
                    else:self.assertEqual((await task).status_code,504)
                    self.assertEqual((await self.request(app=app)).status_code,429)
                    self.assertEqual(tracker.snapshot().active_foreground_count,1)
                finally:release.set()
                await asyncio.to_thread(finished.wait,1);await asyncio.sleep(0.03)
                self.assertEqual(tracker.snapshot().active_foreground_count,0)
                self.assertEqual((await self.request(app=app)).status_code,200)

    async def test_busy_registry_and_optional_api_publisher_visible_to_old_reader(self):
        with TemporaryDirectory() as path:
            registry=ForegroundRegistry(path,expected_publishers=('lab','production'))
            trackers=[ForegroundActivityTracker(registry_path=path,logical_publisher=p,expected_publishers=('lab','production')) for p in ['lab','production','api']]
            for tracker in trackers:tracker.start();self.addCleanup(tracker.close)
            self.assertEqual(registry.read().state,RegistryState.IDLE)
            def generator(*_a,**_kw):
                self.assertEqual(registry.read().state,RegistryState.BUSY);return response()
            self.assertEqual((await self.request(app=self.make_app(generator=generator,tracker=trackers[-1]))).status_code,200)
            self.assertEqual(registry.read().state,RegistryState.IDLE)
            trackers[-1].close();self.assertEqual(registry.read().state,RegistryState.IDLE)

    async def test_raw_asgi_disconnect_slow_body_and_auth_before_read(self):
        async def run(app, receive, headers):
            sent=[]
            scope={'type':'http','asgi':{'version':'3.0'},'http_version':'1.1','method':'POST','scheme':'http',
                   'path':'/v1/chat/completions','raw_path':b'/v1/chat/completions','query_string':b'',
                   'headers':headers,'server':('synthetic',80),'client':('127.0.0.1',1)}
            async def send(message):sent.append(message)
            await app(scope,receive,send)
            return next(x['status'] for x in sent if x['type']=='http.response.start')
        h=[(b'authorization',('Bearer '+KEY).encode()),(b'content-type',b'application/json')]
        async def forbidden():self.fail('unauthorized body must not be read')
        self.assertEqual(await run(self.app,forbidden,[]),401)
        async def slow():await asyncio.sleep(1);return {'type':'http.request','body':b'{}'}
        self.assertEqual(await run(self.make_app(body_seconds=0.005),slow,h),408)
        async def disconnected():return {'type':'http.disconnect'}
        self.assertEqual(await run(self.app,disconnected,h),499)
        first=True;started=threading.Event();release=threading.Event()
        def generator(*_a,**_kw):started.set();release.wait(2);return response()
        async def after_body_disconnect():
            nonlocal first
            if first:first=False;return {'type':'http.request','body':json.dumps(BODY).encode(),'more_body':False}
            if started.is_set():
                return {'type':'http.disconnect'}
            await asyncio.sleep(0.01)
            return {'type':'http.request','body':b'', 'more_body':False}
        app=self.make_app(generator=generator)
        try:
            self.assertEqual(await run(app,after_body_disconnect,h),499)
            self.assertEqual((await self.request(app=app)).status_code,429)
        finally:release.set()
        await asyncio.sleep(0.03)


class MemoryIsolation(unittest.TestCase):
    def test_fresh_process_never_imports_or_touches_memory_on_success_failure_timeout(self):
        code=r'''
import sys,importlib.abc,tempfile,os,pathlib,hashlib,asyncio,socket,threading
class Block(importlib.abc.MetaPathFinder):
 def find_spec(self,name,*args):
  if name.split('.')[0] in ('memory','personality') or name.startswith(('app.conversation_runtime','app.hindsight','app.async_retain','app.runtime_lifecycle','app.working_context','app.arena')):raise AssertionError('forbidden module '+name)
sys.meta_path.insert(0,Block())
def audit(event,args):
 if event=='sqlite3.connect':raise AssertionError('database access')
 if event=='open' and isinstance(args[0],(str,bytes)):
  p=os.fsdecode(args[0])
  if '/srv/data/' in p or '/.config/corvus' in p:raise AssertionError('private data access')
 if event in ('socket.connect','socket.getaddrinfo'):raise AssertionError('live network')
sys.addaudithook(audit)
import httpx
from app.openai_api import create_app
from app.model_client import ModelClientError
key='SyntheticApiKeyForOfflineTests_'+'A'*32
async def main():
 with tempfile.TemporaryDirectory() as d:
  p=pathlib.Path(d)/'keys';p.write_text(hashlib.sha256(key.encode()).hexdigest());p.chmod(0o600)
  for scenario in ['success','failure','timeout']:
   event=threading.Event()
   def generator(*args,**kwargs):
    if scenario=='failure':raise ModelClientError('MODEL_HTTP_ERROR','synthetic')
    if scenario=='timeout':event.wait(1)
    return {'id':'chatcmpl-test','object':'chat.completion','created':1,'model':'corvus','choices':[{'index':0,'message':{'role':'assistant','content':'ok'},'finish_reason':'stop'}],'usage':{'prompt_tokens':1,'completion_tokens':1,'total_tokens':2}}
   app=create_app(enabled=True,key_file=p,generator=generator,request_seconds=0.01)
   async with app.router.lifespan_context(app):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://synthetic') as c:
     try:
      r=await c.post('/v1/chat/completions',headers={'Authorization':'Bearer '+key},json={'model':'corvus','messages':[{'role':'user','content':'synthetic'}]})
      assert r.status_code=={'success':200,'failure':502,'timeout':504}[scenario],r.text
     finally:event.set()
    await asyncio.sleep(0.02)
asyncio.run(main());print('NO_MEMORY_PASS')
'''
        p=subprocess.run([sys.executable,'-B','-c',code],cwd=ROOT,capture_output=True,text=True,timeout=15)
        self.assertEqual(p.returncode,0,p.stderr);self.assertIn('NO_MEMORY_PASS',p.stdout)


if __name__=='__main__':unittest.main()
