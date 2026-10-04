"""Capture private reboot evidence, or verify it without changing service state."""
import argparse
import hashlib
import itertools
import json
import os
from pathlib import Path
import sqlite3
import stat
import subprocess
import time
import urllib.request

LAB = Path('/home/ethan/srv/apps/corvus-lab')
PRIVATE = Path('/home/ethan/.config/corvus-lab')
BASELINE = PRIVATE / 'reboot-acceptance-baseline.json'
FINAL_CHECKPOINT = LAB / 'deploy/lab/acceptance/final-reboot-checkpoint.json'
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))

def require(condition, message):
    if not condition:
        raise RuntimeError(message)

def cli(*args):
    return subprocess.check_output(args, text=True).strip()

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

def compatible_host_config_hashes(host_config):
    """Only unset Docker DNS lists may vary between null and [].

    Retain all other fields exactly. Enumerating these representations also
    supports the existing raw-hash baseline without rewriting it.
    """
    keys = [key for key in ('Dns', 'DnsOptions', 'DnsSearch')
            if key in host_config and host_config[key] in (None, [])]
    hashes = set()
    for values in itertools.product((None, []), repeat=len(keys)):
        candidate = dict(host_config)
        candidate.update(zip(keys, values))
        hashes.add(digest(candidate))
    return sorted(hashes)


def containers_match(current, previous, compatible_hashes):
    if current.keys() != previous.keys():
        return False
    for name, expected in previous.items():
        actual = dict(current[name])
        if expected['host_config_sha256'] not in compatible_hashes[name]:
            return False
        actual['host_config_sha256'] = expected['host_config_sha256']
        if actual != expected:
            return False
    return True


def verify_dense_readiness():
    # Use Lab's pinned dependencies and explicit Lab paths. The child only
    # reads persistent state; no schema ensure, indexing or progress writes.
    environment = dict(os.environ, CORVUS_DATA_DIR='/home/ethan/srv/data/corvus/lab')
    output = subprocess.check_output(
        [str(LAB / '.venv/bin/python'), '-B',
         str(LAB / 'deploy/lab/check_dense_readiness.py')],
        cwd=LAB, env=environment, text=True)
    return json.loads(output)


def unit(name):
    output = cli('systemctl', 'show', name, '-p', 'MainPID', '-p', 'ActiveState', '-p', 'SubState',
                 '-p', 'UnitFileState', '-p', 'Restart', '-p', 'ExecMainStartTimestamp')
    result = dict(line.split('=', 1) for line in output.splitlines())
    pid = int(result['MainPID'])
    require(pid > 0 and result['ActiveState'] == 'active' and result['SubState'] == 'running', name + ' not running')
    result['start_ticks'] = Path('/proc', str(pid), 'stat').read_text().rsplit(')', 1)[1].split()[19]
    require(result['UnitFileState'] == 'enabled', name + ' not boot enabled')
    return result

def container(name):
    raw = json.loads(cli('docker', 'inspect', name))[0]
    state = raw['State']
    safe = {'Id': raw['Id'], 'Image': raw['Image'], 'Mounts': raw['Mounts'],
            'restart': raw['HostConfig']['RestartPolicy']['Name'],
            'host_config_sha256': digest(raw['HostConfig']),
            'environment_sha256': digest(sorted(raw['Config']['Env']))}
    return raw, safe, state

def file_data(path):
    result = {}
    def walk(directory_fd, prefix):
        with os.scandir(directory_fd) as iterator:
            entries = sorted(iterator, key=lambda item: item.name)
        for entry in entries:
            relative = prefix + entry.name
            metadata = entry.stat(follow_symlinks=False)
            if stat.S_ISDIR(metadata.st_mode):
                child = os.open(entry.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOATIME | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=directory_fd)
                try:
                    walk(child, relative + '/')
                finally:
                    os.close(child)
            else:
                require(stat.S_ISREG(metadata.st_mode), 'Unexpected data file type')
                fd = os.open(entry.name, os.O_RDONLY | os.O_NOATIME | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=directory_fd)
                with os.fdopen(fd, 'rb') as stream:
                    before = os.fstat(stream.fileno())
                    value = hashlib.file_digest(stream, 'sha256').hexdigest()
                    after = os.fstat(stream.fileno())
                require((before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns), 'Data file changed during read')
                result[relative] = {'size': after.st_size, 'mtime_ns': after.st_mtime_ns, 'sha256': value}
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOATIME | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        walk(fd, '')
    finally:
        os.close(fd)
    return result


def production_data():
    result = file_data('/home/ethan/srv/data/corvus/private')
    require(len(result) == 445, 'Production file count changed')
    return result


def firewall_state():
    boot_id = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    path = LAB / 'deploy/lab/acceptance' / ('firewall-' + boot_id + '.json')
    require(path.is_file(), 'Capture read-only firewall evidence with sudo for this boot')
    require(path.stat().st_uid == 0, 'Firewall evidence must come from the root capture helper')
    evidence = json.loads(path.read_text())
    require(evidence.pop('boot_id') == boot_id, 'Firewall evidence is from another boot')
    evidence['services'] = cli('systemctl', 'show', 'nftables.service', 'ufw.service',
        'firewalld.service', '-p', 'LoadState', '-p', 'ActiveState', '-p', 'UnitFileState',
        '-p', 'FragmentPath')
    return evidence


def cgroup_state():
    return cli('systemctl', 'show', 'corvus-lab-api.service', 'corvus-api.service',
        '-p', 'Slice', '-p', 'ControlGroup', '-p', 'Delegate', '-p', 'MemoryMax',
        '-p', 'CPUQuotaPerSecUSec', '-p', 'TasksMax', '-p', 'AllowedCPUs',
        '-p', 'AllowedMemoryNodes')


def verify_original_invariants(now, previous):
    require(containers_match(now['containers'], previous['containers'],
                             now['compatible_host_config_sha256']),
            'Baseline mismatch: containers; stop and review, do not repair production')
    for key in ['unit_sha256', 'production_data', 'lab_rows_sha256', 'saved_chats_sha256']:
        require(now[key] == previous[key], 'Baseline mismatch: ' + key + '; stop and review, do not repair production')
    for name, state in now['units'].items():
        for field in ['Restart', 'UnitFileState']:
            require(state[field] == previous['units'][name][field], name + ' lifecycle setting changed')


def final_checkpoint(now):
    return {key: now[key] for key in ['boot_id', 'units', 'webui_started_at',
                                     'dense_state', 'dense_files', 'firewall_state', 'cgroup_state']}


def verify_final_checkpoint(now, checkpoint, after_reboot):
    require(checkpoint['original_baseline_sha256'] == hashlib.sha256(BASELINE.read_bytes()).hexdigest(),
            'Original durable baseline was changed')
    require((now['boot_id'] != checkpoint['boot_id']) if after_reboot else
            (now['boot_id'] == checkpoint['boot_id']), 'Unexpected boot identity for final reboot check')
    for key in ['dense_state', 'dense_files', 'firewall_state', 'cgroup_state']:
        require(now[key] == checkpoint[key], 'Final reboot checkpoint mismatch: ' + key)
    for name, state in now['units'].items():
        if after_reboot:
            require(state['ExecMainStartTimestamp'] != checkpoint['units'][name]['ExecMainStartTimestamp'],
                    name + ' still reports the pre-reboot process start')
        else:
            require(state == checkpoint['units'][name], name + ' process changed before final reboot')
    require((now['webui_started_at'] != checkpoint['webui_started_at']) if after_reboot else
            (now['webui_started_at'] == checkpoint['webui_started_at']),
            'Unexpected WebUI start time for final reboot check')

def request(path, token=None, payload=None):
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    req = urllib.request.Request('http://127.0.0.1:3003' + path, headers=headers,
                                 data=None if payload is None else json.dumps(payload).encode())
    with OPENER.open(req, timeout=10) as response:
        require(response.status == 200, 'Unexpected WebUI HTTP status')
        return json.load(response)

def webui_saved_state(manifest):
    credentials = json.loads((PRIVATE / 'admin-bootstrap.json').read_text())
    token = request('/api/v1/auths/signin', payload={'email': credentials['email'], 'password': credentials['password']})['token']
    functions = request('/api/v1/functions/', token)
    require(len(functions) == 1 and functions[0]['id'] == 'corvus_pipe' and functions[0]['is_active'], 'Pipe inventory changed')
    pipe = request('/api/v1/functions/id/corvus_pipe', token)
    require(hashlib.sha256(pipe['content'].encode()).hexdigest() == manifest['pipe_sha256'], 'Sealed Pipe checksum changed')
    require(request('/api/v1/functions/id/corvus_pipe/valves', token) == {
        'CORVUS_CHAT_URL': 'http://127.0.0.1:18096/api/chat', 'INSTANCE_ID': manifest['instance_id'],
        'WEB_MODE': 'off', 'TIMEOUT_SECONDS': 300}, 'Pipe valves changed')
    models = request('/api/models', token)['data']
    require(len(models) == 1 and models[0]['id'] == 'corvus_pipe' and 'pipe' in models[0], 'Model inventory changed')
    require(all(not value for value in models[0]['info']['meta']['capabilities'].values()), 'Model capabilities changed')
    require(not request('/openai/config', token)['ENABLE_OPENAI_API'], 'OpenAI enabled')
    require(not request('/ollama/config', token)['ENABLE_OLLAMA_API'], 'Ollama enabled')
    require(not request('/api/v1/configs/direct_connections', token)['ENABLE_DIRECT_CONNECTIONS'], 'Direct providers enabled')
    require(request('/api/v1/configs/tool_servers', token)['TOOL_SERVER_CONNECTIONS'] == [], 'Tool/Hindsight integration changed')
    config = request('/api/config', token)
    require(config['name'] == 'Corvus' and config['features']['auth'] and not config['features']['enable_signup'], 'Branding/auth/signup changed')
    evidence = json.loads((LAB / 'deploy/lab/acceptance/acceptance-evidence.json').read_text())
    chats = {}
    for key in ['chat_a', 'chat_b']:
        chat_id = evidence[key]
        chat = request('/api/v1/chats/' + chat_id, token)['chat']
        chats[chat_id] = digest(chat['history']['messages'])
    return chats

def health(wait_seconds):
    deadline = time.monotonic() + wait_seconds
    while True:
        try:
            with OPENER.open('http://127.0.0.1:18096/api/health', timeout=5) as response:
                require(json.load(response)['status'] == 'OK', 'Lab API degraded')
            require(request('/health')['status'] is True, 'WebUI unhealthy')
            return
        except Exception:
            if time.monotonic() >= deadline:
                raise RuntimeError('Lab health did not become ready within deadline') from None
            time.sleep(1)

def snapshot(wait_seconds):
    health(wait_seconds)
    dense_state = verify_dense_readiness()
    require(dense_state == {'table': 'evidence_dense_v1', 'canonical_messages': 6,
                           'indexed_messages': 6, 'progress_after': 6, 'caught_up': True},
            'Unexpected final Lab dense readiness state')
    with OPENER.open('http://127.0.0.1:8096/api/health', timeout=10) as response:
        production_health = json.load(response)
    require(production_health['status'] == 'OK', 'Production API degraded')
    units = {name: unit(name) for name in ['corvus-lab-api.service', 'corvus-api.service']}
    require(units['corvus-api.service']['Restart'] == 'on-failure', 'Production restart policy changed')
    require(units['corvus-lab-api.service']['Restart'] == 'no', 'Lab API restart policy changed')
    listeners = [line.split()[3] for line in cli('ss', '-H', '-ltn').splitlines()]
    for port in [8096, 18096, 3003]:
        require([value for value in listeners if value.endswith(':' + str(port))] == ['127.0.0.1:' + str(port)], 'Unexpected bind at ' + str(port))
    for port in [3001, 3002]:
        require(not any(value.endswith(':' + str(port)) for value in listeners), 'Retained WebUI listening')
    manifest = json.loads((LAB / 'deploy/lab/deployment.json').read_text())
    raw, webui, state = container('corvus-lab-open-webui')
    require(webui['restart'] == 'unless-stopped' and state['Running'] and state['Health']['Status'] == 'healthy', 'Lab WebUI lifecycle incorrect')
    require(webui['Image'] == manifest['image_id'] and not raw['HostConfig']['CgroupParent'], 'WebUI image/cgroup changed')
    require(len(webui['Mounts']) == 1 and webui['Mounts'][0]['Name'] == manifest['volume'], 'Lab volume changed')
    environment = dict(value.split('=', 1) for value in raw['Config']['Env'])
    require(environment['HOST'] == '127.0.0.1' and environment['PORT'] == '3003' and 'LD_PRELOAD' not in environment, 'WebUI environment incorrect')
    saved = {'webui': webui}
    host_hashes = {'webui': compatible_host_config_hashes(raw['HostConfig'])}
    for name, expected_id in [
        ('corvus-open-webui-ow1-open-webui-1', '17cc49346a65d0edfc34a6d50da1f0f5a0978763be67adef3eba4454d9b1ecb9'),
        ('corvus-ow2d-b-branded-ui', '670c3777cea198ed87363c7570ba086e977203b2829925a1544a90e0106196ec')]:
        retained_raw, saved[name], old_state = container(name)
        host_hashes[name] = compatible_host_config_hashes(retained_raw['HostConfig'])
        require(saved[name]['Id'] == expected_id and saved[name]['restart'] == 'no' and old_state['Status'] == 'exited', 'Retained WebUI changed')
    for name in ['corvus-llama', 'hindsight-lab']:
        shared_raw, saved[name], _ = container(name)
        host_hashes[name] = compatible_host_config_hashes(shared_raw['HostConfig'])
    require(cli('systemctl', 'is-enabled', 'docker.service') == 'enabled', 'Docker boot enablement changed')
    unit_hashes = {name: hashlib.sha256(Path('/etc/systemd/system', name).read_bytes()).hexdigest() for name in units}
    path = Path('/home/ethan/srv/data/corvus/lab/corvus.db')
    require(not any(Path(str(path) + suffix).exists() for suffix in ['-wal', '-shm', '-journal']), 'Review SQLite sidecars before immutable read')
    with sqlite3.connect('file:' + str(path) + '?mode=ro&immutable=1', uri=True) as connection:
        connection.execute('pragma query_only=ON')
        rows = connection.execute('select id,session_id,role,content from messages order by id').fetchall()
    require(len(rows) == 6 and len({row[1] for row in rows}) == 2, 'Canonical Lab acceptance history changed')
    require(cli('git', '-C', '/home/ethan/srv/apps/small-vram-companion', 'rev-parse', 'HEAD') == manifest['baseline'], 'Production HEAD changed')
    require(cli('git', '-C', '/home/ethan/srv/apps/small-vram-companion', 'status', '--porcelain') == '', 'Production worktree changed')
    require(not any(Path(path).exists() for path in ['/etc/corvus-lab', '/etc/systemd/system/corvus-lab-webui-guard.service', '/sys/fs/cgroup/corvuslabwebui.slice']), 'Destination guard appeared')
    return {'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(), 'units': units,
            'unit_sha256': unit_hashes, 'containers': saved, 'webui_started_at': state['StartedAt'],
            'compatible_host_config_sha256': host_hashes, 'dense_state': dense_state,
            'dense_files': file_data('/home/ethan/srv/data/corvus/lab/corvus-retrieval.lancedb'),
            'firewall_state': firewall_state(), 'cgroup_state': cgroup_state(),
            'production_health': production_health,
            'production_data': production_data(), 'lab_rows_sha256': digest(rows),
            'saved_chats_sha256': webui_saved_state(manifest)}

def main():
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--capture', action='store_true')
    mode.add_argument('--prepare-final-reboot', action='store_true')
    mode.add_argument('--before-reboot', action='store_true')
    mode.add_argument('--after-reboot', action='store_true')
    parser.add_argument('--wait-seconds', type=int, default=180)
    args = parser.parse_args()
    now = snapshot(args.wait_seconds)
    if args.capture:
        original = json.loads(Path('/tmp/corvus-ow2e-a/production-data-recovery-baseline.json').read_text())
        require(now['production_data'] == original, 'Production differs from original accepted baseline')
        require(now['units']['corvus-api.service']['MainPID'] == '5711' and now['units']['corvus-api.service']['start_ticks'] == '2640', 'Production process changed before capture')
        require(stat.S_IMODE(PRIVATE.stat().st_mode) == 0o700, 'Private baseline directory permissions incorrect')
        fd = os.open(BASELINE, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'w') as stream:
            json.dump(now, stream, indent=2)
            stream.write('\n')
        print('PASS: durable private reboot baseline captured outside repository; no secrets/tokens stored')
        return
    previous = json.loads(BASELINE.read_text())
    verify_original_invariants(now, previous)
    if args.prepare_final_reboot:
        evidence = json.loads((LAB / 'deploy/lab/acceptance/dense-bootstrap-runtime-validation.json').read_text())
        require(evidence['result'] == 'OW2e-A DENSE BOOTSTRAP RUNTIME VALIDATION PASSED',
                'Approved dense runtime validation evidence missing')
        accepted = evidence['after_second_restart']
        require(now['boot_id'] == accepted['boot_id'], 'Boot changed since approved runtime validation')
        require(now['units']['corvus-lab-api.service'] == accepted['lab_unit'],
                'Lab process changed since approved second restart')
        require(now['units']['corvus-api.service'] == accepted['production_unit'],
                'Production process changed since approved runtime validation')
        require(now['dense_files'] == accepted['dense']['files'],
                'Dense files changed since approved second restart')
        checkpoint = final_checkpoint(now)
        checkpoint['original_baseline_sha256'] = hashlib.sha256(BASELINE.read_bytes()).hexdigest()
        fd = os.open(FINAL_CHECKPOINT, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'w') as stream:
            json.dump(checkpoint, stream, indent=2)
            stream.write('\n')
        print('PASS: final reboot checkpoint captured; original durable production baseline retained unchanged')
        return
    checkpoint = json.loads(FINAL_CHECKPOINT.read_text())
    verify_final_checkpoint(now, checkpoint, args.after_reboot)
    for name, state in now['units'].items():
        print(name + ': enabled, active, PID=' + state['MainPID'] + ', start=' + state['ExecMainStartTimestamp'])
    print('PASS: persistent dense table/files preserved; 6 unique rows; progress=6; firewall/cgroup state unchanged')
    print('PASS: loopback health; fixed sole Pipe/providers; persistent image/volume/chats/sessions; 445 production file hashes/sizes/mtimes; retained 3001/3002; unchanged model/Hindsight container configuration')
    print('POST-REBOOT ACCEPTANCE PASS' if args.after_reboot else 'PRE-REBOOT ACCEPTANCE PASS; REBOOT NOT RUN')

if __name__ == '__main__':
    main()
