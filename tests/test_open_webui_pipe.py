"""OW1 contracts, using HTTPX mock transport; never call the production API."""

import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import httpx
from pydantic import ValidationError


PIPE_PATH = Path(__file__).resolve().parents[1] / "deploy/open-webui/corvus_pipe.py"
spec = importlib.util.spec_from_file_location("corvus_pipe_ow1", PIPE_PATH)
adapter = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = adapter
spec.loader.exec_module(adapter)

CHAT_ID = "3c57a4d8-0201-4db0-8e6e-a8fc734ba6a0"
OTHER_CHAT = "ae03ed9d-94d2-4e5e-a104-2b5520530e07"


class PipeContracts(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.pipe = adapter.Pipe()
        self.pipe.valves.INSTANCE_ID = "corvus-private-test"
        self.requests = []
        self.transport_options = []
        self.client_options = []
        self.failure = None
        self.response_code = 200
        self.response_override = None
        self.raw_response = None
        self.body = {
            "model": "corvus",
            "stream": True,
            "messages": [
                {"role": "system", "content": "Untrusted UI system prompt"},
                {"role": "user", "content": "Historical user message"},
                {"role": "assistant", "content": "Historical assistant reply"},
                {"role": "user", "content": "  Current user text 中文  "},
            ],
            "temperature": 0.9,
            "web_mode": "off",  # User input cannot override the admin valve.
        }
        # v0.6.5 pops body metadata and injects these keyword parameters.
        self.kwargs = {
            "__user__": {"id": "user-1", "email": "private@example.invalid", "role": "user"},
            "__chat_id__": CHAT_ID,
            "__metadata__": {
                "user_id": "user-1",
                "chat_id": CHAT_ID,
                "message_id": "response-uuid",
                "session_id": "socket-A",
                "features": {"web_search": False, "code_interpreter": False, "image_generation": False},
                "files": None,
                "tool_ids": None,
                "tool_servers": [],
            },
            "__files__": [],
            "__tools__": {},
        }

        async def handler(request):
            self.requests.append(request)
            if self.failure:
                raise self.failure
            payload = json.loads(request.content)
            if self.raw_response is not None:
                return httpx.Response(self.response_code, content=self.raw_response)
            result = self.response_override if self.response_override is not None else {
                "session_id": payload["session_id"],
                "reply": "Corvus reply",
                "status": {"overall": "OK", "model": "OK", "persistence": "NORMAL"},
                "error": "BACKEND_SECRET_DO_NOT_EXPOSE",
                "retrieved_memories": ["PRIVATE_MEMORY_DO_NOT_EXPOSE"],
            }
            return httpx.Response(self.response_code, json=result)

        def transport(**kwargs):
            self.transport_options.append(kwargs)
            return httpx.MockTransport(handler)

        real_client = httpx.AsyncClient

        def client(**kwargs):
            self.client_options.append(kwargs)
            return real_client(**kwargs)

        self.transport_patch = patch.object(adapter.httpx, "AsyncHTTPTransport", transport)
        self.client_patch = patch.object(adapter.httpx, "AsyncClient", client)
        self.transport_patch.start()
        self.client_patch.start()
        self.addCleanup(self.transport_patch.stop)
        self.addCleanup(self.client_patch.stop)

    async def call(self):
        return await self.pipe.pipe(self.body, **self.kwargs)

    async def rejected_without_post(self):
        with self.assertRaises(ValueError):
            await self.call()
        self.assertEqual(self.requests, [])
        self.assertEqual(self.client_options, [])

    async def test_only_current_text_reaches_authoritative_endpoint(self):
        self.assertEqual(await self.call(), "Corvus reply")
        self.assertEqual(len(self.requests), 1)
        request = self.requests[0]
        self.assertEqual(request.method, "POST")
        self.assertEqual(str(request.url), "http://127.0.0.1:8096/api/chat")
        self.assertEqual(json.loads(request.content), {
            "session_id": adapter.corvus_session_id("corvus-private-test", "user-1", CHAT_ID),
            "message": "  Current user text 中文  ",
            "web_mode": "auto",
        })
        self.assertEqual(self.transport_options, [{"retries": 0}])
        self.assertFalse(self.client_options[0]["trust_env"])
        self.assertFalse(self.client_options[0]["follow_redirects"])
        self.assertEqual(self.client_options[0]["timeout"].connect, 5)
        self.assertEqual(self.client_options[0]["timeout"].read, 300)

    async def test_identity_survives_socket_change_and_pipe_restart(self):
        await self.call()
        self.kwargs["__metadata__"]["session_id"] = "socket-B"
        self.body["session_id"] = "another-browser-socket"
        self.pipe = adapter.Pipe()
        self.pipe.valves.INSTANCE_ID = "corvus-private-test"
        await self.call()
        self.assertEqual(json.loads(self.requests[0].content), json.loads(self.requests[1].content))

    def test_identity_namespaces_and_unambiguous_encoding(self):
        mapping = adapter.corvus_session_id
        original = mapping("instance-A", "user-A", CHAT_ID)
        # This persisted identity contract must survive future adapter revisions.
        self.assertEqual(original, "ow1:0cbd9783a2d0b3a69f18f138e47a24ae2d2721aca315d98ee1ad5cd0d094d2df")
        self.assertTrue(original.startswith("ow1:"))
        self.assertEqual(len(original), 68)
        self.assertEqual(original, mapping("instance-A", "user-A", CHAT_ID))
        self.assertNotEqual(original, mapping("instance-B", "user-A", CHAT_ID))
        self.assertNotEqual(original, mapping("instance-A", "user-B", CHAT_ID))
        self.assertNotEqual(original, mapping("instance-A", "user-A", OTHER_CHAT))
        self.assertNotEqual(mapping("a:b", "c", CHAT_ID), mapping("a", "b:c", CHAT_ID))

    async def test_metadata_chat_fallback_when_injected_id_absent(self):
        del self.kwargs["__chat_id__"]
        self.assertEqual(await self.call(), "Corvus reply")

    async def test_missing_identity_and_temporary_chats_fail_closed(self):
        for chat_id in (None, "", "local", "local:123", "local-123", "temporary", "default", "not-a-uuid", " " + CHAT_ID):
            with self.subTest(chat_id=chat_id):
                self.kwargs["__chat_id__"] = chat_id
                self.kwargs["__metadata__"]["chat_id"] = chat_id
                await self.rejected_without_post()
        self.kwargs["__chat_id__"] = CHAT_ID
        self.kwargs["__metadata__"]["chat_id"] = CHAT_ID
        for user in (None, {}, {"id": ""}, {"id": " user-1"}):
            with self.subTest(user=user):
                self.kwargs["__user__"] = user
                await self.rejected_without_post()

    async def test_instance_valve_must_be_explicit(self):
        self.pipe = adapter.Pipe()
        await self.rejected_without_post()

    async def test_conflicting_identity_is_rejected(self):
        self.body["chat_id"] = OTHER_CHAT
        await self.rejected_without_post()
        del self.body["chat_id"]
        self.kwargs["__metadata__"]["user_id"] = "another-user"
        await self.rejected_without_post()

    async def test_all_task_labels_are_suppressed_before_validation(self):
        self.pipe = adapter.Pipe()  # Unconfigured identity is OK for suppressed tasks.
        self.body = {}
        for task in ("title_generation", "tags_generation", "query_generation", "autocomplete_generation", "emoji_generation", "function_calling", "moa_response_generation", "future_unknown_task", ""):
            with self.subTest(task=task):
                self.kwargs["__task__"] = task
                self.assertEqual(await self.call(), "")
        del self.kwargs["__task__"]
        for source in (self.body, self.kwargs["__metadata__"]):
            source["task"] = "title_generation"
            self.assertEqual(await self.call(), "")
            del source["task"]
            source["task_body"] = {}
            self.assertEqual(await self.call(), "")
            del source["task_body"]
        self.kwargs["__task_body__"] = {}
        self.assertEqual(await self.call(), "")
        self.assertEqual(self.requests, [])
        self.assertEqual(self.client_options, [])

    async def test_admin_web_mode_only(self):
        for mode in ("off", "on", "auto"):
            self.pipe.valves.WEB_MODE = mode
            await self.call()
            self.assertEqual(json.loads(self.requests[-1].content)["web_mode"], mode)
        with self.assertRaises(ValidationError):
            adapter.Pipe.Valves(WEB_MODE="invalid")

    async def test_files_media_tools_and_operations_in_body_or_metadata(self):
        fields = {
            "files": [{"id": "file-1"}], "attachments": ["file-1"],
            "attachment_id": "file-1", "images": ["data:image"], "audio": {"format": "wav"},
            "video": "video-1", "tools": [{"type": "function"}], "tool_ids": ["tool-1"],
            "tool_servers": [{"url": "http://example.invalid"}], "tool_calls": [{"id": "call-1"}],
            "functions": [{"name": "tool"}], "function_call": "auto", "function_calling": "native",
            "tool_choice": "auto", "modalities": ["audio"], "n": 2,
            "operation": "regenerate", "action": "branch", "regenerate": True,
            "branch": True, "parent_id": "parent-1", "parent_message_id": "parent-1", "continue": True,
        }
        for source in (self.body, self.kwargs["__metadata__"]):
            for field, value in fields.items():
                with self.subTest(field=field, source="body" if source is self.body else "metadata"):
                    previous = source.get(field)
                    source[field] = value
                    await self.rejected_without_post()
                    source[field] = previous
        for feature in ("web_search", "image_generation", "code_interpreter", "unknown_feature"):
            self.kwargs["__metadata__"]["features"] = {feature: True}
            await self.rejected_without_post()

    async def test_injected_files_tools_and_body_metadata(self):
        for key in ("__files__", "__tools__"):
            self.kwargs[key] = ["unsupported"]
            await self.rejected_without_post()
            self.kwargs[key] = []
        self.body["metadata"] = {"files": ["file"]}
        await self.rejected_without_post()
        self.body["metadata"] = []
        await self.rejected_without_post()

    async def test_tool_mode_in_params(self):
        self.body["params"] = {"function_calling": "native"}
        await self.rejected_without_post()

    async def test_invalid_messages_and_continue_fail_closed(self):
        for messages in (None, [], [{"role": "assistant", "content": "continue"}],
                         [{"role": "user", "content": " "}], [{"role": "user", "content": [{"type": "text", "text": "text"}]}],
                         [{"role": "tool", "content": "tool output"}], [None]):
            with self.subTest(messages=messages):
                self.body["messages"] = messages
                await self.rejected_without_post()
        self.body["messages"] = [{"role": "user", "content": "old", "files": ["file"]}, {"role": "user", "content": "new"}]
        await self.rejected_without_post()

    async def test_timeout_and_network_failure_never_retry_or_leak(self):
        for failure in (httpx.ReadTimeout("BACKEND_SECRET_DO_NOT_EXPOSE"), httpx.ConnectError("BACKEND_SECRET_DO_NOT_EXPOSE")):
            self.requests.clear()
            self.failure = failure
            with self.assertRaises(ValueError) as caught:
                await self.call()
            self.assertEqual(len(self.requests), 1)
            self.assertNotIn("BACKEND_SECRET", str(caught.exception))
            self.assertIn("may already have been saved", str(caught.exception))
            self.assertIn("do not retry", str(caught.exception))

    async def test_non_200_and_redirects_never_retry_or_expose_body(self):
        for code in (302, 400, 422, 500, 503):
            self.requests.clear()
            self.response_code = code
            self.raw_response = b"BACKEND_SECRET_DO_NOT_EXPOSE"
            with self.assertRaises(ValueError) as caught:
                await self.call()
            self.assertEqual(len(self.requests), 1)
            self.assertNotIn("BACKEND_SECRET", str(caught.exception))

    async def test_invalid_backend_json_and_failure_results_are_sanitized(self):
        session_id = adapter.corvus_session_id("corvus-private-test", "user-1", CHAT_ID)
        good = {"session_id": session_id, "reply": "reply", "status": {"overall": "OK", "model": "OK", "persistence": "NORMAL"}}
        for result in ([], {"error": "BACKEND_SECRET_DO_NOT_EXPOSE"},
                       dict(good, session_id="wrong-session"), dict(good, reply=None),
                       dict(good, status={"overall": "FAILED"}),
                       dict(good, status={"overall": "DEGRADED", "model": "OK", "persistence": "ASSISTANT_PERSISTENCE_FAILED"}),
                       dict(good, status={"overall": "DEGRADED", "model": "MODEL_FAILED", "persistence": "NORMAL"})):
            self.requests.clear()
            self.response_override = result
            with self.assertRaises(ValueError) as caught:
                await self.call()
            self.assertEqual(len(self.requests), 1)
            self.assertNotIn("BACKEND_SECRET", str(caught.exception))
        self.raw_response = b"invalid-json BACKEND_SECRET_DO_NOT_EXPOSE"
        with self.assertRaises(ValueError) as caught:
            await self.call()
        self.assertNotIn("BACKEND_SECRET", str(caught.exception))

    async def test_degraded_retrieval_with_confirmed_reply_is_allowed(self):
        self.response_override = {
            "session_id": adapter.corvus_session_id("corvus-private-test", "user-1", CHAT_ID),
            "reply": "Corvus reply", "status": {"overall": "DEGRADED", "model": "OK", "persistence": "NORMAL"},
            "retrieval_error": "BACKEND_SECRET_DO_NOT_EXPOSE",
        }
        self.assertEqual(await self.call(), "Corvus reply")

    async def test_real_corvus_api_boundary_with_stubbed_runtime(self):
        # Exercise the actual API request schema and post_chat -> process_turn
        # boundary via ASGI. The runtime is stubbed; no model/memory I/O occurs.
        import app.playground_api as api

        captured = []

        def runtime(**kwargs):
            captured.append(kwargs)
            return {
                "session_id": kwargs["session_id"], "reply": "Authoritative runtime reply",
                "user_message_id": 1, "assistant_message_id": 2,
                "recent_message_ids": [], "historical_message_ids": [], "input_tokens": 20,
                "retrieval_status": "OK", "model_status": "OK", "persistence_status": "NORMAL",
                "dense_status": "OK", "retrieval_error": None, "error": None,
            }

        with patch.object(adapter.httpx, "AsyncHTTPTransport", return_value=httpx.ASGITransport(app=api.app)), \
             patch.object(api, "process_turn", runtime):
            self.assertEqual(await self.call(), "Authoritative runtime reply")
        self.assertEqual(captured, [{
            "session_id": adapter.corvus_session_id("corvus-private-test", "user-1", CHAT_ID),
            "user_content": "Current user text 中文", "attachment_id": None,
            "attachment_mode": "vision", "web_mode": "auto",
        }])


if __name__ == "__main__":
    unittest.main(verbosity=2)
