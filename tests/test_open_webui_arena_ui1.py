"""UI-1 Pipe/overlay verification. No live API, database, recall or model I/O."""
import ast
import asyncio
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import socket
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

import httpx

REPO = Path(__file__).resolve().parents[1]
DEPLOY = REPO / 'deploy/open-webui'
spec = importlib.util.spec_from_file_location('arena_ui1_pipe', DEPLOY / 'corvus_pipe.py')
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)

CHAT = '3c57a4d8-0201-4db0-8e6e-a8fc734ba6a0'
TRIAL = '25415702-8bac-4f1a-9dd8-5eba47de0ff4'
LAB = 'http://127.0.0.1:18096/api/chat'


class ArenaPipeTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.pipe = adapter.Pipe()
        self.pipe.valves = adapter.Pipe.Valves(INSTANCE_ID='test-lab', CORVUS_CHAT_URL=LAB, ARENA_ENABLED=True)
        self.requests = []
        self.events = []
        self.body = {'messages': [{'role': 'user', 'content': ' Question '}]}
        self.metadata = {'chat_id': CHAT, 'user_id': 'user', 'message_id': 'assistant', 'corvus_arena': True}
        self.main = {'reply': 'Canonical RAG reply',
                     'session_id': adapter.corvus_session_id('test-lab', 'user', CHAT),
                     'status': {'overall': 'OK', 'retrieval': 'OK', 'model': 'OK', 'persistence': 'NORMAL'},
                     'historical_recall_elapsed_ms': 10, 'generation_elapsed_ms': 20,
                     'retrieved_memories': [{'id': 1, 'content': 'Evidence', 'private_metadata': 'omit'}]}
        self.result = {'trial_id': TRIAL, 'fairness': 'BEST_EFFORT_PRE_TURN', 'main': self.main,
                       'shadow': {'status': 'OK', 'reply': 'Shadow reply', 'error': None,
                                  'recall': {'status': 'OK', 'elapsed_ms': 30, 'private_internals': 'omit'},
                                  'generation_elapsed_ms': 40, 'evidence': [{'source_id': 'fact', 'text': 'Derived', 'metadata': 'omit'}]},
                       'evaluation': {'status': 'STORED', 'votable': True}, 'personality_sha256': 'omit'}
        self.failure = None
        self.code = 200

        async def handler(request):
            self.requests.append(request)
            if self.failure:
                raise self.failure
            data = self.result if request.url.path == '/api/arena/chat' else self.main
            return httpx.Response(self.code, json=data)

        self.transport = patch.object(adapter.httpx, 'AsyncHTTPTransport', lambda **kwargs: httpx.MockTransport(handler))
        self.transport.start(); self.addCleanup(self.transport.stop)
        blocked = patch.object(socket.socket, 'connect', side_effect=AssertionError('Live network forbidden'))
        blocked.start(); self.addCleanup(blocked.stop)

    async def emit(self, event):
        self.events.append(event)

    async def call(self, emitter=None, **extra):
        return await self.pipe.pipe(self.body, __user__={'id': 'user'}, __chat_id__=CHAT,
                                    __metadata__=self.metadata, __event_emitter__=emitter or self.emit, **extra)

    async def test_off_unchanged_even_when_admin_enables_arena(self):
        self.metadata.pop('corvus_arena')
        with patch.object(adapter, 'arena_ui_payload', side_effect=AssertionError('OFF must not assemble event')):
            self.assertEqual(await self.call(), self.main['reply'])
        self.assertEqual(str(self.requests[0].url), LAB)
        self.assertEqual(json.loads(self.requests[0].content), {
            'session_id': self.main['session_id'], 'message': ' Question ', 'web_mode': 'auto'})
        self.assertEqual(self.events, [])

    async def test_on_routes_once_returns_main_and_emits_minimal_event(self):
        self.assertEqual(await self.call(), self.main['reply'])
        self.assertEqual(len(self.requests), 1)
        self.assertEqual(str(self.requests[0].url), 'http://127.0.0.1:18096/api/arena/chat')
        self.assertEqual(json.loads(self.requests[0].content), {'session_id': self.main['session_id'], 'message': ' Question '})
        self.assertEqual(len(self.events), 1)
        self.assertEqual(self.events[0]['type'], 'corvus:arena:v1')
        data = self.events[0]['data']
        self.assertEqual(set(data), {'version', 'trial_id', 'fairness', 'main', 'shadow', 'evaluation'})
        self.assertEqual(data['main']['evidence'], [{'message_id': 1, 'text': 'Evidence'}])
        self.assertEqual(data['shadow']['evidence'], [{'source_id': 'hindsight:fact', 'text': 'Derived'}])
        encoded = json.dumps(data)
        for omitted in ['private_metadata', 'personality', 'session_id', 'Canonical RAG reply']:
            self.assertNotIn(omitted, encoded)

    async def test_admin_default_disabled_and_production_destination_fail_before_io(self):
        for enabled, url in [(False, LAB), (True, 'http://127.0.0.1:8096/api/chat')]:
            self.pipe.valves.ARENA_ENABLED = enabled
            self.pipe.valves.CORVUS_CHAT_URL = url
            with self.assertRaises(ValueError): await self.call()
        self.assertEqual(self.requests, [])
        self.assertFalse(adapter.Pipe.Valves().ARENA_ENABLED)

    async def test_only_strict_injected_boolean_can_opt_in(self):
        for flag in ['true', 1, None, {}]:
            self.metadata['corvus_arena'] = flag
            with self.assertRaises(ValueError): await self.call()
        self.assertEqual(self.requests, [])
        self.metadata.pop('corvus_arena')
        self.body['metadata'] = {'corvus_arena': True}
        await self.call()
        self.assertEqual(str(self.requests[0].url), LAB)

    async def test_emitter_failure_never_replaces_main_and_is_attempted_once(self):
        emitter = AsyncMock(side_effect=RuntimeError('socket failed'))
        self.assertEqual(await self.call(emitter=emitter), self.main['reply'])
        self.assertEqual(emitter.await_count, 1)
        self.assertEqual(len(self.requests), 1)

    async def test_event_construction_failure_never_replaces_main(self):
        for broken in ['not-a-uuid', None]:
            self.result['trial_id'] = broken
            self.assertEqual(await self.call(), self.main['reply'])
        self.assertEqual(len(self.requests), 2)
        self.assertEqual(self.events, [])

    async def test_cancelled_or_stalled_emitter_still_returns_main(self):
        emitter = AsyncMock(side_effect=asyncio.CancelledError)
        self.assertEqual(await self.call(emitter=emitter), self.main['reply'])
        self.assertEqual(emitter.await_count, 1)
        async def stalled(event):
            self.events.append(event)
            await asyncio.Event().wait()
        self.assertEqual(await self.call(emitter=stalled), self.main['reply'])
        self.assertEqual(len(self.events), 1)
        self.assertEqual(len(self.requests), 2)

    async def test_missing_event_callback_still_returns_main(self):
        reply = await self.pipe.pipe(self.body, __user__={'id':'user'}, __chat_id__=CHAT, __metadata__=self.metadata)
        self.assertEqual(reply,self.main['reply']); self.assertEqual(len(self.requests),1)

    async def test_provider_or_evaluation_failure_emits_clean_panel(self):
        self.result['shadow'].update(status='SKIPPED', reply=None, error='HINDSIGHT_RECALL_UNAVAILABLE')
        self.result['shadow']['recall'].update(status='ERROR', elapsed_ms=None)
        self.result['shadow']['evidence'] = []
        self.result['evaluation'] = {'status':'UNAVAILABLE','votable':False}
        self.assertEqual(await self.call(),self.main['reply'])
        self.assertEqual(self.events[0]['data']['shadow']['error_code'],'HINDSIGHT_RECALL_UNAVAILABLE')
        self.assertEqual(self.events[0]['data']['evaluation']['status'],'UNAVAILABLE')

    async def test_timeout_and_unsuccessful_response_never_retry_or_fallback(self):
        self.failure = httpx.ReadTimeout('private')
        with self.assertRaisesRegex(ValueError,'may already have been saved'): await self.call()
        self.assertEqual(len(self.requests),1)
        self.failure = None; self.code = 500
        with self.assertRaises(ValueError): await self.call()
        self.assertEqual(len(self.requests),2); self.assertEqual(self.events,[])
        self.assertTrue(all(r.url.path=='/api/arena/chat' for r in self.requests))

    async def test_failed_main_no_event_and_task_suppression_no_io(self):
        self.main['status']['persistence'] = 'ERROR'
        with self.assertRaises(ValueError): await self.call()
        self.assertEqual(self.events,[])
        self.requests.clear(); self.pipe.valves.ARENA_ENABLED=False
        self.assertEqual(await self.call(__task__='title_generation'),'')
        self.assertEqual(self.requests,[])


class ArenaOverlayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        archive=os.getenv('CORVUS_OW2D_ARCHIVE')
        if not archive: raise unittest.SkipTest('Set CORVUS_OW2D_ARCHIVE for pinned-source integration')
        spec=importlib.util.spec_from_file_location('ui1_verifier',DEPLOY/'branding/verify_branding.py')
        cls.verifier=importlib.util.module_from_spec(spec); spec.loader.exec_module(cls.verifier)
        cls.temp=tempfile.TemporaryDirectory(prefix='corvus-ui1-test-'); cls.addClassCleanup(cls.temp.cleanup)
        cls.source=Path(cls.temp.name)/'source'
        cls.verifier.prepare_source(cls.source,archive,arena_ui1=True)

    def test_layered_source_and_backend_parse(self):
        result=self.verifier.source_checks(self.source,arena_ui1=True)
        self.assertEqual(result['application_branding_findings'],0)
        ast.parse((self.source/'backend/open_webui/main.py').read_text())

    def test_metadata_accepts_only_literal_true_and_keeps_authenticated_identity(self):
        tree=ast.parse((self.source/'backend/open_webui/main.py').read_text())
        assign=next(n for n in ast.walk(tree) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='arena_metadata' for t in n.targets))
        condition=next(n for n in ast.walk(tree) if isinstance(n,ast.If) and ast.unparse(n.test).startswith('isinstance(arena_metadata, dict)'))
        block=ast.fix_missing_locations(ast.Module(body=[assign,condition],type_ignores=[]))
        for value,expected in [(True,True),(False,False),('true',False),(1,False),(None,False)]:
            context={'form_data':{'metadata':{'corvus_arena':value,'user_id':'attacker','secret':'drop'}},'metadata':{'user_id':'authenticated'}}
            exec(compile(block,'metadata','exec'),context)
            self.assertEqual(context['metadata'], {'user_id':'authenticated',**({'corvus_arena':True} if expected else {})})
            self.assertNotIn('metadata',context['form_data'])

    def test_pinned_backend_message_upsert_preserves_saved_arena_field_on_completion(self):
        tree = ast.parse((self.source/'backend/open_webui/models/chats.py').read_text())
        node = deepcopy(next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
                             and n.name == 'upsert_message_to_chat_by_id_and_message_id'))
        node.returns = None
        for argument in node.args.args:
            argument.annotation = None
        namespace = {}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])), 'pinned-upsert', 'exec'), namespace)
        saved = {'history': {'messages': {'assistant': {'content': '', 'corvus_arena': {'trial_id': TRIAL}}}}}
        def update(chat_id, data):
            saved.clear()
            saved.update(json.loads(json.dumps(data)))
            return SimpleNamespace(chat=saved)
        fake = SimpleNamespace(get_chat_by_id=lambda _: SimpleNamespace(chat=deepcopy(saved)), update_chat_by_id=update)
        namespace[node.name](fake, CHAT, 'assistant', {'content': 'Canonical reply', 'done': True})
        self.assertEqual(saved['history']['messages']['assistant']['corvus_arena'], {'trial_id': TRIAL})
        self.assertEqual(saved['history']['messages']['assistant']['content'], 'Canonical reply')

    def test_lab_overlay_does_not_change_existing_production_build_or_compose(self):
        import subprocess
        for name in ['deploy/open-webui/Dockerfile.corvus','deploy/open-webui/compose.ow1.yml',
                     'deploy/open-webui/compose.ow2d.yml','deploy/lab/compose.webui.yml']:
            before=subprocess.check_output(['git','show','de2e236:'+name],cwd=REPO)
            self.assertEqual((REPO/name).read_bytes(),before,name)
        self.assertIn('0.6.5-arena-ui1.2',(DEPLOY/'Dockerfile.arena-ui1').read_text())


if __name__=='__main__': unittest.main()
