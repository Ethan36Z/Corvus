"""Linux host-local activity metadata. No default path or runtime integration.

Provision/initialize explicitly, then publish *serialized* local tracker snapshots.
Readers require an explicit expected logical-publisher contract. Foreground calls
may continue on failure; missing live health makes background admission UNKNOWN.
Readers never write; recovery grace is reader-local and resets on reader restart.
Lock files are permanent: do not unlink, replace, or inherit their descriptors.
"""

from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
import fcntl
import json
import math
import os
from pathlib import Path
import re
import stat
from threading import Lock
from time import monotonic, sleep
import uuid
import weakref


class RegistryState(str, Enum):
    BUSY = "BUSY"
    IDLE = "IDLE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class RegistrySnapshot:
    state: RegistryState
    active_foreground_count: int | None = None
    last_foreground_finished_at: float | None = None
    recovery_grace_started_at: float | None = None
    reason: str | None = None

    @property
    def idle_grace_anchor(self):
        values = (self.last_foreground_finished_at, self.recovery_grace_started_at)
        return max((value for value in values if value is not None), default=None)


class RegistryError(RuntimeError):
    pass


_ID = re.compile(r"([1-9][0-9]*)-([0-9]+)-[0-9a-f]{32}\Z")
_LOGICAL = re.compile(r"[a-z][a-z0-9_-]{0,63}\Z")
_FLAGS = os.O_CLOEXEC | os.O_NOFOLLOW
_publishers = weakref.WeakSet()
_fd_lock = Lock()
_fds = set()


def _after_fork():
    # Closing (not LOCK_UN) preserves the parent's open-file-description locks.
    global _fd_lock
    for fd in _fds:
        os.close(fd)
    _fds.clear()
    for publisher in list(_publishers):
        publisher._fds.clear()
        publisher._closed = True
    _fd_lock = Lock()


def _before_fork():
    _fd_lock.acquire()


def _after_fork_parent():
    _fd_lock.release()


os.register_at_fork(before=_before_fork, after_in_parent=_after_fork_parent,
                    after_in_child=_after_fork)


def _close(fd):
    with _fd_lock:
        _fds.remove(fd)
        os.close(fd)


def _domain():
    return {
        "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
        "time_offsets": Path("/proc/self/timens_offsets").read_text().strip(),
    }


def _start_ticks():
    return int(Path("/proc/self/stat").read_text().rsplit(")", 1)[1].split()[19])


def _inode(fd):
    info = os.fstat(fd)
    if not stat.S_ISREG(info.st_mode):
        raise RegistryError("non-regular registry file")
    return [info.st_dev, info.st_ino]


def _open(directory, name, flags):
    with _fd_lock:
        fd = os.open(name, flags | _FLAGS | os.O_NONBLOCK, 0o600, dir_fd=directory)
        _fds.add(fd)
    try:
        _inode(fd)
        return fd
    except BaseException:
        _close(fd)
        raise


def _load(directory, name):
    fd = _open(directory, name, os.O_RDONLY)
    try:
        if os.fstat(fd).st_size > 65536:
            raise RegistryError("oversized registry metadata")
        with os.fdopen(fd, "r", closefd=False) as stream:
            def unique(pairs):
                result = {}
                for key, value in pairs:
                    if key in result:
                        raise RegistryError("duplicate JSON key")
                    result[key] = value
                return result
            value = json.load(stream, object_pairs_hook=unique)
    finally:
        _close(fd)
    if not isinstance(value, dict):
        raise RegistryError("metadata is not an object")
    return value


def _write(directory, name, value):
    temporary = f".pending-{uuid.uuid4().hex}"
    fd = _open(directory, temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
    try:
        with os.fdopen(fd, "w", closefd=False) as stream:
            json.dump(value, stream, allow_nan=False, sort_keys=True)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, name, src_dir_fd=directory, dst_dir_fd=directory)
    finally:
        _close(fd)
        try:
            os.unlink(temporary, dir_fd=directory)
        except FileNotFoundError:
            pass


@contextmanager
def _guard(directory, writable=False, create=False):
    flags = os.O_RDWR if writable else os.O_RDONLY
    if create:
        flags |= os.O_CREAT
    fd = _open(directory, "registry.lock", flags)
    try:
        deadline = monotonic() + 1.0
        while True:
            try:
                fcntl.flock(fd, (fcntl.LOCK_EX if writable else fcntl.LOCK_SH) | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if not writable or monotonic() >= deadline:
                    raise
                sleep(0.001)
        info = os.stat("registry.lock", dir_fd=directory, follow_symlinks=False)
        if _inode(fd) != [info.st_dev, info.st_ino]:
            raise RegistryError("registry lock replaced")
        yield fd
    finally:
        _close(fd)


def _timestamp(value):
    if value is not None and (type(value) not in (int, float) or
                              not math.isfinite(value) or value < 0):
        raise RegistryError("invalid monotonic timestamp")


def _valid_inode(value):
    return (type(value) is list and len(value) == 2 and
            all(type(part) is int and part >= 0 for part in value))


def _locked(fd):
    try:
        fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
    except BlockingIOError:
        return True
    else:
        fcntl.flock(fd, fcntl.LOCK_UN)
        return False


class ForegroundRegistry:
    def __init__(self, path, *, clock=monotonic, expected_publishers=()):
        self.path = Path(path)
        if isinstance(expected_publishers, str):
            raise RegistryError("expected publishers must be a collection of logical names")
        self.expected_publishers = frozenset(expected_publishers)
        if any(not isinstance(name, str) or not _LOGICAL.fullmatch(name)
               for name in self.expected_publishers):
            raise RegistryError("invalid expected logical publisher")
        self._pid = os.getpid()
        self._clock = clock
        self._recoveries = {}
        self._read_lock = Lock()

    def _directory(self):
        if self._pid != os.getpid():
            raise RegistryError("inherited registry; create a new instance")
        with _fd_lock:
            fd = os.open(self.path, os.O_RDONLY | os.O_DIRECTORY | _FLAGS)
            _fds.add(fd)
            return fd

    def _header(self, directory, guard):
        header = _load(directory, "registry.json")
        if (type(header.get("version")) is not int or
            not _valid_inode(header.get("lock_inode")) or
            header != {"version": 2, "clock_domain": _domain(), "lock_inode": _inode(guard)}):
            raise RegistryError("registry version, clock domain, or lock identity mismatch")

    def initialize(self):
        """Initialize an existing empty directory; never provision /run implicitly."""
        directory = self._directory()
        try:
            with _guard(directory, writable=True, create=True) as guard:
                if "registry.json" in os.listdir(directory):
                    self._header(directory, guard)
                else:
                    if set(os.listdir(directory)) != {"registry.lock"}:
                        raise RegistryError("refusing to initialize nonempty registry")
                    _write(directory, "registry.json", {
                        "version": 2, "clock_domain": _domain(), "lock_inode": _inode(guard),
                    })
        finally:
            _close(directory)

    def read(self):
        """Nonblocking, read-only snapshot; all untrusted states fail closed."""
        if self._pid != os.getpid():
            return RegistrySnapshot(RegistryState.UNKNOWN, reason="inherited registry")
        with self._read_lock:
            directory = None
            try:
                directory = self._directory()
                with _guard(directory) as guard:
                    self._header(directory, guard)
                    if not self.expected_publishers:
                        raise RegistryError("expected publisher contract is not configured")
                    names = set(os.listdir(directory)) - {"registry.lock", "registry.json"}
                    ids = {name.removesuffix(".json") for name in names if name.endswith(".json")}
                    expected = {identity + suffix for identity in ids
                                for suffix in (".json", ".busy", ".fault", ".live", ".health")}
                    if names != expected:
                        raise RegistryError("orphaned or unexpected registry files")
                    total, finished, recoveries, healthy = 0, [], [], set()
                    for identity in sorted(ids):
                        match = _ID.fullmatch(identity)
                        record = _load(directory, identity + ".json")
                        if (match is None or set(record) != {
                            "identity", "pid", "start_ticks", "active_count", "last_finished",
                            "busy_inode", "fault_inode", "live_inode", "health_inode", "logical_publisher",
                        } or record["identity"] != identity or
                            type(record["pid"]) is not int or record["pid"] != int(match[1]) or
                            type(record["start_ticks"]) is not int or record["start_ticks"] != int(match[2]) or
                            type(record["active_count"]) is not int or record["active_count"] < 0 or
                            not _valid_inode(record["busy_inode"]) or
                            not _valid_inode(record["fault_inode"]) or
                            not _valid_inode(record["live_inode"]) or
                            not _valid_inode(record["health_inode"]) or
                            not isinstance(record["logical_publisher"], str) or
                            not _LOGICAL.fullmatch(record["logical_publisher"])):
                            raise RegistryError("invalid publisher metadata")
                        _timestamp(record["last_finished"])
                        if record["last_finished"] is not None:
                            if record["last_finished"] > self._clock():
                                raise RegistryError("future finish timestamp")
                            finished.append(record["last_finished"])
                        # A fresh identity may replace a process whose failed
                        # initialization left no published finish. Observe one
                        # grace for every identity, including healthy replacements.
                        if identity not in self._recoveries:
                            self._recoveries[identity] = self._clock()
                        recoveries.append(self._recoveries[identity])
                        locks = {}
                        try:
                            for kind in ("busy", "fault", "live", "health"):
                                fd = _open(directory, identity + "." + kind, os.O_RDONLY)
                                locks[kind] = fd
                                if _inode(fd) != record[kind + "_inode"]:
                                    raise RegistryError("publisher lock replaced")
                            fault = _locked(locks["fault"])
                            live = _locked(locks["live"])
                            health = _locked(locks["health"])
                            busy = _locked(locks["busy"])
                        finally:
                            for fd in locks.values():
                                _close(fd)
                        if live:
                            if fault or not health:
                                raise RegistryError("live publisher is degraded")
                            logical = record["logical_publisher"]
                            if logical in healthy:
                                raise RegistryError("duplicate live logical publisher")
                            healthy.add(logical)
                        elif busy or health or fault:
                            raise RegistryError("publisher ownership without lifetime lock")
                        if live and busy:
                            if record["active_count"] == 0:
                                raise RegistryError("busy lock with idle metadata")
                            total += record["active_count"]
                        elif live and record["active_count"] > 0:
                            raise RegistryError("live active metadata without busy ownership")
                    if not self.expected_publishers <= healthy:
                        raise RegistryError("missing live healthy expected publisher: " +
                                            ", ".join(sorted(self.expected_publishers - healthy)))
                    return RegistrySnapshot(
                        RegistryState.BUSY if total else RegistryState.IDLE, total,
                        max(finished, default=None), max(recoveries, default=None),
                    )
            except (OSError, ValueError, TypeError, OverflowError, RecursionError, RegistryError) as exc:
                return RegistrySnapshot(RegistryState.UNKNOWN, reason=str(exc))
            finally:
                if directory is not None:
                    _close(directory)


class ForegroundPublisher:
    """One unique logical service/worker slot with kernel-backed live health.

    Call publish under the same serialization as local tracker transitions.
    Publication failure poisons this publisher: close it and recover before reuse.
    """
    def __init__(self, registry, *, logical_publisher):
        if not isinstance(logical_publisher, str) or not _LOGICAL.fullmatch(logical_publisher):
            raise RegistryError("configure a valid logical publisher name")
        self._registry = registry
        self._pid = os.getpid()
        self._mutex = Lock()
        self._closed = False
        self._failed = False
        self._fds = []
        self._health_fd = None
        self.identity = f"{self._pid}-{_start_ticks()}-{uuid.uuid4().hex}"
        with _fd_lock:
            _publishers.add(self)
        try:
            self._directory_fd = registry._directory()
            self._fds.append(self._directory_fd)
            with _guard(self._directory_fd, writable=True) as guard:
                registry._header(self._directory_fd, guard)
                self._busy_fd = _open(self._directory_fd, self.identity + ".busy",
                                      os.O_RDWR | os.O_CREAT | os.O_EXCL)
                self._fds.append(self._busy_fd)
                self._fault_fd = _open(self._directory_fd, self.identity + ".fault",
                                       os.O_RDWR | os.O_CREAT | os.O_EXCL)
                self._fds.append(self._fault_fd)
                self._live_fd = _open(self._directory_fd, self.identity + ".live",
                                      os.O_RDWR | os.O_CREAT | os.O_EXCL)
                self._fds.append(self._live_fd)
                fcntl.flock(self._live_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                self._health_fd = _open(self._directory_fd, self.identity + ".health",
                                        os.O_RDWR | os.O_CREAT | os.O_EXCL)
                self._fds.append(self._health_fd)
                self._record = {
                    "identity": self.identity, "pid": self._pid,
                    "start_ticks": _start_ticks(), "active_count": 0, "last_finished": None,
                    "busy_inode": _inode(self._busy_fd), "fault_inode": _inode(self._fault_fd),
                    "live_inode": _inode(self._live_fd), "health_inode": _inode(self._health_fd),
                    "logical_publisher": logical_publisher,
                }
                _write(self._directory_fd, self.identity + ".json", self._record)
                fcntl.flock(self._health_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BaseException:
            self._close_fds()
            self._closed = True
            raise

    def publish(self, active_foreground_count, last_foreground_finished_at):
        if self._pid != os.getpid():
            raise RegistryError("inherited publisher")
        with self._mutex:
            if self._closed or self._pid != os.getpid() or self._failed:
                raise RegistryError("closed, inherited, or failed publisher")
            try:
                # Revoke trust BEFORE any fallible admission/write operation.
                # Closing ownership is independent of best-effort fault signaling.
                self._revoke_health()
                if type(active_foreground_count) is not int or active_foreground_count < 0:
                    raise RegistryError("invalid local count")
                _timestamp(last_foreground_finished_at)
                previous = self._record["last_finished"]
                if (previous is not None and (last_foreground_finished_at is None or
                                              last_foreground_finished_at < previous)):
                    raise RegistryError("finish watermark regressed")
                if (last_foreground_finished_at is not None and
                    last_foreground_finished_at > self._registry._clock()):
                    raise RegistryError("future finish timestamp")
                if active_foreground_count < self._record["active_count"] and last_foreground_finished_at is None:
                    raise RegistryError("completion requires finish timestamp")
                with _guard(self._directory_fd, writable=True) as guard:
                    self._registry._header(self._directory_fd, guard)
                    for fd, suffix in ((self._busy_fd, ".busy"), (self._fault_fd, ".fault"),
                                       (self._live_fd, ".live")):
                        info = os.stat(self.identity + suffix, dir_fd=self._directory_fd, follow_symlinks=False)
                        if _inode(fd) != [info.st_dev, info.st_ino]:
                            raise RegistryError("publisher lock replaced")
                    if active_foreground_count > 0:
                        fcntl.flock(self._busy_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    record = dict(self._record, active_count=active_foreground_count,
                                  last_finished=last_foreground_finished_at)
                    _write(self._directory_fd, self.identity + ".json", record)
                    self._record = record
                    if active_foreground_count == 0:
                        fcntl.flock(self._busy_fd, fcntl.LOCK_UN)
                    fd = _open(self._directory_fd, self.identity + ".health", os.O_RDWR)
                    self._health_fd = fd
                    self._fds.append(fd)
                    if _inode(fd) != self._record["health_inode"]:
                        raise RegistryError("publisher health lock replaced")
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BaseException:
                self._failed = True
                self._revoke_health()
                try:
                    self._mark_fault()
                except Exception:
                    # Live-but-unhealthy remains UNKNOWN even if signaling fails.
                    pass
                raise

    def _revoke_health(self):
        if self._health_fd is not None:
            fd, self._health_fd = self._health_fd, None
            self._fds.remove(fd)
            _close(fd)

    def _mark_fault(self):
        fcntl.flock(self._fault_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

    def degrade(self):
        """Withdraw trust without needing a successful metadata/fault write."""
        if self._pid != os.getpid() or self._closed:
            return
        with self._mutex:
            self._failed = True
            self._revoke_health()
            try:
                self._mark_fault()
            except Exception:
                pass

    def _close_fds(self):
        for fd in reversed(self._fds):
            _close(fd)
        self._fds.clear()

    def close(self):
        """Close ownership without erasing history; active close is crash recovery."""
        if self._closed:
            return
        with self._mutex:
            if not self._closed:
                self._close_fds()
                self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
