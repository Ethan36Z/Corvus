"""Process-local foreground generation activity; timestamps are monotonic seconds."""

from contextlib import contextmanager
from dataclasses import dataclass
from threading import Lock
from time import monotonic


@dataclass(frozen=True)
class ForegroundActivitySnapshot:
    active_foreground_count: int
    last_foreground_started_at: float | None
    last_foreground_finished_at: float | None


class ForegroundActivityTracker:
    def __init__(self, clock=monotonic):
        self._clock = clock
        self._lock = Lock()
        self._active_foreground_count = 0
        self._last_foreground_started_at = None
        self._last_foreground_finished_at = None

    @contextmanager
    def generation(self):
        """Balance one increment/decrement, including exceptional exits."""
        with self._lock:
            self._last_foreground_started_at = self._clock()
            self._active_foreground_count += 1
        try:
            yield
        finally:
            with self._lock:
                self._active_foreground_count -= 1
                self._last_foreground_finished_at = self._clock()

    def snapshot(self) -> ForegroundActivitySnapshot:
        """Return an immutable, consistent copy without changing activity."""
        with self._lock:
            return ForegroundActivitySnapshot(
                active_foreground_count=self._active_foreground_count,
                last_foreground_started_at=self._last_foreground_started_at,
                last_foreground_finished_at=self._last_foreground_finished_at,
            )


_tracker = ForegroundActivityTracker()


def track_foreground_generation():
    return _tracker.generation()


def snapshot() -> ForegroundActivitySnapshot:
    return _tracker.snapshot()
