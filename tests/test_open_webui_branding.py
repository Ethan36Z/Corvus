"""Corvus branding/distribution contracts; no live services or chat requests.

Set CORVUS_OW2D_ARCHIVE to the pinned local archive for full source verification.
The source integration checks are explicit skips when that archive is absent.
"""
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import unittest
from unittest.mock import patch

import yaml


REPO = Path(__file__).resolve().parents[1]
DEPLOY = REPO / "deploy/open-webui"
spec = importlib.util.spec_from_file_location("corvus_branding", DEPLOY / "branding/verify_branding.py")
branding = importlib.util.module_from_spec(spec)
spec.loader.exec_module(branding)


class BrandingArtifacts(unittest.TestCase):
    def test_pinned_artifacts_and_legal_notices(self):
        lock = branding.artifact_checks()
        self.assertEqual(lock["platform"], "linux/amd64")
        self.assertGreater(len(lock["assets"]), 9)
        self.assertIn("Redistribution and use in source and binary forms", lock["license_text"])

    def test_detects_common_branding_and_promotional_destinations(self):
        for text in ["<title>Open WebUI</title>", "OpenWebUI", "Open Web UI", "WebUI Settings", '<img src="https://img.shields.io/badge/Open-WebUI">',
                     '<a href="https://docs.openwebui.com">Help</a>', "https://github.com/open-webui/openapi-servers"]:
            with self.subTest(text=text):
                self.assertTrue(branding.scan_text("src/example.svelte", text))
        self.assertFalse(branding.scan_text("src/example.svelte", "Corvus · v0.6.5"))

    def test_internal_identifiers_are_not_product_labels(self):
        self.assertFalse(branding.scan_text("src/example.svelte", "required_open_webui_version: WEBUI_VERSION"))
        self.assertTrue(branding.scan_text("src/example.svelte", "Required version: Open WebUI"))

    def test_formatter_allowance_is_narrow(self):
        text = ".replace('" + branding.FORMATTER_INPUTS[0] + "',"
        self.assertFalse(branding.scan_text("src/lib/corvus-branding.ts", text))
        self.assertTrue(branding.scan_text("src/other.ts", text))
        self.assertTrue(branding.scan_text("src/lib/corvus-branding.ts", "return 'Open WebUI';"))

    def test_origin_allowance_does_not_allow_visible_links(self):
        path = next(iter(branding.ORIGIN_FILES))
        self.assertFalse(branding.scan_text(path, "!['https://openwebui.com', 'https://www.openwebui.com', 'http://localhost:9999'].includes(event.origin)"))
        self.assertTrue(branding.scan_text(path, '<a href="https://openwebui.com">Community</a>'))

    def test_replacement_compose_preserves_isolation_and_auth(self):
        base = yaml.safe_load((DEPLOY / "compose.ow1.yml").read_text())
        override = yaml.safe_load((DEPLOY / "compose.ow2d.yml").read_text())
        service = base["services"]["open-webui"]
        replacement = override["services"]["open-webui"]
        self.assertEqual(set(override), {"services"})
        self.assertNotIn("volumes", replacement)
        self.assertNotIn("ports", replacement)
        self.assertNotIn("network_mode", replacement)
        environment = service["environment"] | replacement["environment"]
        self.assertEqual(service["network_mode"], "host")
        self.assertEqual(environment["HOST"], "127.0.0.1")
        self.assertEqual(environment["PORT"], "3001")
        self.assertEqual(environment["WEBUI_AUTH"], "true")
        for name in ["ENABLE_SIGNUP", "ENABLE_OPENAI_API", "ENABLE_OLLAMA_API", "ENABLE_EVALUATION_ARENA_MODELS",
                     "ENABLE_TITLE_GENERATION", "ENABLE_TAGS_GENERATION", "ENABLE_AUTOCOMPLETE_GENERATION"]:
            self.assertEqual(environment[name], "false")
        self.assertEqual(replacement["pull_policy"], "never")
        self.assertEqual(environment["WEBUI_URL"], "http://127.0.0.1:3001")
        self.assertEqual(service["volumes"], ["open-webui-data:/app/backend/data"])

    def test_build_does_not_include_repo_or_corvus_runtime(self):
        dockerfile = (DEPLOY / "Dockerfile.corvus").read_text()
        self.assertNotIn("COPY . ", dockerfile)
        self.assertNotIn("pip install", dockerfile)
        self.assertNotIn("npm run build", dockerfile)
        self.assertIn("rm -rf /app/build", dockerfile)
        self.assertIn("--image-root /", dockerfile)
        self.assertNotIn("8096", dockerfile)
        self.assertNotIn("18096", dockerfile)

    def test_tampered_asset_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            copy = Path(temporary) / "branding"
            shutil.copytree(branding.HERE, copy)
            (copy / "assets/favicon.png").write_bytes(b"wrong image")
            with patch.object(branding, "HERE", copy):
                shutil.copyfile(DEPLOY / "Dockerfile.corvus", copy.parent / "Dockerfile.corvus")
                with self.assertRaisesRegex(ValueError, "Asset checksum mismatch"):
                    branding.artifact_checks()


class PinnedSourceIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        archive = os.getenv("CORVUS_OW2D_ARCHIVE")
        if not archive:
            raise unittest.SkipTest("Set CORVUS_OW2D_ARCHIVE for checksum-verified upstream integration tests")
        cls.archive = Path(archive)
        cls.temporary = tempfile.TemporaryDirectory(prefix="corvus-branding-tests-")
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.source = Path(cls.temporary.name) / "source"
        branding.prepare_source(cls.source, cls.archive)
        import tarfile
        with tarfile.open(cls.archive) as upstream:
            cls.before = {m.name.split('/', 1)[1]: upstream.extractfile(m).read() for m in upstream.getmembers() if m.isfile()}

    def test_full_patch_applies_and_source_scan_passes(self):
        self.assertEqual(branding.source_checks(self.source)["application_branding_findings"], 0)

    def test_wrong_archive_is_rejected_before_extraction(self):
        invalid = Path(self.temporary.name) / "invalid.tar.gz"
        invalid.write_bytes(b"untrusted source")
        destination = Path(self.temporary.name) / "invalid-source"
        with self.assertRaisesRegex(ValueError, "archive checksum mismatch"):
            branding.prepare_source(destination, invalid)
        self.assertFalse(destination.exists())

    def test_chat_payload_storage_and_session_code_are_unchanged(self):
        path = "src/lib/components/chat/Chat.svelte"
        before = self.before[path].decode()
        after = (self.source / path).read_text()
        after = after.replace("\timport { corvusLabel } from '$lib/corvus-branding';\n", "")
        after = re.sub(r"toast\.error\(corvusLabel\(([^\n]+)\)\)", r"toast.error(\1)", after)
        self.assertEqual(before, after)

    def test_disabled_backend_router_changes_are_only_error_labels(self):
        for path in ["backend/open_webui/routers/audio.py", "backend/open_webui/routers/ollama.py", "backend/open_webui/routers/openai.py"]:
            with self.subTest(path=path):
                before = ast.parse(self.before[path])
                after_text = (self.source / path).read_text().replace('"Corvus: Server Connection Error"', '"Open WebUI: Server Connection Error"')
                self.assertEqual(ast.dump(before), ast.dump(ast.parse(after_text)))

    def test_main_changes_leave_all_conversation_and_auth_functions_unchanged(self):
        path = "backend/open_webui/main.py"
        before = ast.parse(self.before[path])
        after = ast.parse((self.source / path).read_text())
        functions = lambda tree: {n.name: ast.dump(n) for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
        a, b = functions(before), functions(after)
        for name in ["get_app_latest_release_version", "get_app_changelog", "get_manifest_json"]:
            a.pop(name)
            b.pop(name)
        self.assertEqual(a, b)

    def test_localized_branding_retains_interpolation_contract(self):
        for path, content in self.before.items():
            if path.startswith("src/lib/i18n/locales/") and path.endswith("translation.json"):
                before = json.loads(content)
                after = json.loads((self.source / path).read_text())
                self.assertEqual(len(before), len(after), path)
                for key, value in before.items():
                    renamed = branding.BARE_PRODUCT.sub("Corvus", branding.BRAND.sub("Corvus", key))
                    self.assertIn(renamed, after, path)
                    self.assertEqual(re.findall(r"\{\{[^}]+\}\}", str(value)), re.findall(r"\{\{[^}]+\}\}", str(after[renamed])), path)

    def test_runtime_update_check_has_no_network_access(self):
        tree = ast.parse((self.source / "backend/open_webui/main.py").read_text())
        function = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == "get_app_latest_release_version")
        self.assertEqual(len(function.body), 1)
        self.assertIsInstance(function.body[0], ast.Return)
        self.assertEqual({k.value for k in function.body[0].value.keys}, {"current", "latest"})


if __name__ == "__main__":
    unittest.main()
