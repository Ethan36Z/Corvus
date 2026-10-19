"""Exact pinned CPU service startup, with output containment before imports."""
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from guard import contain_output, configure_logging, emit, Outcomes

contain_output()
configure_logging()

# Preserve the installed entrypoint's optional model provisioning command.
# Child stdout/stderr inherit contained descriptors; never pipe their text back.
if os.environ.get('DOWNLOAD_MODEL') == 'true':
    emit('download')
    result = subprocess.run([
        sys.executable, 'download_model.py', '--output', 'api/src/models/v1_1_zh',
        '--voices-output', 'api/src/voices/v1_1_zh',
    ], check=False)
    if result.returncode:
        emit('exit', 'ERROR')
        raise SystemExit(result.returncode)

# Main's original logger setup runs only at import; contain it too, then replace.
sys.path.insert(0, '/app')
from api.src.main import app
configure_logging()
import uvicorn
emit('startup')
uvicorn.run(Outcomes(app), host='0.0.0.0', port=8880,
            log_config=None, access_log=False, log_level='debug')
