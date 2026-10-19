"""Run selected offline contracts with isolated data and denied network I/O."""
import os,sys,pathlib
os.umask(0o077)
import tempfile
PRIVATE_HOME=pathlib.Path.home().resolve()
ROOT=pathlib.Path(tempfile.mkdtemp(prefix='corvus-w2-offline-'));ROOT.chmod(0o700)
for k in list(os.environ):
 if k.startswith('CORVUS_') or any(t in k.upper() for t in ['TOKEN','PASSWORD','SECRET','API_KEY','PROXY']):os.environ.pop(k,None)
for k,sub in {'HOME':'home','TMPDIR':'tmp','XDG_CACHE_HOME':'cache','HF_HOME':'hf','TORCH_HOME':'torch','CORVUS_DATA_DIR':'data'}.items():
 p=ROOT/sub;p.mkdir(exist_ok=True,parents=True);os.environ[k]=str(p)
tempfile.tempdir=str(ROOT/'tmp')
os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',CORVUS_HINDSIGHT_ASYNC_RETAIN_ENABLED='false',CORVUS_FOREGROUND_REGISTRY_DIR='',PYTHONDONTWRITEBYTECODE='1')
sys.dont_write_bytecode=True
CODE=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(CODE))
venv=pathlib.Path(sys.prefix).resolve();events=[]
def audit(event,args):
 if event=='open' and isinstance(args[0],(str,bytes)):
  p=pathlib.Path(os.fsdecode(args[0])).resolve();mode,flags=args[1:3]
  write=isinstance(mode,str) and any(c in mode for c in 'wax+') or isinstance(flags,int) and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC)
  if write and not p.is_relative_to(ROOT) and str(p)!="/dev/null":events.append('write-outside-test-root');raise RuntimeError('Forbidden write')
  if p.is_relative_to(PRIVATE_HOME) and not (p.is_relative_to(venv) or p.is_relative_to(CODE)):events.append('private-or-deployed-read');raise RuntimeError('Forbidden home/deployed read')
 if event in ('socket.connect','socket.getaddrinfo','subprocess.Popen'):
  events.append(event);raise RuntimeError('Offline: network/subprocess forbidden')
 if event=='sqlite3.connect' and args[0]!=':memory:' and not pathlib.Path(args[0]).resolve().is_relative_to(ROOT):
  events.append('deployed-sqlite');raise RuntimeError('Forbidden database')
sys.addaudithook(audit)
import types
# Regression imports reference dense_index, but no embedding model may load.
embedding = types.ModuleType('sentence_transformers')
class NoEmbeddingModel:
 def __init__(self,*args,**kwargs):raise AssertionError('Embedding inference/model loading forbidden')
embedding.SentenceTransformer=NoEmbeddingModel
sys.modules['sentence_transformers']=embedding
import importlib.util,unittest,json,signal,faulthandler
faulthandler.enable()
def expired(*unused):
 faulthandler.dump_traceback();os._exit(124)
signal.signal(signal.SIGALRM,expired)
names=sys.argv[1:] or ['test_web_acceptance.py']
if any(pathlib.Path(name).name!=name or not name.startswith('test_') or not name.endswith('.py') for name in names):
 raise ValueError('Only test filenames from this checkout are accepted')
passed=[];total=0;skipped=[]
for filename in names:
 signal.alarm(30)
 spec=importlib.util.spec_from_file_location('w2_'+filename[:-3],CODE/'tests'/filename);module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
 if filename=='test_open_webui_pipe.py':
  for obj in vars(module).values():
   if isinstance(obj,type) and issubclass(obj,unittest.TestCase) and hasattr(obj,'test_fresh_corvus_process_uses_only_isolated_memory_paths'):
    method=getattr(obj,'test_fresh_corvus_process_uses_only_isolated_memory_paths');method.__unittest_skip__=True;method.__unittest_skip_why__='Offline guard forbids subprocesses; remaining Pipe tests run in process'
 # Bound each module, including legacy module-level assert contracts.
 suite=unittest.defaultTestLoader.loadTestsFromModule(module)
 result=unittest.TextTestRunner(verbosity=2).run(suite)
 if not result.wasSuccessful():raise SystemExit(1)
 signal.alarm(0)
 total+=result.testsRun;skipped.extend(reason for test,reason in result.skipped);passed.append(filename)
assert not events,events
summary={'scripts_passed':passed,'unittest_cases':total,'skipped':skipped,'network_or_private_access_violations':events,'result_directory':str(ROOT)}
(ROOT/'last-results.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary))
