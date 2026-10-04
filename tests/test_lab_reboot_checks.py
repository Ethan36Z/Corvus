"""Acceptance regressions; no live services, baselines, or sign-ins."""
import copy
import importlib.util
import itertools
from pathlib import Path
import unittest
from unittest.mock import patch

from test_dense_bootstrap import DenseFixture
import memory.dense_index as dense

ROOT = Path(__file__).resolve().parents[1]


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'deploy/lab' / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


checker = load('lab_reboot_check', 'check_reboot_acceptance.py')
readiness = load('lab_dense_check', 'check_dense_readiness.py')


class DenseReadinessTests(DenseFixture):
    def verify(self):
        return readiness.verify_dense_state(self.db_path, self.lance_path)

    def test_cached_ok_cannot_mask_missing_table(self):
        self.messages(1)
        dense.ensure_dense_progress_table()
        self.lance_path.mkdir()
        with self.assertRaises(ValueError):
            self.verify()

    def test_empty_bootstrapped_state_is_ready(self):
        dense.sync_dense_tail_once()
        self.assertEqual(self.verify()['canonical_messages'], 0)

    def test_caught_up_state_is_ready_and_verification_is_read_only(self):
        self.messages(2)
        dense.sync_dense_tail_once()
        before = self.db_path.read_bytes(), self.files()
        result = self.verify()
        self.assertTrue(result['caught_up'])
        self.assertEqual(result['progress_after'], 2)
        self.assertEqual((self.db_path.read_bytes(), self.files()), before)

    def test_progress_ahead_of_rows_is_rejected(self):
        self.messages(2)
        dense.ensure_dense_table()
        dense.set_dense_progress(2)
        with self.assertRaisesRegex(RuntimeError, 'exactly cover'):
            self.verify()

    def test_complete_rows_but_lagging_progress_are_rejected(self):
        self.messages(2)
        dense.sync_dense_message_ids([1, 2])
        dense.ensure_dense_progress_table()
        with self.assertRaisesRegex(RuntimeError, 'not caught up'):
            self.verify()

    def test_stale_metadata_is_rejected(self):
        self.messages(1)
        dense.sync_dense_tail_once()
        self.table().update(where='message_id = 1', values={'embedding_revision': 'wrong'})
        with self.assertRaisesRegex(RuntimeError, 'metadata differs'):
            self.verify()

    def test_missing_directory_is_rejected_without_creating_it(self):
        with self.assertRaisesRegex(RuntimeError, 'directory is missing'):
            self.verify()
        self.assertFalse(self.lance_path.exists())

    def test_sqlite_sidecars_are_rejected_without_reading_them(self):
        dense.sync_dense_tail_once()
        sidecar = Path(str(self.db_path) + '-wal')
        sidecar.write_bytes(b'sentinel')
        with self.assertRaisesRegex(RuntimeError, 'sidecars'):
            self.verify()
        self.assertEqual(sidecar.read_bytes(), b'sentinel')

    def test_snapshot_checks_persistent_state_even_if_http_health_is_ok(self):
        with patch.object(checker, 'health'), patch.object(
                checker, 'verify_dense_readiness', side_effect=RuntimeError('missing dense table')), patch.object(
                checker, 'unit') as unit:
            with self.assertRaisesRegex(RuntimeError, 'missing dense table'):
                checker.snapshot(180)
            unit.assert_not_called()


class HostConfigTests(unittest.TestCase):
    def setUp(self):
        self.host = {
            'Dns': None, 'DnsOptions': None, 'DnsSearch': None,
            'RestartPolicy': {'Name': 'unless-stopped', 'MaximumRetryCount': 0},
            'NetworkMode': 'host', 'Binds': ['volume:/app/backend/data:rw'],
            'SecurityOpt': ['no-new-privileges:true'], 'CapDrop': ['ALL'],
            'CapAdd': None, 'PortBindings': {}, 'CgroupParent': '',
            'Privileged': False,
        }

    def matches(self, host, baseline=None, **changed):
        expected = {'Id': 'same', 'Image': 'same', 'Mounts': ['same'],
                    'restart': 'unless-stopped', 'environment_sha256': 'same',
                    'host_config_sha256': checker.digest(self.host if baseline is None else baseline)}
        current = dict(expected, host_config_sha256=checker.digest(host), **changed)
        return checker.containers_match(
            {'webui': current}, {'webui': expected},
            {'webui': checker.compatible_host_config_hashes(host)},
        )

    def test_all_null_empty_dns_representations_match_legacy_hash(self):
        original = copy.deepcopy(self.host)
        for values in itertools.product((None, []), repeat=3):
            host = copy.deepcopy(self.host)
            host.update(zip(('Dns', 'DnsOptions', 'DnsSearch'), values))
            with self.subTest(values=values):
                self.assertTrue(self.matches(host))
                self.assertTrue(self.matches(self.host, baseline=host))
        self.assertEqual(self.host, original)

    def test_substantive_host_changes_remain_strict(self):
        mutations = {
            'RestartPolicy': {'Name': 'no', 'MaximumRetryCount': 0},
            'NetworkMode': 'bridge', 'Binds': ['other:/app/backend/data:rw'],
            'SecurityOpt': [], 'CapDrop': [], 'CapAdd': ['SYS_ADMIN'],
            'PortBindings': {'3003/tcp': [{'HostIp': '0.0.0.0', 'HostPort': '3003'}]},
            'CgroupParent': 'custom', 'Privileged': True,
        }
        for key, value in mutations.items():
            with self.subTest(key=key):
                host = copy.deepcopy(self.host)
                host[key] = value
                self.assertFalse(self.matches(host))

    def test_configured_dns_is_not_normalized(self):
        for key in ('Dns', 'DnsOptions', 'DnsSearch'):
            host = copy.deepcopy(self.host)
            host[key] = ['custom']
            with self.subTest(key=key):
                self.assertFalse(self.matches(host))

    def test_missing_dns_key_is_not_normalized(self):
        host = copy.deepcopy(self.host)
        del host['Dns']
        self.assertFalse(self.matches(host))

    def test_other_null_empty_fields_remain_strict(self):
        host = copy.deepcopy(self.host)
        host['CapAdd'] = []
        self.assertFalse(self.matches(host))

    def test_image_mount_environment_and_identity_changes_remain_strict(self):
        for key in ('Id', 'Image', 'Mounts', 'environment_sha256', 'restart'):
            with self.subTest(key=key):
                self.assertFalse(self.matches(self.host, **{key: 'different'}))


class FinalCheckpointTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        import hashlib
        self.temporary = tempfile.TemporaryDirectory(prefix='.ow2e-checkpoint-test-', dir=ROOT)
        self.addCleanup(self.temporary.cleanup)
        baseline = Path(self.temporary.name) / 'original-baseline.json'
        baseline.write_bytes(b'original protected baseline')
        patcher = patch.object(checker, 'BASELINE', baseline)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.before = {
            'boot_id': 'before-boot',
            'units': {'lab': {'MainPID': '10', 'ExecMainStartTimestamp': 'before'},
                      'production': {'MainPID': '20', 'ExecMainStartTimestamp': 'before'}},
            'webui_started_at': 'before',
            'dense_state': {'indexed_messages': 6, 'progress_after': 6, 'caught_up': True},
            'dense_files': {'version2': {'sha256': 'unchanged', 'size': 10, 'mtime_ns': 100}},
            'firewall_state': {'nft_policy_sha256': 'same', 'persistent_config_sha256': {'ufw': 'same'}},
            'cgroup_state': 'same',
        }
        self.checkpoint = checker.final_checkpoint(copy.deepcopy(self.before))
        self.checkpoint['original_baseline_sha256'] = hashlib.sha256(baseline.read_bytes()).hexdigest()
        self.after = copy.deepcopy(self.before)
        self.after['boot_id'] = 'after-boot'
        self.after['webui_started_at'] = 'after'
        for value in self.after['units'].values():
            value['MainPID'] += '0'
            value['ExecMainStartTimestamp'] = 'after'

    def test_pre_reboot_process_and_dense_state_match(self):
        checker.verify_final_checkpoint(self.before, self.checkpoint, False)

    def test_new_boot_preserves_dense_firewall_and_cgroup_state(self):
        checker.verify_final_checkpoint(self.after, self.checkpoint, True)

    def test_old_boot_cannot_pass_after_reboot(self):
        self.after['boot_id'] = 'before-boot'
        with self.assertRaisesRegex(RuntimeError, 'boot identity'):
            checker.verify_final_checkpoint(self.after, self.checkpoint, True)

    def test_pre_reboot_process_change_is_rejected(self):
        self.before['units']['lab']['MainPID'] = 'changed'
        with self.assertRaisesRegex(RuntimeError, 'process changed'):
            checker.verify_final_checkpoint(self.before, self.checkpoint, False)

    def test_old_process_start_cannot_pass_after_reboot(self):
        self.after['units']['lab']['ExecMainStartTimestamp'] = 'before'
        with self.assertRaisesRegex(RuntimeError, 'pre-reboot process start'):
            checker.verify_final_checkpoint(self.after, self.checkpoint, True)

    def test_recreated_dense_files_are_rejected_even_with_correct_counts(self):
        self.after['dense_files']['version2']['mtime_ns'] = 200
        with self.assertRaisesRegex(RuntimeError, 'dense_files'):
            checker.verify_final_checkpoint(self.after, self.checkpoint, True)

    def test_progress_change_is_rejected(self):
        self.after['dense_state']['progress_after'] = 7
        with self.assertRaisesRegex(RuntimeError, 'dense_state'):
            checker.verify_final_checkpoint(self.after, self.checkpoint, True)

    def test_firewall_and_cgroup_changes_are_rejected(self):
        for key in ('firewall_state', 'cgroup_state'):
            current = copy.deepcopy(self.after)
            current[key] = 'changed'
            with self.subTest(key=key), self.assertRaisesRegex(RuntimeError, key):
                checker.verify_final_checkpoint(current, self.checkpoint, True)

    def test_original_production_baseline_cannot_be_rebased(self):
        checker.BASELINE.write_bytes(b'changed')
        with self.assertRaisesRegex(RuntimeError, 'durable baseline was changed'):
            checker.verify_final_checkpoint(self.after, self.checkpoint, True)

    def test_webui_must_have_new_start_after_reboot(self):
        self.after['webui_started_at'] = 'before'
        with self.assertRaisesRegex(RuntimeError, 'WebUI start time'):
            checker.verify_final_checkpoint(self.after, self.checkpoint, True)


firewall = load('lab_firewall_capture', 'capture_firewall_evidence.py')


class FirewallEvidenceTests(unittest.TestCase):
    def test_nft_handles_and_independent_declaration_order_are_not_policy(self):
        rules = [
            {'metainfo': {'version': 'ignored'}},
            {'table': {'family': 'ip', 'name': 'filter', 'handle': 1}},
            {'chain': {'family': 'ip', 'table': 'filter', 'name': 'INPUT', 'handle': 2}},
            {'rule': {'family': 'ip', 'table': 'filter', 'chain': 'INPUT',
                      'handle': 3, 'expr': [{'accept': None}]}},
        ]
        changed = copy.deepcopy(rules)
        changed[1]['table']['handle'] = 10
        changed[2]['chain']['handle'] = 20
        changed[3]['rule']['handle'] = 30
        changed[1], changed[2] = changed[2], changed[1]
        self.assertEqual(firewall.nft_policy({'nftables': rules}),
                         firewall.nft_policy({'nftables': changed}))
        changed[3]['rule']['expr'] = [{'drop': None}]
        self.assertNotEqual(firewall.nft_policy({'nftables': rules}),
                            firewall.nft_policy({'nftables': changed}))

    def test_rule_order_within_chain_remains_strict(self):
        first = {'family': 'ip', 'table': 'filter', 'chain': 'INPUT', 'expr': [{'accept': None}]}
        second = dict(first, expr=[{'drop': None}])
        self.assertNotEqual(firewall.nft_policy({'nftables': [{'rule': first}, {'rule': second}]}),
                            firewall.nft_policy({'nftables': [{'rule': second}, {'rule': first}]}))

    def test_iptables_counters_and_generation_comments_are_not_policy(self):
        first = '# Generated at time 1\n*filter\n:INPUT ACCEPT [10:100]\n-A INPUT -j ACCEPT\nCOMMIT\n'
        second = first.replace('time 1', 'time 2').replace('[10:100]', '[20:200]')
        self.assertEqual(firewall.iptables_policy(first), firewall.iptables_policy(second))
        self.assertNotEqual(firewall.iptables_policy(first),
                            firewall.iptables_policy(second.replace('-j ACCEPT', '-j DROP')))


if __name__ == '__main__':
    unittest.main()
