"""Focused R7 packaging/topology/rollback contracts; no runtime mutation."""
import ast
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

class PackagingContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.artifacts=json.loads((ROOT/'deploy/lab/stt/package/artifacts.json').read_text())
        cls.current=json.loads(Path(sys.argv[1]).read_text())
        cls.base=json.loads(Path(sys.argv[2]).read_text())
        cls.output=Path(sys.argv[3])
        cls.rollback=module('rollback_r7',ROOT/'deploy/lab/stt/package/rollback_plan.py')

    def test_existing_webui_tts_pipe_environment_network_and_volume(self):
        now=self.current['services']['open-webui'];old=self.base['services']['open-webui']
        self.assertEqual(now['environment'],old['environment'])
        self.assertEqual(now['volumes'],old['volumes'])
        self.assertEqual(now['network_mode'],'host')
        self.assertEqual(now['image'],self.artifacts['images']['webui'])
        self.assertEqual(now['environment']['USER_PERMISSIONS_CHAT_STT'],'false')
        self.assertEqual(now['environment']['AUDIO_TTS_ENGINE'],'corvus-kokoro')
        self.assertEqual(now['environment']['DEFAULT_MODELS'],'corvus_pipe')

    def test_topology_no_public_whisper_or_legacy_fallback(self):
        services=self.current['services'];self.assertEqual(set(services),{'open-webui','corvus-stt-bridge','corvus-whisper-dictation'})
        b=services['corvus-stt-bridge'];w=services['corvus-whisper-dictation']
        self.assertEqual(set(w['networks']),{'dictation-private'});self.assertFalse(w.get('ports'))
        self.assertTrue(self.current['networks']['dictation-private']['internal'])
        self.assertEqual(set(b['networks']),{'dictation-ingress','dictation-private'})
        self.assertEqual([(p['host_ip'],p['published'],p['target']) for p in b['ports']],[('127.0.0.1','18106',8106)])
        self.assertNotIn('--convert',w['command'][0]);self.assertEqual(w['cpus'],8)
        self.assertEqual(int(w['mem_limit']),1140850688)
        self.assertEqual(int(w['memswap_limit']),1140850688)
        self.assertTrue(b['read_only']);self.assertFalse(b.get('volumes'));self.assertEqual(b['logging']['driver'],'none')
        self.assertEqual(int(b['mem_limit']),268435456);self.assertEqual(int(b['memswap_limit']),268435456)
        self.assertEqual(b['cpus'],1)

    def test_backend_native_auth_disabled_gates_and_fixed_local_target(self):
        audio=(self.output/'webui/audio.py').read_text();tree=ast.parse(audio)
        route=next(n for n in tree.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='transcription')
        self.assertEqual(ast.unparse(route.args),'request: Request, user=Depends(get_verified_user)')
        self.assertNotIn('UploadFile',ast.unparse(route))
        helper=(self.output/'webui/corvus_stt.py').read_text()
        self.assertIn("BRIDGE_URL = 'http://127.0.0.1:18106/v1/transcribe'",helper)
        self.assertIn('if bridge is None:',helper)
        bridge=(self.output/'bridge/app/stt_bridge.py').read_text()
        self.assertIn('app = create_app()',bridge)
        self.assertIn("WHISPER_BASE = 'http://corvus-whisper-dictation:8080'",bridge)
        self.assertNotIn("WHISPER_BASE = 'http://corvus-whisper:8080'",bridge)

    def test_frontend_arena_control_review_before_send_tts_privacy(self):
        source=self.output/'source'
        composer=(source/'src/lib/components/chat/MessageInput.svelte').read_text()
        self.assertIn('Memory A/B',composer);self.assertIn('export let arenaAvailable',composer)
        self.assertIn('Dictation stays editable; retain speechAutoSend',composer)
        response=(source/'src/lib/components/chat/Messages/ResponseMessage.svelte').read_text()
        self.assertNotIn('Prepared message content for TTS',response)
        self.assertTrue((source/'build/index.html').exists())
        self.assertIn('normalizeRecording',(source/'src/lib/components/chat/MessageInput/VoiceRecording.svelte').read_text())

    def test_package_proof_and_bridge_content_reuse(self):
        proof=json.loads((self.output/'proof.json').read_text())
        self.assertEqual(proof['runtime_image'],self.artifacts['base_image'])
        for path,digest in proof['modified_frontend'].items():
            self.assertEqual(hashlib.sha256((self.output/'source'/path).read_bytes()).hexdigest(),digest)
        for path in proof['bridge_modules']:
            self.assertEqual((self.output/'bridge'/path).read_bytes(),(ROOT/path).read_bytes())
        self.assertNotIn('pip install',(self.output/'bridge/Dockerfile').read_text())
        self.assertNotIn('npm install',(self.output/'webui/Dockerfile').read_text())

    def test_rollback_only_owned_new_ids(self):
        owner={'com.docker.compose.project':'corvus-lab-open-webui','com.docker.compose.service':'corvus-stt-bridge','io.corvus.stt.owner':'r7-lab'}
        obj={'Id':'a'*64,'Image':self.artifacts['images']['bridge'],'Config':{'Labels':owner}}
        self.assertEqual(self.rollback.container_plan([obj]),[['docker','stop','a'*64],['docker','rm','a'*64]])
        for field,value in [('com.docker.compose.project','production'),('com.docker.compose.service','corvus-whisper'),('io.corvus.stt.owner','other')]:
            bad=copy.deepcopy(obj);bad['Config']['Labels'][field]=value
            with self.assertRaises(AssertionError):self.rollback.container_plan([bad])
        bad=copy.deepcopy(obj);bad['Image']='sha256:'+'b'*64
        with self.assertRaises(AssertionError):self.rollback.container_plan([bad])
        with self.assertRaises(AssertionError):self.rollback.container_plan([obj,obj])

    def test_rollback_never_removes_consumed_or_unowned_network(self):
        obj={'Id':'c'*64,'Name':'corvus-stt-dictation-private','Containers':{},'Labels':{'io.corvus.stt.owner':'r7-lab','com.docker.compose.project':'corvus-lab-open-webui'}}
        self.assertEqual(self.rollback.network_plan([obj]),[['docker','network','rm','c'*64]])
        obj['Containers']={'existing-consumer':{}}
        with self.assertRaises(AssertionError):self.rollback.network_plan([obj])
        obj['Containers']={};obj['Name']='existing-data-network'
        with self.assertRaises(AssertionError):self.rollback.network_plan([obj])

if __name__=='__main__':
    # Keep paths available to setUpClass while unittest sees only its own arguments.
    unittest.main(argv=[sys.argv[0]],verbosity=2)
