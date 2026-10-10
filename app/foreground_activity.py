"""Process-local activity with optional registry publication; monotonic timestamps."""

from contextlib import contextmanager
from dataclasses import dataclass
import logging
import os
from threading import Lock
from time import monotonic

from app.runtime_config import (
    FOREGROUND_REGISTRY_DIR, FOREGROUND_REGISTRY_PUBLISHER,
    FOREGROUND_REGISTRY_EXPECTED_PUBLISHERS,
)


logger = logging.getLogger(__name__)


class ForegroundPublicationError(RuntimeError):
    """Tracker lifecycle misuse; metadata failures must not block generation."""


@dataclass(frozen=True)
class ForegroundActivitySnapshot:
    active_foreground_count: int
    last_foreground_started_at: float | None
    last_foreground_finished_at: float | None


class ForegroundActivityTracker:
    def __init__(self, clock=monotonic, *, registry_path=None,
                 logical_publisher=None, expected_publishers=()):
        self._clock = clock
        self._lock = Lock()
        self._active_foreground_count = 0
        self._last_foreground_started_at = None
        self._last_foreground_finished_at = None
        self._pid = os.getpid()
        self._registry_path = registry_path
        self._logical_publisher = logical_publisher
        self._expected_publishers = expected_publishers
        self._publisher = None
        self._publication_failed = False
        self._closing = False

    def _check_process(self):
        if self._pid != os.getpid():
            raise ForegroundPublicationError("Create a new tracker after fork")

    def _start_locked(self):
        if (self._registry_path is None or self._publisher is not None or
            self._publication_failed):
            return
        # Import only when enabled; no directory provisioning or import-time IO.
        try:
            from app.foreground_registry import ForegroundPublisher, ForegroundRegistry
            registry = ForegroundRegistry(self._registry_path, clock=self._clock,
                                          expected_publishers=self._expected_publishers)
            registry.initialize()
            # Missing peers / UNKNOWN must not prevent a publisher from joining.
            # Validation stays in the core; consumer health is independent.
            self._publisher = ForegroundPublisher(registry,
                                                   logical_publisher=self._logical_publisher)
        except Exception as exc:
            self._publication_failed = True
            self._log_failure("initialization", exc)
            return
        logger.info("Foreground registry publisher started path=%s identity=%s",
                    self._registry_path, self._publisher.identity)

    def start(self):
        """API startup, after worker PID exists; repeated starts reuse ownership."""
        self._check_process()
        with self._lock:
            if self._active_foreground_count:
                raise ForegroundPublicationError("Cannot start during foreground activity")
            self._closing = False
            self._start_locked()

    def _log_failure(self, phase, exc):
        logger.error("Foreground registry %s failed path=%s: %s; "
                     "foreground continues; background must defer; repair registry/restart publisher",
                     phase, self._registry_path, exc)

    def _publish_locked(self, phase):
        if self._publisher is not None and not self._publication_failed:
            try:
                self._publisher.publish(self._active_foreground_count,
                                        self._last_foreground_finished_at)
            except Exception as exc:
                self._publication_failed = True
                try:
                    self._publisher.degrade()
                except Exception as health_exc:
                    self._log_failure("health revocation", health_exc)
                self._log_failure(phase, exc)

    def _close_locked(self):
        if self._publisher is not None:
            try:
                self._publisher.close()
            except Exception as exc:
                self._log_failure("shutdown", exc)
            finally:
                self._publisher = None
        self._publication_failed = False

    def close(self):
        """Drain ownership; never drop a busy lock over a live model call."""
        self._check_process()
        with self._lock:
            if self._registry_path is None:
                return
            self._closing = True
            if self._active_foreground_count == 0:
                self._close_locked()
            else:
                logger.warning("Foreground registry shutdown awaiting %s active calls; "
                               "busy ownership retained", self._active_foreground_count)

    @contextmanager
    def generation(self):
        """Balance one increment/decrement, including exceptional exits."""
        self._check_process()
        with self._lock:
            if self._closing:
                raise ForegroundPublicationError("Foreground publisher is shutting down")
            self._start_locked()
            self._last_foreground_started_at = self._clock()
            self._active_foreground_count += 1
            try:
                self._publish_locked("begin publication")
            except BaseException as exc:
                self._active_foreground_count -= 1
                self._last_foreground_finished_at = self._clock()
                # Interrupts are not scheduling errors: propagate, but balance.
                self._publication_failed = True
                self._log_failure("interrupted begin publication", exc)
                raise
        try:
            yield
        finally:
            with self._lock:
                self._active_foreground_count -= 1
                self._last_foreground_finished_at = self._clock()
                try:
                    self._publish_locked("completion publication")
                finally:
                    if self._closing and self._active_foreground_count == 0:
                        self._close_locked()

    def snapshot(self) -> ForegroundActivitySnapshot:
        """Return an immutable, consistent copy without changing activity."""
        self._check_process()
        with self._lock:
            return ForegroundActivitySnapshot(
                active_foreground_count=self._active_foreground_count,
                last_foreground_started_at=self._last_foreground_started_at,
                last_foreground_finished_at=self._last_foreground_finished_at,
            )


_tracker = ForegroundActivityTracker(
    registry_path=FOREGROUND_REGISTRY_DIR,
    logical_publisher=FOREGROUND_REGISTRY_PUBLISHER,
    expected_publishers=FOREGROUND_REGISTRY_EXPECTED_PUBLISHERS,
)


def _after_fork():
    global _tracker
    _tracker = ForegroundActivityTracker(
        registry_path=_tracker._registry_path,
        logical_publisher=_tracker._logical_publisher,
        expected_publishers=_tracker._expected_publishers,
    )


os.register_at_fork(after_in_child=_after_fork)


def start_foreground_publication():
    _tracker.start()


def stop_foreground_publication():
    _tracker.close()


@contextmanager
def track_foreground_generation():
    try:
        with _tracker.generation():
            yield
    except ForegroundPublicationError as exc:
        from app.model_client import ModelClientError

        raise ModelClientError("FOREGROUND_REGISTRY_UNAVAILABLE", str(exc)) from exc


def snapshot() -> ForegroundActivitySnapshot:
    return _tracker.snapshot()
