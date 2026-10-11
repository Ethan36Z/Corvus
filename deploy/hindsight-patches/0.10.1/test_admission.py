"""Offline registry-v2 interoperability and actual wrapper/provider gate checks."""
import argparse
import asyncio
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import selectors
import subprocess
import sys
from tempfile import TemporaryDirectory
import types
import unittest
from unittest.mock import AsyncMock, Mock, patch

ART = Path(__file__).resolve().parent
REPO = ART.parents[2]
sys.path.insert(0, str(REPO))
# Test-only protocol producer; the introduced Hindsight module never imports app.
from app.foreground_registry import ForegroundPublisher, ForegroundRegistry
h = None
ad = None


def snapshot(path):
    return {p.name:(p.stat().st_ino,hashlib.sha256(p.read_bytes()).hexdigest()) for p in path.iterdir()}


class RegistryFixture:
    def setup_registry(self):
        self.temp=TemporaryDirectory(prefix='corvus-hindsight-reader-')
        self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name);self.now=[100.0]
        self.registry=ForegroundRegistry(self.path,clock=lambda:self.now[0],expected_publishers=('lab','production'))
        self.registry.initialize();self.publishers={}
        for name in ('lab','production'): self.publisher(name)
        self.reader=ad.ForegroundRegistryReader(self.path,clock=lambda:self.now[0])

    def publisher(self,name):
        p=ForegroundPublisher(self.registry,logical_publisher=name)
        p.publish(0,70.0);self.publishers[name]=p;self.addCleanup(p.close)
        return p

    def admitted(self):
        self.assertEqual(self.reader.read(),ad.RegistryState.UNKNOWN)
        self.now[0]=131.0
        self.assertEqual(self.reader.read(),ad.RegistryState.IDLE)

    def corrupt(self,name='production',**changes):
        file=self.path/(self.publishers[name].identity+'.json')
        data=json.loads(file.read_text());data.update(changes);file.write_text(json.dumps(data))


class ReaderTests(RegistryFixture,unittest.TestCase):
    def setUp(self): self.setup_registry()

    def test_healthy_pair_recovery_grace_and_old_finish(self): self.admitted()

    def test_either_publisher_busy_and_overlap(self):
        self.admitted()
        for name in ('lab','production'):
            p=self.publishers[name];p.publish(2,70.0)
            self.assertEqual(self.reader.read(),ad.RegistryState.BUSY)
            p.publish(1,self.now[0]);self.assertEqual(self.reader.read(),ad.RegistryState.BUSY)
            p.publish(0,self.now[0]);self.assertEqual(self.reader.read(),ad.RegistryState.UNKNOWN)
            self.now[0]+=31;self.assertEqual(self.reader.read(),ad.RegistryState.IDLE)

    def test_missing_either_expected_slot_stale_history_cannot_satisfy_health(self):
        for name in ('lab','production'):
            with self.subTest(name=name):
                self.publishers[name].close()
                self.assertEqual(self.reader.read(),ad.RegistryState.UNKNOWN)
                self.now[0]+=100;self.assertEqual(self.reader.read(),ad.RegistryState.UNKNOWN)
                self.publisher(name)
                self.assertEqual(self.reader.read(),ad.RegistryState.UNKNOWN)
                self.now[0]+=31;self.assertEqual(self.reader.read(),ad.RegistryState.IDLE)

    def test_malformed_and_unreadable_metadata(self):
        file=self.path/(self.publishers['lab'].identity+'.json');old=file.read_bytes()
        for data in (b'{',b'[]',b'{"identity":1,"identity":2}',b'x'*65537):
            file.write_bytes(data);self.assertEqual(self.reader.read(),ad.RegistryState.UNKNOWN)
        file.write_bytes(old)
        with patch.object(ad,'_load',side_effect=PermissionError('denied')):
            self.assertEqual(self.reader.read(),ad.RegistryState.UNKNOWN)
        file.chmod(0)
        if os.geteuid()!=0: self.assertEqual(self.reader.read(),ad.RegistryState.UNKNOWN)
        file.chmod(0o600)
        self.assertEqual(self.reader.read(),ad.RegistryState.UNKNOWN)
        self.now[0]+=31;self.assertEqual(self.reader.read(),ad.RegistryState.IDLE)

    def test_missing_directory(self):
        self.assertEqual(ad.ForegroundRegistryReader(self.path/'missing').read(),ad.RegistryState.UNKNOWN)

    def test_pid_start_identity_and_inode_mismatch(self):
        path=self.path/(self.publishers['lab'].identity+'.json');original=path.read_bytes()
        for fields in ({'pid':123},{'start_ticks':0},{'identity':'wrong'}, {'live_inode':[0,0]}, {'health_inode':[0,0]}):
            self.corrupt('lab',**fields);self.assertEqual(self.reader.read(),ad.RegistryState.UNKNOWN);path.write_bytes(original)

    def test_protocol_boot_and_time_domain_mismatch(self):
        path=self.path/'registry.json';old=path.read_bytes();original=json.loads(old)
        for change in ({'version':1},{'version':True},{'clock_domain':{'boot_id':'wrong','time_offsets':'wrong'}}, {'lock_inode':[0,0]}):
            path.write_text(json.dumps(dict(original,**change)))
            self.assertEqual(self.reader.read(),ad.RegistryState.UNKNOWN)
        path.write_bytes(old)

    def test_inconsistent_busy_metadata_is_unknown(self):
        self.corrupt(active_count=1)
        self.assertEqual(self.reader.read(),ad.RegistryState.UNKNOWN)
        self.publishers['production'].publish(1,70)
        self.corrupt(active_count=0)
        self.assertEqual(self.reader.read(),ad.RegistryState.UNKNOWN)

    def test_degradation_health_and_fault_failure_unknown(self):
        p=self.publishers['production']
        with patch.object(p,'_mark_fault',side_effect=OSError('fault failed')): p.degrade()
        self.assertEqual(self.reader.read(),ad.RegistryState.UNKNOWN)

    def test_finished_inside_grace_boundary_then_elapsed(self):
        self.admitted();self.publishers['lab'].publish(1,70);self.publishers['lab'].publish(0,131)
        self.assertEqual(self.reader.read(),ad.RegistryState.UNKNOWN)
        self.now[0]=161;self.assertEqual(self.reader.read(),ad.RegistryState.UNKNOWN)
        self.now[0]=161.01;self.assertEqual(self.reader.read(),ad.RegistryState.IDLE)

    def test_reader_restart_new_identity_and_unknown_recovery_require_new_grace(self):
        self.admitted();self.reader=ad.ForegroundRegistryReader(self.path,clock=lambda:self.now[0])
        self.assertEqual(self.reader.read(),ad.RegistryState.UNKNOWN)
        self.now[0]+=31;self.assertEqual(self.reader.read(),ad.RegistryState.IDLE)
        self.publishers['production'].close();self.publisher('production')
        self.assertEqual(self.reader.read(),ad.RegistryState.UNKNOWN)
        self.now[0]+=31;self.assertEqual(self.reader.read(),ad.RegistryState.IDLE)
        with patch.object(ad,'_load',side_effect=OSError('transient')):
            self.assertEqual(self.reader.read(),ad.RegistryState.UNKNOWN)
        self.assertEqual(self.reader.read(),ad.RegistryState.UNKNOWN)
        self.now[0]+=31;self.assertEqual(self.reader.read(),ad.RegistryState.IDLE)

    def test_missing_initial_completion_never_fabricated(self):
        for name in self.publishers: self.corrupt(name,last_finished=None)
        self.assertEqual(self.reader.read(),ad.RegistryState.UNKNOWN)
        self.now[0]+=100;self.assertEqual(self.reader.read(),ad.RegistryState.UNKNOWN)

    def test_future_regressing_watermark_unknown(self):
        self.corrupt(last_finished=101);self.assertEqual(self.reader.read(),ad.RegistryState.UNKNOWN)
        self.corrupt(last_finished=70);self.reader.read();self.corrupt(last_finished=69)
        self.assertEqual(self.reader.read(),ad.RegistryState.UNKNOWN)

    def test_orphan_symlink_duplicate_logical_untrusted(self):
        extra=self.path/'extra';extra.write_text('x');self.assertEqual(self.reader.read(),ad.RegistryState.UNKNOWN);extra.unlink()
        self.publisher('extra');self.corrupt('extra',logical_publisher='lab')
        self.assertEqual(self.reader.read(),ad.RegistryState.UNKNOWN)
        record=self.path/(self.publishers['production'].identity+'.json');data=record.read_bytes();record.unlink()
        target=self.path/'hidden';target.write_bytes(data);record.symlink_to(target)
        self.assertEqual(self.reader.read(),ad.RegistryState.UNKNOWN)

    def test_reader_uses_only_readonly_nonblocking_cloexec_files_and_no_mutation(self):
        before=snapshot(self.path);original=ad.os.open;opens=[]
        def open_file(name,flags,*a,**k):
            opens.append(flags);return original(name,flags,*a,**k)
        with patch.object(ad.os,'open',side_effect=open_file): self.admitted()
        self.assertEqual(snapshot(self.path),before)
        for flags in opens:
            self.assertEqual(flags&os.O_ACCMODE,os.O_RDONLY)
            self.assertFalse(flags&(os.O_CREAT|os.O_TRUNC|os.O_APPEND))
            self.assertTrue(flags&os.O_CLOEXEC);self.assertTrue(flags&os.O_NONBLOCK)

    def test_untrusted_writable_permissions_unknown(self):
        self.admitted();self.path.chmod(0o777)
        self.assertEqual(self.reader.read(),ad.RegistryState.UNKNOWN);self.path.chmod(0o700)
        file=self.path/'registry.json';file.chmod(0o666)
        self.assertEqual(self.reader.read(),ad.RegistryState.UNKNOWN);file.chmod(0o600)

    def test_clock_or_inherited_process_mismatch_unknown(self):
        self.admitted();self.now[0]=1;self.assertEqual(self.reader.read(),ad.RegistryState.UNKNOWN)
        self.reader.pid=-1;self.assertEqual(self.reader.read(),ad.RegistryState.UNKNOWN)

    def test_crashed_process_lock_release_and_replacement_grace(self):
        self.publishers['production'].close()
        code='''import sys,time
from app.foreground_registry import ForegroundRegistry,ForegroundPublisher
r=ForegroundRegistry(sys.argv[1],clock=lambda:100)
p=ForegroundPublisher(r,logical_publisher="production");p.publish(1,70)
print(p.identity,flush=True)
time.sleep(30)
'''
        process=subprocess.Popen([sys.executable,'-B','-c',code,str(self.path)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,cwd=REPO)
        def close():
            if process.poll() is None: process.kill()
            process.communicate(timeout=5)
        self.addCleanup(close)
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout,selectors.EVENT_READ);self.assertTrue(selector.select(5))
        identity=process.stdout.readline().strip();self.assertTrue(identity)
        self.assertEqual(self.reader.read(),ad.RegistryState.BUSY)
        process.kill();process.wait(timeout=5)
        self.assertEqual(self.reader.read(),ad.RegistryState.UNKNOWN)
        self.now[0]+=100;self.assertEqual(self.reader.read(),ad.RegistryState.UNKNOWN)
        self.publisher('production');self.assertEqual(self.reader.read(),ad.RegistryState.UNKNOWN)
        self.now[0]+=31;self.assertEqual(self.reader.read(),ad.RegistryState.IDLE)


class GateTests(RegistryFixture,unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.setup_registry();ad._reader_cache=None
        env={'CORVUS_FOREGROUND_REGISTRY_DIR':str(self.path),'CORVUS_FOREGROUND_EXPECTED_PUBLISHERS':'lab,production',
             'CORVUS_FOREGROUND_IDLE_GRACE_SECONDS':'30'}
        p=patch.dict(os.environ,env,clear=True);p.start();self.addCleanup(p.stop)
        original=ad.ForegroundRegistryReader
        p=patch.object(ad,'ForegroundRegistryReader',side_effect=lambda *a,**k:original(*a,**k,clock=lambda:self.now[0]));p.start();self.addCleanup(p.stop)
        self.ns=h.core();self.ns['DeferOperation']=ad.DeferOperation
        h.load('engine/llm_wrapper.py',['_acquire_permits','_attempt_permits','_request_params','LLMProvider.call'],self.ns)
        self.permits=[asyncio.Semaphore(1),asyncio.Semaphore(1)]
        self.ns['_semaphores_for_scope']=lambda scope:self.permits
        self.sender=AsyncMock(return_value=types.SimpleNamespace(content={'facts':[]},usage=h.Usage()))
        self.ns['sanitize_value']=lambda x:x
        async def provider_call(attempt_context,**kwargs):
            async with attempt_context():
                self.assertTrue(all(x.locked() for x in self.permits));return await self.sender(**kwargs)
        provider=types.SimpleNamespace(supports_attempt_scoped_concurrency=lambda:True,supports_prompt_caching=lambda:False,call=provider_call)
        self.wrapper=types.SimpleNamespace(provider='llamacpp',model='fake',max_retries=2,initial_backoff=0,max_backoff=0,_provider_impl=provider)
        self.wrapper.call=types.MethodType(self.ns['call'],self.wrapper)

    def prime(self):
        with self.assertRaises(ad.DeferOperation): ad.check_foreground_admission()
        self.now[0]=131;ad.check_foreground_admission()

    async def call(self):
        return await self.wrapper.call(messages=[{'role':'user','content':'frozen'}],scope='retain_extract_facts',response_format=dict,strict_schema=True)

    def assert_released(self): self.assertTrue(all(not s.locked() for s in self.permits))

    async def test_idle_allows_provider_after_permits(self):
        self.prime();await self.call();self.sender.assert_awaited_once();self.assert_released()

    async def test_busy_unknown_and_grace_defer_before_send_and_release(self):
        with self.assertRaises(ad.DeferOperation): await self.call()
        self.sender.assert_not_awaited();self.assert_released()
        self.prime();self.publishers['lab'].publish(1,70)
        with self.assertRaisesRegex(ad.DeferOperation,'BUSY'): await self.call()
        self.sender.assert_not_awaited();self.assert_released()
        self.publishers['lab'].publish(0,131)
        with self.assertRaisesRegex(ad.DeferOperation,'UNKNOWN'): await self.call()
        self.now[0]=162;await self.call();self.sender.assert_awaited_once()
        self.sender.reset_mock();self.publishers['production'].degrade()
        with self.assertRaisesRegex(ad.DeferOperation,'UNKNOWN'): await self.call()
        self.sender.assert_not_awaited();self.assert_released()

    async def test_absent_config_disabled_no_registry_io(self):
        with patch.dict(os.environ,{},clear=True),patch.object(ad,'ForegroundRegistryReader',side_effect=AssertionError('reader must not initialize')):
            await self.call()
        self.sender.assert_awaited_once();self.assert_released()

    async def test_invalid_configuration_fails_closed(self):
        for grace in ('-1','0','nan','bad'):
            with patch.dict(os.environ,{'CORVUS_FOREGROUND_IDLE_GRACE_SECONDS':grace}):
                with self.assertRaises(ad.DeferOperation): await self.call()
        with patch.dict(os.environ,{'CORVUS_FOREGROUND_EXPECTED_PUBLISHERS':''}):
            with self.assertRaises(ad.DeferOperation): await self.call()
        self.sender.assert_not_awaited();self.assert_released()

    async def test_ordinary_provider_exception_identity_unchanged(self):
        self.prime();error=RuntimeError('ordinary');self.sender.side_effect=error
        with self.assertRaises(RuntimeError) as caught: await self.call()
        self.assertIs(caught.exception,error);self.sender.assert_awaited_once();self.assert_released()

    async def test_retain_and_consolidation_defer_not_model_failure(self):
        ns=h.extraction();ns['DeferOperation']=ad.DeferOperation
        with self.assertRaises(ad.DeferOperation):
            await ns['extract_facts_from_text']('exact',None,self.wrapper,ns['config'])
        ns=h.consolidation();ns['DeferOperation']=ad.DeferOperation
        with self.assertRaises(ad.DeferOperation):
            await ns['_consolidate_batch_with_llm'](self.wrapper,[{'id':'one','text':'source'}],[],{},ns['config'])
        self.assertEqual(ns['metrics'].failures,[]);self.sender.assert_not_awaited();self.assert_released()

    async def test_non_attempt_scoped_provider_never_bypasses_configured_gate(self):
        self.prime();self.wrapper._provider_impl.supports_attempt_scoped_concurrency=lambda:False
        self.wrapper._provider_impl.call=AsyncMock()
        with self.assertRaises(ad.DeferOperation): await self.call()
        self.wrapper._provider_impl.call.assert_not_awaited();self.assert_released()
        with patch.dict(os.environ,{},clear=True): await self.call()
        self.wrapper._provider_impl.call.assert_awaited_once()

    async def test_defer_not_recorded_as_failed_model_call(self):
        recorder=types.SimpleNamespace(record_llm_call=Mock())
        with patch.object(sys.modules['hindsight_api.tracing'],'get_span_recorder',return_value=recorder):
            with self.assertRaises(ad.DeferOperation): await self.call()
        recorder.record_llm_call.assert_not_called();self.assert_released()

    async def test_generic_tool_wrapper_uses_same_gate_without_reflect(self):
        auto = object()
        self.ns['LLMToolChoiceMode'] = types.SimpleNamespace(AUTO=auto)
        self.ns['LLM_TOOL_CHOICE_AUTO'] = types.SimpleNamespace(mode=auto, function_name=None)
        h.load('engine/llm_wrapper.py',['LLMProvider.call_with_tools'],self.ns)
        self.wrapper._provider_impl.call_with_tools=self.wrapper._provider_impl.call
        call=lambda:self.ns['call_with_tools'](self.wrapper,messages=[{'role':'user','content':'fake'}],tools=[])
        with self.assertRaises(ad.DeferOperation): await call()
        self.sender.assert_not_awaited();self.assert_released()
        with patch.dict(os.environ,{},clear=True): await call()
        self.sender.assert_awaited_once();self.assert_released()

    async def test_real_openai_provider_retries_errors_and_checks_each_attempt(self):
        provider_ns=h.namespace('hindsight_api.engine.providers')
        for name in ('LengthFinishReasonError','APIConnectionError','APIStatusError','ProviderResponseError'):
            provider_ns[name]=type(name,(Exception,),{})
        provider_ns.update(apply_bank_attribution=h.noop,apply_cache_affinity=h.noop,apply_opencode_session=h.noop,
            _ensure_json_word_in_user_message=lambda x:x,describe_transport_error=str,set_stage=h.noop)
        h.load('engine/providers/openai_compatible_llm.py',['call'],provider_ns)
        sdk_send=AsyncMock();error=provider_ns['APIConnectionError']('transport')
        p=types.SimpleNamespace(provider='llamacpp',model='fake',base_url='http://offline.invalid',ollama_num_ctx=None,
            _config_extra_body={},_cache_affinity=None,_client=types.SimpleNamespace(chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=sdk_send))),
            _supports_reasoning_model=lambda:False,_sends_reasoning_effort=lambda:False,_apply_provider_extra_body_defaults=h.noop,
            supports_attempt_scoped_concurrency=lambda:True)
        p.call=types.MethodType(provider_ns['call'],p);self.wrapper._provider_impl=p
        self.prime();sdk_send.side_effect=error
        with self.assertRaises(provider_ns['APIConnectionError']) as caught: await self.call()
        self.assertIs(caught.exception,error);self.assertEqual(sdk_send.await_count,3);self.assert_released()
        sdk_send.reset_mock()
        async def send(**kwargs):
            self.publishers['lab'].publish(1,70);raise error
        sdk_send.side_effect=send
        with self.assertRaises(ad.DeferOperation): await self.call()
        self.assertEqual(sdk_send.await_count,1);self.assert_released() # retry 2 gated before SDK send


def main():
    global h,ad
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source',required=True,type=Path);args=parser.parse_args()
    spec=importlib.util.spec_from_file_location('control_harness',ART/'test_control_flow.py');h=importlib.util.module_from_spec(spec);sys.modules[spec.name]=h;spec.loader.exec_module(h)
    h.SOURCE=args.source.resolve()
    spec=importlib.util.spec_from_file_location('patch_apply',ART/'apply.py');apply=importlib.util.module_from_spec(spec);spec.loader.exec_module(apply);apply.verify(h.SOURCE,patched=True)
    manifest=json.loads((ART/'manifest.json').read_text())
    assert hashlib.sha256((REPO/'app/foreground_registry.py').read_bytes()).hexdigest()==manifest['registry_protocol']['corvus_source_sha256']
    h.core()
    spec=importlib.util.spec_from_file_location('hindsight_api.engine.foreground_admission',h.SOURCE/'hindsight_api/engine/foreground_admission.py');ad=importlib.util.module_from_spec(spec);sys.modules[spec.name]=ad;spec.loader.exec_module(ad)
    spec=importlib.util.spec_from_file_location('hindsight_api.engine.consolidation_budget',h.SOURCE/'hindsight_api/engine/consolidation_budget.py')
    budget=importlib.util.module_from_spec(spec);sys.modules[spec.name]=budget;spec.loader.exec_module(budget)
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(c) for c in (ReaderTests,GateTests))
    return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1


if __name__=='__main__': sys.exit(main())
