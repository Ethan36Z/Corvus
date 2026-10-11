"""Offline configuration-preservation guards; no Docker/service/model calls."""
import copy
import unittest
import runtime as r

class RecipeTests(unittest.TestCase):
    def setUp(self):
        self.original={'Config':{'Image':'cached','Env':['MODEL=unchanged'],'User':'hindsight','Cmd':['/app/start-all.sh']},
            'HostConfig':{'Binds':['data:/data'],'OomKillDisable':None,'Memory':0,'CapDrop':None},
            'NetworkSettings':{'Networks':{'local':{'IPAMConfig':None,'Aliases':None,'GwPriority':0}}},
            'Mounts':[{'Type':'volume','Name':'data','Destination':'/data','RW':True}]}
        self.plan=r.plan(self.original,'derived')
        self.actual={'Config':{k:v for k,v in self.plan.items() if k not in ('HostConfig','NetworkingConfig')},
            'HostConfig':copy.deepcopy(self.plan['HostConfig']),
            'NetworkSettings':copy.deepcopy(self.original['NetworkSettings']),
            'Mounts':copy.deepcopy(self.original['Mounts'])+[{'Type':'bind','Source':'/run/corvus-foreground',
              'Destination':'/run/corvus-foreground','RW':False}]}
    def test_only_image_environment_bind_change_and_original_not_mutated(self):
        original=copy.deepcopy(self.original);r.plan(self.original,'derived')
        self.assertEqual(self.original,original)
        self.assertEqual(self.actual['Config']['Env'][:-3],original['Config']['Env'])
        self.assertEqual(self.actual['HostConfig']['Binds'][:-1],original['HostConfig']['Binds'])
        r.validate(self.actual,self.original,'derived')
    def test_only_unset_to_false_oom_normalization_allowed(self):
        self.actual['HostConfig']['OomKillDisable']=False;r.validate(self.actual,self.original,'derived')
        self.actual['HostConfig']['OomKillDisable']=True
        with self.assertRaises(AssertionError):r.validate(self.actual,self.original,'derived')
    def test_resource_security_and_data_changes_rejected(self):
        for key,value in [('Memory',100),('CapDrop',['ALL']),('Binds',['other:/data',r.BIND])]:
            with self.subTest(key=key):
                changed=copy.deepcopy(self.actual);changed['HostConfig'][key]=value
                with self.assertRaises(AssertionError):r.validate(changed,self.original,'derived')
        changed=copy.deepcopy(self.actual);changed['Mounts'][0]['Name']='different-data'
        with self.assertRaises(AssertionError):r.validate(changed,self.original,'derived')
    def test_writable_registry_and_changed_model_rejected(self):
        self.actual['Mounts'][-1]['RW']=True
        with self.assertRaises(AssertionError):r.validate(self.actual,self.original,'derived')
        self.actual['Mounts'][-1]['RW']=False;self.actual['Config']['Env'][0]='MODEL=wrong'
        with self.assertRaises(AssertionError):r.validate(self.actual,self.original,'derived')

class BoundedUpgradeTests(unittest.TestCase):
    setUp = RecipeTests.setUp
    def test_live_admission_preserved_only_budget_env_and_image_change(self):
        old=copy.deepcopy(self.actual)
        candidate=r.plan(old,'bounded-image',bounded=True)
        self.assertEqual(candidate['HostConfig'],old['HostConfig'])
        self.assertEqual(candidate['Env'][:len(old['Config']['Env'])],old['Config']['Env'])
        self.assertEqual(dict(x.split('=',1) for x in candidate['Env'][-6:]),r.BUDGET_SETTINGS)
        now=copy.deepcopy(old)
        now['Config']={k:v for k,v in candidate.items() if k not in ('HostConfig','NetworkingConfig')}
        r.validate(now,old,'bounded-image',bounded=True)
        bad=copy.deepcopy(now);bad['Config']['Env'][-6]='CORVUS_CONSOLIDATION_CONTEXT_LIMIT=99999'
        with self.assertRaises(AssertionError):r.validate(bad,old,'bounded-image',bounded=True)
        self.assertEqual(old,self.actual)

    def test_existing_admission_drift_or_writable_bind_rejected(self):
        for field,value in [('Env',['MODEL=unchanged','CORVUS_FOREGROUND_IDLE_GRACE_SECONDS=0'])]:
            old=copy.deepcopy(self.actual);old['Config'][field]=value
            with self.assertRaises(AssertionError):r.plan(old,'bounded',bounded=True)
        old=copy.deepcopy(self.actual);old['HostConfig']['Binds'][-1]=r.BIND.replace(':ro',':rw')
        with self.assertRaises(AssertionError):r.plan(old,'bounded',bounded=True)

    def test_preexisting_budget_config_rejected_before_mutation(self):
        old=copy.deepcopy(self.actual);old['Config']['Env'].append('CORVUS_CONSOLIDATION_CONTEXT_LIMIT=8192')
        with self.assertRaises(AssertionError):r.plan(old,'bounded',bounded=True)

if __name__=='__main__':unittest.main(verbosity=2)
