"""Validate docker compose config --format json output; no daemon/service calls."""
import copy
import json
from pathlib import Path
import sys

IMAGE = 'sha256:caf0cd77c922e9c53f10a9bc17c2f74cc2295d12e7b0f96b630fb3b3c55a0026'
COMMAND = 'exec /app/build/bin/whisper-server --host 0.0.0.0 --port 8080 -m /models/ggml-small.bin -t 8 -l auto --no-gpu >/dev/null 2>&1'

def validate(config):
    assert set(config['services']) == {'corvus-whisper-dictation'}
    service = config['services']['corvus-whisper-dictation']
    assert service['image'] == IMAGE and service['pull_policy'] == 'never'
    assert service['read_only'] and service['user'] == '10001:10001'
    assert service['cap_drop'] == ['ALL'] and service['security_opt'] == ['no-new-privileges:true']
    assert service['restart'] == 'no' and not service.get('privileged')
    assert not service.get('ports') and not service.get('devices')
    assert not service.get('tmpfs') and not service.get('volumes_from')
    assert service['entrypoint'] == ['/bin/sh', '-c'] and service['command'] == [COMMAND]
    assert service['logging']['driver'] == 'none' and service['pids_limit'] == 64
    assert int(service['mem_limit']) == int(service['memswap_limit']) == 1140850688
    assert service['cpus'] == 8
    # Compose JSON elides numeric zero fields; the required core entry remains.
    core = service['ulimits']['core']
    assert core.get('soft',0) == core.get('hard',0) == 0
    assert set(service['networks']) == {'dictation-private'}
    assert config['networks']['dictation-private']['internal']
    assert not config['networks']['dictation-private'].get('external')
    assert len(service['volumes']) == 1
    model = service['volumes'][0]
    assert model['type'] == 'bind' and model['target'] == '/models/ggml-small.bin'
    assert Path(model['source']).name == 'ggml-small.bin'
    assert model['read_only'] and not model['bind']['create_host_path']
    assert not service.get('environment') and not service.get('env_file')
    return True

if __name__ == '__main__':
    config = json.loads(Path(sys.argv[1]).read_text())
    assert validate(config)
    # Negative cases demonstrate that weakenings fail closed in review.
    for field, value in [('read_only',False), ('ports',[{'target':8080,'published':'8107'}]),
                         ('command',[COMMAND+' --convert']), ('logging',{'driver':'json-file'}),
                         ('memswap_limit','2147483648')]:
        bad=copy.deepcopy(config);bad['services']['corvus-whisper-dictation'][field]=value
        try: validate(bad)
        except AssertionError: pass
        else: raise AssertionError('Unsafe configuration accepted: '+field)
    print('Private service config + 5 unsafe-configuration rejection cases passed')
