"""Process-local activity with optional registry publication; monotonic timestamps."""

from contextlib import contextmanager
from dataclasses import dataclass
import logging
import os
from threading import Lock
from time import monotonic

from app.runtime_config import FOREGROUND_REGISTRY_DIR


logger = logging.getLogger(__name__)


class ForegroundPublicationError(RuntimeError):
    """Enabled publication cannot safely admit a new foreground model call."""


@dataclass(frozen=True)
class ForegroundActivitySnapshot:
    active_foreground_count: int
    last_foreground_started_at: float | None
    last_foreground_finished_at: float | None


class ForegroundActivityTracker:
    def __init__(self, clock=monotonic, *, registry_path=None):
        self._clock = clock
        self._lock = Lock()
        self._active_foreground_count = 0
        self._last_foreground_started_at = None
        self._last_foreground_finished_at = None
        self._pid = os.getpid()
        self._registry_path = registry_path
        self._publisher = None
        self._closing = False

    def _check_process(self):
        if self._pid != os.getpid():
            raise ForegroundPublicationError("Create a new tracker after fork")

    def _start_locked(self):
        if self._registry_path is None or self._publisher is not None:
            return
        # Import only when enabled; no directory provisioning or import-time IO.
        from app.foreground_registry import (
            ForegroundPublisher, ForegroundRegistry, RegistryState,
        )

        try:
            registry = ForegroundRegistry(self._registry_path, clock=self._clock)
            registry.initialize()
            state = registry.read()
            if state.state == RegistryState.UNKNOWN:
                raise ForegroundPublicationError(f"Registry state is UNKNOWN: {state.reason}")
            self._publisher = ForegroundPublisher(registry)
        except Exception as exc:
            self._log_failure("initialization", exc)
            raise ForegroundPublicationError(
                "Foreground registry unavailable; repair configured directory and restart"
            ) from exc
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
                     "repair registry/restart publisher; state must defer background work",
                     phase, self._registry_path, exc)

    def _publish_locked(self):
        if self._publisher is not None:
            self._publisher.publish(self._active_foreground_count,
                                    self._last_foreground_finished_at)

    def _close_locked(self):
        if self._publisher is not None:
            self._publisher.close()
            self._publisher = None

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
                self._publish_locked()
            except BaseException as exc:
                self._active_foreground_count -= 1
                self._last_foreground_finished_at = self._clock()
                self._log_failure("begin publication (model call blocked)", exc)
                if isinstance(exc, Exception):
                    raise ForegroundPublicationError(
                        "Foreground registry publication failed; repair registry and restart"
                    ) from exc
                raise
        try:
            yield
        finally:
            with self._lock:
                self._active_foreground_count -= 1
                self._last_foreground_finished_at = self._clock()
                try:
                    self._publish_locked()
                except Exception as exc:
                    # The core retains its fault lock (UNKNOWN). Do not discard a
                    # valid model reply or replace the original generation error.
                    self._log_failure("completion publication", exc)
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


_tracker = ForegroundActivityTracker(registry_path=FOREGROUND_REGISTRY_DIR)


def _after_fork():
    global _tracker
    _tracker = ForegroundActivityTracker(registry_path=_tracker._registry_path)


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
