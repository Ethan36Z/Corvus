"""Offline budget tests + actual provider request/control-flow bodies, no inference."""
import argparse
import asyncio
from contextlib import asynccontextmanager
import importlib.util
import json
import os
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import AsyncMock, Mock, patch

ART = Path(__file__).resolve().parent


def module_file(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec);sys.modules[name] = value;spec.loader.exec_module(value)
    return value


class BudgetTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {'CORVUS_CONSOLIDATION_CONTEXT_LIMIT':'8192',
            'HINDSIGHT_API_CONSOLIDATION_MAX_COMPLETION_TOKENS':'1024',
            'CORVUS_CONSOLIDATION_SAFETY_MARGIN_TOKENS':'256'}, clear=True)
        self.env.start();self.addCleanup(self.env.stop)
        self.provider = types.SimpleNamespace(provider='openai',model='corvus',base_url='http://offline/v1',_max_tokens_param_name=lambda:'max_tokens')
        self.params = {'model':'corvus','messages':[{'role':'user','content':'exact source'}],'max_tokens':4090}
        self.count = patch.object(b,'_count_rendered',new=AsyncMock(return_value=4038));self.counter=self.count.start();self.addCleanup(self.count.stop)
        self.gate = patch.object(ad,'check_foreground_admission');self.check=self.gate.start();self.addCleanup(self.gate.stop)

    async def enforce(self,scope='consolidation'):
        return await b.enforce_consolidation_budget(self.provider,scope,self.params)

    async def test_known_failure_cannot_get_4090_output(self):
        await self.enforce();self.assertEqual(self.params['max_tokens'],1024)
        self.assertEqual(4038+self.params['max_tokens']+256,5318)
        self.assertEqual(self.params['reasoning_effort'],'none')
        self.assertFalse(self.params['extra_body']['chat_template_kwargs']['enable_thinking'])

    def test_all_context_counts_obey_invariant_or_defer(self):
        for count in range(8193):
            if count>7424:
                with self.assertRaises(b.DeferOperation):b.completion_budget(count,8192,1024,256)
            else:
                allowed=b.completion_budget(count,8192,1024,256)
                self.assertGreaterEqual(allowed,512);self.assertLessEqual(allowed,1024)
                self.assertLessEqual(count+allowed+256,8192)

    async def test_small_input_keeps_useful_cap(self):
        self.counter.return_value=500;await self.enforce();self.assertEqual(self.params['max_tokens'],1024)

    async def test_near_limit_shrinks_completion_not_source(self):
        self.counter.return_value=7424;before=json.loads(json.dumps(self.params['messages']))
        await self.enforce();self.assertEqual(self.params['max_tokens'],512);self.assertEqual(self.params['messages'],before)

    async def test_oversized_defers_no_truncation_or_retries(self):
        self.counter.return_value=7425;before=json.loads(json.dumps(self.params))
        with self.assertRaises(b.DeferOperation):await self.enforce()
        self.assertEqual(self.params,before);self.counter.assert_awaited_once()

    async def test_counter_failure_untrusted_model_defers(self):
        for failure in (OSError('unreadable tokenizer'),ValueError('model mismatch'),asyncio.TimeoutError()):
            self.counter.side_effect=failure
            with self.assertRaises(b.DeferOperation):await self.enforce()

    async def test_invalid_config_defer_not_provider_failure(self):
        for value in ('bad','0','-1','1.5'):
            with patch.dict(os.environ,{'CORVUS_CONSOLIDATION_CONTEXT_LIMIT':value}):
                with self.assertRaises(b.DeferOperation):await self.enforce()

    async def test_extra_body_cannot_override_measured_request_or_cap(self):
        for key in ('max_tokens','max_completion_tokens','messages','model'):
            self.params['extra_body']={key:'unsafe'}
            with self.assertRaises(b.DeferOperation):await self.enforce()
        self.counter.assert_not_awaited()

    async def test_non_consolidation_and_unconfigured_unchanged(self):
        for scope in ('retain_extract_facts','reflect','verification'):
            original=json.loads(json.dumps(self.params));await self.enforce(scope);self.assertEqual(self.params,original)
        with patch.dict(os.environ,{},clear=True):await self.enforce()
        self.counter.assert_not_awaited();self.check.assert_not_called()

    async def test_dedup_also_bounded_and_alternate_cap_removed(self):
        self.params['max_completion_tokens']=4090;await self.enforce('consolidation_dedup')
        self.assertNotIn('max_completion_tokens',self.params);self.assertEqual(self.params['max_tokens'],1024)

    async def test_foreground_arrival_during_count_defers_before_send(self):
        self.check.side_effect=b.DeferOperation(None,'BUSY')
        with self.assertRaises(b.DeferOperation):await self.enforce()
        self.check.assert_called_once()

    async def test_real_provider_caps_final_soft_schema_request_under_permits(self):
        ns=h.namespace('hindsight_api.engine.providers')
        for name in ('LengthFinishReasonError','APIConnectionError','APIStatusError','ProviderResponseError'):
            ns[name]=type(name,(Exception,),{})
        ns.update(apply_bank_attribution=h.noop,apply_cache_affinity=h.noop,apply_opencode_session=h.noop,
                  set_stage=h.noop, describe_transport_error=str, _ensure_json_word_in_user_message=lambda x:x,provider_json_schema=lambda x:{'required':['updates']})
        h.load('engine/providers/openai_compatible_llm.py',['call'],ns)
        sent=[];sem=asyncio.Semaphore(1)
        class Sent(Exception):pass
        async def send(**params):
            self.assertTrue(sem.locked());sent.append(params.copy());raise Sent()
        provider=types.SimpleNamespace(**vars(self.provider),ollama_num_ctx=None,_config_extra_body={},_cache_affinity=None,
            _client=types.SimpleNamespace(chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=send))),
            _supports_reasoning_model=lambda:False,_sends_reasoning_effort=lambda:False,_apply_provider_extra_body_defaults=h.noop,_get_max_reasoning_tokens=lambda:None)
        @asynccontextmanager
        async def permits():
            async with sem:yield
        class Schema:
            @classmethod
            def model_json_schema(cls):return {'required':['updates']}
        async def count(*args):
            self.assertTrue(sem.locked());self.assertIn('matching this schema',args[1]['messages'][0]['content']);return 4038
        self.counter.side_effect=count
        call=lambda:ns['call'](provider,[{'role':'system','content':'real prompt'}],response_format=Schema,max_completion_tokens=4090,scope='consolidation',attempt_context=permits,max_retries=3)
        with self.assertRaises(Sent):await call()
        self.assertEqual(len(sent),1);self.assertEqual(sent[0]['max_tokens'],1024);self.assertFalse(sem.locked())
        sent.clear();self.counter.side_effect=None;self.counter.return_value=8000
        with self.assertRaises(b.DeferOperation):await call()
        self.assertEqual(sent,[]);self.assertFalse(sem.locked())
        sent.clear();self.counter.side_effect=None;self.counter.return_value=4038
        async def retry_error(**params):
            sent.append(params.copy());raise ns['APIConnectionError']('ordinary provider failure')
        provider._client.chat.completions.create=retry_error
        self.counter.reset_mock()
        with self.assertRaises(ns['APIConnectionError']):
            await ns['call'](provider,[],scope='consolidation',attempt_context=permits,max_retries=2,initial_backoff=0,max_backoff=0)
        self.assertEqual(len(sent),3);self.assertEqual(self.counter.await_count,3)
        self.assertTrue(all(p['max_tokens']==1024 for p in sent));self.assertFalse(sem.locked())
        self.counter.reset_mock()
        @asynccontextmanager
        async def busy():
            async with sem:raise b.DeferOperation(None,'BUSY');yield
        with self.assertRaises(b.DeferOperation):
            await ns['call'](provider,[],scope='consolidation',attempt_context=busy)
        self.counter.assert_not_awaited();self.assertFalse(sem.locked())

    async def test_budget_defer_uses_existing_consolidator_control_path_no_failed_fact(self):
        ns=h.consolidation();ns['DeferOperation']=b.DeferOperation
        llm=types.SimpleNamespace(call=lambda **kw:b.enforce_consolidation_budget(self.provider,'consolidation',self.params))
        self.counter.return_value=8000
        with self.assertRaises(b.DeferOperation):
            await ns['_consolidate_batch_with_llm'](llm,[{'id':'grounded','text':'exact'}],[],{},ns['config'])
        self.assertEqual(ns['metrics'].failures,[]);self.counter.assert_awaited_once()


class CounterTests(unittest.IsolatedAsyncioTestCase):
    async def test_actual_counter_posts_template_then_special_token_count_not_chars(self):
        responses=[{'model_alias':'corvus','default_generation_settings':{'n_ctx':8192}}, {'prompt':'chat template special tokens'}, {'tokens':[1,2,3,4]}];calls=[]
        class Response:
            def raise_for_status(self):pass
            async def json(self):return responses.pop(0)
            async def __aenter__(self):return self
            async def __aexit__(self,*a):pass
        class Session:
            def __init__(self,**kwargs):self.options=kwargs
            async def __aenter__(self):return self
            async def __aexit__(self,*a):pass
            def request(self,*args,**kwargs):calls.append((args,kwargs));return Response()
        fake=types.SimpleNamespace(ClientSession=Session,ClientTimeout=lambda **k:k)
        body={'messages':[{'role':'system','content':'exact wrapped schema'}],'chat_template_kwargs':{'enable_thinking':False}}
        with patch.dict(sys.modules,{'aiohttp':fake}):count=await b._count_rendered('http://same-model/v1',body,'corvus',8192)
        self.assertEqual(count,4)
        self.assertEqual([v[0] for v in calls],[('GET','http://same-model/props'),('POST','http://same-model/apply-template'),('POST','http://same-model/tokenize')])
        self.assertEqual(calls[1][1]['json'],body);self.assertEqual(calls[2][1]['json'],{'content':'chat template special tokens','add_special':True,'parse_special':True})


def main():
    global h,ad,b
    p=argparse.ArgumentParser();p.add_argument('--source',required=True,type=Path);args=p.parse_args()
    h=module_file('budget_control_harness',ART/'test_control_flow.py');h.SOURCE=args.source.resolve()
    guard=module_file('budget_guard',ART/'apply.py');guard.verify(h.SOURCE,patched=True)
    h.core();ad=module_file('hindsight_api.engine.foreground_admission',h.SOURCE/'hindsight_api/engine/foreground_admission.py')
    b=module_file('hindsight_api.engine.consolidation_budget',h.SOURCE/'hindsight_api/engine/consolidation_budget.py')
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(c) for c in (BudgetTests,CounterTests))
    return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1


if __name__=='__main__':sys.exit(main())
