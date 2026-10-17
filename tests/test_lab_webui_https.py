"""Offline Lab HTTPS/PWA contracts; never use real credentials or runtime data."""

import ast
import asyncio
import __future__
from copy import deepcopy
import hashlib
import importlib.util
import json
import os
import inspect
import logging
from pathlib import Path
import struct
import subprocess
import tempfile
import time
from types import SimpleNamespace
from typing import AsyncGenerator, Generator, Iterator
import unittest
from unittest.mock import patch
import uuid

import httpx
from pydantic import BaseModel

from starlette.responses import JSONResponse, StreamingResponse


ROOT = Path(__file__).resolve().parents[1]
LAB = ROOT / "deploy/lab"
BRAND = ROOT / "deploy/open-webui/branding"


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LabHTTPSContracts(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="corvus-r03b-contract-")
        cls.addClassCleanup(cls.temp.cleanup)
        cls.source = Path(cls.temp.name) / "source"
        archive = Path(os.environ.get("CORVUS_OW2D_ARCHIVE", "/tmp/corvus-arena-ui1/upstream.tar.gz"))
        if not archive.is_file():
            raise RuntimeError("Pinned local archive required; do not download dependencies")
        load(BRAND / "verify_branding.py", "https_branding").prepare_source(
            cls.source, archive, arena_ui2=True)
        cls.patch = load(LAB / "https/prepare_manifest.py", "https_manifest")
        cls.manifest = json.loads((LAB / "https/manifest.json").read_text())

    def compose(self, remote):
        files = ["compose.webui.yml", "compose.boot.yml", "compose.arena-ui2.yml"]
        if remote:
            files.append("compose.https.yml")
        args = ["docker", "compose", "--env-file", "/dev/null"]
        for filename in files:
            args += ["-f", str(LAB / filename)]
        # Placeholder for interpolation only; never read the private env file.
        env = dict(os.environ, CORVUS_LAB_WEBUI_SECRET_KEY="OFFLINE_VALIDATION_PLACEHOLDER")
        return json.loads(subprocess.check_output(args + ["config", "--format", "json"], env=env))

    def test_override_changes_only_image_build_and_supported_https_settings(self):
        local = self.compose(False)
        remote = self.compose(True)
        self.assertEqual(set(remote["services"]), {"open-webui"})
        before = deepcopy(local["services"]["open-webui"])
        after = deepcopy(remote["services"]["open-webui"])
        self.assertEqual(before.pop("image"), "corvus-open-webui:0.6.5-arena-ui2.1")
        self.assertEqual(after.pop("image"), "corvus-open-webui:0.6.5-arena-ui2.1-https-r03b")
        before.pop("build")
        self.assertEqual(after.pop("build"), {"context": str(LAB / "https"), "dockerfile": "Dockerfile"})
        expected = {"WEBUI_URL": "https://lab-corvus.foxluma.com",
                    "WEBUI_AUTH_COOKIE_SECURE": "true", "WEBUI_SESSION_COOKIE_SECURE": "true",
                    "WEBUI_AUTH_COOKIE_SAME_SITE": "lax", "WEBUI_SESSION_COOKIE_SAME_SITE": "lax"}
        for key, value in expected.items():
            self.assertEqual(after["environment"].pop(key), value)
        self.assertEqual(before["environment"].pop("WEBUI_URL"), "http://127.0.0.1:3003")
        self.assertEqual(before, after)  # Auth, secrets, volume, host/port and boot policy unchanged.
        self.assertEqual(local["volumes"], remote["volumes"])
        self.assertEqual(after["environment"]["HOST"], "127.0.0.1")
        self.assertEqual(after["environment"]["PORT"], "3003")
        self.assertEqual(after["environment"]["WEBUI_AUTH"], "true")
        self.assertNotIn("ports", after)

    def test_cookie_flags_are_supported_and_auth_cookie_remains_httponly(self):
        env_source = (self.source / "backend/open_webui/env.py").read_text()
        names = {"WEBUI_SESSION_COOKIE_SECURE", "WEBUI_AUTH_COOKIE_SECURE",
                 "WEBUI_SESSION_COOKIE_SAME_SITE", "WEBUI_AUTH_COOKIE_SAME_SITE"}
        nodes = [n for n in ast.parse(env_source).body if isinstance(n, ast.Assign)
                 and any(isinstance(t, ast.Name) and t.id in names for t in n.targets)]
        self.assertEqual(len(nodes), 4)
        namespace = {"os": type("Env", (), {"environ": {
            "WEBUI_AUTH_COOKIE_SECURE": "true", "WEBUI_SESSION_COOKIE_SECURE": "true"}})}
        exec(compile(ast.Module(body=nodes, type_ignores=[]), "pinned-cookie-flags", "exec"), namespace)
        self.assertIs(namespace["WEBUI_AUTH_COOKIE_SECURE"], True)
        self.assertIs(namespace["WEBUI_SESSION_COOKIE_SECURE"], True)
        self.assertEqual(namespace["WEBUI_AUTH_COOKIE_SAME_SITE"], "lax")
        auth = ast.parse((self.source / "backend/open_webui/routers/auths.py").read_text())
        signin = next(n for n in auth.body if isinstance(n, ast.AsyncFunctionDef) and n.name == "signin")
        cookie = next(n for n in ast.walk(signin) if isinstance(n, ast.Call)
                      and isinstance(n.func, ast.Attribute) and n.func.attr == "set_cookie")
        args = {kw.arg: kw.value for kw in cookie.keywords}
        self.assertIs(ast.literal_eval(args["httponly"]), True)
        self.assertEqual(args["secure"].id, "WEBUI_AUTH_COOKIE_SECURE")
        self.assertNotIn("domain", args)

    async def test_manifest_response_and_existing_asset_dimensions(self):
        original = (self.source / "backend/open_webui/main.py").read_text()
        patched = self.patch.prepare(original, self.manifest)
        tree = ast.parse(patched)
        handler = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef)
                       and n.name == "get_manifest_json")
        handler.decorator_list = []
        namespace = {"JSONResponse": JSONResponse}
        exec(compile(ast.Module(body=[handler], type_ignores=[]), "lab-manifest", "exec"), namespace)
        response = await namespace["get_manifest_json"]()
        self.assertEqual(response.media_type, "application/manifest+json")
        self.assertEqual(json.loads(response.body), self.manifest)
        self.assertEqual([self.manifest[k] for k in ("name", "short_name", "start_url", "scope", "display")],
                         ["Corvus", "Corvus", "/", "/", "standalone"])
        for icon in self.manifest["icons"]:
            asset = BRAND / "assets" / Path(icon["src"]).name
            width, height = struct.unpack(">II", asset.read_bytes()[16:24])
            self.assertEqual(icon["sizes"], f"{width}x{height}")
            self.assertIn(icon["sizes"], {"192x192", "512x512"})
            self.assertEqual(icon["type"], "image/png")
        self.assertEqual({i["sizes"] for i in self.manifest["icons"]}, {"192x192", "512x512"})
        html = (self.source / "src/app.html").read_text()
        self.assertIn('href="/manifest.json" crossorigin="use-credentials"', html)
        self.assertIn('rel="apple-touch-icon" sizes="180x180" href="/static/apple-touch-icon.png"', html)
        self.assertEqual(struct.unpack(">II", (BRAND / "assets/apple-touch-icon.png").read_bytes()[16:24]),
                         (180, 180))

    def test_manifest_patch_changes_no_other_function_and_rejects_drift(self):
        source = (self.source / "backend/open_webui/main.py").read_text()
        def without_manifest(text):
            tree = ast.parse(text)
            tree.body = [n for n in tree.body if getattr(n, "name", None) != "get_manifest_json"]
            return ast.dump(tree, include_attributes=False)
        self.assertEqual(without_manifest(source), without_manifest(self.patch.prepare(source, self.manifest)))
        with self.assertRaisesRegex(ValueError, "pinned Lab"):
            self.patch.prepare(source + "\n# drift\n", self.manifest)
        dockerfile = (LAB / "https/Dockerfile").read_text()
        self.assertIn("@sha256:8dea93c991ce80e1d1496783ee7badca025ec38be3fee666a682a679705980be", dockerfile)
        self.assertNotIn("pip install", dockerfile)
        self.assertNotIn("npm", dockerfile)
        self.assertEqual(hashlib.sha256((ROOT / "deploy/open-webui/corvus_pipe.py").read_bytes()).hexdigest(),
                         "cc5299b32fedb0f10ee2a37c7466121049a2837c09dc0ec0c7d6f8bd157ec890")


def pinned_functions(path, names, namespace):
    """Execute complete pinned function bodies with fake I/O, without app startup."""
    tree = ast.parse(path.read_text())
    nodes = [deepcopy(n) for n in tree.body
             if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in names]
    if {n.name for n in nodes} != set(names):
        raise AssertionError("Pinned function missing")
    for node in nodes:
        node.decorator_list = []
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec",
                 flags=__future__.annotations.compiler_flag), namespace)


class PinnedTaskSocketTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        LabHTTPSContracts.setUpClass.__func__(cls)

    def setUp(self):
        self.started = asyncio.Event()
        self.release = asyncio.Event()
        self.posts = []
        self.emissions = []
        self.saved = {}
        self.adapter = load(ROOT / "deploy/open-webui/corvus_pipe.py", "https_test_pipe")
        self.pipe = self.adapter.Pipe()
        self.pipe.valves.INSTANCE_ID = "offline-test-only"
        self.pipe.valves.CORVUS_CHAT_URL = "http://127.0.0.1:18096/api/chat"
        self.chat_id = "3c57a4d8-0201-4db0-8e6e-a8fc734ba6a0"
        self.metadata = {"user_id": "offline-user", "chat_id": self.chat_id,
                         "message_id": "offline-response", "session_id": "socket-before"}
        self.user = SimpleNamespace(id="offline-user", email="offline@example.invalid",
                                    name="Offline", role="user")
        self.request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(
            config=SimpleNamespace(), WEBUI_NAME="Corvus")))
        self.session_pool = {"socket-before": {"id": self.user.id}}
        self.user_pool = {self.user.id: ["socket-before"]}

        async def emit(name, data, **kwargs):
            self.emissions.append((name, deepcopy(data), kwargs))

        def save(chat_id, message_id, data):
            self.assertEqual((chat_id, message_id), (self.chat_id, "offline-response"))
            self.saved.update(deepcopy(data))

        chats = SimpleNamespace(
            upsert_message_to_chat_by_id_and_message_id=save,
            get_message_by_id_and_message_id=lambda *args: dict(self.saved),
            get_messages_by_chat_id=lambda *args: {},
            get_chat_title_by_id=lambda *args: "Offline test")

        async def filters(**kwargs):
            return kwargs["form_data"], {}

        self.ns = {"asyncio": asyncio, "json": json, "inspect": inspect,
                   "time": time, "uuid": uuid, "uuid4": uuid.uuid4,
                   "log": logging.getLogger("offline-pinned-task"),
                   "BaseModel": BaseModel, "AsyncGenerator": AsyncGenerator,
                   "Generator": Generator, "Iterator": Iterator,
                   "StreamingResponse": StreamingResponse,
                   "Models": SimpleNamespace(get_model_by_id=lambda *args: None),
                   "get_function_module_by_id": lambda *args: self.pipe,
                   "get_tools": lambda *args: {}, "Chats": chats,
                   "get_sorted_filter_ids": lambda *args: [],
                   "process_filter_functions": filters,
                   "get_active_status_by_user_id": lambda *args: True,
                   "ENABLE_REALTIME_CHAT_SAVE": False,
                   "USER_POOL": self.user_pool, "SESSION_POOL": self.session_pool,
                   "sio": SimpleNamespace(emit=emit), "tasks": {}, "chat_tasks": {}}
        backend = self.source / "backend/open_webui"
        pinned_functions(backend / "utils/misc.py", ["openai_chat_message_template",
            "openai_chat_chunk_message_template", "openai_chat_completion_message_template"], self.ns)
        pinned_functions(backend / "socket/main.py", ["get_event_emitter", "get_event_call", "disconnect"], self.ns)
        pinned_functions(backend / "tasks.py", ["create_task", "cleanup_task", "list_task_ids_by_chat_id"], self.ns)
        pinned_functions(backend / "functions.py", ["generate_function_chat_completion"], self.ns)
        pinned_functions(backend / "utils/middleware.py", ["process_chat_response"], self.ns)

    async def submit(self, *, confirmed=True):
        async def transport(request):
            self.posts.append(request)
            payload = json.loads(request.content)
            self.started.set()
            await self.release.wait()
            return httpx.Response(200, json={"session_id": payload["session_id"],
                "reply": "Offline confirmed reply", "status": {"overall": "OK", "model": "OK",
                    "persistence": "NORMAL" if confirmed else "ASSISTANT_PERSISTENCE_FAILED"}})

        original_client = httpx.AsyncClient
        def client(**kwargs):
            self.assertIs(kwargs["follow_redirects"], False)
            self.assertIs(kwargs["trust_env"], False)
            kwargs["transport"] = httpx.MockTransport(transport)
            return original_client(**kwargs)
        self.client_patch = patch.object(self.adapter.httpx, "AsyncClient", client)
        self.client_patch.start()
        self.addCleanup(self.client_patch.stop)
        body = {"model": "corvus_pipe", "stream": True,
                "messages": [{"role": "user", "content": "Offline synthetic input"}],
                "metadata": dict(self.metadata)}
        response = await self.ns["generate_function_chat_completion"](
            self.request, body, self.user, {"corvus_pipe": {}})
        result = await self.ns["process_chat_response"](
            self.request, response, body, self.user, self.metadata, {}, [], None)
        self.assertIs(result["status"], True)
        self.assertEqual(set(result), {"status", "task_id"})
        self.task_id = result["task_id"]
        self.task = self.ns["tasks"][self.task_id]
        self.addAsyncCleanup(self.cancel_pending)
        await asyncio.wait_for(self.started.wait(), 1)
        return result

    async def cancel_pending(self):
        if not self.task.done():
            self.task.cancel()
            await asyncio.gather(self.task, return_exceptions=True)

    async def test_delayed_pipe_keeps_task_and_socket_identity_with_one_post(self):
        result = await self.submit()
        self.assertFalse(self.task.done())
        self.assertEqual(self.ns["list_task_ids_by_chat_id"](self.chat_id), [result["task_id"]])
        self.assertEqual(len(self.posts), 1)
        self.assertFalse(self.emissions)
        self.release.set()
        await asyncio.wait_for(self.task, 1)
        final = [e for e in self.emissions if e[1].get("data", {}).get("data", {}).get("done")]
        self.assertEqual(len(final), 1)
        event, data, target = final[0]
        self.assertEqual(event, "chat-events")
        self.assertEqual(target, {"to": "socket-before"})
        self.assertEqual((data["chat_id"], data["message_id"]),
                         (self.chat_id, self.metadata["message_id"]))
        self.assertEqual(data["data"]["type"], "chat:completion")
        self.assertIn("Offline confirmed reply", data["data"]["data"]["content"])
        self.assertEqual(len(self.posts), 1)
        self.assertNotIn(self.task_id, self.ns["tasks"])

    async def test_disconnect_and_reconnect_bookkeeping_does_not_resubmit(self):
        await self.submit()
        await self.ns["disconnect"]("socket-before")
        self.assertFalse(self.task.done())
        # Simulate an authenticated new socket registration; no browser/network I/O.
        self.user_pool[self.user.id] = ["socket-after"]
        self.session_pool["socket-after"] = {"id": self.user.id}
        self.assertEqual(self.ns["list_task_ids_by_chat_id"](self.chat_id), [self.task_id])
        self.release.set()
        await asyncio.wait_for(self.task, 1)
        self.assertEqual(len(self.posts), 1)
        self.assertTrue(any(e[0] == "chat-events" and e[2] == {"to": "socket-after"}
                            for e in self.emissions))
        layout = (self.source / "src/routes/+layout.svelte").read_text()
        setup = layout.split("const setupSocket =", 1)[1].split("const executePythonAsWorker", 1)[0]
        self.assertIn("reconnection: true", setup)
        self.assertIn("path: '/ws/socket.io'", setup)
        self.assertNotIn("generateOpenAIChatCompletion", setup)
        self.assertNotIn("/chat/completions", setup)
        self.assertNotIn("fetch(", setup)

    async def test_unconfirmed_persistence_never_emits_successful_reply(self):
        await self.submit(confirmed=False)
        self.release.set()
        await asyncio.wait_for(self.task, 1)
        events = [e[1] for e in self.emissions if e[0] == "chat-events"]
        self.assertTrue(any("may already have been saved" in json.dumps(e) for e in events))
        self.assertNotIn("Offline confirmed reply", json.dumps(events))
        self.assertNotIn("Offline confirmed reply", json.dumps(self.saved))
        self.assertEqual(len(self.posts), 1)
