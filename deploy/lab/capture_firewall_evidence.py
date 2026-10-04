"""Capture firewall evidence; never change rules or service state.

Run manually with sudo before and after the final controlled reboot.
Only the resulting hashes/identifiers are saved in the Lab evidence directory.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

LAB = Path(__file__).resolve().parents[2]
DIRECTORY = LAB / 'deploy/lab/acceptance'


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def nft_policy(value):
    # Handles and the CLI metainfo are identities, not policy. Preserve rule
    # order within each chain; sorting independent declarations/groups is safe.
    declarations = []
    rules = {}
    for item in value['nftables']:
        if 'metainfo' in item:
            continue
        kind, raw = next(iter(item.items()))
        body = dict(raw)
        body.pop('handle', None)
        if kind == 'rule':
            key = (body['family'], body['table'], body['chain'])
            rules.setdefault(key, []).append(body)
        else:
            declarations.append({kind: body})
    return {'declarations': sorted(declarations, key=lambda item: json.dumps(item, sort_keys=True)),
            'chains': [{'key': list(key), 'rules': rules[key]} for key in sorted(rules)]}


def iptables_policy(text):
    lines = []
    for line in text.splitlines():
        if not line or line.startswith('#'):
            continue
        if line.startswith(':'):
            line = re.sub(r'\[\d+:\d+\]', '[0:0]', line)
        lines.append(line)
    return lines


def file_hash(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOATIME | os.O_NOFOLLOW | os.O_CLOEXEC)
    with os.fdopen(fd, 'rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    if os.geteuid() != 0:
        raise RuntimeError('Run this read-only firewall evidence capture with sudo')
    boot_id = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    config = {}
    for path in [Path('/etc/nftables.conf'), Path('/etc/default/ufw')]:
        config[str(path)] = file_hash(path) if path.exists() else None
    for directory in ['/etc/ufw', '/etc/firewalld']:
        parent = Path(directory)
        if parent.exists():
            for path in sorted(parent.rglob('*')):
                if path.is_file():
                    config[str(path)] = file_hash(path)
    nft = subprocess.check_output(['nft', '--stateless', '--json', 'list', 'ruleset'], text=True)
    ipv4 = subprocess.check_output(['iptables-save'], text=True)
    ipv6 = subprocess.check_output(['ip6tables-save'], text=True)
    policy = nft_policy(json.loads(nft))
    evidence = {'boot_id': boot_id, 'persistent_config_sha256': config,
                'nft_policy_sha256': digest(policy),
                'nft_rule_count': sum(len(chain['rules']) for chain in policy['chains']),
                'iptables_policy_sha256': digest(iptables_policy(ipv4)),
                'ip6tables_policy_sha256': digest(iptables_policy(ipv6))}
    target = DIRECTORY / ('firewall-' + boot_id + '.json')
    # Fail rather than replace evidence or follow a preexisting symlink.
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644)
    with os.fdopen(fd, 'w') as stream:
        json.dump(evidence, stream, indent=2)
        stream.write('\n')
    print('FIREWALL READ-ONLY EVIDENCE CAPTURED: ' + str(target))


if __name__ == '__main__':
    main()
