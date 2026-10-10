"""Offline Production behavior equivalence and optional mixed Lab/Production protocol check."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import app.foreground_activity as activity
from app.conversation_runtime import process_turn
from app.foreground_registry import ForegroundRegistry, RegistryState
from app.model_client import ModelClientError

ROOT = Path(__file__).resolve().parents[1]
BASELINE = 'f453ed161994c8131bf8d9ed7c43cc15914176cf'


def fake_turn(fn, scenario):
    events = []
    def add(session_id, role, content):
        events.append(('persist', session_id, role, content))
        if scenario == 'persist_error' and role == 'assistant':
            raise RuntimeError('synthetic persistence failure')
        return 1 if role == 'user' else 2
    def generate(messages):
        events.append(('generate', messages))
        if scenario == 'model_error':
            raise ModelClientError('MODEL_FAILED', 'synthetic model failure')
        if scenario == 'unexpected_error':
            raise ValueError('synthetic unexpected model failure')
        return 'faithful reply'
    def dense(ids):
        events.append(('dense', ids))
        if scenario == 'dense_error':
            raise RuntimeError('synthetic dense failure')
    try:
        result = fn(session_id='offline-production', user_content='hello',
            add_message_fn=add, build_context_fn=lambda **kw: {
                'messages': [{'role': 'user', 'content': 'hello'}],
                'recent_message_ids': [], 'historical_message_ids': [],
                'input_tokens': 1, 'retrieval_status': 'OK', 'retrieval_error': None,
            }, count_tokens_fn=lambda messages: 1, generate_fn=generate,
            dense_sync_fn=dense, system_prompt_fn=lambda: 'SYS')
        return result, events, None
    except Exception as exc:
        return None, events, (type(exc), str(exc))


class ProductionCompatibilityTests(unittest.TestCase):
    def test_disabled_matches_original_production_results_events_and_exceptions(self):
        source = subprocess.check_output(
            ['git', 'show', BASELINE + ':app/conversation_runtime.py'], cwd=ROOT, text=True)
        original = {}
        exec(compile(source, '<original-production-conversation>', 'exec'), original)
        tracker = activity.ForegroundActivityTracker()
        with patch.object(activity, '_tracker', tracker):
            for scenario in ('success', 'model_error', 'unexpected_error', 'persist_error', 'dense_error'):
                with self.subTest(scenario=scenario):
                    self.assertEqual(fake_turn(process_turn, scenario),
                                     fake_turn(original['process_turn'], scenario))
                    self.assertEqual(tracker.snapshot().active_foreground_count, 0)
                    self.assertIsNone(tracker._publisher)

    def test_production_publication_failure_preserves_success_and_persistence(self):
        with TemporaryDirectory() as directory:
            tracker = activity.ForegroundActivityTracker(registry_path=directory,
                logical_publisher='production', expected_publishers=('lab', 'production'))
            reader = ForegroundRegistry(directory, expected_publishers=('lab', 'production'))
            self.addCleanup(tracker.close)
            with patch.object(activity, '_tracker', tracker), patch(
                'app.foreground_registry.ForegroundPublisher', side_effect=PermissionError('denied')):
                with self.assertLogs(activity.logger, level='ERROR'):
                    result, events, error = fake_turn(process_turn, 'success')
                self.assertEqual(result['reply'], 'faithful reply')
                self.assertEqual(result['persistence_status'], 'NORMAL')
                self.assertIsNone(error)
                self.assertEqual(len([e for e in events if e[0]=='persist']), 2)
                self.assertEqual(tracker.snapshot().active_foreground_count, 0)
                self.assertEqual(reader.read().state, RegistryState.UNKNOWN)

    @unittest.skipUnless(os.getenv('CORVUS_REFERENCE_LAB_ROOT'), 'optional offline Lab reference')
    def test_mixed_lab_and_production_processes_share_protocol_and_recover_crash(self):
        lab = Path(os.environ['CORVUS_REFERENCE_LAB_ROOT'])
        for name in ('app/foreground_registry.py', 'app/foreground_activity.py'):
            self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).digest(),
                             hashlib.sha256((lab/name).read_bytes()).digest())
        code = '''
import json,sys
sys.path.insert(0,sys.argv[1])
from app.foreground_activity import ForegroundActivityTracker
t=ForegroundActivityTracker(registry_path=sys.argv[2],logical_publisher="lab",expected_publishers=("lab","production"))
t.start()
print(t._publisher.identity,flush=True)
for command in sys.stdin:
    command=command.strip()
    if command=="begin":
        scope=t.generation();scope.__enter__()
    elif command=="finish":
        scope.__exit__(None,None,None)
    else:
        break
    print("ok",flush=True)
t.close()
'''
        with TemporaryDirectory() as directory:
            tracker=activity.ForegroundActivityTracker(registry_path=directory,
                logical_publisher='production', expected_publishers=('lab','production'))
            self.addCleanup(tracker.close)
            tracker.start()
            reader=ForegroundRegistry(directory,expected_publishers=('lab','production'))
            self.assertEqual(reader.read().state,RegistryState.UNKNOWN)
            def start():
                child=subprocess.Popen([sys.executable,'-B','-c',code,str(lab),directory],
                    stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
                self.addCleanup(lambda: child.poll() is None and child.kill())
                identity=child.stdout.readline().strip()
                self.assertTrue(identity,child.stderr.read() if child.poll() is not None else '')
                return child,identity
            def command(child,value):
                child.stdin.write(value+'\n');child.stdin.flush()
                self.assertEqual(child.stdout.readline().strip(),'ok')
            child,first=start()
            try:
                self.assertEqual(reader.read().state,RegistryState.IDLE)
                with tracker.generation():
                    command(child,'begin')
                    state=reader.read()
                    self.assertEqual((state.state,state.active_foreground_count),(RegistryState.BUSY,2))
                self.assertEqual(reader.read().active_foreground_count,1)
                command(child,'finish')
                self.assertEqual((reader.read().state,reader.read().active_foreground_count),(RegistryState.IDLE,0))
                command(child,'begin')
                child.kill();child.communicate(timeout=10)
                self.assertEqual(reader.read().state,RegistryState.UNKNOWN)
                child,second=start()
                self.assertNotEqual(first,second)
                self.assertEqual(reader.read().state,RegistryState.IDLE)
                child.stdin.write('stop\n');child.stdin.flush()
                child.communicate(timeout=10)
                self.assertEqual(child.returncode,0)
                self.assertEqual(reader.read().state,RegistryState.UNKNOWN)
            finally:
                if child.poll() is None:
                    child.kill();child.communicate(timeout=10)


if __name__ == '__main__':
    unittest.main()
