"""Plan-only owned-resource rollback checks. Never executes Docker mutations."""
import json
from pathlib import Path
import re
import sys

ARTIFACTS=Path(__file__).with_name('artifacts.json')
PROJECT='corvus-lab-open-webui'
SERVICES={'corvus-stt-bridge','corvus-whisper-dictation'}

def container_plan(observations):
    images=json.loads(ARTIFACTS.read_text())['images']
    expected={'corvus-stt-bridge':images['bridge'],'corvus-whisper-dictation':'sha256:caf0cd77c922e9c53f10a9bc17c2f74cc2295d12e7b0f96b630fb3b3c55a0026'}
    plan=[];seen=set()
    for obj in observations:
        labels=obj['Config']['Labels'];service=labels.get('com.docker.compose.service')
        assert service in SERVICES and service not in seen
        assert labels.get('com.docker.compose.project')==PROJECT
        assert labels.get('io.corvus.stt.owner')=='r7-lab'
        assert obj['Image']==expected[service]
        cid=obj['Id'];assert re.fullmatch('[0-9a-f]{64}',cid)
        seen.add(service)
        # Commands use full verified IDs only, never names, volume removal or prune.
        plan.extend([['docker','stop',cid],['docker','rm',cid]])
    return plan

def network_plan(observations):
    plan=[]
    for obj in observations:
        assert obj['Name'] in {'corvus-stt-dictation-private','corvus-stt-dictation-ingress'}
        assert obj['Labels'].get('io.corvus.stt.owner')=='r7-lab'
        assert obj['Labels'].get('com.docker.compose.project')==PROJECT
        assert not obj.get('Containers'), 'Refuse network removal with any consumer'
        nid=obj['Id'];assert re.fullmatch('[0-9a-f]{64}',nid)
        plan.append(['docker','network','rm',nid])
    return plan

if __name__=='__main__':
    payload=json.loads(Path(sys.argv[1]).read_text())
    print(json.dumps({'container_plan':container_plan(payload.get('containers',[])),
                      'network_plan':network_plan(payload.get('empty_networks',[])),
                      'execute':False},indent=2))
