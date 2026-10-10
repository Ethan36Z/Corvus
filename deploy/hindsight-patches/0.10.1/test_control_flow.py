"""Offline tests execute selected COMPLETE installed functions/closures via AST.

No Hindsight import/startup, SDK network client, PostgreSQL, bank, or model is used.
Source hashes are checked before loading. Infrastructure collaborators are fakes;
exception aggregation, parsing, retries, streaming queue/consumer, batch dispatch,
engine routing and poller control handling are the actual frozen source bodies.
"""
import argparse
import ast
import asyncio
from contextlib import AsyncExitStack, asynccontextmanager, nullcontext
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import StrEnum
import importlib.util
import json
import logging
from pathlib import Path
import sys
import time
import shutil
import subprocess
import tempfile
import types
import unittest
import uuid
from unittest.mock import AsyncMock, Mock

ART = Path(__file__).resolve().parent
SOURCE = None


def noop(*args, **kwargs):
    pass


def module(name, **values):
    value = types.ModuleType(name)
    value.__dict__.update(values)
    sys.modules[name] = value
    return value


# Only local import collaborators needed by the selected functions.
module('openai', BadRequestError=type('BadRequestError', (Exception,), {}))
module('hindsight_api.worker.stage', get_stage=lambda: None, set_stage=noop)
module('hindsight_api.config', get_config=lambda: types.SimpleNamespace(llm_strict_schema=False, llamacpp_no_grammar=True))
module('hindsight_api.tracing', get_span_recorder=lambda: types.SimpleNamespace(record_llm_call=noop), _serialize_for_span=str)
module('hindsight_api.engine.llm_trace', record_queue_wait=noop, set_call_metadata=noop, reset_call_metadata=noop,
       set_request_context=noop, reset_request_context=noop, set_response_usage=noop, reset_response_usage=noop,
       current_response_usage=lambda: None)


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    def __add__(self, other):
        return Usage(self.input_tokens + other.input_tokens, self.output_tokens + other.output_tokens)


class FakeLLM:
    model = 'fake'
    provider = 'llamacpp'
    def __init__(self, outcome):
        self.outcome = outcome
        self.calls = 0
    async def call(self, **kwargs):
        self.calls += 1
        if isinstance(self.outcome, BaseException):
            raise self.outcome
        return types.SimpleNamespace(content=self.outcome, usage=Usage())


class FakeMetrics:
    def __init__(self):
        self.failures = []
        self.terminal = []
    def record_consolidation_batch_failure(self, **kwargs):
        self.failures.append(kwargs)
    def record_operation_result(self, *args, **kwargs):
        self.terminal.append((args, kwargs))


@asynccontextmanager
async def context(value=None):
    yield value


def namespace(package='hindsight_api.engine'):
    ns = module(package+'.offline').__dict__
    ns.update(__name__=package+'.offline', __package__=package, asyncio=asyncio,
                logging=logging, logger=logging.getLogger('offline'), time=time, json=json,
                datetime=datetime, timedelta=timedelta, timezone=timezone, uuid=uuid,
                Any=object, dataclass=dataclass, field=field, StrEnum=StrEnum,
                asynccontextmanager=asynccontextmanager, AsyncExitStack=AsyncExitStack,
                nullcontext=nullcontext, TokenUsage=Usage,
                OutputTooLongError=type('OutputTooLongError', (Exception,), {}),
                ProviderContentPolicyError=type('ProviderContentPolicyError', (Exception,), {}),
                ProviderRateLimitResetError=type('ProviderRateLimitResetError', (Exception,), {}),
                ValidationError=type('ValidationError', (Exception,), {}))
    return ns


def load(path, names, ns):
    tree = ast.parse((SOURCE/'hindsight_api'/path).read_text())
    for name in names:
        # Unique names below, except provider .call: first match belongs to its real class.
        search = tree
        if '.' in name:
            owner, name = name.split('.')
            search = next(x for x in ast.walk(tree) if isinstance(x, ast.ClassDef) and x.name == owner)
        nodes = [x for x in ast.walk(search) if isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and x.name == name]
        if len(nodes) != 1:
            raise AssertionError((path, name, len(nodes)))
        node = nodes[0]
        # Retain decorators needed for contexts/classes; no decorated engine entry is loaded.
        program = ast.Module(body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0), node], type_ignores=[])
        exec(compile(ast.fix_missing_locations(program), str(SOURCE/'hindsight_api'/path), 'exec'), ns)
    return ns


def core():
    ns = namespace()
    load('worker/exceptions.py', ['DeferOperation', 'RetryTaskAt'], ns)
    module('hindsight_api.worker.exceptions', DeferOperation=ns['DeferOperation'])
    ns['defer'] = ns['DeferOperation'](datetime.now(timezone.utc)+timedelta(seconds=30), 'foreground busy')
    return ns


def extraction():
    ns = core()
    ns['__package__'] = 'hindsight_api.engine.retain'
    ns.update(build_chunk_prompt_parts=lambda *a, **k: types.SimpleNamespace(system_prompt='frozen', response_schema=dict, user_message=k['chunk']),
              chunk_text=lambda text, **k: text.split('|'), _build_extraction_prompt_and_schema=lambda c: object())
    names=['_coerce_fact_response','_extract_facts_from_chunk','_extract_facts_with_auto_split','extract_facts_from_text','extract_facts_from_contents']
    if '_raise_if_deferred' in (SOURCE/'hindsight_api/engine/retain/fact_extraction.py').read_text():
        names.insert(0, '_raise_if_deferred')
    load('engine/retain/fact_extraction.py', names, ns)
    ns['config'] = types.SimpleNamespace(retain_extraction_mode='concise', retain_extract_causal_links=False,
        retain_llm_max_retries=0, llm_max_retries=0, retain_llm_initial_backoff=None, llm_initial_backoff=0,
        retain_llm_max_backoff=None, llm_max_backoff=0, llm_temperature_retain=0, llm_strict_schema_retain=True,
        retain_max_completion_tokens=4096, retain_chunk_size=100, retain_structured_chunk_size=100,
        retain_max_attachments_per_chunk=1, retain_batch_enabled=False)
    return ns


async def extract(ns, outcome, text='one'):
    llm = FakeLLM(outcome)
    result = await ns['extract_facts_from_text'](text, None, llm, ns['config'])
    return result, llm


class RetainTests(unittest.IsolatedAsyncioTestCase):
    async def test_llm_defer_identity_not_runtime_error(self):
        ns=extraction(); llm=FakeLLM(ns['defer'])
        with self.assertRaises(ns['DeferOperation']) as caught:
            await ns['extract_facts_from_text']('one', None, llm, ns['config'])
        self.assertIs(caught.exception, ns['defer']); self.assertEqual(llm.calls,1)

    async def test_mixed_errors_defer_latest_logged_no_partial_result(self):
        ns=extraction(); ordinary=ValueError('real parse problem'); later=ns['DeferOperation'](ns['defer'].exec_date+timedelta(seconds=2),'later')
        with self.assertLogs(level='WARNING') as logs:
            with self.assertRaises(ns['DeferOperation']) as caught:
                ns['_raise_if_deferred']([ordinary,([],Usage()),ns['defer'],later])
        self.assertIs(caught.exception,later);self.assertTrue(any('real parse problem' in x for x in logs.output))

    async def test_multicontent_ordinary_first_cannot_mask_defer(self):
        ns=extraction()
        async def fake(text, **kw):
            raise ValueError('ordinary') if text=='bad' else ns['defer']
        ns['extract_facts_from_text']=fake
        items=[types.SimpleNamespace(content=t,event_date=None,context='',metadata={}) for t in ('bad','defer')]
        with self.assertRaises(ns['DeferOperation']) as caught:
            await ns['extract_facts_from_contents'](items,FakeLLM(None),ns['config'])
        self.assertIs(caught.exception,ns['defer'])

    async def test_split_ordinary_first_cannot_mask_defer(self):
        ns=extraction();ns['_split_chunk_for_output_retry']=lambda x: ('bad','defer')
        async def fake(chunk, **kw):
            if chunk=='root': raise ns['OutputTooLongError']('split')
            raise ValueError('ordinary') if chunk=='bad' else ns['defer']
        ns['_extract_facts_from_chunk']=fake
        with self.assertRaises(ns['DeferOperation']) as caught:
            await ns['_extract_facts_with_auto_split']('root',0,1,None,'',FakeLLM(None),ns['config'])
        self.assertIs(caught.exception,ns['defer'])

    async def test_stream_partial_commit_defer_then_resume_skips_checkpoint(self):
        ns=extraction();committed=set();finals=[];completed=asyncio.Event();calls=[]
        ns.update(chunk_to_content=[0,0],contents=[types.SimpleNamespace(context='',event_date=None,metadata={},entities=[],resolve_entities=False,tags=[],attachment_filenames=[],observation_scopes=None)],
            RetainContent=types.SimpleNamespace, effective_doc_id='doc', llm_config=None,config=ns['config'],
            format_date_fn=None,fact_type_override=None,log_buffer=[],pool=None,operation_id='same-operation',schema=None,
            attachment_loader=None,vlm_config=None,chunk_storage=types.SimpleNamespace(compute_chunk_hash=lambda t:t),
            total_chunks=2,chunk_batch_size=1,all_unit_ids=[],progress_callback=None,pipeline_aborted=[False],
            memory_budget=types.SimpleNamespace(reserve=AsyncMock(),release=noop,should_flush=lambda n:False),
            coalescing_embedder=types.SimpleNamespace(close=noop,stats=types.SimpleNamespace(describe=lambda:'fake')))
        async def work(contents,*args,**kw):
            text=contents[0].content;calls.append(text)
            if text=='second' and not ns.get('resume'):
                await completed.wait();raise ns['defer']
            return types.SimpleNamespace(extracted_facts=[],processed_facts=[],chunks=[],usage=Usage())
        async def write(batch, index, is_last):
            committed.update(item[1].content for item in batch);finals.append(is_last);completed.set()
        ns.update(_extract_and_embed=work, estimate_chunk_bytes=lambda *a:1,_process_db_batch=write)
        load('engine/retain/orchestrator.py',['_llm_producer','_db_consumer'],ns)
        async def run():
            ns.update(all_pre_chunks=['first','second'],existing_chunk_hashes=set(committed),chunk_queue=asyncio.Queue(),
                reserved_by_chunk={},producer_error=[])
            producer=asyncio.create_task(ns['_llm_producer']());consumer=asyncio.create_task(ns['_db_consumer']())
            try:
                await asyncio.gather(producer,consumer)
            finally:
                for task in (producer,consumer):
                    if not task.done(): task.cancel()
                results=await asyncio.gather(producer,consumer,return_exceptions=True)
                ns['_raise_if_deferred'](results)
        with self.assertRaises(ns['DeferOperation']) as caught: await asyncio.wait_for(run(),2)
        self.assertIs(caught.exception,ns['defer']);self.assertEqual(committed,{'first'})
        self.assertNotIn(True,finals);self.assertEqual(ns['producer_error'],[])
        ns['resume']=True;await asyncio.wait_for(run(),2)
        self.assertEqual(committed,{'first','second'});self.assertEqual(calls,['first','second','second'])

    async def test_pipeline_defer_precedence_over_consumer_failure(self):
        ns=extraction()
        # Execute the actual driver/finally statements (the subsequent storage body is excluded).
        tree=ast.parse((SOURCE/'hindsight_api/engine/retain/orchestrator.py').read_text())
        driver=next(n for n in ast.walk(tree) if isinstance(n,ast.If) and ast.unparse(n.test)=='not facts_already_committed')
        body=driver.body[:3]  # producer task, consumer task, try/finally cancellation + drain
        fn=ast.AsyncFunctionDef(name='driver',args=ast.arguments(posonlyargs=[],args=[],kwonlyargs=[],kw_defaults=[],defaults=[]),body=body,decorator_list=[])
        exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),'stream-driver','exec'),ns)
        async def producer(): raise ns['defer']
        async def consumer(): raise ValueError('consumer ordinary')
        ns.update(_llm_producer=producer,_db_consumer=consumer)
        with self.assertRaises(ns['DeferOperation']) as caught: await ns['driver']()
        self.assertIs(caught.exception,ns['defer'])

    async def test_document_group_ordinary_first_does_not_mask_defer(self):
        ns=extraction();tree=ast.parse((SOURCE/'hindsight_api/engine/retain/orchestrator.py').read_text())
        owner=next(x for x in ast.walk(tree) if isinstance(x,ast.AsyncFunctionDef) and x.name=='retain_batch')
        blocks=next(n.body for n in ast.walk(owner) if isinstance(n,ast.If) and any(isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='group_results' for t in x.targets) for x in n.body))
        start=next(i for i,x in enumerate(blocks) if isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='group_results' for t in x.targets))
        fn=ast.AsyncFunctionDef(name='group_driver',args=ast.arguments(posonlyargs=[],args=[],kwonlyargs=[],kw_defaults=[],defaults=[]),body=blocks[start:start+3],decorator_list=[])
        exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),'group-driver','exec'),ns)
        async def group(name,*args): raise ValueError('document error') if name=='bad' else ns['defer']
        ns.update(groups={'bad':(None,None),'defer':(None,None)},_run_group=group)
        with self.assertRaises(ns['DeferOperation']) as caught: await ns['group_driver']()
        self.assertIs(caught.exception,ns['defer'])

    async def test_completed_subbatch_defer_wins_over_ordinary_error(self):
        ns=extraction();tree=ast.parse((SOURCE/'hindsight_api/engine/memory_engine.py').read_text())
        throttle=next(n for n in ast.walk(tree) if isinstance(n,ast.While) and ast.unparse(n.test)=='len(pending) >= concurrency')
        final=next(n for n in ast.walk(tree) if isinstance(n,ast.If) and ast.unparse(n.test)=='pending' and any(isinstance(x,ast.Name) and x.id=='collected' for x in ast.walk(n)))
        for block in (throttle,final):
            async def defer(): raise ns['defer']
            async def ordinary(): raise ValueError('sub-batch ordinary')
            ns.update(pending=[asyncio.create_task(ordinary()),asyncio.create_task(defer())],collected=[],concurrency=2)
            await asyncio.sleep(0) # both complete; FIRST_COMPLETED cannot mask either result
            fn=ast.AsyncFunctionDef(name='subbatch_driver',args=ast.arguments(posonlyargs=[],args=[],kwonlyargs=[],kw_defaults=[],defaults=[]),body=[block],decorator_list=[])
            # Globals declaration lets the complete original block update injected pending state.
            fn.body.insert(0,ast.Global(names=['pending','collected']))
            exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),'subbatch-driver','exec'),ns)
            with self.assertRaises(ns['DeferOperation']) as caught: await ns['subbatch_driver']()
            self.assertIs(caught.exception,ns['defer']);self.assertEqual(ns['collected'],[])


def consolidation():
    ns=core();metrics=FakeMetrics()
    ns.update(build_consolidation_system_prompt=lambda **k:'frozen',build_consolidation_input=lambda **k:'input',
        _build_response_model=lambda **k:dict,_dedupe_updates=lambda x,**k:x,get_metrics_collector=lambda:metrics,
        _OUTER_RETRY_INITIAL_BACKOFF=0,_OUTER_RETRY_MAX_BACKOFF=0)
    load('engine/consolidation/consolidator.py', ['_BatchLLMResult','_BatchDeltas','_BatchFailureClass','_classify_batch_failure',
        '_consolidate_batch_with_llm','_process_one_llm_batch','_process_tag_group','_gather_or_cancel','_process_memory_batch'],ns)
    ns['config']=types.SimpleNamespace(llm_output_language=None,observations_mission='',llm_supports_max_items=True,
        consolidation_max_attempts=3,consolidation_llm_max_retries=0,llm_temperature_consolidation=0,
        llm_strict_schema_consolidation=True,consolidation_max_completion_tokens=None)
    ns['metrics']=metrics
    return ns


class FakePerf:
    timings = {}
    total_prompt_chars = 0
    llm_calls = 0
    def __init__(self, *args): pass
    def record_timing(self, *args): pass
    def record_llm_call(self, *args): pass
    def record_llm_batch_failures(self, *args): pass
    def merge_from(self, *args): pass


def batch_environment(ns):
    stamps=[]
    async def mark(**kwargs): stamps.append((kwargs['unit_ids'],kwargs['failed']))
    conn=types.SimpleNamespace(transaction=lambda:context())
    store=types.SimpleNamespace(mark_consolidated=mark)
    ns.update(bank_id='bank',pool=None,request_context=None,operation_id='stable-operation',set_stage=noop,
        memory_engine=types.SimpleNamespace(_check_op_alive=AsyncMock(return_value=True),_write_operation_progress=AsyncMock()),
        ConsolidationPerfLog=FakePerf,perf=FakePerf(), _batch_scope_signature=lambda m:(),
        _resolve_obs_tags_list=lambda m:None,_effective_scope_limit=lambda *a:-1,
        _dedup_active=lambda c:False,record_source_memory_ids=noop, get_memories=lambda:store,
        acquire_with_retry=lambda pool:context(conn),fq_table=lambda name:name,
        _find_related_observations=AsyncMock(return_value=types.SimpleNamespace(results=[],source_facts={})),
        _progress_total=AsyncMock(return_value=3),total_count=3,
        cumulative_progress=dict(processed=0,observations_created=0,observations_updated=0,observations_merged=0,
                                 observations_deleted=0,memories_failed=0))
    return stamps


class ConsolidationTests(unittest.IsolatedAsyncioTestCase):
    async def test_defer_no_retries_failure_metrics_or_failed_result(self):
        ns=consolidation();llm=FakeLLM(ns['defer'])
        with self.assertRaises(ns['DeferOperation']) as caught:
            await ns['_consolidate_batch_with_llm'](llm,[{'id':'one','text':'source'}],[],{},ns['config'])
        self.assertIs(caught.exception,ns['defer']);self.assertEqual(llm.calls,1);self.assertEqual(ns['metrics'].failures,[])

    async def test_defer_leaves_batch_unstamped_no_transaction(self):
        ns=consolidation();store=types.SimpleNamespace(mark_consolidated=AsyncMock());acquire=Mock(side_effect=AssertionError('no DB transaction on defer'))
        ns.update(record_source_memory_ids=noop,_find_related_observations=AsyncMock(return_value=types.SimpleNamespace(results=[],source_facts={})),
                  _effective_scope_limit=lambda *a:-1, acquire_with_retry=acquire,get_memories=lambda:store)
        with self.assertRaises(ns['DeferOperation']):
            await ns['_process_memory_batch'](None,None,FakeLLM(ns['defer']),'bank',[{'id':'one','text':'source'}],None,config=ns['config'],mark_consolidated_ids=['one'])
        acquire.assert_not_called();store.mark_consolidated.assert_not_awaited()

    async def test_actual_bisection_dispatch_is_bypassed_on_defer(self):
        ns=consolidation();calls=[];failed=[]
        ns.update(bank_id='bank',ConsolidationPerfLog=lambda *a:types.SimpleNamespace(),
                  _batch_scope_signature=lambda m:(), _resolve_obs_tags_list=lambda m:None,pool=None,request_context=None,memory_engine=None,llm_config=None)
        async def process(**kw):
            calls.append([m['id'] for m in kw['memories']]);raise ns['defer']
        ns.update(_process_memory_batch=process, get_memories=lambda:types.SimpleNamespace(mark_consolidated=AsyncMock(side_effect=lambda **k:failed.append(k))))
        with self.assertRaises(ns['DeferOperation']) as caught:
            await ns['_process_one_llm_batch']([{'id':'one','text':'1'},{'id':'two','text':'2'}],1)
        self.assertIs(caught.exception,ns['defer']);self.assertEqual(calls,[['one','two']]);self.assertEqual(failed,[])

    async def test_serial_committed_batch_preserved_remaining_eligible_no_duplicate(self):
        ns=consolidation();stamps=batch_environment(ns)
        llm=FakeLLM(types.SimpleNamespace(creates=[],updates=[],deletes=[]));calls=[]
        original_call=llm.call
        async def call(**kwargs):
            calls.append(kwargs)
            if len(calls)==2: raise ns['defer']
            return await original_call(**kwargs)
        llm.call=call;ns['llm_config']=llm
        groups=[([{'id':name,'text':name}],number) for number,name in enumerate(('one','two','three'),1)]
        with self.assertRaises(ns['DeferOperation']) as caught: await ns['_process_tag_group'](groups)
        self.assertIs(caught.exception,ns['defer']);self.assertEqual(stamps,[(['one'],False)])
        self.assertEqual(len(calls),2);self.assertEqual(ns['cumulative_progress']['processed'],1)
        # The fake store returns only unstamped facts, just as the existing pending query does.
        await ns['_process_tag_group'](groups[1:])
        self.assertEqual(stamps,[(['one'],False),(['two'],False),(['three'],False)])
        self.assertEqual(ns['cumulative_progress']['processed'],3);self.assertEqual(ns['metrics'].failures,[])

    async def test_parallel_group_cancellation_rethrows_same_defer(self):
        ns=consolidation();stopped=asyncio.Event()
        async def defer(): raise ns['defer']
        async def sibling():
            try: await asyncio.Event().wait()
            finally: stopped.set()
        with self.assertRaises(ns['DeferOperation']) as caught: await ns['_gather_or_cancel']([defer(),sibling()])
        self.assertIs(caught.exception,ns['defer']);self.assertTrue(stopped.is_set())


class OrdinaryRegressionTests(unittest.IsolatedAsyncioTestCase):
    async def test_retain_model_error_still_runtime_error(self):
        ns=extraction()
        with self.assertRaisesRegex(RuntimeError,'ValueError: provider failed'):
            await extract(ns,ValueError('provider failed'))

    async def test_retain_invalid_schema_still_runtime_error(self):
        ns=extraction()
        with self.assertRaisesRegex(RuntimeError,'non-dict JSON'):
            await extract(ns,'not an object')

    async def test_retain_invalid_facts_still_fails(self):
        ns=extraction()
        with self.assertRaisesRegex(RuntimeError,'unusable'):
            await extract(ns,{'facts':['bad shape']})

    async def test_retain_legitimate_empty_facts_succeeds(self):
        ns=extraction();(facts,metadata,usage),llm=await extract(ns,{'facts':[]})
        self.assertEqual(facts,[]);self.assertEqual(metadata,[('one',0)]);self.assertEqual(llm.calls,1)

    async def test_retain_split_ordinary_error_identity(self):
        ns=extraction();error=ValueError('ordinary');ns['_split_chunk_for_output_retry']=lambda x:('a','b')
        async def fake(chunk,**kw):
            if chunk=='root': raise ns['OutputTooLongError']('split')
            raise error
        ns['_extract_facts_from_chunk']=fake
        with self.assertRaises(ValueError) as caught:
            await ns['_extract_facts_with_auto_split']('root',0,1,None,'',None,ns['config'])
        self.assertIs(caught.exception,error)

    async def test_consolidation_transport_error_retries_and_fails(self):
        ns=consolidation();llm=FakeLLM(RuntimeError('ordinary'))
        result=await ns['_consolidate_batch_with_llm'](llm,[{'id':'one','text':'source'}],[],{},ns['config'])
        self.assertTrue(result.failed);self.assertEqual(llm.calls,3);self.assertEqual(result.failed_attempts,3)

    async def test_consolidation_parse_error_failfast_for_bisection(self):
        ns=consolidation()
        for error in (json.JSONDecodeError('bad','{',0),ns['ValidationError']('schema'),ns['OutputTooLongError']('length')):
            with self.subTest(error=type(error).__name__):
                llm=FakeLLM(error)
                result=await ns['_consolidate_batch_with_llm'](llm,[{'id':'one','text':'source'}],[],{},ns['config'])
                self.assertTrue(result.failed);self.assertEqual(llm.calls,1);self.assertEqual(result.failed_attempts,1)

    async def test_consolidation_auth_failure_still_propagates(self):
        ns=consolidation();err=RuntimeError('auth');err.status_code=401;llm=FakeLLM(err)
        with self.assertRaises(RuntimeError) as caught:
            await ns['_consolidate_batch_with_llm'](llm,[{'id':'one','text':'source'}],[],{},ns['config'])
        self.assertIs(caught.exception,err);self.assertEqual(llm.calls,1)

    async def test_ordinary_failed_batch_still_bisects_and_marks_singletons_failed(self):
        ns=consolidation();stamps=batch_environment(ns)
        ns['llm_config']=FakeLLM(json.JSONDecodeError('bad','{',0));sizes=[]
        original=ns['_process_memory_batch']
        async def process(**kwargs):
            sizes.append(len(kwargs['memories']));return await original(**kwargs)
        ns['_process_memory_batch']=process
        result=await ns['_process_one_llm_batch']([{'id':'one','text':'one'},{'id':'two','text':'two'}],1)
        self.assertEqual(sizes,[2,1,1]);self.assertEqual(stamps,[(['one','two'],True)])
        self.assertEqual(result.stats['memories_failed'],2);self.assertEqual(ns['llm_config'].calls,3)

    async def test_consolidation_success_actions_unchanged(self):
        ns=consolidation();response=types.SimpleNamespace(creates=[],updates=[],deletes=[]);llm=FakeLLM(response)
        result=await ns['_consolidate_batch_with_llm'](llm,[{'id':'one','text':'source'}],[],{},ns['config'])
        self.assertFalse(result.failed);self.assertEqual(result.failed_attempts,0);self.assertEqual(llm.calls,1)


class BoundaryTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_wrapper_provider_seam_defer_releases_permits_no_http_retry(self):
        ns=core();sem=asyncio.Semaphore(1)
        load('engine/llm_wrapper.py',['_acquire_permits','_attempt_permits','_request_params'],ns)
        ns['_semaphores_for_scope']=lambda scope:[sem]
        original=ns['_attempt_permits'];entries=[]
        @asynccontextmanager
        async def admission(scope):
            async with original(scope):
                entries.append(scope);self.assertTrue(sem.locked());raise ns['defer']
                yield
        ns['_attempt_permits']=admission
        provider_ns=namespace('hindsight_api.engine.providers')
        for name in ('LengthFinishReasonError','APIConnectionError','APIStatusError','ProviderResponseError'):
            provider_ns[name]=type(name,(Exception,),{})
        provider_ns.update(apply_bank_attribution=noop,apply_cache_affinity=noop,apply_opencode_session=noop,
                           _ensure_json_word_in_user_message=lambda x:x)
        load('engine/providers/openai_compatible_llm.py',['call'],provider_ns)
        client=types.SimpleNamespace(chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=AsyncMock())))
        provider=types.SimpleNamespace(provider='llamacpp',model='fake',base_url='http://offline.invalid',ollama_num_ctx=None,
            _config_extra_body={},_cache_affinity=None,_client=client,_supports_reasoning_model=lambda:False,
            _sends_reasoning_effort=lambda:False,_apply_provider_extra_body_defaults=noop,
            supports_attempt_scoped_concurrency=lambda:True)
        provider.call=types.MethodType(provider_ns['call'],provider)
        load('engine/llm_wrapper.py',['LLMProvider.call'],ns)
        wrapper=types.SimpleNamespace(provider='llamacpp',model='fake',max_retries=4,initial_backoff=0,max_backoff=0,_provider_impl=provider)
        with self.assertRaises(ns['DeferOperation']) as caught:
            await ns['call'](wrapper,[{'role':'user','content':'exact input'}],response_format=dict,scope='retain_extract_facts',strict_schema=False)
        self.assertIs(caught.exception,ns['defer']);self.assertFalse(sem.locked())
        self.assertEqual(entries,['retain_extract_facts']);client.chat.completions.create.assert_not_awaited()

    async def test_real_engine_and_worker_defer_pending_identity_payload_retry_unchanged(self):
        for task_type in ('batch_retain','consolidation'):
            with self.subTest(task_type=task_type):
                ns=core();ns['__package__']='hindsight_api.engine'
                load('engine/memory_engine.py',['_execute_task'],ns)
                load('worker/poller.py',['_updated_row_count','_defer_operation','_defer_all','_execute_task_inner'],ns)
                row={'status':'processing','retry_count':2,'payload':{'contents':['exact payload']},'operation_id':str(uuid.uuid4()),'error_message':None}
                identity=row['operation_id'];payload=json.loads(json.dumps(row['payload']));sql=[]
                async def execute(query,*params):
                    sql.append(query)
                    self.assertIn("status = 'pending'",query);self.assertNotIn('retry_count',query)
                    self.assertNotIn('error_message',query);self.assertNotIn('INSERT',query)
                    self.assertEqual(params[0],identity);row['status']='pending';row['next_retry_at']=params[1]
                    return 'UPDATE 1'
                conn=types.SimpleNamespace(fetchrow=AsyncMock(return_value={'status':'processing'}),execute=execute)
                backend=types.SimpleNamespace(acquire=lambda:context(conn))
                metrics=FakeMetrics()
                ns.update(acquire_with_retry=lambda pool:context(conn),fq_table=lambda name,schema=None:name,
                    _current_schema=types.SimpleNamespace(set=noop),audit_context=lambda *a,**k:context(types.SimpleNamespace(response=None)),
                    set_stage=noop, _metric_operation_label=lambda x:x,get_metrics_collector=lambda:metrics,
                    _WallTimeoutExceeded=type('_WallTimeoutExceeded',(Exception,),{}))
                engine=types.SimpleNamespace(_get_backend=AsyncMock(return_value=backend),_audit_logger=None,
                    _mark_operation_completed=AsyncMock(),_mark_operation_completed_and_fire_webhook=AsyncMock())
                async def handler(task):
                    # Actual retain/consolidation LLM entry, through engine routing.
                    if task_type=='batch_retain':
                        ext=extraction();ext['defer']=ns['defer']
                        # Exception type shared with the engine/worker instance.
                        ext['DeferOperation']=ns['DeferOperation']
                        await extract(ext,ns['defer'])
                    else:
                        con=consolidation();con['DeferOperation']=ns['DeferOperation']
                        await con['_consolidate_batch_with_llm'](FakeLLM(ns['defer']),[{'id':'one','text':'source'}],[],{},con['config'])
                engine._handle_batch_retain=handler;engine._handle_consolidation=handler
                async def executor(task,*args):
                    try: await ns['_execute_task'](engine,task.task_dict)
                    except ns['DeferOperation'] as err:
                        self.assertIs(err,ns['defer']);raise
                poller=types.SimpleNamespace(_backend=backend,_run_executor=executor,_mark_all_completed=AsyncMock(),_mark_all_failed=AsyncMock(),_schedule_retry_all=AsyncMock())
                for name in ('_defer_operation','_defer_all'):
                    setattr(poller,name,types.MethodType(ns[name],poller))
                task=types.SimpleNamespace(operation_id=identity,all_operation_ids=[identity],schema=None,
                    task_dict={'type':task_type,'operation_id':identity,'bank_id':'bank',**payload})
                await ns['_execute_task_inner'](poller,task)
                self.assertEqual(row['status'],'pending');self.assertEqual(row['retry_count'],2)
                self.assertEqual(row['next_retry_at'],ns['defer'].exec_date);self.assertEqual(row['payload'],payload)
                self.assertEqual(row['operation_id'],identity);self.assertIsNone(row['error_message'])
                self.assertEqual(len(sql),1);self.assertEqual(metrics.terminal,[])
                engine._mark_operation_completed.assert_not_awaited();engine._mark_operation_completed_and_fire_webhook.assert_not_awaited()
                poller._mark_all_failed.assert_not_awaited();poller._mark_all_completed.assert_not_awaited();poller._schedule_retry_all.assert_not_awaited()


class ArtifactTests(unittest.TestCase):
    def test_all_patched_python_compiles(self):
        manifest=json.loads((ART/'manifest.json').read_text())
        for name in manifest['files']:
            if name.endswith('.py'):
                compile((SOURCE/name).read_text(),name,'exec')

    def test_patch_application_and_hash_version_guards(self):
        # Start from a pinned source, reconstruct pristine copies only in /tmp.
        with tempfile.TemporaryDirectory(prefix='corvus-hindsight-patch-test-') as directory:
            root=Path(directory)/'api';shutil.copytree(SOURCE,root)
            subprocess.run(['git','apply','--unidiff-zero','--reverse','--unsafe-paths','--directory='+str(root),str(ART/'defer-control-flow.patch')],check=True,capture_output=True)
            def cli(mode):
                return subprocess.run([sys.executable,'-B',str(ART/'apply.py'),'--root',str(root),mode],capture_output=True,text=True)
            original={p:p.read_bytes() for p in root.rglob('*') if p.is_file()}
            self.assertEqual(cli('--check').returncode,0)
            introduced=root/'hindsight_api/engine/foreground_admission.py'
            introduced.write_text('# unexpected pre-existing reader\n')
            self.assertNotEqual(cli('--apply').returncode,0)
            self.assertEqual((root/'hindsight_api/engine/llm_wrapper.py').read_bytes(),original[root/'hindsight_api/engine/llm_wrapper.py'])
            introduced.unlink()
            dependency=root/'hindsight_api/worker/poller.py';dependency.write_bytes(dependency.read_bytes()+b'\n# drift\n')
            self.assertNotEqual(cli('--apply').returncode,0)
            self.assertEqual((root/'hindsight_api/engine/retain/fact_extraction.py').read_bytes(),original[root/'hindsight_api/engine/retain/fact_extraction.py'])
            dependency.write_bytes(original[dependency])
            version=root/'pyproject.toml';version.write_bytes(version.read_bytes().replace(b'0.10.1',b'0.10.2'))
            self.assertNotEqual(cli('--apply').returncode,0);version.write_bytes(original[version])
            self.assertEqual(cli('--apply').returncode,0);self.assertEqual(cli('--verify-patched').returncode,0)
            self.assertNotEqual(cli('--apply').returncode,0) # already patched is not silently applied twice
            for name in json.loads((ART/'manifest.json').read_text())['files']:
                self.assertEqual((root/name).read_bytes(),(SOURCE/name).read_bytes())


def main():
    global SOURCE
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True,type=Path)
    parser.add_argument('--upstream-source',type=Path,help='Also run ordinary-error regressions against unpatched source')
    args=parser.parse_args()
    spec=importlib.util.spec_from_file_location('patch_apply',ART/'apply.py');apply=importlib.util.module_from_spec(spec);spec.loader.exec_module(apply)
    SOURCE=args.source.resolve();apply.verify(SOURCE,patched=True)
    core()
    spec = importlib.util.spec_from_file_location('hindsight_api.engine.foreground_admission', SOURCE/'hindsight_api/engine/foreground_admission.py')
    admission = importlib.util.module_from_spec(spec);sys.modules[spec.name] = admission;spec.loader.exec_module(admission)
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(cls) for cls in
        (RetainTests,ConsolidationTests,BoundaryTests,OrdinaryRegressionTests,ArtifactTests))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful(): return 1
    if args.upstream_source:
        SOURCE=args.upstream_source.resolve();apply.verify(SOURCE)
        print('\nUnpatched ordinary-error regression comparison:',flush=True)
        result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(OrdinaryRegressionTests))
        if not result.wasSuccessful(): return 1
    return 0


if __name__=='__main__':
    sys.exit(main())
