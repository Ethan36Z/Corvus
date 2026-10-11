"""Exact inspected Docker recipe; replace only Hindsight, retaining rollback container.

Snapshot contains environment values: keep it mode 0600 outside the repository.
No volume removal, model restart, routing change, or in-place source mutation.
"""
import argparse
import copy
import http.client
import json
import socket
from pathlib import Path
import subprocess
import time
from urllib.parse import urlencode, quote
import urllib.request

NAME='hindsight-lab'
SETTINGS={'CORVUS_FOREGROUND_REGISTRY_DIR':'/run/corvus-foreground',
          'CORVUS_FOREGROUND_EXPECTED_PUBLISHERS':'lab,production',
          'CORVUS_FOREGROUND_IDLE_GRACE_SECONDS':'30'}
BIND='/run/corvus-foreground:/run/corvus-foreground:ro'
BUDGET_SETTINGS={'CORVUS_CONSOLIDATION_CONTEXT_LIMIT':'8192',
                 'CORVUS_CONSOLIDATION_SAFETY_MARGIN_TOKENS':'256',
                 'HINDSIGHT_API_CONSOLIDATION_MAX_COMPLETION_TOKENS':'1024',
                 'HINDSIGHT_API_CONSOLIDATION_LLM_BATCH_SIZE':'1',
                 'HINDSIGHT_API_CONSOLIDATION_LLM_REASONING_EFFORT':'none',
                 'HINDSIGHT_API_CONSOLIDATION_LLM_EXTRA_BODY':'{"chat_template_kwargs":{"enable_thinking":false}}'}

class UnixHTTP(http.client.HTTPConnection):
    def connect(self):
        self.sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout);self.sock.connect('/var/run/docker.sock')


def engine(method,path,body=None,*,allowed=(200,201,204),timeout=90):
    connection=UnixHTTP('localhost',timeout=timeout)
    try:
        data=json.dumps(body).encode() if body is not None else None
        connection.request(method,path,body=data,headers={'Content-Type':'application/json'})
        response=connection.getresponse();raw=response.read()
        if response.status not in allowed:
            raise RuntimeError(f'Docker {method} {path} returned {response.status}: '+raw.decode(errors='replace')[:500])
        return json.loads(raw) if raw else None
    finally:connection.close()


def inspect(identity):return engine('GET','/containers/'+quote(identity,safe='')+'/json')


def plan(original,image,*,admission=True,bounded=False):
    config=copy.deepcopy(original['Config']);host=copy.deepcopy(original['HostConfig'])
    config['Image']=image
    if admission:
        existing=dict(x.split('=',1) for x in config['Env'])
        for key,value in SETTINGS.items():
            if key in existing:assert existing[key]==value, 'Admission configuration drift'
            else:config['Env'].append(key+'='+value)
        present=[x for x in host.get('Binds',[]) if '/run/corvus-foreground' in x]
        if present:assert present==[BIND], 'Existing registry bind differs'
        else:host['Binds']=(host.get('Binds') or [])+[BIND]
    if bounded:
        assert not any(x.split('=',1)[0] in BUDGET_SETTINGS for x in config['Env']), 'Existing budget config'
        config['Env'] += [k+'='+v for k,v in BUDGET_SETTINGS.items()]
    # Preserve configured network properties; Docker allocates new endpoint IDs,
    # IP/MAC for an ordinary dynamic endpoint. No new static IP is invented.
    endpoints={}
    for name,old in original['NetworkSettings']['Networks'].items():
        endpoints[name]={k:copy.deepcopy(old[k]) for k in
                         ('IPAMConfig','Links','Aliases','DriverOpts','GwPriority') if k in old}
    return dict(config,HostConfig=host,NetworkingConfig={'EndpointsConfig':endpoints})


def equivalent_host(actual,expected):
    # Docker normalizes unset OomKillDisable to false on create. Both enable
    # normal kernel OOM killing; this is not a resource-policy change. No other
    # host/security/resource difference is accepted.
    actual=copy.deepcopy(actual);expected=copy.deepcopy(expected)
    if actual.get('OomKillDisable') is False and expected.get('OomKillDisable') is None:
        expected['OomKillDisable']=False
    return actual==expected


def validate(actual,original,image,*,bounded=False):
    expected=plan(original,image,bounded=bounded)
    assert actual['Config']=={k:v for k,v in expected.items() if k not in ('HostConfig','NetworkingConfig')}, 'Runtime Config differs'
    assert equivalent_host(actual['HostConfig'],expected['HostConfig']), 'Runtime HostConfig differs'
    assert set(actual['NetworkSettings']['Networks'])==set(original['NetworkSettings']['Networks'])
    for name,fields in expected['NetworkingConfig']['EndpointsConfig'].items():
        now=actual['NetworkSettings']['Networks'][name]
        assert all(now[k]==v for k,v in fields.items()), 'Configured network properties differ'
    prior={x['Destination']:x for x in original['Mounts']}
    current={x['Destination']:x for x in actual['Mounts']}
    assert set(current)==set(prior)|{'/run/corvus-foreground'}
    for destination,old in prior.items():assert current[destination]==old, 'Original persistent mount differs'
    mount=current['/run/corvus-foreground']
    assert mount['Type']=='bind' and mount['Source']==mount['Destination']=='/run/corvus-foreground' and mount['RW'] is False


def wait_health(seconds=180):
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        try:
            with opener.open('http://127.0.0.1:8888/health',timeout=3) as r:
                if r.status==200 and json.load(r)['status'] in ('healthy','ok','OK'):return
        except (OSError,ValueError):pass
        time.sleep(2)
    raise RuntimeError('Hindsight startup health timeout')


def rollback_name(original):return NAME+'-h17d3c-rollback-'+original['Id'][:12]


def rollback(original,new_id=None):
    # No volume deletion. A stopped original container retains the EXACT recipe.
    if new_id is not None:
        engine('POST',f'/containers/{new_id}/stop?t=60',allowed=(204,304))
        engine('DELETE',f'/containers/{new_id}',allowed=(204,))
    engine('POST',f"/containers/{original['Id']}/rename?"+urlencode({'name':NAME}))
    engine('POST',f"/containers/{original['Id']}/start",allowed=(204,304))
    wait_health()
    restored=inspect(original['Id'])
    assert restored['Config']==original['Config'] and equivalent_host(restored['HostConfig'],original['HostConfig'])
    assert restored['Mounts']==original['Mounts'] and restored['Image']==original['Image']
    print('ROLLBACK PASS: original image/config/volumes restored',flush=True)


def deploy(snapshot,image,accept,*,bounded=False):
    original=snapshot['container']
    now=inspect(NAME)
    assert now['Id']==original['Id'] and now['State']['Running']
    assert now['Config']==original['Config'] and now['HostConfig']==original['HostConfig'] and now['Mounts']==original['Mounts']
    # Fail before stopping if retained rollback name already exists.
    try:inspect(rollback_name(original))
    except RuntimeError as error:
        if 'returned 404' not in str(error):raise
    else:raise RuntimeError('Rollback container name already exists')
    image_now=engine('GET','/images/'+quote(image,safe='')+'/json')
    assert image_now['Id']==image
    new_id=None;renamed=False
    try:
        # Validate the exact create recipe while the original is still running.
        # This candidate is stopped: no process opens the shared data volumes.
        prepared=NAME+'-h17d3c-prepared-'+image.split(':')[-1][:12]
        created=engine('POST','/containers/create?'+urlencode({'name':prepared}),plan(original,image,bounded=bounded))
        new_id=created['Id'];validate(inspect(new_id),original,image,bounded=bounded)
        engine('POST',f"/containers/{original['Id']}/stop?t=60",allowed=(204,))
        assert not inspect(original['Id'])['State']['Running']
        engine('POST',f"/containers/{original['Id']}/rename?"+urlencode({'name':rollback_name(original)}));renamed=True
        engine('POST',f'/containers/{new_id}/rename?'+urlencode({'name':NAME}))
        print('Created patched Hindsight '+new_id,flush=True)
        engine('POST',f'/containers/{new_id}/start',allowed=(204,))
        wait_health();validate(inspect(new_id),original,image,bounded=bounded)
        accept(inspect(new_id))
        print('PASS: patched Hindsight healthy; original retained for rollback',flush=True)
        return new_id
    except BaseException:
        if renamed:rollback(original,new_id)
        else:
            if new_id is not None:engine('DELETE',f'/containers/{new_id}',allowed=(204,))
            engine('POST',f"/containers/{original['Id']}/start",allowed=(204,304));wait_health()
        raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot',required=True,type=Path)
    parser.add_argument('--image',required=True)
    parser.add_argument('--rollback',action='store_true')
    parser.add_argument('--bounded-consolidation',action='store_true')
    args=parser.parse_args();snapshot=json.loads(args.snapshot.read_text())
    if args.rollback:
        current=inspect(NAME)
        assert current['Id']!=snapshot['container']['Id'], 'Original already live'
        validate(current,snapshot['container'],args.image,bounded=args.bounded_consolidation)
        rollback(snapshot['container'],current['Id'])
    else:
        print(json.dumps(plan(snapshot['container'],args.image,bounded=args.bounded_consolidation),indent=2)) # Review only; contains environment values.

if __name__=='__main__':main()
