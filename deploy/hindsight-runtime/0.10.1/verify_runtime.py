"""Read-only final-image/runtime verification; never patches live source."""
from importlib.metadata import version
import importlib.util
from pathlib import Path
p=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('guard',p/'apply.py')
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
manifest=m.verify(Path('/app/api'),patched=True)
assert version(manifest['distribution'])==manifest['version']=='0.10.1'
print('PASS: installed distribution/version and all eleven patched/dependency hashes')
