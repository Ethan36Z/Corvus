"""Synthetic TTS contracts; no real audio, auth data, storage or network calls."""

import ast
import asyncio
from contextlib import asynccontextmanager, contextmanager
import hashlib
import importlib.util
import io
import json
import logging
import os
from pathlib import Path
import sqlite3
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch
import wave

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
import httpx
import yaml


ROOT = Path(__file__).resolve().parents[1]
TTS = ROOT / "deploy/lab/tts"
SOURCE = Path(os.environ.get("CORVUS_TTS1_SOURCE", "/tmp/corvus-arena-ui1/source"))
FRONTEND = Path(os.environ.get("CORVUS_TTS1_FRONTEND", "/tmp/corvus-tts1-frontend-base.js"))
RealClient = httpx.AsyncClient


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


adapter = load("tts1_adapter", TTS / "kokoro.py")
prepare = load("tts1_prepare", TTS / "prepare_audio.py")


def wav_bytes():
    stream = io.BytesIO()
    with wave.open(stream, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(24000)
        wav.writeframes(b"\x00\x00" * 240)
    return stream.getvalue()


class Reply:
    def __init__(self, body=None, status=200, mime="audio/wav", encoding="identity", error=None):
        self.body = wav_bytes() if body is None else body
        self.status_code = status
        self.headers = {"content-type": mime, "content-encoding": encoding}
        self.error = error

    async def aiter_raw(self):
        if self.error:
            raise self.error
        for start in range(0, len(self.body), 80):
            yield self.body[start:start + 80]


@contextmanager
def kokoro(reply=None, delay=None):
    seen = {"calls": [], "closed": False, "response_closed": False}

    class Client:
        def __init__(self, **kwargs):
            seen["options"] = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            seen["closed"] = True

        @asynccontextmanager
        async def stream(self, *args, **kwargs):
            seen["calls"].append((args, kwargs))
            try:
                if delay:
                    seen["started"].set()
                    await asyncio.Event().wait()
                yield reply or Reply()
            finally:
                seen["response_closed"] = True

    seen["started"] = asyncio.Event()
    with patch.object(adapter.httpx, "AsyncClient", Client):
        yield seen


class TTSContracts(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.audio = (SOURCE / "backend/open_webui/routers/audio.py").read_text()
        cls.patched = prepare.patch_audio(cls.audio)
        # Execute only the native verified-role dependency and patched routes.
        # JWT/user lookup is a synthetic boundary; no application/DB imports.
        native = ast.parse((SOURCE / "backend/open_webui/utils/auth.py").read_text())
        verified = next(n for n in native.body if isinstance(n, ast.FunctionDef)
                        and n.name == "get_verified_user")

        async def current_user(request: Request):
            role = request.headers.get("x-synthetic-role")
            if not role:
                raise HTTPException(401, "Not authenticated")
            return SimpleNamespace(role=role)

        namespace = {"Depends": Depends, "get_current_user": current_user,
                     "HTTPException": HTTPException, "status": SimpleNamespace(HTTP_401_UNAUTHORIZED=401),
                     "ERROR_MESSAGES": SimpleNamespace(ACCESS_PROHIBITED="Access prohibited")}
        exec(compile(ast.Module(body=[verified], type_ignores=[]), "native-verified-user", "exec"), namespace)
        router = APIRouter()
        namespace.update(router=router, Request=Request)
        handlers = [n for n in ast.parse(cls.patched).body
                    if isinstance(n, ast.AsyncFunctionDef) and n.name in {"speech", "get_voices"}]
        cls.module_patch = patch.dict(sys.modules, {
            "open_webui": ModuleType("open_webui"),
            "open_webui.routers": ModuleType("open_webui.routers"),
            "open_webui.routers.corvus_tts": adapter,
        })
        cls.module_patch.start()
        cls.addClassCleanup(cls.module_patch.stop)
        exec(compile(ast.Module(body=handlers, type_ignores=[]), "patched-native-audio", "exec"), namespace)
        cls.app = FastAPI()
        cls.app.state.config = SimpleNamespace(TTS_ENGINE=adapter.ENGINE)
        cls.app.include_router(router, prefix="/api/v1/audio")

    async def request(self, payload=None, role="user", path="speech", raw=None, headers=None):
        h = {"x-synthetic-role": role} if role else {}
        h.update(headers or {})
        async with RealClient(transport=httpx.ASGITransport(app=self.app), base_url="http://synthetic") as c:
            if path == "voices":
                return await c.get("/api/v1/audio/voices", headers=h)
            if raw is not None:
                return await c.post("/api/v1/audio/speech", content=raw, headers=h)
            h["content-type"] = "application/json"
            return await c.post("/api/v1/audio/speech", content=json.dumps(
                {"input": "你好，Corvus。"} if payload is None else payload).encode(), headers=h)

    async def test_authenticated_native_route_and_exact_kokoro_contract(self):
        with kokoro() as seen:
            response = await self.request({"input": "  你好，\n Corvus。 ", "voice": "af_mica"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, wav_bytes())
        self.assertEqual(response.headers["content-type"], "audio/wav")
        self.assertEqual(response.headers["cache-control"], "private, no-store")
        self.assertEqual(response.headers["x-content-type-options"], "nosniff")
        args, kwargs = seen["calls"][0]
        self.assertEqual(args, ("POST", "http://127.0.0.1:8105/v1/audio/speech"))
        self.assertEqual(kwargs["json"], {"model": "kokoro", "input": "你好， Corvus。",
                         "voice": "af_mica", "lang_code": "z", "speed": 0.95,
                         "response_format": "wav", "stream": False, "return_download_link": False})
        self.assertEqual(kwargs["headers"], {"Accept": "audio/wav", "Accept-Encoding": "identity"})
        self.assertFalse(seen["options"]["follow_redirects"])
        self.assertFalse(seen["options"]["trust_env"])
        self.assertEqual(seen["options"]["timeout"].read, 60)
        self.assertEqual(seen["options"]["timeout"].connect, 3)
        self.assertEqual(seen["options"]["transport"]._pool._retries, 0)
        self.assertTrue(seen["closed"] and seen["response_closed"])
        self.assertEqual(len(seen["calls"]), 1)

    async def test_unauthenticated_and_unverified_roles_never_dispatch(self):
        for role in (None, "pending", "blocked"):
            with kokoro() as seen:
                self.assertEqual((await self.request(role=role)).status_code, 401)
                self.assertEqual((await self.request(role=role, path="voices")).status_code, 401)
                self.assertEqual(seen["calls"], [])

    async def test_admin_keeps_native_access(self):
        with kokoro():
            self.assertEqual((await self.request(role="admin")).status_code, 200)

    async def test_disabled_engine_fails_closed(self):
        try:
            self.app.state.config.TTS_ENGINE = "openai"
            with kokoro() as seen:
                self.assertEqual((await self.request()).status_code, 503)
                self.assertEqual((await self.request(path="voices")).status_code, 503)
                self.assertEqual(seen["calls"], [])
        finally:
            self.app.state.config.TTS_ENGINE = adapter.ENGINE

    async def test_static_compatible_voice_list_has_no_upstream_request(self):
        with kokoro() as seen:
            r = await self.request(path="voices")
        self.assertEqual(r.json(), {"voices": [{"id": "af_mica", "name": "af_mica"}]})
        self.assertEqual(r.headers["cache-control"], "private, no-store")
        self.assertEqual(seen["calls"], [])

    async def test_input_validation_and_destination_cannot_be_overridden(self):
        cases = [{}, {"input": ""}, {"input": " "}, {"input": 7}, {"input": "x" * 4001},
                 {"input": "x", "voice": "alloy"}, {"input": "x", "model": "tts-1"},
                 {"input": "x", "url": "http://private.invalid"},
                 {"input": "x", "speed": 2}, {"input": "x", "message_id": 42},
                 {"input": "x\x00"}, {"input": "\ud800"}]
        for payload in cases:
            with self.subTest(payload_keys=list(payload)), kokoro() as seen:
                self.assertEqual((await self.request(payload)).status_code, 400)
                self.assertEqual(seen["calls"], [])

    async def test_raw_body_limit_and_invalid_json(self):
        for raw, code in [(b"x" * (adapter.MAX_REQUEST_BYTES + 1), 413), (b"not-json", 400),
                          (b"[]", 400), (b"\xff", 400)]:
            with kokoro() as seen:
                r = await self.request(raw=raw, headers={"content-type": "application/json"})
                self.assertEqual(r.status_code, code)
                self.assertEqual(seen["calls"], [])
        self.assertEqual((await self.request(raw=b"{}", headers={"content-type": "text/plain"})).status_code, 415)

    async def test_upstream_failure_redirect_and_network_error_are_sanitized(self):
        for reply in [Reply(status=500, body=b"PRIVATE_SENTINEL"), Reply(status=302),
                      Reply(error=httpx.ConnectError("PRIVATE_SENTINEL"))]:
            with kokoro(reply) as seen:
                r = await self.request()
                self.assertEqual(r.status_code, 502)
                self.assertNotIn("PRIVATE_SENTINEL", r.text)
                self.assertEqual(r.headers["cache-control"], "private, no-store")
                self.assertEqual(len(seen["calls"]), 1)
                self.assertTrue(seen["closed"] and seen["response_closed"])

    async def test_upstream_transport_timeout(self):
        with kokoro(Reply(error=httpx.ReadTimeout("PRIVATE_SENTINEL"))) as seen:
            r = await self.request()
        self.assertEqual(r.status_code, 504)
        self.assertNotIn("PRIVATE_SENTINEL", r.text)
        self.assertEqual(len(seen["calls"]), 1)

    async def test_total_deadline_closes_transport_without_retry(self):
        with patch.object(adapter, "SYNTHESIS_SECONDS", 0.02), kokoro(delay=True) as seen:
            self.assertEqual((await self.request()).status_code, 504)
        self.assertTrue(seen["closed"] and seen["response_closed"])
        self.assertEqual(len(seen["calls"]), 1)

    async def test_response_size_type_and_wav_validation(self):
        replies = [Reply(body=b"not WAV"), Reply(body=wav_bytes()[:-2]),
                   Reply(mime="audio/mpeg"), Reply(encoding="gzip"), Reply(body=b"")]
        for reply in replies:
            with kokoro(reply):
                self.assertEqual((await self.request()).status_code, 502)
        with patch.object(adapter, "MAX_AUDIO_BYTES", 90), kokoro():
            self.assertEqual((await self.request()).status_code, 502)

    async def test_observed_kokoro_streaming_wav_lengths_are_finalized(self):
        original = wav_bytes()
        streaming = bytearray(original)
        streaming[4:8] = b"\xff" * 4
        data = streaming.index(b"data")
        streaming[data + 4:data + 8] = b"\xff" * 4
        with kokoro(Reply(body=bytes(streaming))):
            r = await self.request()
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content, original)
        # A finite but inconsistent header must not be silently repaired.
        streaming[data + 4:data + 8] = b"\x01\x00\x00\x00"
        with kokoro(Reply(body=bytes(streaming))):
            self.assertEqual((await self.request()).status_code, 502)

    async def test_missing_or_oversized_wav_chunk_is_rejected(self):
        for audio in (b"RIFF" + b"\xff" * 4 + b"WAVE", b"RIFF" + b"\xff" * 4 + b"WAVEJUNK" + b"\xff" * 4):
            with kokoro(Reply(body=audio)):
                self.assertEqual((await self.request()).status_code, 502)

    async def test_request_body_deadline(self):
        async def receive():
            await asyncio.Event().wait()
        request = Request({"type": "http", "method": "POST", "path": "/", "headers":
                           [(b"content-type", b"application/json")]}, receive)
        with patch.object(adapter, "BODY_SECONDS", 0.02):
            with self.assertRaises(HTTPException) as caught:
                await adapter.read_text(request)
        self.assertEqual(caught.exception.status_code, 408)

    async def test_client_disconnect_cancels_and_closes_upstream(self):
        with kokoro(delay=True) as seen:
            body_read = False
            async def receive():
                nonlocal body_read
                if not body_read:
                    body_read = True
                    return {"type": "http.request", "body": b'{"input":"hello"}'}
                await seen["started"].wait()
                return {"type": "http.disconnect"}
            request = Request({"type": "http", "method": "POST", "path": "/", "app": self.app,
                               "headers": [(b"content-type", b"application/json")]}, receive)
            with self.assertRaises(HTTPException) as caught:
                await adapter.speech(request)
            self.assertEqual(caught.exception.status_code, 499)
        self.assertTrue(seen["closed"] and seen["response_closed"])
        self.assertEqual(len(seen["calls"]), 1)

    async def test_asgi_cancellation_closes_upstream(self):
        with kokoro(delay=True) as seen:
            task = asyncio.create_task(self.request())
            await asyncio.wait_for(seen["started"].wait(), 1)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
        self.assertTrue(seen["closed"] and seen["response_closed"])

    async def test_no_storage_canonical_calls_or_private_logging(self):
        records = []
        class Capture(logging.Handler):
            def emit(self, record):
                records.append(record.getMessage())
        handler = Capture()
        logging.getLogger().addHandler(handler)
        try:
            with patch("builtins.open", side_effect=AssertionError("No file access")), \
                 patch.object(Path, "open", side_effect=AssertionError("No path access")), \
                 patch.object(sqlite3, "connect", side_effect=AssertionError("No DB access")), \
                 kokoro():
                r = await self.request({"input": "PRIVATE_SENTINEL"})
                self.assertEqual(r.status_code, 200)
            with kokoro(Reply(error=httpx.ConnectError("PRIVATE_SENTINEL"))):
                self.assertEqual((await self.request({"input": "PRIVATE_SENTINEL"})).status_code, 502)
        finally:
            logging.getLogger().removeHandler(handler)
        self.assertFalse(any("PRIVATE_SENTINEL" in record for record in records))


class ArtifactContracts(unittest.TestCase):
    def test_exact_pinned_patch_preserves_auth_and_all_other_handlers(self):
        source = (SOURCE / "backend/open_webui/routers/audio.py").read_text()
        result = prepare.patch_audio(source)
        original, changed = ast.parse(source), ast.parse(result)
        def normalize(tree):
            output = []
            for node in tree.body:
                if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "SPEECH_CACHE_DIR" for t in node.targets):
                    continue
                if isinstance(node, ast.Expr) and "SPEECH_CACHE_DIR.mkdir" in ast.unparse(node):
                    continue
                if isinstance(node, ast.AsyncFunctionDef) and node.name in {"speech", "get_voices"}:
                    self.assertEqual(ast.unparse(node.args), "request: Request, user=Depends(get_verified_user)")
                    node.body = [ast.Pass()]
                output.append(ast.dump(node, include_attributes=False))
            return output
        self.assertEqual(normalize(original), normalize(changed))
        self.assertNotIn("SPEECH_CACHE_DIR", result)
        with self.assertRaises(ValueError):
            prepare.patch_audio(source + "\n")
        with self.assertRaises(ValueError):
            prepare.patch_audio(result)

    def test_compiled_frontend_changes_only_private_debug_call(self):
        source = FRONTEND.read_text()
        result = prepare.patch_frontend(source)
        self.assertNotIn("Prepared message content for TTS", result)
        self.assertEqual(source, result.replace("return}G=kt.reduce", "return}" + prepare.DEBUG_CALL + "G=kt.reduce", 1))
        with self.assertRaises(ValueError):
            prepare.patch_frontend(source + "\n")

    def test_adapter_has_no_corvus_storage_logging_or_file_imports(self):
        tree = ast.parse((TTS / "kokoro.py").read_text())
        imports = [n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
        imports += [a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names]
        self.assertFalse(any(x.startswith(("app", "memory", "sqlite", "logging", "tempfile", "os")) for x in imports))
        self.assertNotIn("open(", (TTS / "kokoro.py").read_text().replace("wave.open(", ""))

    def test_existing_pipe_and_arena_patches_unchanged(self):
        expected = {
            "deploy/open-webui/corvus_pipe.py": "68967bd0ed499aaf2ecce38bc6afc80c3fc3cdeb805aab6a57182a2e907af861",
        }
        for name, digest in expected.items():
            self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), digest)
        for name in ("arena-ui1", "arena-ui2"):
            lock = json.loads((ROOT / f"deploy/open-webui/branding/{name}.lock.json").read_text())
            self.assertEqual(hashlib.sha256((ROOT / f"deploy/open-webui/branding/patches/{name}.patch").read_bytes()).hexdigest(), lock["patch_sha256"])

    def test_prepared_override_and_exact_https_image_inheritance(self):
        config = yaml.safe_load((ROOT / "deploy/lab/compose.tts.yml").read_text())
        self.assertEqual(set(config), {"services"})
        service = config["services"]["open-webui"]
        self.assertEqual(set(service), {"image", "pull_policy", "build", "environment"})
        self.assertEqual(service["environment"], {"AUDIO_TTS_ENGINE": "corvus-kokoro", "AUDIO_TTS_MODEL": "kokoro",
                                               "AUDIO_TTS_VOICE": "af_mica", "USER_PERMISSIONS_CHAT_TTS": "true"})
        dockerfile = (TTS / "Dockerfile").read_text()
        self.assertIn("FROM corvus-open-webui@sha256:453f9f2c4cee37c5e0d158ed3fcbdfc1e099bc6ef55ab47a7cbcce8b7331df76", dockerfile)
        self.assertNotIn("install", dockerfile.lower().replace("no dependency install", ""))
        self.assertNotIn("COPY . ", dockerfile)


if __name__ == "__main__":
    unittest.main()
