"""Synthetic, isolated Corvus attachment operation replay/concurrency contracts."""
import concurrent.futures
import importlib
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest

class Operation(unittest.TestCase):
    def test_idempotence_conflict_and_concurrency(self):
        with tempfile.TemporaryDirectory(prefix='corvus-vision-operation-') as root:
            os.environ['CORVUS_DATA_DIR']=root
            import memory.config, memory.store, memory.attachments
            for m in (memory.config,memory.store,memory.attachments):importlib.reload(m)
            memory.store.init_db();a=memory.attachments
            key='a'*64
            def write(data=b'\x89PNG\r\n\x1a\nsynthetic',operation=key):
                return a.store_attachment_bytes(data,original_filename='synthetic.png',media_type='image/png',operation_key=operation,max_bytes=1024)
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
                records=list(pool.map(lambda _:write(),range(8)))
            self.assertEqual(len({r['id'] for r in records}),1)
            self.assertEqual(a.get_attachment_operation(key)['id'],records[0]['id'])
            with self.assertRaises(ValueError):write(b'\x89PNG\r\n\x1a\nconflict')
            with self.assertRaises(ValueError):write(operation='invalid')
            self.assertNotEqual(write(operation='b'*64)['id'],records[0]['id'])
            with sqlite3.connect(memory.config.DB_PATH) as db:
                self.assertEqual(db.execute('SELECT COUNT(*) FROM attachments').fetchone()[0],2)
                self.assertEqual(db.execute('SELECT COUNT(*) FROM attachment_blobs').fetchone()[0],1)
            self.assertEqual(list((Path(root)/'attachments/tmp').iterdir()),[])

    def test_actual_api_operation_branch_and_disabled_default(self):
        import ast, asyncio, httpx
        from fastapi import FastAPI, HTTPException, Request, Query
        with tempfile.TemporaryDirectory(prefix='corvus-vision-api-') as root:
            os.environ['CORVUS_DATA_DIR']=root
            import memory.config, memory.store, memory.attachments
            for m in (memory.config,memory.store,memory.attachments):importlib.reload(m)
            memory.store.init_db()
            app=FastAPI()
            source=ast.parse((Path(__file__).resolve().parents[1]/'app/playground_api.py').read_text())
            nodes=[n for n in source.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name in {'post_attachment','attachment_operation_status'}]
            namespace={'app':app,'Request':Request,'Query':Query,'HTTPException':HTTPException,
                       'ATTACHMENT_MAX_BYTES':32*1024*1024,'ATTACHMENT_DEFAULT_RETENTION':'STANDARD',
                       'store_attachment_bytes':memory.attachments.store_attachment_bytes,
                       'get_attachment_operation':memory.attachments.get_attachment_operation}
            exec(compile(ast.Module(body=nodes,type_ignores=[]),'actual-api-branches','exec'),namespace)
            async def check():
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://offline') as client:
                    headers={'Content-Type':'image/png','X-Corvus-Image-Operation':'a'*64}
                    png=b'\x89PNG\r\n\x1a\nsynthetic'
                    os.environ.pop('CORVUS_SINGLE_STORE_VISION',None)
                    self.assertEqual((await client.post('/api/attachments?filename=image',headers=headers,content=png)).status_code,404)
                    os.environ['CORVUS_SINGLE_STORE_VISION']='offline-reviewed-v1'
                    first=await client.post('/api/attachments?filename=image',headers=headers,content=png)
                    self.assertEqual(first.status_code,201,first.text)
                    second=await client.post('/api/attachments?filename=image',headers=headers,content=png)
                    self.assertEqual(first.json()['attachment_id'],second.json()['attachment_id'])
                    self.assertEqual((await client.post('/api/attachments?filename=image',headers=headers,content=png+b'changed')).status_code,409)
                    self.assertEqual((await client.post('/api/attachments?filename=image',headers=headers,content=b'bad')).status_code,400)
                    self.assertEqual((await client.post('/api/attachments?filename=image',headers=headers,content=png+b'x'*(20*1024*1024+1-len(png)))).status_code,413)
                    boundary=png+b'x'*(20*1024*1024-len(png))
                    accepted=await client.post('/api/attachments?filename=image',headers={**headers,'X-Corvus-Image-Operation':'c'*64},content=boundary)
                    self.assertEqual(accepted.status_code,201)
                    self.assertEqual(accepted.json()['size_bytes'],20*1024*1024)
                    from app.vision_input import load_vision_attachment
                    self.assertEqual(len(load_vision_attachment(accepted.json()['attachment_id'])['data']),20*1024*1024)
                    status=await client.get('/api/attachments/operations/'+'a'*64)
                    self.assertEqual(status.json()['attachment_id'],first.json()['attachment_id'])
                    self.assertNotIn('storage_path',status.json())
            try:asyncio.run(check())
            finally:os.environ.pop('CORVUS_SINGLE_STORE_VISION',None)

if __name__=='__main__':unittest.main(verbosity=2)
