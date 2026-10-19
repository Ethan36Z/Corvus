"""Offline credential distribution and one-line WebUI ownership specialization.

Never prints/returns credential values. Run distribute only in an isolated
provisioning helper with an existing secret read-only and a new protected output.
"""
import hashlib
import hmac
import os
from pathlib import Path
import stat

ROOT = Path(__file__).resolve().parents[4]
PROTOCOL_SHA256 = 'eef17564962707b60143e9e3680733b095b67e458689b2ac6ed9fb2a2334768a'
WEBUI_IMAGE = 'sha256:88330ac2e1aa941386d8d2aaff5640f77d7343557969b74452798a6968bc60de'
BRIDGE_IMAGE = 'sha256:5d3cd6aff2db1a9712ce98669942d093858640298e9c04903f3cee3b510dc6b2'


def webui_protocol():
    source = (ROOT / 'app/stt_protocol.py').read_bytes()
    if hashlib.sha256(source).hexdigest() != PROTOCOL_SHA256:
        raise ValueError('Pinned credential validator changed.')
    old = b'metadata.st_uid != 10001'
    if source.count(old) != 1:
        raise ValueError('Unexpected credential owner check.')
    return source.replace(old, b'metadata.st_uid != 0')


def read_secret(path, owner):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        meta = os.fstat(fd)
        if (not stat.S_ISREG(meta.st_mode) or meta.st_uid != owner
                or stat.S_IMODE(meta.st_mode) != 0o400 or meta.st_size != 64
                or meta.st_nlink != 1):
            raise ValueError('Invalid credential metadata.')
        data = os.read(fd, 65)
        if len(data) != 64 or any(c not in b'0123456789abcdef' for c in data):
            raise ValueError('Invalid credential format.')
        return data
    finally:
        os.close(fd)


def distribute(source, output):
    """Copy existing credential to fresh 0700 consumer dirs, 0400 owner files.

    The provisioning container is root with narrowly scoped copy/chown caps;
    consumers retain their original UIDs and zero capabilities. No overwrite.
    """
    output = Path(output)
    meta = output.lstat()
    if (not stat.S_ISDIR(meta.st_mode) or stat.S_IMODE(meta.st_mode) != 0o700
            or any(output.iterdir()) or os.geteuid() != 0):
        raise ValueError('Fresh protected credential directory required.')
    token = read_secret(source, 10001)
    for name, uid in [('webui', 0), ('bridge', 10001)]:
        parent = output / name
        parent.mkdir(mode=0o700)
        os.chown(parent, uid, uid)
        target = parent / 'credential'
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o400)
        try:
            with os.fdopen(fd, 'wb', closefd=False) as f:
                f.write(token)
                f.flush()
                os.fchown(fd, uid, uid)
                os.fchmod(fd, 0o400)
                os.fsync(fd)
        finally:
            os.close(fd)
    if not hmac.compare_digest(read_secret(output/'webui/credential', 0),
                               read_secret(output/'bridge/credential', 10001)):
        raise ValueError('Credential distribution failed.')
    # Neither credential bytes nor a credential digest are returned/published.
