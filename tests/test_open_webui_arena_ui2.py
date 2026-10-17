"""Pinned UI-2 Action contract without importing or starting Open WebUI."""

import ast
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import tempfile
from types import SimpleNamespace
import unittest
from uuid import UUID, uuid4

from fastapi import HTTPException


ROOT = Path(__file__).resolve().parents[1]
BRAND = ROOT / "deploy/open-webui/branding"


class ArenaActionTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("ui2_verifier", BRAND / "verify_branding.py")
        cls.verifier = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.verifier)
        archive = Path(os.environ.get("CORVUS_OW2D_ARCHIVE", "/tmp/corvus-arena-ui1/upstream.tar.gz"))
        cls.temp = tempfile.TemporaryDirectory(prefix="corvus-ui2-test-")
        cls.source = Path(cls.temp.name) / "source"
        cls.verifier.prepare_source(cls.source, archive, arena_ui2=True)
        tree = ast.parse((cls.source / "backend/open_webui/main.py").read_text())
        nodes = deepcopy([n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                          and n.name in {"persist_corvus_arena_vote", "corvus_arena_vote"}])
        for node in nodes:
            node.decorator_list = []
            node.args.defaults = []
        cls.code = compile(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])),
                           "pinned-ui2-action", "exec")

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.trial = str(uuid4())
        self.message_id = str(uuid4())
        self.message = {"role": "assistant", "model": "corvus_pipe", "done": True,
                        "corvus_arena_requested": True,
                        "content": "Canonical answer",
                        "corvus_arena": {"trial_id": self.trial,
                                         "evaluation": {"status": "STORED", "votable": True}}}
        self.chat = SimpleNamespace(chat={"history": {"currentId": self.message_id,
            "messages": {self.message_id: self.message}}})
        self.connection = sqlite3.connect(":memory:")
        self.engine = SimpleNamespace(dialect=SimpleNamespace(name="sqlite"),
                                      begin=lambda: self.connection)
        with self.connection as conn:
            conn.execute("CREATE TABLE chat (id TEXT PRIMARY KEY, user_id TEXT, chat TEXT, updated_at INTEGER)")
            for chat_id, content in (("chat", self.chat.chat), ("other", {"history": {"messages": {}}})):
                conn.execute("INSERT INTO chat VALUES (:id, 'owner', :chat, 0)",
                             {"id": chat_id, "chat": json.dumps(content)})
        self.addCleanup(self.connection.close)
        self.posts = []
        self.lookups = []
        self.after_post = lambda: None
        self.active_chat = "chat"

        def lookup(chat_id, user_id):
            self.lookups.append((chat_id, user_id))
            return self.chat if (chat_id, user_id) == ("chat", "owner") else None

        outer = self
        class Client:
            def __init__(self, **kwargs):
                assert kwargs["follow_redirects"] is False
                assert kwargs["trust_env"] is False
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                return False
            async def post(self, url, json):
                outer.posts.append((url, json))
                outer.after_post()
                return SimpleNamespace(raise_for_status=lambda: None,
                                       json=lambda: dict(json, recorded_at="2026-10-16T00:00:00+00:00"))

        namespace = {"HTTPException": HTTPException, "UUID": UUID,
                     "Chats": SimpleNamespace(get_chat_by_id_and_user_id=lookup),
                     "engine": self.engine, "text": lambda value: value,
                     "time": SimpleNamespace(time=lambda: 1),
                     "httpx": SimpleNamespace(AsyncClient=Client,
                                               Timeout=lambda *a, **kw: object(),
                                               AsyncHTTPTransport=lambda **kw: object())}
        exec(self.code, namespace)
        self.action = namespace["corvus_arena_vote"]

    def body(self, choice="rag"):
        return {"chat_id": "chat", "message_id": self.message_id,
                "trial_id": self.trial, "choice": choice}

    def saved(self, chat_id="chat"):
        return json.loads(self.connection.execute("SELECT chat FROM chat WHERE id=:id",
            {"id": chat_id}).fetchone()[0])

    async def test_rag_and_hindsight_forward_only_vote_fields_once(self):
        for choice in ("rag", "hindsight"):
            result = await self.action(self.body(choice), SimpleNamespace(id="owner"))
            self.assertEqual(result["choice"], choice)
            self.assertIs(result["marker_persisted"], True)
        self.assertEqual(self.lookups, [("chat", "owner"), ("chat", "owner")])
        self.assertEqual(self.posts, [
            ("http://127.0.0.1:18096/api/arena/vote", {"trial_id": self.trial, "choice": choice})
            for choice in ("rag", "hindsight")])
        self.assertFalse(any("/api/arena/chat" in url for url, _ in self.posts))
        self.assertEqual(self.saved()["history"]["messages"][self.message_id]["corvus_arena"]["vote"], "hindsight")

    async def test_navigation_keeps_original_message_and_other_chat_unchanged(self):
        other_before = self.saved("other")
        def navigate_and_update_canonical():
            self.active_chat = "other"
            newer = self.saved()
            newer["history"]["messages"][self.message_id]["content"] = "Newer canonical answer"
            with self.connection as conn:
                conn.execute("UPDATE chat SET chat=:chat WHERE id='chat'", {"chat": json.dumps(newer)})
        self.after_post = navigate_and_update_canonical
        result = await self.action(self.body(), SimpleNamespace(id="owner"))
        self.assertEqual(self.active_chat, "other")
        self.assertIs(result["marker_persisted"], True)
        saved = self.saved()
        self.assertEqual(saved["history"]["messages"][self.message_id]["corvus_arena"]["vote"], "rag")
        self.assertEqual(saved["history"]["messages"][self.message_id]["content"], "Newer canonical answer")
        self.assertEqual(saved["history"]["currentId"], self.message_id)
        self.assertEqual(self.saved("other"), other_before)

    async def test_marker_failure_reports_false_without_undoing_durable_vote(self):
        def remove_association():
            with self.connection as conn:
                conn.execute("UPDATE chat SET chat=:chat WHERE id='chat'",
                             {"chat": json.dumps({"history": {"messages": {}}})})
        self.after_post = remove_association
        result = await self.action(self.body(), SimpleNamespace(id="owner"))
        self.assertEqual(len(self.posts), 1)
        self.assertIs(result["marker_persisted"], False)
        self.assertEqual(self.saved()["history"]["messages"], {})

    async def test_unowned_or_unavailable_trial_and_extra_fields_fail_without_forwarding(self):
        for body, user in ((self.body(), "other"),
                           (dict(self.body(), trial_id=str(uuid4())), "owner"),
                           (dict(self.body(), choice="tie"), "owner"),
                           (dict(self.body(), arbitrary="value"), "owner")):
            with self.assertRaises(HTTPException):
                await self.action(body, SimpleNamespace(id=user))
        self.assertEqual(self.posts, [])


if __name__ == "__main__":
    unittest.main()
