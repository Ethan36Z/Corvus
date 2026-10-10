#!/usr/bin/env python3
"""Verify pinned source and apply only to an offline API source/build directory."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tomllib

ARTIFACTS = Path(__file__).resolve().parent


def verify(root, *, patched=False):
    manifest = json.loads((ARTIFACTS / 'manifest.json').read_text())
    project = tomllib.loads((root / 'pyproject.toml').read_text())['project']
    if (project['name'], project['version']) != (manifest['distribution'], manifest['version']):
        raise ValueError('Unexpected Hindsight distribution/version')
    field = 'patched_sha256' if patched else 'upstream_sha256'
    for name, hashes in manifest['files'].items():
        path = root / name
        if not patched and hashes['upstream_sha256'] is None:
            if path.exists() or path.is_symlink():
                raise ValueError('Unexpected existing introduced file: ' + name)
            continue
        if path.is_symlink() or not path.is_file():
            raise ValueError('Missing/unsafe source file: ' + name)
        if hashlib.sha256(path.read_bytes()).hexdigest() != hashes[field]:
            raise ValueError('Unexpected source hash: ' + name)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path, help='Offline /app/api-equivalent source root')
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check', action='store_true')
    mode.add_argument('--apply', action='store_true')
    mode.add_argument('--verify-patched', action='store_true')
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    # No live-container in-place application; build/review a replacement separately.
    if root == Path('/app/api'):
        raise ValueError('Refusing live /app/api; use an isolated build/source directory')
    verify(root, patched=args.verify_patched)
    if not args.verify_patched:
        command = ['git', 'apply', '--unidiff-zero', '--unsafe-paths', '--directory=' + str(root),
                   str(ARTIFACTS / 'defer-control-flow.patch')]
        subprocess.run(command[:2] + ['--check'] + command[2:], check=True)
        if args.apply:
            subprocess.run(command, check=True)
            verify(root, patched=True)
    print('PASS: ' + ('patched hashes' if args.verify_patched or args.apply else 'upstream hashes + patch check'))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        print('BLOCKED: ' + str(error), file=sys.stderr)
        sys.exit(1)
