"""Expected logical slots and kernel-owned health, without inference or /run."""

import fcntl
import json
from pathlib import Path
import selectors
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from app.foreground_registry import (
    ForegroundPublisher, ForegroundRegistry, RegistryState,
)


class RegistryHealthTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path = Path(temp.name)
        self.now = [100.0]
        self.registry = ForegroundRegistry(
            self.path, expected_publishers=("lab",), clock=lambda: self.now[0],
        )
        self.registry.initialize()

    def publisher(self, name):
        p = ForegroundPublisher(self.registry, logical_publisher=name)
        self.addCleanup(p.close)
        return p

    def state(self, expected):
        snapshot = self.registry.read()
        self.assertEqual(snapshot.state, expected, snapshot.reason)
        return snapshot

    def test_missing_expected_publisher_is_unknown(self):
        self.state(RegistryState.UNKNOWN)

    def test_unspecified_expected_contract_never_claims_idle(self):
        self.publisher("lab")
        self.assertEqual(ForegroundRegistry(self.path).read().state, RegistryState.UNKNOWN)

    def test_lab_only_contract_accepts_healthy_lab_idle(self):
        self.publisher("lab")
        state = self.state(RegistryState.IDLE)
        self.assertEqual(state.active_foreground_count, 0)
        self.assertIsNone(state.last_foreground_finished_at)
        self.assertEqual(state.idle_grace_anchor, 100.0)

    def test_lab_and_production_contract_rejects_lab_only(self):
        self.registry.expected_publishers = frozenset(("lab", "production"))
        self.publisher("lab")
        self.state(RegistryState.UNKNOWN)

    def test_both_expected_idle_and_either_busy(self):
        self.registry.expected_publishers = frozenset(("lab", "production"))
        lab, prod = self.publisher("lab"), self.publisher("production")
        self.state(RegistryState.IDLE)
        lab.publish(2, None)
        self.assertEqual(self.state(RegistryState.BUSY).active_foreground_count, 2)
        prod.publish(1, None)
        self.assertEqual(self.state(RegistryState.BUSY).active_foreground_count, 3)
        self.now[0] = 101.0
        lab.publish(0, 101.0)
        self.assertEqual(self.state(RegistryState.BUSY).active_foreground_count, 1)
        prod.publish(0, 101.0)
        self.assertEqual(self.state(RegistryState.IDLE).last_foreground_finished_at, 101.0)

    def test_closed_idle_metadata_cannot_satisfy_presence(self):
        p = self.publisher("lab")
        self.state(RegistryState.IDLE)
        p.close()
        self.state(RegistryState.UNKNOWN)

    def test_fault_signaling_failure_leaves_live_publisher_unhealthy(self):
        p = self.publisher("lab")
        with patch.object(p, "_mark_fault", side_effect=OSError("fault lock failed")), patch(
            "app.foreground_registry._write", side_effect=OSError("metadata failed"),
        ):
            with self.assertRaisesRegex(OSError, "metadata failed"):
                p.publish(1, None)
        self.assertIsNone(p._health_fd)
        self.assertEqual(json.loads((self.path / (p.identity + ".json")).read_text())["active_count"], 0)
        self.state(RegistryState.UNKNOWN)
        # Even another healthy process using the same name cannot mask a live
        # degraded process. Trust requires all live records to be healthy.
        self.publisher("lab")
        self.state(RegistryState.UNKNOWN)

    def test_guard_failure_revokes_health_before_acquiring_busy(self):
        p = self.publisher("lab")
        with patch("app.foreground_registry._guard", side_effect=PermissionError("write denied")):
            with self.assertRaises(PermissionError):
                p.publish(1, None)
        self.state(RegistryState.UNKNOWN)

    def test_duplicate_live_logical_slots_are_unknown(self):
        self.publisher("lab")
        self.publisher("lab")
        self.state(RegistryState.UNKNOWN)

    def test_malformed_health_metadata_is_unknown(self):
        p = self.publisher("lab")
        record = self.path / (p.identity + ".json")
        value = json.loads(record.read_text())
        value["health_inode"] = "invalid"
        record.write_text(json.dumps(value))
        self.state(RegistryState.UNKNOWN)

    def test_healthy_metadata_without_live_ownership_is_unknown(self):
        p = self.publisher("lab")
        fcntl.flock(p._live_fd, fcntl.LOCK_UN)  # Deliberate corruption by the test.
        self.state(RegistryState.UNKNOWN)

    def test_idle_and_busy_crashes_release_health_and_restart_recovers(self):
        code = '''
import sys
from app.foreground_registry import ForegroundRegistry, ForegroundPublisher
r = ForegroundRegistry(sys.argv[1], expected_publishers=("lab",), clock=lambda: 100.)
p = ForegroundPublisher(r, logical_publisher="lab")
if sys.argv[2] == "busy":
    p.publish(1, None)
print(p.identity, flush=True)
sys.stdin.readline()
'''
        for activity in ("idle", "busy"):
            with self.subTest(activity=activity):
                child = subprocess.Popen(
                    [sys.executable, "-B", "-c", code, str(self.path), activity],
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    text=True,
                )
                try:
                    with selectors.DefaultSelector() as ready:
                        ready.register(child.stdout, selectors.EVENT_READ)
                        self.assertTrue(ready.select(5), "publisher did not become ready")
                    identity = child.stdout.readline().strip()
                    self.assertTrue(identity)
                    self.state(RegistryState.BUSY if activity == "busy" else RegistryState.IDLE)
                    child.kill()
                    child.wait(timeout=5)
                    self.state(RegistryState.UNKNOWN)
                    replacement = self.publisher("lab")
                    self.assertNotEqual(replacement.identity, identity)
                    self.now[0] += 1
                    self.assertEqual(self.state(RegistryState.IDLE).idle_grace_anchor, self.now[0])
                    replacement.close()
                    self.state(RegistryState.UNKNOWN)
                finally:
                    if child.poll() is None:
                        child.kill()
                    child.communicate(timeout=5)

    def test_old_schema_is_unknown_and_is_not_automatically_migrated(self):
        path = self.path / "registry.json"
        value = json.loads(path.read_text())
        value["version"] = 1
        path.write_text(json.dumps(value))
        self.state(RegistryState.UNKNOWN)


if __name__ == "__main__":
    unittest.main()
