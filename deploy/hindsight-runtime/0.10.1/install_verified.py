"""Build-layer source guard and installation of the host-applied exact patch."""
import hashlib
import importlib.util
from importlib.metadata import version
import os
from pathlib import Path

root=Path('/app/api')
base=Path('/opt/corvus-build')
spec=importlib.util.spec_from_file_location('guard',base/'patch/apply.py')
guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
manifest=guard.verify(root)
assert version(manifest['distribution'])==manifest['version']=='0.10.1'
# Validate ALL replacement bytes before installing any. Host outputs were made
# using the guarded unified patch; no git/package download is needed in image.
replacements={}
for name,hashes in manifest['files'].items():
    if hashes['upstream_sha256']!=hashes['patched_sha256']:
        data=(base/'outputs'/name).read_bytes()
        assert hashlib.sha256(data).hexdigest()==hashes['patched_sha256'],name
        replacements[name]=data
for name,data in replacements.items():
    path=root/name;path.write_bytes(data)
    os.chown(path,1000,1000)
guard.verify(root,patched=True)
print('PASS: original build/version/source guarded; six exact patched sources installed')
