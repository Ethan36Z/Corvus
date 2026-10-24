"""Offline deployment contracts. No sockets, services, real keys or inference."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
from tempfile import TemporaryDirectory
import unittest
from types import SimpleNamespace
from unittest.mock import patch, Mock

ROOT = Path(__file__).resolve().parents[1]
DEPLOY = ROOT / 'deploy/lab/api-v1'
spec = importlib.util.spec_from_file_location('api_deployment', DEPLOY / 'serve.py')
serve = importlib.util.module_from_spec(spec)
spec.loader.exec_module(serve)


class DeploymentContracts(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        app = self.root / 'opt/corvus/app'
        app.mkdir(parents=True)
        manifest = {'implementation_commit': serve.COMMIT, 'files': {}}
        for name in serve.APP_FILES:
            data = (ROOT / 'app' / name).read_bytes()
            (app / name).write_bytes(data)
            manifest['files'][name] = hashlib.sha256(data).hexdigest()
        (self.root / 'opt/deployment').mkdir()
        (self.root / 'opt/deployment/source-manifest.json').write_text(json.dumps(manifest))
        self.env = patch.dict(os.environ, serve.EXPECTED_ENV, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_minimal_root_preflight_has_no_network_or_key_read(self):
        self.assertEqual(serve.preflight(self.root), self.root / 'run/corvus-api-keys/keys.sha256')

    def test_manifest_pins_approved_source(self):
        manifest = json.loads((DEPLOY / 'source-manifest.json').read_text())
        self.assertEqual(manifest['implementation_commit'], serve.COMMIT)
        self.assertEqual(set(manifest['files']), serve.APP_FILES)
        for name, digest in manifest['files'].items():
            self.assertEqual(hashlib.sha256((ROOT / 'app' / name).read_bytes()).hexdigest(), digest)

    def test_wrong_disabled_inherited_or_proxy_configuration_rejected(self):
        for key, value in [('CORVUS_API_ENABLED','FALSE'),
                           ('CORVUS_MODEL_BASE_URL','http://example.invalid'),
                           ('CORVUS_API_FOREGROUND_REGISTRY_DIR','/shared'),
                           ('CORVUS_DATA_DIR','/private'), ('HTTPS_PROXY','http://proxy.invalid')]:
            with self.subTest(key=key), patch.dict(os.environ,{key:value}):
                with self.assertRaises(ValueError):
                    serve.preflight(self.root)

    def test_private_paths_and_extra_application_code_rejected(self):
        for path in ['srv','home/ethan','etc/corvus-lab','opt/corvus/personality',
                     'opt/corvus/app/conversation_runtime.py']:
            p=self.root/path
            p.parent.mkdir(parents=True,exist_ok=True)
            p.touch()
            with self.subTest(path=path), self.assertRaises(ValueError):
                serve.preflight(self.root)
            p.unlink()

    def test_tampered_or_symlink_source_rejected(self):
        p=self.root/'opt/corvus/app/api_auth.py'
        original=p.read_bytes()
        p.write_bytes(b'changed')
        with self.assertRaises(ValueError):serve.preflight(self.root)
        p.unlink()
        other=self.root/'untrusted';other.write_bytes(original);p.symlink_to(other)
        with self.assertRaises(ValueError):serve.preflight(self.root)

    def test_safe_startup_failure_does_not_import_server_or_bind(self):
        with patch.object(serve,'preflight',side_effect=ValueError('DO_NOT_DISCLOSE')):
            with self.assertRaises(SystemExit) as caught:serve.main()
        self.assertEqual(str(caught.exception),'Corvus API startup checks failed')

    def test_main_keeps_direct_server_limits_and_checks_auth_configuration(self):
        runner=Mock(); checker=Mock(return_value=False); marker=object()
        fake={'app.api_auth':SimpleNamespace(check_key_file=checker),
              'app.openai_api':SimpleNamespace(app=marker),
              'uvicorn':SimpleNamespace(run=runner)}
        with patch.object(serve,'preflight',return_value=Path('/synthetic/keys')), \
                patch.dict(__import__('sys').modules,fake), \
                patch.object(__import__('sys'),'path',list(__import__('sys').path)):
            serve.main()
        checker.assert_called_once()
        runner.assert_called_once_with(marker,host='127.0.0.1',port=18120,workers=1,
            loop='asyncio',http='h11',limit_concurrency=8,backlog=8,access_log=False,
            log_level='critical',proxy_headers=False,timeout_graceful_shutdown=None)

    def test_edge_fragments_are_hostname_only_https_block_and_cache_bypass(self):
        rules=json.loads((DEPLOY/'edge-rule-additions.json').read_text())['rules_to_add']
        block,=rules['http_request_firewall_custom']
        self.assertEqual(block['expression'],'(http.host eq "api-corvus.foxluma.com" and not ssl)')
        self.assertEqual(block['action'],'block')
        cache,=rules['http_request_cache_settings']
        self.assertEqual(cache['expression'],'(http.host eq "api-corvus.foxluma.com")')
        self.assertEqual(cache['action_parameters'],{'cache':False})

    def test_exact_ingress_and_fail_closed_hostname_fallback(self):
        rules=json.loads((DEPLOY/'ingress-additions.json').read_text())['ingress_additions']
        def route(host,path):
            for rule in rules:
                if host==rule['hostname'] and ('path' not in rule or re.search(rule['path'],path)):
                    return rule['service']
            return None
        for path in ['/v1/models','/v1/chat/completions']:
            self.assertEqual(route('api-corvus.foxluma.com',path),'http://127.0.0.1:18120')
        for path in ['/','/openapi.json','/docs','/api/chat','/health','/metrics','/tokenize',
                     '/v1/models/','/v1//models','/v1/models/../chat/completions',
                     '/v1/%6dodels','/v1/chat/completions/extra']:
            self.assertEqual(route('api-corvus.foxluma.com',path),'http_status:404')
        for host in ['corvus.foxluma.com','lab-corvus.foxluma.com','demo-corvus.foxluma.com',
                     '127.0.0.1','anything.invalid']:
            self.assertIsNone(route(host,'/v1/models'))

    def test_service_is_independent_direct_process_and_drains_without_force(self):
        unit=(DEPLOY/'corvus-text-api.service').read_text()
        for expected in ['User=corvus-text-api','RootDirectory=/opt/corvus-text-api/root',
                         'ExecStart=/opt/venv/bin/python -I -B /opt/deployment/serve.py',
                         'SendSIGKILL=no','TimeoutStopSec=infinity','Restart=no',
                         'MemoryMax=512M','LimitAS=536870912','ProtectSystem=strict',
                         'BindReadOnlyPaths=/var/lib/corvus-text-api/keys:/run/corvus-api-keys']:
            self.assertIn(expected,unit)
        for prohibited in ['EnvironmentFile=', 'Requires=corvus-', 'PartOf=', 'ExecStop=',
                           '/home/ethan', '0.0.0.0', 'PrivateNetwork=yes']:
            self.assertNotIn(prohibited,unit)


if __name__ == '__main__':
    unittest.main()
