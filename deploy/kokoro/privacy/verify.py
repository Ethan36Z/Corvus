"""Fail the derivative build on any unexpected installed application source."""
import hashlib
import json
from pathlib import Path


def verify(root, lock):
    expected = json.loads(Path(lock).read_text())
    root = Path(root)
    actual = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(root.rglob('*.py'))}
    if actual != expected:
        raise SystemExit('Pinned Kokoro source mismatch')


if __name__ == '__main__':
    verify('/app/api/src', '/opt/corvus-kokoro/source-lock.json')
    print('Pinned Kokoro application source verified')
