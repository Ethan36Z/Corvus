"""Local interactive root copy only. Reuse credential_repair, never rotate secrets."""
import hashlib
import hmac
import importlib.util
import os
from pathlib import Path
import stat
import sys

ROOT = Path(__file__).resolve().parents[4]
SOURCE = Path('/home/ethan/corvus-stt-activation-recovery.o35xbp1g/stt-bridge.key')
REVIEWED = Path('/home/ethan/corvus-stt-retry3-recovery._vhexclc')
DEST = Path('/etc/corvus-lab/stt')
spec = importlib.util.spec_from_file_location('existing_credential_repair', ROOT/'deploy/lab/stt/activation/credential_repair.py')
repair = importlib.util.module_from_spec(spec)
spec.loader.exec_module(repair)

def regular(path, uid, gid, mode):
    info = path.lstat()
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != uid or info.st_gid != gid
            or stat.S_IMODE(info.st_mode) != mode or info.st_nlink != 1):
        raise ValueError('Unexpected protected file metadata')

def public_material():
    regular(REVIEWED/'webui-protocol.py',1000,1000,0o444)
    regular(REVIEWED/'stt-admissions',1000,1000,0o444)
    protocol = (REVIEWED/'webui-protocol.py').read_bytes()
    if protocol != repair.webui_protocol():
        raise ValueError('Pinned WebUI owner-check artifact mismatch')
    admission = (REVIEWED/'stt-admissions').read_bytes()
    if admission not in (b'open\n', b'closed\n'):
        raise ValueError('Invalid existing admission state')
    return protocol, admission

def validate_destination(original, protocol, admission):
    for name,owner in [('webui',0),('bridge',10001)]:
        p=DEST/name
        info=p.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid!=owner or info.st_gid!=owner or stat.S_IMODE(info.st_mode)!=0o700:
            raise ValueError('Consumer directory metadata mismatch')
        regular(p/'credential',owner,owner,0o400)
        if not hmac.compare_digest(repair.read_secret(p/'credential',owner),original):
            raise ValueError('Credential equality failed; no rotation allowed')
    for name,data,owner in [('webui-protocol.py',protocol,0),('stt-admissions',admission,1000)]:
        regular(DEST/name,owner,owner,0o444)
        if (DEST/name).read_bytes()!=data:
            raise ValueError('Persistent public artifact mismatch')

def provision():
    if os.geteuid()!=0 or not os.isatty(0):
        raise ValueError('Run locally with interactive sudo; never provide a password to the program')
    os.umask(0o077)
    for parent in [Path('/etc'),Path('/etc/corvus-lab')]:
        if not parent.exists():parent.mkdir(mode=0o755)
        meta=parent.lstat()
        if not stat.S_ISDIR(meta.st_mode) or meta.st_uid!=0 or stat.S_IMODE(meta.st_mode)&0o022:
            raise ValueError('Unsafe destination parent')
    for parent in [SOURCE.parent, REVIEWED]:
        meta=parent.lstat()
        if not stat.S_ISDIR(meta.st_mode) or meta.st_uid!=1000 or stat.S_IMODE(meta.st_mode)!=0o700:
            raise ValueError('Protected recovery directory mismatch')
    regular(SOURCE,10001,10001,0o400)
    protocol, admission=public_material()
    original=repair.read_secret(SOURCE,10001)
    if DEST.exists() or DEST.is_symlink():
        meta=DEST.lstat()
        if not stat.S_ISDIR(meta.st_mode) or meta.st_uid!=0 or meta.st_gid!=0 or stat.S_IMODE(meta.st_mode)!=0o700:
            raise ValueError('Unsafe persistent directory')
        validate_destination(original,protocol,admission)
        print('PERSISTENT_STT_MATERIAL_ALREADY_VERIFIED; no overwrite or rotation')
        return
    DEST.mkdir(mode=0o700)
    repair.distribute(SOURCE,DEST)
    for name,data,owner in [('webui-protocol.py',protocol,0),('stt-admissions',admission,1000)]:
        fd=os.open(DEST/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o444)
        try:
            assert os.write(fd,data)==len(data);os.fchown(fd,owner,owner);os.fchmod(fd,0o444);os.fsync(fd)
        finally:os.close(fd)
    validate_destination(original,protocol,admission)
    print('PERSISTENT_STT_MATERIAL_READY; original credential reused; no services changed')

if __name__=='__main__':
    try:provision()
    except Exception:
        print('STOP: protected material validation/copy failed; no automatic overwrite or credential rotation. Preserve state for review.',file=sys.stderr)
        sys.exit(1)
