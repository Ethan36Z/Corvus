"""Registry contracts using temporary files, real flock and disposable processes."""

from contextlib import ExitStack
from concurrent.futures import ThreadPoolExecutor
import fcntl
import json
import os
from pathlib import Path
import selectors
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Barrier
import time
import unittest
from unittest.mock import patch

from app.foreground_activity import ForegroundActivityTracker
from app.foreground_registry import (
    ForegroundPublisher, ForegroundRegistry, RegistryError, RegistryState,
)
import app.foreground_registry as core


CHILD = '''
import json, os, sys, time
from app.foreground_registry import ForegroundPublisher, ForegroundRegistry, RegistryError, RegistryState
p = ForegroundPublisher(ForegroundRegistry(sys.argv[1], expected_publishers=(sys.argv[2],)), logical_publisher=sys.argv[2])
print(p.identity, flush=True)
def fork_sleeper():
    read_fd, write_fd = os.pipe()
    child = os.fork()
    if child == 0:
        os.close(read_fd)
        assert p._registry.read().state == RegistryState.UNKNOWN
        try:
            p.publish(1, None)
        except RegistryError:
            pass
        else:
            raise AssertionError("inherited publisher was reusable")
        os.write(write_fd, b"ready")  # Child at-fork cleanup has completed.
        os.close(write_fd)
        time.sleep(30)
        os._exit(0)
    os.close(write_fd)
    assert os.read(read_fd, 5) == b"ready"
    os.close(read_fd)
    return child
for line in sys.stdin:
    command = json.loads(line)
    if command == "fork":
        print(fork_sleeper(), flush=True)
    elif command == "fork_guard":
        import app.foreground_registry as core
        with core._guard(p._directory_fd, writable=True):
            child = fork_sleeper()
        print(child, flush=True)
    elif command == "close":
        p.close()
        print("closed", flush=True)
    else:
        p.publish(*command)
        print("published", flush=True)
'''


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.now = [100.0]
        self.registry = ForegroundRegistry(self.path, clock=lambda: self.now[0], expected_publishers=("lab",))
        self.claims = []
        self.registry.initialize()

    def next_logical(self):
        live = {name for name, owner in self.claims if
                (not owner._closed if isinstance(owner, ForegroundPublisher) else owner.poll() is None)}
        name = next(name for name in ("lab", "production", "worker2", "worker3") if name not in live)
        self.registry.expected_publishers |= {name}
        return name

    def publisher(self):
        name = self.next_logical()
        publisher = ForegroundPublisher(self.registry, logical_publisher=name)
        self.claims.append((name, publisher))
        self.addCleanup(publisher.close)
        return publisher

    def record_path(self, publisher):
        return self.path / (publisher.identity + ".json")

    def corrupt(self, publisher, **changes):
        path = self.record_path(publisher)
        record = json.loads(path.read_text())
        record.update(changes)
        path.write_text(json.dumps(record))

    def assert_state(self, state, count):
        snapshot = self.registry.read()
        self.assertEqual(snapshot.state, state, snapshot.reason)
        self.assertEqual(snapshot.active_foreground_count, count)
        return snapshot

    def child(self):
        name = self.next_logical()
        child = subprocess.Popen(
            [sys.executable, "-B", "-c", CHILD, str(self.path), name],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, cwd=Path(__file__).resolve().parents[1],
        )
        def cleanup():
            if child.poll() is None:
                child.kill()
            child.communicate(timeout=5)
        self.addCleanup(cleanup)
        identity = self.line(child)
        self.claims.append((name, child))
        return child, identity

    def line(self, child):
        with selectors.DefaultSelector() as selector:
            selector.register(child.stdout, selectors.EVENT_READ)
            self.assertTrue(selector.select(5), "child did not report readiness")
        line = child.stdout.readline().strip()
        self.assertTrue(line, "child exited before reporting readiness")
        return line

    def command(self, child, command):
        child.stdin.write(json.dumps(command) + "\n")
        child.stdin.flush()
        return self.line(child)

    def test_empty_initialized_registry_is_unknown_until_expected_publisher_joins(self):
        snapshot = self.assert_state(RegistryState.UNKNOWN, None)
        self.assertIsNone(snapshot.last_foreground_finished_at)
        self.assertIsNone(snapshot.idle_grace_anchor)
        self.assertEqual(ForegroundRegistry(self.path / "missing").read().state,
                         RegistryState.UNKNOWN)
        with TemporaryDirectory() as empty:
            self.assertEqual(ForegroundRegistry(empty).read().state, RegistryState.UNKNOWN)

    def test_one_idle_and_one_active_publisher(self):
        p = self.publisher()
        self.assert_state(RegistryState.IDLE, 0)
        p.publish(1, None)
        self.assert_state(RegistryState.BUSY, 1)
        p.publish(0, 100.0)
        snapshot = self.assert_state(RegistryState.IDLE, 0)
        self.assertEqual(snapshot.last_foreground_finished_at, 100.0)

    def test_two_processes_aggregate_and_finish_independently(self):
        first, _ = self.child()
        second, _ = self.child()
        self.command(first, [1, None])
        self.command(second, [2, None])
        self.assert_state(RegistryState.BUSY, 3)
        self.command(first, [0, 90.0])
        self.assertEqual(self.assert_state(RegistryState.BUSY, 2).last_foreground_finished_at, 90.0)
        self.command(second, [0, 95.0])
        self.assertEqual(self.assert_state(RegistryState.IDLE, 0).last_foreground_finished_at, 95.0)
        self.command(first, [1, 90.0])
        self.command(first, [0, 99.0])
        self.assertEqual(self.assert_state(RegistryState.IDLE, 0).idle_grace_anchor, 100.0)

    def test_concurrent_publications_and_reads_remain_consistent(self):
        registry = ForegroundRegistry(self.path, expected_publishers=("lab", "production"))
        publishers = [ForegroundPublisher(registry, logical_publisher=name)
                      for name in ("lab", "production")]
        for p in publishers:
            self.addCleanup(p.close)
        barrier = Barrier(3)

        def publish(p):
            barrier.wait(timeout=5)
            finished = None
            for _ in range(12):
                p.publish(1, finished)
                finished = time.monotonic()
                p.publish(0, finished)

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(publish, p) for p in publishers]
            barrier.wait(timeout=5)
            while not all(future.done() for future in futures):
                snapshot = registry.read()
                if snapshot.state != RegistryState.UNKNOWN:
                    self.assertIn(snapshot.active_foreground_count, (0, 1, 2))
                    self.assertEqual(snapshot.state == RegistryState.IDLE,
                                     snapshot.active_foreground_count == 0)
                time.sleep(0.001)
            for future in futures:
                future.result(timeout=5)
        self.assertEqual(registry.read().state, RegistryState.IDLE)

    def test_local_overlap_uses_tracker_snapshots_and_stable_busy_inode(self):
        tracker = ForegroundActivityTracker(clock=lambda: self.now[0])
        p = self.publisher()
        busy = self.path / (p.identity + ".busy")
        inode = busy.stat().st_ino
        def publish():
            snapshot = tracker.snapshot()
            p.publish(snapshot.active_foreground_count, snapshot.last_foreground_finished_at)
        with ExitStack() as stack:
            first = stack.enter_context(tracker.generation())
            publish()
            second = tracker.generation()
            second.__enter__()
            publish()
            self.assert_state(RegistryState.BUSY, 2)
            self.now[0] = 101.0
            second.__exit__(None, None, None)
            publish()
            self.assert_state(RegistryState.BUSY, 1)
            self.assertEqual(busy.stat().st_ino, inode)
        publish()
        self.assert_state(RegistryState.IDLE, 0)
        self.assertEqual(busy.stat().st_ino, inode)

    def test_crash_releases_busy_ownership_and_grace_does_not_reset(self):
        child, identity = self.child()
        self.command(child, [1, None])
        self.assert_state(RegistryState.BUSY, 1)
        child.kill()
        child.wait(timeout=5)
        self.assertEqual(json.loads((self.path / (identity + ".json")).read_text())["active_count"], 1)
        self.assert_state(RegistryState.UNKNOWN, None)
        self.child()  # Replacement proves live health; stale busy ownership is gone.
        recovered = self.assert_state(RegistryState.IDLE, 0)
        self.assertEqual(recovered.recovery_grace_started_at, 100.0)
        self.now[0] = 120.0
        self.assertEqual(self.assert_state(RegistryState.IDLE, 0).idle_grace_anchor, 100.0)
        # Reader restart conservatively observes one new grace, without writing.
        fresh = ForegroundRegistry(self.path, clock=lambda: self.now[0], expected_publishers=("lab",))
        self.assertEqual(fresh.read().recovery_grace_started_at, 120.0)

    def test_crash_of_one_publisher_preserves_other_busy_count(self):
        child, _ = self.child()
        live = self.publisher()
        self.command(child, [3, None])
        live.publish(2, None)
        self.assert_state(RegistryState.BUSY, 5)
        child.kill()
        child.wait(timeout=5)
        self.assert_state(RegistryState.UNKNOWN, None)
        self.child()
        self.assert_state(RegistryState.BUSY, 2)

    def test_independent_restart_uses_new_identity_and_keeps_watermark(self):
        p = self.publisher()
        p.publish(1, None)
        p.publish(0, 99.0)
        p.close()
        child, old_identity = self.child()
        self.command(child, [1, None])
        child.kill()
        child.wait(timeout=5)
        replacement, new_identity = self.child()
        self.assertNotEqual(old_identity, new_identity)
        idle = self.assert_state(RegistryState.IDLE, 0)
        self.assertEqual(idle.last_foreground_finished_at, 99.0)
        self.command(replacement, [1, None])
        self.assert_state(RegistryState.BUSY, 1)
        self.command(replacement, [0, 100.0])
        self.assert_state(RegistryState.IDLE, 0)

    def test_malformed_json_is_unknown_even_with_another_busy_publisher(self):
        p, other = self.publisher(), self.publisher()
        other.publish(1, None)
        self.record_path(p).write_text("{broken")
        self.assert_state(RegistryState.UNKNOWN, None)

    def test_invalid_counts_identity_timestamps_and_fields_are_unknown(self):
        p = self.publisher()
        original = self.record_path(p).read_text()
        for changes in ({"active_count": -1}, {"active_count": True},
                        {"active_count": 1.5}, {"pid": 1}, {"start_ticks": -1},
                        {"identity": "wrong"}, {"last_finished": float("nan")},
                        {"last_finished": -1}, {"last_finished": 101},
                        {"last_finished": "yesterday"}, {"busy_inode": [True, 1]},
                        {"fault_inode": "invalid"}, {"extra": 1}):
            with self.subTest(changes=changes):
                self.record_path(p).write_text(original)
                self.corrupt(p, **changes)
                self.assert_state(RegistryState.UNKNOWN, None)

    def test_duplicate_json_keys_are_unknown(self):
        p = self.publisher()
        text = self.record_path(p).read_text()
        self.record_path(p).write_text('{"active_count": 0,' + text[1:])
        self.assert_state(RegistryState.UNKNOWN, None)

    def test_oversized_nested_and_nonregular_metadata_are_unknown(self):
        p = self.publisher()
        path = self.record_path(p)
        for text in (" " * 65537, "[" * 2000 + "]" * 2000):
            path.write_text(text)
            self.assert_state(RegistryState.UNKNOWN, None)
        path.unlink()
        os.mkfifo(path)
        self.assert_state(RegistryState.UNKNOWN, None)

    def test_unreadable_registry_and_metadata_are_unknown(self):
        with patch.object(self.registry, "_directory", side_effect=PermissionError("denied")):
            self.assert_state(RegistryState.UNKNOWN, None)
        p = self.publisher()
        os.chmod(self.record_path(p), 0)
        try:
            self.assert_state(RegistryState.UNKNOWN, None)
        finally:
            os.chmod(self.record_path(p), 0o600)
        os.chmod(self.path, 0)
        try:
            self.assert_state(RegistryState.UNKNOWN, None)
        finally:
            os.chmod(self.path, 0o700)

    def test_read_is_read_only_and_supports_read_only_metadata_permissions(self):
        p = self.publisher()
        p.publish(1, None)
        before = {path.name: (path.stat().st_mtime_ns, path.read_bytes()) for path in self.path.iterdir()}
        for path in self.path.iterdir():
            os.chmod(path, 0o400)
        os.chmod(self.path, 0o500)
        try:
            self.assert_state(RegistryState.BUSY, 1)
            self.assertEqual(before, {path.name: (path.stat().st_mtime_ns, path.read_bytes())
                                     for path in self.path.iterdir()})
        finally:
            os.chmod(self.path, 0o700)
            for path in self.path.iterdir():
                os.chmod(path, 0o600)

    def test_missing_record_or_lock_and_orphan_temporary_are_unknown(self):
        p = self.publisher()
        busy = self.path / (p.identity + ".busy")
        saved = busy.with_suffix(".saved")
        busy.rename(saved)  # Test corruption only; core never renames lock files.
        self.assert_state(RegistryState.UNKNOWN, None)
        saved.rename(busy)
        record = self.record_path(p)
        text = record.read_text()
        record.unlink()
        self.assert_state(RegistryState.UNKNOWN, None)
        record.write_text(text)
        pending = self.path / ".pending-crash"
        pending.write_text("{}")
        self.assert_state(RegistryState.UNKNOWN, None)

    def test_replacing_live_busy_lock_inode_is_unknown(self):
        p = self.publisher()
        p.publish(1, None)
        path = self.path / (p.identity + ".busy")
        path.rename(path.with_suffix(".old"))
        path.touch()
        path.with_suffix(".old").unlink()  # Deliberate violation by test fixture.
        self.assert_state(RegistryState.UNKNOWN, None)
        with self.assertRaises(RegistryError):
            p.publish(2, None)

    def test_registry_guard_contention_fails_closed_without_waiting(self):
        self.publisher()
        fd = os.open(self.path / "registry.lock", os.O_RDONLY)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            self.assert_state(RegistryState.UNKNOWN, None)
        finally:
            os.close(fd)
        self.assert_state(RegistryState.IDLE, 0)

    def test_replaced_registry_lock_or_malformed_header_is_unknown(self):
        header = self.path / "registry.json"
        original = header.read_text()
        value = json.loads(original)
        value["version"] = True
        header.write_text(json.dumps(value))
        self.assert_state(RegistryState.UNKNOWN, None)
        header.write_text(original)
        guard = self.path / "registry.lock"
        guard.rename(self.path / "old.lock")
        guard.touch()
        (self.path / "old.lock").unlink()
        self.assert_state(RegistryState.UNKNOWN, None)

    def test_failed_registration_leaves_unknown_not_false_idle(self):
        with patch.object(core, "_write", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                ForegroundPublisher(self.registry, logical_publisher="lab")
        self.assert_state(RegistryState.UNKNOWN, None)

    def test_busy_lock_with_idle_metadata_is_unknown(self):
        p = self.publisher()
        fcntl.flock(p._busy_fd, fcntl.LOCK_EX)
        self.assert_state(RegistryState.UNKNOWN, None)

    def test_publication_failure_is_unknown_and_failed_publisher_cannot_resume(self):
        p = self.publisher()
        p.publish(1, None)
        with patch.object(core, "_write", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                p.publish(0, 100.0)
        self.assert_state(RegistryState.UNKNOWN, None)
        with self.assertRaises(RegistryError):
            p.publish(0, 100.0)
        p.close()
        self.assert_state(RegistryState.UNKNOWN, None)
        self.publisher()
        self.assert_state(RegistryState.IDLE, 0)
        self.assertEqual(self.registry.read().recovery_grace_started_at, 100.0)

    def test_first_busy_publication_failure_cannot_appear_idle(self):
        p = self.publisher()
        with patch.object(core, "_write", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                p.publish(1, None)
        self.assert_state(RegistryState.UNKNOWN, None)
        p.close()  # Foreground may have proceeded; replacement must apply grace.
        self.assert_state(RegistryState.UNKNOWN, None)
        self.publisher()
        self.assertEqual(self.assert_state(RegistryState.IDLE, 0).recovery_grace_started_at, 100.0)

    def test_boot_or_time_domain_mismatch_is_unknown(self):
        domain = core._domain()
        for key in ("boot_id", "time_offsets"):
            with self.subTest(key=key), patch.object(core, "_domain", return_value=dict(domain, **{key: "different"})):
                self.assert_state(RegistryState.UNKNOWN, None)

    def test_symlink_registry_and_metadata_are_unknown(self):
        p = self.publisher()
        alias = self.path / "alias"
        alias.symlink_to(self.path, target_is_directory=True)
        self.assertEqual(ForegroundRegistry(alias).read().state, RegistryState.UNKNOWN)
        alias.unlink()
        record = self.record_path(p)
        saved = self.path / "saved"
        record.rename(saved)
        record.symlink_to(saved)
        self.assert_state(RegistryState.UNKNOWN, None)

    def test_invalid_publication_poisoning_and_closed_publisher(self):
        for count, finished in ((-1, None), (True, None), (1, float("nan")), (0, 101)):
            with self.subTest(count=count, finished=finished):
                p = self.publisher()
                with self.assertRaises(RegistryError):
                    p.publish(count, finished)
                self.assert_state(RegistryState.UNKNOWN, None)
                p.close()
        p = self.publisher()
        p.publish(1, None)
        with self.assertRaises(RegistryError):
            p.publish(0, None)
        p.close()
        with self.assertRaises(RegistryError):
            p.publish(1, None)

    def test_finish_watermark_cannot_regress(self):
        p = self.publisher()
        p.publish(1, None)
        p.publish(0, 99.0)
        with self.assertRaises(RegistryError):
            p.publish(1, 98.0)
        self.assert_state(RegistryState.UNKNOWN, None)

    def test_no_inherited_busy_descriptors_keep_crashed_parent_busy(self):
        parent, _ = self.child()
        self.command(parent, [1, None])
        descendant = int(self.command(parent, "fork"))
        self.addCleanup(self.kill_descendant, descendant)
        parent.kill()
        parent.wait(timeout=5)
        self.assert_state(RegistryState.UNKNOWN, None)
        self.child()
        self.assert_state(RegistryState.IDLE, 0)
        os.kill(descendant, 0)  # The child is still alive; inherited locks were closed.

    def test_transient_registry_guard_is_not_inherited_on_fork(self):
        parent, _ = self.child()
        descendant = int(self.command(parent, "fork_guard"))
        self.addCleanup(self.kill_descendant, descendant)
        self.assert_state(RegistryState.IDLE, 0)
        os.kill(descendant, 0)

    @staticmethod
    def kill_descendant(pid):
        try:
            os.kill(pid, 9)
        except ProcessLookupError:
            pass

    def test_descriptors_are_close_on_exec(self):
        p = self.publisher()
        p.publish(1, None)
        for fd in p._fds:
            self.assertFalse(os.get_inheritable(fd))
        # Even explicitly close_fds=False must not pass CLOEXEC descriptors.
        child = subprocess.Popen([sys.executable, "-B", "-c", "import time; time.sleep(30)"],
                                 close_fds=False)
        self.addCleanup(lambda: (child.kill(), child.wait(timeout=5)))
        p.close()
        self.assert_state(RegistryState.UNKNOWN, None)
        self.publisher()
        self.assert_state(RegistryState.IDLE, 0)

    def test_initialize_is_idempotent_and_never_replaces_lock_inode(self):
        inode = (self.path / "registry.lock").stat().st_ino
        self.registry.initialize()
        self.assertEqual((self.path / "registry.lock").stat().st_ino, inode)
        p = self.publisher()
        p.publish(1, None)
        self.registry.initialize()
        self.assert_state(RegistryState.BUSY, 1)


if __name__ == "__main__":
    unittest.main()
