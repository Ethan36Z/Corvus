"""Private digest-file authentication; no credentials in source or process globals."""
import hashlib
import hmac
import os
from pathlib import Path
import re
import stat


class KeyConfigurationError(ValueError):
    pass


def check_key_file(path, key):
    """Read afresh for atomic rotation; fail closed, no stale allowlist cache.

    Format: one lowercase SHA-256 hex digest per line, maximum 16 keys.
    A private, owned, non-symlink parent and a 0600 owned regular file are required.
    Open relative to the checked directory FD; never follow a replacement symlink.
    """
    directory = fd = None
    try:
        p = Path(path)
        if not p.is_absolute():
            raise ValueError()
        flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW
        directory = os.open(p.parent, flags | os.O_DIRECTORY)
        parent = os.fstat(directory)
        if parent.st_uid != os.geteuid() or stat.S_IMODE(parent.st_mode) != 0o700:
            raise ValueError()
        fd = os.open(p.name, flags | os.O_NONBLOCK, dir_fd=directory)
        before = os.fstat(fd)
        if (not stat.S_ISREG(before.st_mode) or before.st_uid != os.geteuid()
                or stat.S_IMODE(before.st_mode) != 0o600 or before.st_nlink != 1):
            raise ValueError()
        data = os.read(fd, 2049)
        after = os.fstat(fd)
        if (len(data) > 2048 or before.st_size != len(data)
                or (before.st_size, before.st_mtime_ns, before.st_ctime_ns)
                != (after.st_size, after.st_mtime_ns, after.st_ctime_ns)):
            raise ValueError()
        digests = data.decode('ascii').splitlines()
        if (not 1 <= len(digests) <= 16 or len(set(digests)) != len(digests)
                or any(re.fullmatch('[0-9a-f]{64}', x) is None for x in digests)):
            raise ValueError()
        actual = hashlib.sha256(key.encode('ascii')).hexdigest()
        # Evaluate every comparison, including keys after the matching one.
        return bool(sum(hmac.compare_digest(actual, candidate) for candidate in digests))
    except (OSError, ValueError, TypeError, UnicodeError):
        raise KeyConfigurationError('API key configuration unavailable') from None
    finally:
        if fd is not None:
            os.close(fd)
        if directory is not None:
            os.close(directory)
