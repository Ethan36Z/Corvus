"""Integrated foreground conversation/publication without inference or /run."""

import asyncio
import fcntl
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Event
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import app.foreground_activity as activity
import app.foreground_registry as registry_core
from app.conversation_runtime import process_turn
from app.model_client import ModelClientError
from app.foreground_registry import ForegroundRegistry, RegistryState


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.now = [100.0]
        self.registry = ForegroundRegistry(self.path, clock=lambda: self.now[0], expected_publishers=("lab",))
        self.tracker = activity.ForegroundActivityTracker(
            clock=lambda: self.now[0], registry_path=self.path, logical_publisher="lab",
            expected_publishers=("lab",),
        )
        self.addCleanup(self.tracker.close)
        patcher = patch.object(activity, '_tracker', self.tracker)
        patcher.start()
        self.addCleanup(patcher.stop)

    def run_turn(self, generate, persisted=None):
        roles = persisted if persisted is not None else []
        def add(session_id, role, content):
            roles.append((role, content))
            return 1 if role == 'user' else 2
        return process_turn(
            session_id='publication-test', user_content='hello',
            add_message_fn=add,
            build_context_fn=lambda **kwargs: {
                'messages': [{'role': 'user', 'content': 'hello'}],
                'recent_message_ids': [], 'historical_message_ids': [],
                'input_tokens': 1, 'retrieval_status': 'OK', 'retrieval_error': None,
            },
            count_tokens_fn=lambda messages: 1,
            generate_fn=generate, dense_sync_fn=lambda ids: None,
            system_prompt_fn=lambda: 'SYS',
        )

    def assert_registry(self, state, count):
        snapshot = self.registry.read()
        self.assertEqual(snapshot.state, state, snapshot.reason)
        self.assertEqual(snapshot.active_foreground_count, count)
        return snapshot

    def test_disabled_does_not_initialize_registry_and_preserves_tracker(self):
        disabled = activity.ForegroundActivityTracker(clock=lambda: self.now[0])
        with patch.object(activity, '_tracker', disabled), patch.object(
            registry_core.ForegroundRegistry, 'initialize', side_effect=AssertionError('disabled IO'),
        ):
            activity.start_foreground_publication()
            def generate(messages):
                self.assertEqual(activity.snapshot().active_foreground_count, 1)
                return 'reply'
            self.assertEqual(self.run_turn(generate)['reply'], 'reply')
            activity.stop_foreground_publication()
            self.assertEqual(activity.snapshot().active_foreground_count, 0)
            self.assertEqual(activity.snapshot().last_foreground_finished_at, 100.0)
            # Disabled lifecycle shutdown does not change subsequent local use.
            self.assertEqual(self.run_turn(generate)['reply'], 'reply')
        self.assertEqual(list(self.path.iterdir()), [])

    def test_enabled_startup_idle_then_busy_before_model_and_idle_after(self):
        activity.start_foreground_publication()
        self.assert_registry(RegistryState.IDLE, 0)
        identity = self.tracker._publisher.identity
        inode = (self.path / (identity + '.busy')).stat().st_ino
        persisted = []
        def generate(messages):
            self.assert_registry(RegistryState.BUSY, 1)
            self.assertEqual(activity.snapshot().active_foreground_count, 1)
            self.now[0] = 101.0
            return 'reply'
        result = self.run_turn(generate, persisted)
        self.assertEqual(result['model_status'], 'OK')
        self.assertEqual(persisted, [('user', 'hello'), ('assistant', 'reply')])
        self.assertEqual(self.assert_registry(RegistryState.IDLE, 0).last_foreground_finished_at, 101.0)
        activity.start_foreground_publication()
        self.assertEqual(self.tracker._publisher.identity, identity)
        self.assertEqual((self.path / (identity + '.busy')).stat().st_ino, inode)

    def test_lazy_initialization_uses_the_same_conversation_seam(self):
        self.assertIsNone(self.tracker._publisher)
        def generate(messages):
            self.assert_registry(RegistryState.BUSY, 1)
            return 'reply'
        self.assertEqual(self.run_turn(generate)['reply'], 'reply')
        self.assert_registry(RegistryState.IDLE, 0)

    def test_initialization_before_registration_failure_keeps_api_and_chat_available(self):
        import app.playground_api as api
        self.registry.initialize()
        app = SimpleNamespace(state=SimpleNamespace())
        persisted = []
        def generate(messages):
            self.assertEqual(activity.snapshot().active_foreground_count, 1)
            self.assert_registry(RegistryState.UNKNOWN, None)
            return 'reply despite failed init'
        async def run():
            with patch.object(registry_core, 'ForegroundPublisher', side_effect=PermissionError('create denied')):
                with patch.object(api, 'prepare_runtime_startup', return_value={'status': 'OK'}) as prepare:
                    with self.assertLogs(activity.logger, level='ERROR'):
                        async with api.lifespan(app):
                            prepare.assert_called_once()
                            result = self.run_turn(generate, persisted)
                            self.assertEqual(result['reply'], 'reply despite failed init')
                            self.assertEqual(activity.snapshot().active_foreground_count, 0)
        asyncio.run(run())
        self.assertEqual(persisted, [('user', 'hello'), ('assistant', 'reply despite failed init')])
        self.assert_registry(RegistryState.UNKNOWN, None)

    def test_writer_only_permission_failure_does_not_leave_trustworthy_idle(self):
        self.registry.initialize()
        for path in self.path.iterdir():
            path.chmod(0o400)  # Reader can read; writer cannot initialize/acquire its guard.
        try:
            with self.assertLogs(activity.logger, level='ERROR'):
                self.tracker.start()
            self.assertEqual(self.run_turn(lambda messages: 'reply')['reply'], 'reply')
            self.assert_registry(RegistryState.UNKNOWN, None)
        finally:
            for path in self.path.iterdir():
                path.chmod(0o600)

    def test_busy_lock_and_fault_signaling_failures_still_allow_model_and_defer_background(self):
        self.tracker.start()
        publisher = self.tracker._publisher
        original = fcntl.flock
        def fail_busy(fd, flags):
            if fd == publisher._busy_fd and flags == (fcntl.LOCK_EX | fcntl.LOCK_NB):
                raise OSError('busy lock unavailable')
            return original(fd, flags)
        def generate(messages):
            self.assert_registry(RegistryState.UNKNOWN, None)
            self.assertEqual(activity.snapshot().active_foreground_count, 1)
            return 'safe foreground reply'
        with patch.object(registry_core.fcntl, 'flock', side_effect=fail_busy), patch.object(
            publisher, '_mark_fault', side_effect=OSError('fault signaling failed'),
        ):
            with self.assertLogs(activity.logger, level='ERROR'):
                self.assertEqual(self.run_turn(generate)['reply'], 'safe foreground reply')
        self.assertIsNone(publisher._health_fd)
        self.assertEqual(activity.snapshot().active_foreground_count, 0)
        self.assert_registry(RegistryState.UNKNOWN, None)

    def test_write_and_fault_signaling_failure_remain_unknown_during_model(self):
        self.tracker.start()
        def generate(messages):
            self.assert_registry(RegistryState.UNKNOWN, None)
            self.assertEqual(activity.snapshot().active_foreground_count, 1)
            return 'reply'
        with patch.object(registry_core, '_write', side_effect=OSError('disk full')), patch.object(
            self.tracker._publisher, '_mark_fault', side_effect=OSError('signal failed'),
        ):
            with self.assertLogs(activity.logger, level='ERROR'):
                self.assertEqual(self.run_turn(generate)['reply'], 'reply')
        self.assert_registry(RegistryState.UNKNOWN, None)

    def test_failed_publication_does_not_mask_foreground_model_error(self):
        self.tracker.start()
        def generate(messages):
            self.assert_registry(RegistryState.UNKNOWN, None)
            raise ModelClientError('MODEL_TIMEOUT', 'original error')
        with patch.object(registry_core, '_write', side_effect=OSError('disk full')):
            with self.assertLogs(activity.logger, level='ERROR'):
                result = self.run_turn(generate)
        self.assertEqual(result['model_status'], 'MODEL_TIMEOUT')
        self.assertEqual(result['error'], 'original error')
        self.assertEqual(activity.snapshot().active_foreground_count, 0)

    def test_invalid_optional_configuration_cannot_block_chat(self):
        for name in (None, 'INVALID NAME'):
            tracker = activity.ForegroundActivityTracker(
                registry_path=self.path, logical_publisher=name, expected_publishers=('lab',),
            )
            self.addCleanup(tracker.close)
            with patch.object(activity, '_tracker', tracker):
                with self.assertLogs(activity.logger, level='ERROR'):
                    self.assertEqual(self.run_turn(lambda messages: 'reply')['reply'], 'reply')
                self.assertEqual(activity.snapshot().active_foreground_count, 0)
                self.assert_registry(RegistryState.UNKNOWN, None)

    def test_restart_after_unpublished_foreground_applies_grace(self):
        with patch.object(registry_core, 'ForegroundPublisher', side_effect=OSError('init failed')):
            with self.assertLogs(activity.logger, level='ERROR'):
                self.assertEqual(self.run_turn(lambda messages: 'reply')['reply'], 'reply')
        self.tracker.close()
        self.now[0] = 101.0
        self.tracker.start()
        self.assertEqual(self.assert_registry(RegistryState.IDLE, 0).idle_grace_anchor, 101.0)

    def test_exception_paths_balance_both_local_and_registry_state(self):
        self.tracker.start()
        for error in (ModelClientError('MODEL_TIMEOUT', 'fake timeout'),
                      RuntimeError('fake generation failure'), KeyboardInterrupt()):
            with self.subTest(error=type(error)):
                def generate(messages):
                    self.assert_registry(RegistryState.BUSY, 1)
                    self.now[0] += 1
                    raise error
                if isinstance(error, ModelClientError):
                    result = self.run_turn(generate)
                    self.assertEqual(result['model_status'], 'MODEL_TIMEOUT')
                else:
                    with self.assertRaises(type(error)):
                        self.run_turn(generate)
                self.assertEqual(activity.snapshot().active_foreground_count, 0)
                self.assert_registry(RegistryState.IDLE, 0)

    def test_two_overlapping_conversation_calls_share_one_publisher(self):
        self.tracker.start()
        identity = self.tracker._publisher.identity
        entered, released = [Event(), Event()], [Event(), Event()]
        def generate(index):
            def fake(messages):
                entered[index].set()
                if not released[index].wait(5):
                    raise AssertionError('fake call not released')
                return 'reply'
            return fake
        with ThreadPoolExecutor(max_workers=2) as pool:
            try:
                first = pool.submit(self.run_turn, generate(0))
                self.assertTrue(entered[0].wait(5))
                self.assert_registry(RegistryState.BUSY, 1)
                second = pool.submit(self.run_turn, generate(1))
                self.assertTrue(entered[1].wait(5))
                self.assert_registry(RegistryState.BUSY, 2)
                self.now[0] = 101.0
                released[0].set()
                first.result(timeout=5)
                self.assertEqual(self.assert_registry(RegistryState.BUSY, 1).last_foreground_finished_at, 101.0)
                self.now[0] = 102.0
                released[1].set()
                second.result(timeout=5)
                self.assert_registry(RegistryState.IDLE, 0)
                self.assertEqual(self.tracker._publisher.identity, identity)
                self.assertEqual(len(list(self.path.glob('*.busy'))), 1)
            finally:
                for event in released:
                    event.set()

    def test_begin_publication_failure_preserves_foreground_and_persistence(self):
        self.tracker.start()
        roles = []
        with patch.object(registry_core, '_write', side_effect=OSError('disk full')):
            with self.assertLogs(activity.logger, level='ERROR') as logs:
                result = self.run_turn(lambda messages: 'reply', roles)
        self.assertEqual(result['model_status'], 'OK')
        self.assertEqual(roles, [('user', 'hello'), ('assistant', 'reply')])
        self.assertEqual(result['assistant_message_id'], 2)
        self.assertEqual(activity.snapshot().active_foreground_count, 0)
        self.assert_registry(RegistryState.UNKNOWN, None)
        self.assertIn('foreground continues', '\n'.join(logs.output))
        self.assertIn('disk full', '\n'.join(logs.output))
        # A poisoned publisher is retained; later foreground is still usable.
        again = self.run_turn(lambda messages: 'again')
        self.assertEqual(again['reply'], 'again')
        self.assert_registry(RegistryState.UNKNOWN, None)

    def test_completion_failure_keeps_successful_reply_and_unknown(self):
        self.tracker.start()
        roles = []
        def generate(messages):
            self.assert_registry(RegistryState.BUSY, 1)
            return 'valid reply'
        original = registry_core._write
        def fail_finish(directory, name, value):
            if value.get('active_count') == 0:
                raise OSError('disk full on completion')
            return original(directory, name, value)
        with patch.object(registry_core, '_write', side_effect=fail_finish):
            with self.assertLogs(activity.logger, level='ERROR'):
                result = self.run_turn(generate, roles)
        self.assertEqual(result['model_status'], 'OK')
        self.assertEqual(result['reply'], 'valid reply')
        self.assertEqual(roles, [('user', 'hello'), ('assistant', 'valid reply')])
        self.assertEqual(activity.snapshot().active_foreground_count, 0)
        self.assert_registry(RegistryState.UNKNOWN, None)

    def test_completion_failure_does_not_mask_original_generation_error(self):
        self.tracker.start()
        original = registry_core._write
        def fail_finish(directory, name, value):
            if value.get('active_count') == 0:
                raise OSError('completion failure')
            return original(directory, name, value)
        def generate(messages):
            raise ModelClientError('MODEL_TIMEOUT', 'original model failure')
        with patch.object(registry_core, '_write', side_effect=fail_finish):
            with self.assertLogs(activity.logger, level='ERROR'):
                result = self.run_turn(generate)
        self.assertEqual(result['model_status'], 'MODEL_TIMEOUT')
        self.assertEqual(result['error'], 'original model failure')
        self.assert_registry(RegistryState.UNKNOWN, None)

    def test_failed_overlapping_entry_preserves_the_existing_call(self):
        self.tracker.start()
        entered, released = Event(), Event()
        def generate(messages):
            entered.set()
            if not released.wait(5):
                raise AssertionError('existing call not released')
            return 'existing reply'
        def second_generate(messages):
            self.assertEqual(activity.snapshot().active_foreground_count, 2)
            self.assert_registry(RegistryState.UNKNOWN, None)
            return 'second reply'
        with ThreadPoolExecutor(max_workers=1) as pool:
            first = pool.submit(self.run_turn, generate)
            try:
                self.assertTrue(entered.wait(5))
                with patch.object(registry_core, '_write', side_effect=OSError('disk full')):
                    with self.assertLogs(activity.logger, level='ERROR'):
                        second = self.run_turn(second_generate)
                self.assertEqual(second['model_status'], 'OK')
                self.assertEqual(activity.snapshot().active_foreground_count, 1)
                self.assert_registry(RegistryState.UNKNOWN, None)
                released.set()
                self.assertEqual(first.result(timeout=5)['reply'], 'existing reply')
                self.assertEqual(activity.snapshot().active_foreground_count, 0)
                self.assert_registry(RegistryState.UNKNOWN, None)
            finally:
                released.set()

    def test_interrupted_begin_publication_balances_count_and_reports_unknown(self):
        self.tracker.start()
        with patch.object(registry_core, '_write', side_effect=KeyboardInterrupt()):
            with self.assertLogs(activity.logger, level='ERROR'):
                with self.assertRaises(KeyboardInterrupt):
                    self.run_turn(lambda messages: self.fail('model must not run'))
        self.assertEqual(activity.snapshot().active_foreground_count, 0)
        self.assert_registry(RegistryState.UNKNOWN, None)

    def test_integrated_reader_permission_failure_is_unknown(self):
        self.tracker.start()
        def generate(messages):
            self.assert_registry(RegistryState.BUSY, 1)
            with patch.object(self.registry, '_directory', side_effect=PermissionError('denied')):
                self.assert_registry(RegistryState.UNKNOWN, None)
            return 'reply'
        self.assertEqual(self.run_turn(generate)['reply'], 'reply')
        self.assert_registry(RegistryState.IDLE, 0)

    def test_unknown_read_or_missing_directory_preserves_foreground(self):
        self.registry.initialize()
        (self.path / 'unexpected').write_text('malformed registry')
        result = self.run_turn(lambda messages: 'reply')
        self.assertEqual(result['model_status'], 'OK')
        self.assert_registry(RegistryState.UNKNOWN, None)
        missing = self.path / 'not-provisioned'
        tracker = activity.ForegroundActivityTracker(registry_path=missing)
        with self.assertLogs(activity.logger, level='ERROR'):
            tracker.start()
        with tracker.generation():
            self.assertEqual(tracker.snapshot().active_foreground_count, 1)
        self.assertFalse(missing.exists())

    def test_shutdown_retains_busy_until_final_completion(self):
        self.tracker.start()
        scope = self.tracker.generation()
        scope.__enter__()
        with self.assertLogs(activity.logger, level='WARNING'):
            self.tracker.close()
        self.assert_registry(RegistryState.BUSY, 1)
        with self.assertRaises(activity.ForegroundPublicationError):
            with self.tracker.generation():
                self.fail('shutting down')
        scope.__exit__(None, None, None)
        self.assert_registry(RegistryState.UNKNOWN, None)
        self.assertIsNone(self.tracker._publisher)

    def test_explicit_lifecycle_restart_gets_fresh_identity_and_preserves_watermark(self):
        self.tracker.start()
        identity = self.tracker._publisher.identity
        self.run_turn(lambda messages: 'reply')
        self.tracker.close()
        self.tracker.start()
        self.assertNotEqual(self.tracker._publisher.identity, identity)
        self.assertEqual(self.assert_registry(RegistryState.IDLE, 0).last_foreground_finished_at, 100.0)

    def test_api_lifespan_starts_before_canonical_preparation_and_closes(self):
        import app.playground_api as api
        app = SimpleNamespace(state=SimpleNamespace())
        def prepare():
            self.assert_registry(RegistryState.IDLE, 0)
            return {'status': 'OK'}
        async def run():
            with patch.object(api, 'prepare_runtime_startup', side_effect=prepare):
                async with api.lifespan(app):
                    self.assertIsNotNone(self.tracker._publisher)
                    self.assertEqual(app.state.startup_recovery, {'status': 'OK'})
            self.assertIsNone(self.tracker._publisher)
        asyncio.run(run())

    def test_api_startup_failure_closes_publisher_and_registry_failure_allows_preparation(self):
        import app.playground_api as api
        app = SimpleNamespace(state=SimpleNamespace())
        async def run():
            with patch.object(api, 'prepare_runtime_startup', side_effect=RuntimeError('startup failed')):
                with self.assertRaises(RuntimeError):
                    async with api.lifespan(app):
                        self.fail('startup did not fail')
            self.assertIsNone(self.tracker._publisher)
            (self.path / 'unexpected').write_text('bad state')
            with patch.object(api, 'prepare_runtime_startup') as prepare:
                async with api.lifespan(app):
                    self.assert_registry(RegistryState.UNKNOWN, None)
                prepare.assert_called_once()
        asyncio.run(run())

    def test_actual_environment_configuration_and_process_restart(self):
        code = '''
import json
import app.foreground_activity as activity
from app.foreground_registry import ForegroundRegistry
from app.runtime_config import FOREGROUND_REGISTRY_DIR
activity.start_foreground_publication()
p = activity._tracker._publisher
result = {"path": FOREGROUND_REGISTRY_DIR, "identity": p.identity if p else None}
if p:
    result["state"] = ForegroundRegistry(FOREGROUND_REGISTRY_DIR, expected_publishers=("lab",)).read().state.value
activity.stop_foreground_publication()
print(json.dumps(result))
'''
        def run(value):
            env = dict(os.environ, CORVUS_FOREGROUND_REGISTRY_PUBLISHER='lab',
                       CORVUS_FOREGROUND_REGISTRY_EXPECTED_PUBLISHERS='lab')
            env.pop('CORVUS_FOREGROUND_REGISTRY_DIR', None)
            if value is not None:
                env['CORVUS_FOREGROUND_REGISTRY_DIR'] = value
            result = subprocess.run([sys.executable, '-B', '-c', code], env=env,
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout)
        for disabled in (None, '', '  '):
            self.assertEqual(run(disabled), {'path': None, 'identity': None})
        first, second = run(str(self.path)), run(str(self.path))
        self.assertEqual(first['state'], 'IDLE')
        self.assertEqual(second['path'], str(self.path))
        self.assertNotEqual(first['identity'], second['identity'])

    def test_fork_gets_fresh_tracker_and_publisher_without_unlocking_parent(self):
        code = '''
import os
import app.foreground_activity as activity
from app.foreground_registry import ForegroundRegistry, RegistryState
from app.runtime_config import FOREGROUND_REGISTRY_DIR
activity.start_foreground_publication()
reader = ForegroundRegistry(FOREGROUND_REGISTRY_DIR, expected_publishers=("lab",))
up_r, up_w = os.pipe()
down_r, down_w = os.pipe()
with activity.track_foreground_generation():
    original_identity = activity._tracker._publisher.identity
    pid = os.fork()
    if pid == 0:
        os.close(up_r)
        os.close(down_w)
        try:
            assert activity.snapshot().active_foreground_count == 0
            activity._tracker._logical_publisher = "child"
            activity.start_foreground_publication()
            assert activity._tracker._publisher.identity != original_identity
            with activity.track_foreground_generation():
                os.write(up_w, b'B')
                assert os.read(down_r, 1) == b'F'
            activity.stop_foreground_publication()
            os.write(up_w, b'D')
            os._exit(0)
        except BaseException:
            import traceback
            traceback.print_exc()
            os._exit(1)
    os.close(up_w)
    os.close(down_r)
    assert os.read(up_r, 1) == b'B'
    reader.expected_publishers = frozenset(("lab", "child"))
    assert reader.read().active_foreground_count == 2
    os.write(down_w, b'F')
    assert os.read(up_r, 1) == b'D'
    assert reader.read().state == RegistryState.UNKNOWN
    reader.expected_publishers = frozenset(("lab",))
    assert reader.read().active_foreground_count == 1
    assert os.waitpid(pid, 0)[1] == 0
    os.close(up_r)
    os.close(down_w)
assert reader.read().state == RegistryState.IDLE
activity.stop_foreground_publication()
print('fork integration passed')
'''
        with TemporaryDirectory() as path:
            env = dict(os.environ, CORVUS_FOREGROUND_REGISTRY_DIR=path,
                       CORVUS_FOREGROUND_REGISTRY_PUBLISHER="lab",
                       CORVUS_FOREGROUND_REGISTRY_EXPECTED_PUBLISHERS="lab")
            result = subprocess.run([sys.executable, '-B', '-c', code], env=env,
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('fork integration passed', result.stdout)


if __name__ == '__main__':
    unittest.main()
