"""Build from the exact cached base, applying the existing patch offline first."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

HERE=Path(__file__).resolve().parent
PATCH=HERE.parents[1]/'hindsight-patches/0.10.1'
MANIFEST=json.loads((PATCH/'manifest.json').read_text())
BASE=MANIFEST['upstream_container']['image']
BASE_TAG='corvus-hindsight-base:0.10.1-b4d3b76f363a'
TAG='corvus-hindsight:0.10.1-h17d3b-47201c6'

def run(*args):
    return subprocess.check_output(args,text=True).strip()

def extract(image,root):
    identity=run('docker','create','--network','none','--entrypoint','python',image,'-V')
    try:
        for name,hashes in MANIFEST['files'].items():
            if hashes['upstream_sha256'] is None:continue
            path=root/name;path.parent.mkdir(parents=True,exist_ok=True)
            run('docker','cp',identity+':/app/api/'+name,str(path))
    finally:
        run('docker','rm',identity) # This scratch container has NO persistent mounts.


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    assert json.loads(run('docker','image','inspect',BASE))[0]['Id']==BASE
    existing=subprocess.run(['docker','image','inspect',BASE_TAG],capture_output=True,text=True)
    if existing.returncode==0:
        assert json.loads(existing.stdout)[0]['Id']==BASE, 'Local base tag drift'
    else:
        run('docker','image','tag',BASE,BASE_TAG)
    with tempfile.TemporaryDirectory(prefix='corvus-hindsight-build-') as directory:
        root=Path(directory);source=root/'source';source.mkdir()
        extract(BASE,source)
        subprocess.run(['python3','-B',str(PATCH/'apply.py'),'--root',str(source),'--apply'],check=True)
        context=root/'context';context.mkdir()
        shutil.copytree(PATCH,context/'patch')
        for name,hashes in MANIFEST['files'].items():
            if hashes['upstream_sha256']!=hashes['patched_sha256']:
                dst=context/'outputs'/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source/name,dst)
        for name in ('Dockerfile','install_verified.py','verify_runtime.py'):shutil.copy2(HERE/name,context/name)
        # Legacy builder consumes the verified daemon-local tag without remote
        # BuildKit source metadata resolution; all RUN steps are offline too.
        subprocess.run(['docker','build','--pull=false','--network=none','--build-arg','BASE_IMAGE='+BASE_TAG,'-t',TAG,str(context)],
                       env=dict(os.environ,DOCKER_BUILDKIT='0'),check=True)
        image=json.loads(run('docker','image','inspect',TAG))[0]
        subprocess.run(['docker','run','--rm','--network','none','--entrypoint','python',image['Id'],'-B','/opt/corvus-admission/verify_runtime.py'],check=True)
        # Focused tests against sources actually copied FROM the derived image.
        final=root/'final';final.mkdir();extract(image['Id'],final)
        scratch=run('docker','create','--network','none','--entrypoint','python',image['Id'],'-V')
        try:run('docker','cp',scratch+':/app/api/hindsight_api/engine/foreground_admission.py',str(final/'hindsight_api/engine/foreground_admission.py'))
        finally:run('docker','rm',scratch)
        subprocess.run(['python3','-B',str(PATCH/'test_admission.py'),'--source',str(final)],check=True)
        subprocess.run(['python3','-B',str(PATCH/'test_control_flow.py'),'--source',str(final)],check=True)
        args.output.write_text(json.dumps({'base':BASE,'tag':TAG,'derived':image['Id'],'size':image['Size'],'layers':image['RootFS']['Layers']},indent=2)+'\n')
        print('PASS: derived image verified and 55 focused patch tests passed; '+image['Id'])

if __name__=='__main__':main()
