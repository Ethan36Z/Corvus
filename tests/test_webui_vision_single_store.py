"""Pinned WebUI SQLAlchemy + mocked local A3. Run in the retained WebUI image.

No real users, sockets, storage mounts, images, chat data or inference.
"""
import asyncio
from contextlib import contextmanager
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import types
import sys
import unittest
from uuid import uuid4

import httpx
from fastapi import FastAPI, HTTPException, Request
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

PATCHED = Path(os.environ['VISION_PATCHED']) / 'backend/open_webui'
UPSTREAM = Path(os.environ['VISION_UPSTREAM']) / 'backend/open_webui'

def module(name, **attrs):
    result = types.ModuleType(name)
    for key, value in attrs.items(): setattr(result, key, value)
    sys.modules[name] = result
    return result

for name in ['open_webui', 'open_webui.internal', 'open_webui.models', 'open_webui.routers', 'open_webui.utils']:
    module(name, __path__=[])
Base = declarative_base()
database_root = tempfile.TemporaryDirectory(prefix='corvus-vision-webui-db-')
engine = create_engine('sqlite:///' + str(Path(database_root.name) / 'synthetic.sqlite'), connect_args={'check_same_thread': False})
Session = sessionmaker(bind=engine)
@contextmanager
def get_db():
    with Session() as session:
        yield session
module('open_webui.internal.db', Base=Base, JSONField=None, get_db=get_db)
module('open_webui.env', SRC_LOG_LEVELS={'MODELS': 'WARNING'})
class Functions:
    @staticmethod
    def get_function_valves_by_id(_):
        return {'CORVUS_CHAT_URL': 'http://127.0.0.1:18096/api/chat', 'INSTANCE_ID': 'synthetic-instance'}
module('open_webui.models.functions', Functions=Functions)
async def user(request: Request):
    token = request.headers.get('authorization', '')
    if token not in {'Bearer alice', 'Bearer bob'}:
        raise HTTPException(401, 'Authentication required')
    return types.SimpleNamespace(id=token[7:])
module('open_webui.utils.auth', get_verified_user=user)
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result
load('open_webui.models.tags', UPSTREAM / 'models/tags.py')
files = load('open_webui.models.files', PATCHED / 'models/files.py')
chats = load('open_webui.models.chats', PATCHED / 'models/chats.py')
v = load('open_webui.routers.corvus_vision', PATCHED / 'routers/corvus_vision.py')
os.environ['CORVUS_SINGLE_STORE_VISION'] = 'offline-reviewed-v1'
import struct, zlib
def png_chunk(kind, data):
    return struct.pack('>I',len(data)) + kind + data + struct.pack('>I',zlib.crc32(kind + data))
REAL_UPSTREAM = v.upstream
PNG = (b'\x89PNG\r\n\x1a\n' + png_chunk(b'IHDR',struct.pack('>IIBBBBB',1,1,8,2,0,0,0))
       + png_chunk(b'IDAT',zlib.compress(b'\x00\xff\x00\x00')) + png_chunk(b'IEND',b''))

class Contracts(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
        self.mid, self.aid = str(uuid4()), str(uuid4())
        self.message = {'id': self.mid, 'role': 'user', 'content': 'Describe synthetic image', 'models': ['corvus_pipe'], 'files': [], 'corvus_image_pending': True, 'childrenIds': [self.aid]}
        self.assistant = {'id': self.aid, 'role': 'assistant', 'content': '', 'model': 'corvus_pipe', 'parentId': self.mid, 'childrenIds': []}
        self.chat = chats.Chats.insert_new_chat('alice', chats.ChatForm(chat={'history': {'messages': {self.mid:self.message,self.aid:self.assistant},'currentId': self.aid}, 'messages': [self.message,self.assistant]}))
        self.cid = self.chat.id
        self.calls = []
        self.blob = None
        async def upstream(method, path, **kwargs):
            import hashlib
            self.calls.append((method,path))
            if method == 'POST':
                self.blob = kwargs['body']
                self.mime = kwargs['headers']['content-type']
                return json.dumps({'attachment_id': 'a'*32, 'media_type': self.mime, 'size_bytes': len(self.blob), 'blob_status':'PRESENT', 'sha256': hashlib.sha256(self.blob).hexdigest()}).encode(), 'application/json'
            if path.endswith('/content'): return self.blob, self.mime
            return json.dumps({'attachment_id':'a'*32, 'media_type':'image/png', 'size_bytes':len(PNG), 'blob_status':'PRESENT', 'sha256':hashlib.sha256(PNG).hexdigest()}).encode(), 'application/json'
        self.upstream = upstream
        v.upstream = upstream
        app = FastAPI()
        app.include_router(v.router, prefix='/api/v1/files')
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test')
    async def asyncTearDown(self): await self.client.aclose()
    async def upload(self, *, who='alice', content=PNG, arena='false', mime='image/png'):
        return await self.client.post(f'/api/v1/files/corvus-image/{self.cid}/{self.mid}', headers={'Authorization':'Bearer '+who,'Content-Type':mime,'X-Corvus-Arena':arena}, content=content)
    def save_ref(self, reference):
        state = json.loads(json.dumps(self.chat.chat))
        state['history']['messages'][self.mid]['files'] = [reference]
        state['history']['messages'][self.mid].pop('corvus_image_pending',None)
        state['messages'] = list(state['history']['messages'].values())
        self.assertIsNotNone(chats.Chats.update_chat_by_id(self.cid,state))
        self.chat = chats.Chats.get_chat_by_id(self.cid)
        return state
    async def ready(self):
        response = await self.upload()
        self.assertEqual(response.status_code,200,response.text)
        reference=response.json();self.save_ref(reference)
        return reference
    async def test_reference_only_upload_display_reload_and_claim(self):
        r = await self.ready()
        result = await v.content(r['corvus_ref'],types.SimpleNamespace(id='alice'))
        self.assertEqual(result.body,PNG)
        self.assertIn('no-store',result.headers['cache-control'])
        with get_db() as db:
            file=db.get(files.File,r['corvus_ref'])
            self.assertIsNone(file.path);self.assertEqual(file.data,{})
            self.assertNotIn('base64',json.dumps(file.meta))
            self.assertNotIn('data:image',json.dumps(db.get(chats.Chat,self.cid).chat))
        self.assertEqual(v.current_image('alice',self.cid,self.aid,'Describe synthetic image',False)[1],'a'*32)
        with self.assertRaises(ValueError): v.current_image('alice',self.cid,self.aid,'Describe synthetic image',False)
        v.finish(r['corvus_ref'],{'user_message_id':1,'assistant_message_id':2})
        with get_db() as db:self.assertEqual(db.get(files.File,r['corvus_ref']).meta['state'],'COMMITTED')
    async def test_authentication_cross_user_and_forgery(self):
        self.assertEqual((await self.client.post(f'/api/v1/files/corvus-image/{self.cid}/{self.mid}',content=PNG)).status_code,401)
        self.assertEqual((await self.upload(who='bob')).status_code,404)
        r=await self.ready()
        with self.assertRaises(HTTPException): await v.content(r['corvus_ref'],types.SimpleNamespace(id='bob'))
        state=json.loads(json.dumps(self.chat.chat));state['history']['messages'][self.mid]['files'][0]['url']='/api/attachments/unsafe/content'
        self.assertIsNone(chats.Chats.update_chat_by_id(self.cid,state))
        with self.assertRaises(ValueError): chats.Chats.insert_new_chat('bob',chats.ChatForm(chat=self.chat.chat))
        with self.assertRaises(ValueError): chats.Chats.import_chat('alice',chats.ChatImportForm(chat=self.chat.chat))
        with self.assertRaises(ValueError): chats.Chats.insert_shared_chat_by_chat_id(self.cid)
    async def test_twenty_mib_upload_and_display_preserves_bytes(self):
        import hashlib
        self.assertEqual(v.LIMIT, 20*1024*1024)
        raw=PNG+b'x'*(v.LIMIT-len(PNG))
        async def upstream(method,path,*,body=None,headers=None,limit=v.LIMIT):
            if path.endswith('/content'): return raw, 'image/png'
            self.assertEqual(body,raw)
            return json.dumps({'attachment_id':'a'*32,'media_type':'image/png','size_bytes':len(raw),'blob_status':'PRESENT','sha256':hashlib.sha256(raw).hexdigest()}).encode(),'application/json'
        v.upstream=upstream
        response=await self.upload(content=raw)
        self.assertEqual(response.status_code,200)
        self.save_ref(response.json())
        displayed=await v.content(response.json()['corvus_ref'],types.SimpleNamespace(id='alice'))
        self.assertEqual(displayed.body,raw)

    async def test_limits_format_arena_before_writes(self):
        for kwargs,code in [({'arena':'true'},400),({'content':b'bad'},400),({'content':b''},400),({'mime':'image/gif'},400),({'content':PNG+b'x'*v.LIMIT},413)]:
            self.assertEqual((await self.upload(**kwargs)).status_code,code)
        with get_db() as db:self.assertEqual(db.query(files.File).count(),0)
        self.assertEqual(self.calls,[])
    async def test_pending_lost_response_conflict_and_reconcile(self):
        async def lost(*args,**kwargs): raise HTTPException(503,'Uncertain')
        v.upstream=lost
        self.assertEqual((await self.upload()).status_code,503)
        v.upstream=self.upstream
        self.assertEqual((await self.upload(content=PNG+b'conflict')).status_code,409)
        self.blob=PNG
        result=await self.client.get(f'/api/v1/files/corvus-image/{self.cid}/{self.mid}',headers={'Authorization':'Bearer alice'})
        self.assertEqual(result.status_code,200)
        self.assertEqual(result.json()['state'],'READY')
        with get_db() as db:self.assertEqual(db.query(files.File).count(),1)
    async def test_revocation_and_chat_deletion_hold_blobs(self):
        r=await self.ready()
        v.revoke(r['corvus_ref'],types.SimpleNamespace(id='alice'))
        with self.assertRaises(HTTPException): await v.content(r['corvus_ref'],types.SimpleNamespace(id='alice'))
        self.assertEqual(self.calls,[('POST','/api/attachments?filename=image')])
        chats.Chats.delete_chat_by_id_and_user_id(self.cid,'alice')
        with get_db() as db:self.assertEqual(db.query(files.File).count(),1)
    async def test_real_pipe_image_dispatch_failure_and_historical_exclusion(self):
        from unittest.mock import patch
        pipe_module = load('vision_pipe', Path('/pipe.py'))
        pipe = pipe_module.Pipe()
        pipe.valves.INSTANCE_ID = 'synthetic-instance'
        pipe.valves.CORVUS_CHAT_URL = 'http://127.0.0.1:18096/api/chat'
        pipe.valves.WEB_MODE = 'off'
        reference = await self.ready()
        calls = []
        result = {'session_id': pipe_module.corvus_session_id('synthetic-instance','alice',self.cid),
                  'reply':'Synthetic reply','user_message_id':1,'assistant_message_id':2,
                  'status':{'overall':'OK','model':'OK','persistence':'NORMAL'}}
        class Client:
            def __init__(self,**kwargs): pass
            async def __aenter__(self): return self
            async def __aexit__(self,*args): pass
            async def post(self,url,json):
                calls.append((url,json));return httpx.Response(200,json=result)
        with patch.object(pipe_module.httpx,'AsyncClient',Client):
            value=await pipe.pipe({'messages':[{'role':'user','content':self.message['content']}]},
                __user__={'id':'alice'},__chat_id__=self.cid,__metadata__={'message_id':self.aid})
            self.assertEqual(value,'Synthetic reply')
            self.assertEqual(calls[0][1]['attachment_id'],'a'*32)
            with self.assertRaises(ValueError):
                await pipe.pipe({'messages':[{'role':'user','content':self.message['content']}]},
                    __user__={'id':'alice'},__chat_id__=self.cid,__metadata__={'message_id':self.aid})
        self.assertEqual(len(calls),1)
        # An old image remains visible, but the next current text turn does not
        # acquire an attachment or resubmit that image to A3.
        mid2, aid2 = str(uuid4()),str(uuid4())
        state=json.loads(json.dumps(self.chat.chat))
        state['history']['messages'][mid2]={'id':mid2,'role':'user','content':'Next text','childrenIds':[aid2]}
        state['history']['messages'][aid2]={'id':aid2,'role':'assistant','parentId':mid2,'content':''}
        state['messages']=list(state['history']['messages'].values())
        self.assertIsNotNone(chats.Chats.update_chat_by_id(self.cid,state))
        self.assertIsNone(v.current_image('alice',self.cid,aid2,'Next text',False))

    async def test_generic_mutations_rejected(self):
        r=await self.ready();rid=r['corvus_ref']
        self.assertIsNone(files.Files.update_file_metadata_by_id(rid,{'state':'READY'}))
        self.assertIsNone(files.Files.update_file_data_by_id(rid,{'content':'not allowed'}))
        self.assertFalse(files.Files.delete_file_by_id(rid))
        self.assertFalse(files.Files.delete_all_files())
    async def test_raw_chat_and_import_rejection_text_unchanged(self):
        for value in [{'prompt':'data:image/png;base64,AAAA'},{'images':['raw']},{'history':{'messages':{self.mid:{**self.message,'files':[{'type':'image','url':'blob:raw'}]}}}}]:
            self.assertIsNone(chats.Chats.update_chat_by_id(self.cid,value))
            with self.assertRaises(ValueError):chats.Chats.insert_new_chat('alice',chats.ChatForm(chat=value))
        self.assertIsNotNone(chats.Chats.insert_new_chat('alice',chats.ChatForm(chat={'history':{'messages':{}},'title':'Text'})))
    async def test_concurrent_claim_and_restore_identity_fail_closed(self):
        reference=await self.ready()
        def attempt():
            try:
                v.claim('alice',self.cid,self.aid,reference)
                return True
            except (ValueError,HTTPException):return False
        outcomes=await asyncio.gather(asyncio.to_thread(attempt),asyncio.to_thread(attempt))
        self.assertEqual(outcomes.count(True),1)
        from unittest.mock import patch
        with patch.object(v,'namespace',return_value='different-restored-instance'):
            with self.assertRaises(HTTPException):await v.content(reference['corvus_ref'],types.SimpleNamespace(id='alice'))
        # Deleting the user-message reference immediately denies future reads.
        state=json.loads(json.dumps(self.chat.chat));state['history']['messages'].pop(self.mid);state['messages']=list(state['history']['messages'].values())
        self.assertIsNotNone(chats.Chats.update_chat_by_id(self.cid,state))
        with self.assertRaises(HTTPException):await v.content(reference['corvus_ref'],types.SimpleNamespace(id='alice'))

    async def test_enabled_vision_preserves_text_arena_route(self):
        from unittest.mock import patch
        pipe_module=load('vision_pipe_arena',Path('/pipe.py'))
        pipe=pipe_module.Pipe();pipe.valves.INSTANCE_ID='synthetic-instance'
        pipe.valves.CORVUS_CHAT_URL='http://127.0.0.1:18096/api/chat';pipe.valves.ARENA_ENABLED=True
        state=json.loads(json.dumps(self.chat.chat));state['history']['messages'][self.mid].pop('corvus_image_pending')
        state['messages']=list(state['history']['messages'].values())
        self.assertIsNotNone(chats.Chats.update_chat_by_id(self.cid,state))
        result={'main':{'session_id':pipe_module.corvus_session_id('synthetic-instance','alice',self.cid),
                       'reply':'Text Arena reply','user_message_id':1,'assistant_message_id':2,
                       'status':{'overall':'OK','model':'OK','persistence':'NORMAL'}}}
        calls=[]
        class Client:
            def __init__(self,**kwargs):pass
            async def __aenter__(self):return self
            async def __aexit__(self,*args):pass
            async def post(self,url,json):calls.append((url,json));return httpx.Response(200,json=result)
        with patch.object(pipe_module.httpx,'AsyncClient',Client):
            reply=await pipe.pipe({'messages':[{'role':'user','content':self.message['content']}]},
                __user__={'id':'alice'},__chat_id__=self.cid,__metadata__={'message_id':self.aid,'corvus_arena':True})
        self.assertEqual(reply,'Text Arena reply');self.assertEqual(calls[0][0],'http://127.0.0.1:18096/api/arena/chat')
        self.assertNotIn('attachment_id',calls[0][1])

    async def test_wrong_model_pending_image_rejected_before_write(self):
        for field in ('models','child_model'):
            state=json.loads(json.dumps(self.chat.chat))
            if field=='models':state['history']['messages'][self.mid]['models']=['another-model']
            else:state['history']['messages'][self.aid]['model']='another-model'
            state['messages']=list(state['history']['messages'].values())
            self.assertIsNone(chats.Chats.update_chat_by_id(self.cid,state))
            with self.assertRaises(ValueError):chats.Chats.insert_new_chat('alice',chats.ChatForm(chat=state))
        self.assertEqual(self.calls,[])
        with get_db() as db:self.assertEqual(db.query(files.File).count(),0)

    async def test_native_admin_message_mutations_do_not_bypass_image_owner(self):
        admin=types.SimpleNamespace(id='bob',role='admin')
        with self.assertRaises(HTTPException):v.mutation_actor(self.chat,admin,{'content':'change'})
        await self.ready()
        with self.assertRaises(HTTPException):v.mutation_actor(self.chat,admin,{'type':'chat:message','data':{}})
        v.mutation_actor(self.chat,types.SimpleNamespace(id='alice',role='user'),{'content':'owned'})
        text=types.SimpleNamespace(user_id='alice',chat={'history':{'messages':{}}})
        v.mutation_actor(text,admin,{'content':'Existing admin text behavior'})
        with self.assertRaises(ValueError):v.mutation_actor(text,admin,{'content':'data:image/png;base64,AAAA'})
        import ast
        source=(PATCHED/'routers/chats.py').read_text()
        self.assertEqual(source.count('mutation_actor(chat, user, form_data.model_dump())'),2)
        ast.parse(source)

    async def test_generic_multipart_blocked_before_parser_or_storage(self):
        import ast
        from fastapi import APIRouter, UploadFile, File as FormFile
        from fastapi.routing import APIRoute
        tree=ast.parse((PATCHED/'routers/files.py').read_text())
        definition=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='ImageOnlyRoute')
        scope={'APIRoute':APIRoute,'os':os,'HTTPException':HTTPException}
        exec(compile(ast.Module(body=[definition],type_ignores=[]),'actual-native-route-wrapper','exec'),scope)
        app=FastAPI();router=APIRouter(route_class=scope['ImageOnlyRoute'])
        @router.post('/api/v1/files/')
        async def forbidden(file:UploadFile=FormFile(...)):
            raise AssertionError('Generic uploader executed')
        app.include_router(router)
        reads=[]
        async def body():
            reads.append(True);yield b'not an actual private multipart'
        os.environ.pop('CORVUS_SINGLE_STORE_VISION',None)
        try:
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
                result=await client.post('/api/v1/files/',headers={'Content-Type':'multipart/form-data; boundary=test'},content=body())
        finally:os.environ['CORVUS_SINGLE_STORE_VISION']='offline-reviewed-v1'
        self.assertEqual(result.status_code,403);self.assertEqual(reads,[])
    async def test_jpeg_uses_same_adapter_and_corvus_only_store(self):
        import io
        from PIL import Image
        output=io.BytesIO();Image.new('RGB',(1,1),(255,0,0)).save(output,format='JPEG')
        image=output.getvalue();result=await self.upload(content=image,mime='image/jpeg')
        self.assertEqual(result.status_code,200,result.text)
        self.save_ref(result.json())
        response=await v.content(result.json()['corvus_ref'],types.SimpleNamespace(id='alice'))
        self.assertEqual(response.body,image)
    async def test_cancelled_upload_stays_pending_without_dispatch(self):
        async def cancelled(*args,**kwargs):raise asyncio.CancelledError()
        v.upstream=cancelled
        with self.assertRaises(asyncio.CancelledError): await self.upload()
        with get_db() as db:self.assertEqual(db.query(files.File).one().meta['state'],'PENDING')
        with self.assertRaises(ValueError):v.current_image('alice',self.cid,self.aid,self.message['content'],False)
    async def test_arena_saved_placeholder_rejected_before_insert(self):
        state=json.loads(json.dumps(self.chat.chat))
        state['history']['messages'][self.aid]['corvus_arena_requested']=True
        state['messages']=list(state['history']['messages'].values())
        with self.assertRaises(ValueError):chats.Chats.insert_new_chat('alice',chats.ChatForm(chat=state))
        self.assertIsNone(chats.Chats.update_chat_by_id(self.cid,state))
        self.assertEqual(self.calls,[])
    async def test_fixed_upstream_redirect_size_and_no_retry(self):
        from unittest.mock import patch
        real_client=httpx.AsyncClient
        for response in [httpx.Response(302,headers={'location':'http://forbidden.invalid'}),httpx.Response(200,content=b'x'*4097)]:
            calls=[]
            def handler(request):calls.append(request);return response
            def client(**kwargs):
                self.assertFalse(kwargs['trust_env']);self.assertFalse(kwargs['follow_redirects'])
                kwargs['transport']=httpx.MockTransport(handler)
                return real_client(**kwargs)
            with patch.object(httpx,'AsyncClient',client):
                with self.assertRaises(HTTPException):await REAL_UPSTREAM('GET','/api/attachments/operations/'+'a'*64,limit=4096)
            self.assertEqual(len(calls),1)
            self.assertEqual(calls[0].url.host,'127.0.0.1')

    async def test_uncertain_and_removed_reference_no_redispatch(self):
        r=await self.ready()
        v.current_image('alice',self.cid,self.aid,'Describe synthetic image',False)
        v.finish(r['corvus_ref'])
        with get_db() as db:self.assertEqual(db.get(files.File,r['corvus_ref']).meta['state'],'UNCERTAIN')
        with self.assertRaises(ValueError):v.current_image('alice',self.cid,self.aid,'Describe synthetic image',False)
        state=json.loads(json.dumps(self.chat.chat));state['history']['messages'][self.mid]['files']=[];state['messages']=list(state['history']['messages'].values())
        self.assertIsNotNone(chats.Chats.update_chat_by_id(self.cid,state))
        with self.assertRaises(ValueError):v.current_image('alice',self.cid,self.aid,'Describe synthetic image',False)

if __name__=='__main__': unittest.main(verbosity=2)
