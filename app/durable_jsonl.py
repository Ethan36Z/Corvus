"""Small append/fsync primitive shared by derived operational JSONL logs."""

import fcntl
import json
import os
from pathlib import Path
import stat


def append_jsonl(path, record, *, validate_records=None):
    """Append under flock; return only after file and directory fsync succeed."""
    path = Path(path)
    data = (json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_CLOEXEC | os.O_NOFOLLOW, 0o600)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError("log must be a regular file")
        fcntl.flock(fd, fcntl.LOCK_EX)
        initial_size = os.fstat(fd).st_size
        if initial_size and os.pread(fd, 1, initial_size - 1) != b"\n":
            raise ValueError("log has an incomplete record")
        if validate_records is not None:
            # Validate under the append lock, so a concurrent event cannot race
            # a ledger identity/state check. Existing shadow writes are unchanged.
            validate_records([*_read_records(fd), record])
        try:
            remaining = memoryview(data)
            while remaining:
                written = os.write(fd, remaining)
                if written <= 0:
                    raise OSError("log write failed")
                remaining = remaining[written:]
            os.fsync(fd)
            directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except Exception:
            # Best-effort rollback under the same lock; failure is never success.
            os.ftruncate(fd, initial_size)
            os.fsync(fd)
            raise
    finally:
        os.close(fd)


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _invalid_constant(value):
    raise ValueError("non-finite JSON value")


def _read_records(fd):
    with os.fdopen(fd, "rb", closefd=False) as stream:
        stream.seek(0)
        records = []
        for line_number, line in enumerate(stream, 1):
            if not line.endswith(b"\n"):
                raise ValueError(f"incomplete JSONL record at line {line_number}")
            try:
                record = json.loads(line.decode("utf-8"), object_pairs_hook=_object,
                                    parse_constant=_invalid_constant)
                if not isinstance(record, dict):
                    raise ValueError("record must be an object")
            except (ValueError, UnicodeError, RecursionError) as exc:
                raise ValueError(f"invalid JSONL record at line {line_number}") from exc
            records.append(record)
        return records


def read_jsonl(path):
    """Read a locked snapshot without creating files or repairing damaged tails."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        return []
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError("log must be a regular file")
        fcntl.flock(fd, fcntl.LOCK_SH)
        return _read_records(fd)
    finally:
        os.close(fd)
