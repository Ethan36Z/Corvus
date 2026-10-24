"""Deployment preflight and direct Uvicorn process; never probes inference.

Run only inside the reviewed minimal root. Keeping Uvicorn in this process makes
systemd SIGTERM reach its graceful handler directly, without a shell supervisor.
"""
import hashlib
import json
import os
from pathlib import Path
import sys

EXPECTED_ENV = {
    'CORVUS_API_ENABLED': 'TRUE',
    'CORVUS_API_KEY_DIGEST_FILE': '/run/corvus-api-keys/keys.sha256',
    'CORVUS_MODEL_BASE_URL': 'http://127.0.0.1:8095',
    'CORVUS_API_FOREGROUND_REGISTRY_DIR': '',
}
APP_FILES = {'openai_api.py', 'api_auth.py', 'model_client.py',
             'foreground_activity.py', 'runtime_config.py'}
COMMIT = 'c2bc84f7cc898ada10b23f5e23f526ad310d4952'


def preflight(root=Path('/')):
    if any(os.environ.get(k) != v for k, v in EXPECTED_ENV.items()):
        raise ValueError('deployment configuration mismatch')
    if any(k.startswith('CORVUS_') and k not in EXPECTED_ENV for k in os.environ):
        raise ValueError('unexpected Corvus configuration')
    if any(k.lower().endswith('_proxy') for k in os.environ):
        raise ValueError('proxy environment prohibited')
    # The service must not see host homes/configuration, memories or companion code.
    for path in ['home/ethan', 'root/.ssh', 'etc/corvus-lab', 'srv', 'opt/corvus/memory',
                 'opt/corvus/personality', 'opt/corvus/app/conversation_runtime.py']:
        try:
            visible = (root / path).exists()
        except PermissionError:
            visible = False  # ProtectHome may make these paths inaccessible.
        if visible:
            raise ValueError('private host path visible')
    manifest = json.loads((root / 'opt/deployment/source-manifest.json').read_text())
    files = manifest['files']
    if manifest['implementation_commit'] != COMMIT or set(files) != APP_FILES:
        raise ValueError('unapproved implementation manifest')
    app = root / 'opt/corvus/app'
    if {p.name for p in app.iterdir()} != APP_FILES:
        raise ValueError('unexpected application files')
    for name, expected in files.items():
        p = app / name
        if p.is_symlink() or hashlib.sha256(p.read_bytes()).hexdigest() != expected:
            raise ValueError('implementation integrity mismatch')
    return root / 'run/corvus-api-keys/keys.sha256'


def main():
    try:
        key_file = preflight()
        sys.path.insert(0, '/opt/corvus')
        from app.api_auth import check_key_file
        # Validate file safety/format without possessing a real client key.
        check_key_file(key_file, 'DeploymentPreflightSyntheticKey_' + 'X' * 32)
        from app.openai_api import app
        import uvicorn
    except Exception:
        # Never print filesystem/credential contents or exception details.
        raise SystemExit('Corvus API startup checks failed') from None
    uvicorn.run(app, host='127.0.0.1', port=18120, workers=1,
                loop='asyncio', http='h11', limit_concurrency=8, backlog=8,
                access_log=False, log_level='critical', proxy_headers=False,
                timeout_graceful_shutdown=None)


if __name__ == '__main__':
    main()
