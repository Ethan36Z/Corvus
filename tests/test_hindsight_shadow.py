"""Shadow recall contracts: no live services, isolated canonical/derived files."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import FrozenInstanceError
from functools import partial
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import BackgroundTasks
import httpx

from app.conversation_runtime import process_turn
import app.hindsight_shadow as shadow
import app.playground_api as api
import memory.historical_memory as historical
import memory.store as store


def result():
    return {
        "session_id": "test-session", "user_message_id": 10,
        "assistant_message_id": 11, "recent_message_ids": [],
        "historical_message_ids": [1], "input_tokens": 100,
        "retrieval_status": "OK", "retrieval_error": None,
        "model_status": "OK", "persistence_status": "NORMAL",
        "dense_status": "OK", "reply": "normal answer", "error": None,
    }


def memory(source_id="provider-only-id", text="SHADOW_ONLY_TEXT", score=1.1):
    return {
        "id": source_id, "text": text, "type": "observation",
        "document_id": None, "chunk_id": None, "metadata": {},
        "tags": [], "scores": {"final": score, "reranker": 0.9},
    }


class ClientTests(unittest.IsolatedAsyncioTestCase):
    async def call_with_transport(self, handler):
        transport = httpx.MockTransport(handler)
        with patch.object(shadow.httpx, "AsyncHTTPTransport", return_value=transport) as factory:
            response = await shadow.recall("exact query")
        factory.assert_called_once_with(retries=0)
        return response

    async def test_real_contract_and_ordered_provider_id_normalization(self):
        requests = []

        def handler(request):
            requests.append(request)
            return httpx.Response(200, json={"results": [
                memory("00123", "first", 1.1), memory("uuid-second", "second", 0.2),
            ], "trace": None})

        observation = await self.call_with_transport(handler)
        self.assertEqual(len(requests), 1)
        request = requests[0]
        self.assertEqual(request.method, "POST")
        self.assertEqual(str(request.url), (
            "http://127.0.0.1:8888/v1/default/banks/corvus-hindsight-lab-v1/memories/recall"
        ))
        self.assertEqual(json.loads(request.content), {
            "query": "exact query", "budget": "mid", "max_tokens": 4096,
            "trace": False, "include": {"entities": None, "chunks": None, "source_facts": None},
        })
        self.assertEqual(observation["status"], "OK")
        self.assertIsNone(observation["error"])
        self.assertGreaterEqual(observation["elapsed_ms"], 0)
        rows = observation["results"]
        self.assertEqual([row["source_id"] for row in rows], ["00123", "uuid-second"])
        self.assertEqual([row["rank"] for row in rows], [1, 2])
        self.assertEqual([row["text"] for row in rows], ["first", "second"])
        self.assertEqual(rows[0]["score"], 1.1)
        self.assertEqual(rows[0]["metadata"]["scores"]["reranker"], 0.9)
        self.assertNotIn("id", rows[0])

    async def test_total_deadline_cancels_one_request_without_retry(self):
        calls = []
        cancelled = []

        async def handler(request):
            calls.append(request)
            try:
                await asyncio.sleep(60)
            finally:
                cancelled.append(True)

        self.assertEqual(shadow.DEADLINE_SECONDS, 10)
        with patch.object(shadow, "DEADLINE_SECONDS", 0.02):
            observation = await self.call_with_transport(handler)
        self.assertEqual(observation["status"], "TIMEOUT")
        self.assertEqual(observation["error"], "DEADLINE_EXCEEDED")
        self.assertEqual(len(calls), 1)
        self.assertEqual(cancelled, [True])
        self.assertGreaterEqual(observation["elapsed_ms"], 15)
        self.assertEqual(observation["results"], [])

    async def test_http_transport_timeout_is_sanitized_without_retry(self):
        calls = []

        def handler(request):
            calls.append(request)
            raise httpx.ReadTimeout("secret transport details", request=request)

        observation = await self.call_with_transport(handler)
        self.assertEqual(observation["status"], "TIMEOUT")
        self.assertNotIn("secret", json.dumps(observation))
        self.assertEqual(len(calls), 1)

    async def test_http_and_malformed_failures_are_errors_without_retry(self):
        cases = [
            (503, {"detail": "SECRET"}),
            (302, {"detail": "SECRET"}),
            (200, {"results": "not a list"}),
            (200, {"results": [{"id": 123, "text": "bad id"}]}),
            (200, {"results": [{"id": "uuid", "text": 123}]}),
            (200, {"results": [memory(score=True)]}),
            (200, {"results": [memory(score=float("inf"))]}),
        ]
        for status, body in cases:
            with self.subTest(status=status, body=body):
                calls = []

                def handler(request):
                    calls.append(request)
                    if status == 200 and body["results"] == [memory(score=float("inf"))]:
                        return httpx.Response(200, content=json.dumps(body))
                    return httpx.Response(status, json=body)

                observation = await self.call_with_transport(handler)
                self.assertEqual(observation["status"], "ERROR")
                self.assertEqual(observation["results"], [])
                self.assertNotIn("SECRET", json.dumps(observation))
                self.assertEqual(len(calls), 1)

    async def test_invalid_json_and_transport_failure_are_sanitized(self):
        for failure in (False, True):
            with self.subTest(transport_failure=failure):
                calls = []

                def handler(request):
                    calls.append(request)
                    if failure:
                        raise httpx.ConnectError("SECRET", request=request)
                    return httpx.Response(200, content=b"SECRET invalid JSON")

                observation = await self.call_with_transport(handler)
                self.assertEqual(observation["status"], "ERROR")
                self.assertNotIn("SECRET", json.dumps(observation))
                self.assertEqual(len(calls), 1)

    async def test_empty_results_without_scores_are_valid(self):
        for rows in ([], [{"id": "uuid", "text": "fact"}]):
            with self.subTest(rows=rows):
                observation = await self.call_with_transport(
                    lambda request: httpx.Response(200, json={"results": rows})
                )
                self.assertEqual(observation["status"], "OK")
                if rows:
                    self.assertIsNone(observation["results"][0]["score"])


class LabFixture(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="corvus-shadow-")
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        for patcher in (
            patch.object(shadow, "DATA_DIR", self.directory),
            patch.object(shadow, "LAB_DATA_DIR", self.directory),
            patch.object(store, "DB_PATH", self.directory / "corvus.db"),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        store.init_db()
        store.add_message("old-session", "user", "CANONICAL_HIST")

    def observations(self):
        return [json.loads(line) for line in (self.directory / shadow.LOG_NAME).read_text().splitlines()]


class SchedulingTests(LabFixture):
    def post(self, runtime_result, **request_fields):
        tasks = BackgroundTasks()
        with patch.object(api, "process_turn", return_value=runtime_result):
            response = api.post_chat(api.ChatRequest(
                session_id="test-session", message=" query ", web_mode="off", **request_fields,
            ), tasks)
        return response, tasks

    def test_confirmed_reply_schedules_one_immutable_snapshot_without_running_it(self):
        runtime_result = result()
        with patch.object(shadow, "recall", new_callable=AsyncMock) as recall:
            response, tasks = self.post(runtime_result)
        recall.assert_not_awaited()
        self.assertEqual(len(tasks.tasks), 1)
        self.assertIs(tasks.tasks[0].func, shadow.run_shadow_recall)
        turn = tasks.tasks[0].args[0]
        self.assertEqual(turn, shadow.ShadowTurn("test-session", 10, 11, "query", (1,)))
        response["historical_message_ids"].append(99)
        self.assertEqual(turn.historical_message_ids, (1,))
        with self.assertRaises(FrozenInstanceError):
            turn.query = "changed"

    def test_failed_uncertain_or_unsupported_turns_do_not_schedule(self):
        for changes in (
            {"assistant_message_id": None},
            {"user_message_id": None},
            {"persistence_status": "ASSISTANT_PERSISTENCE_FAILED"},
            {"persistence_status": "WEB_EVIDENCE_PERSISTENCE_DEGRADED"},
            {"model_status": "MODEL_TIMEOUT"},
            {"reply": ""},
            {"reply": None},
        ):
            with self.subTest(changes=changes):
                _, tasks = self.post(dict(result(), **changes))
                self.assertEqual(tasks.tasks, [])
        for request_fields in ({"attachment_id": "image"}, {"attachment_mode": "voice", "attachment_id": "audio"}):
            _, tasks = self.post(result(), **request_fields)
            self.assertEqual(tasks.tasks, [])
        tasks = BackgroundTasks()
        response = api.build_chat_response(result())
        shadow.schedule_shadow_recall(tasks, response, " ")
        self.assertEqual(tasks.tasks, [])
        for fields in ({"message": ""}, {"attachment_mode": "unsupported"}, {"web_mode": "unsupported"}):
            tasks = BackgroundTasks()
            with patch.object(api, "process_turn") as runtime:
                response = api.post_chat(api.ChatRequest(session_id="test", **fields), tasks)
            self.assertEqual(response.status_code, 400)
            runtime.assert_not_called()
            self.assertEqual(tasks.tasks, [])
        tasks = BackgroundTasks()
        with patch.object(api, "process_turn", side_effect=RuntimeError("failure")):
            response = api.post_chat(api.ChatRequest(message="query"), tasks)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(tasks.tasks, [])

    def test_confirmed_degraded_reply_is_eligible(self):
        _, tasks = self.post(dict(result(), dense_status="DEGRADED"))
        self.assertEqual(len(tasks.tasks), 1)

    def test_disabled_outside_lab_and_scheduling_exception_cannot_change_reply(self):
        with patch.object(shadow, "PROJECT_ROOT", Path("/tmp/other-checkout")):
            response, tasks = self.post(result())
        self.assertEqual(tasks.tasks, [])
        self.assertEqual(response["reply"], "normal answer")
        with patch.object(shadow, "DATA_DIR", self.directory / "other-data"):
            _, tasks = self.post(result())
        self.assertEqual(tasks.tasks, [])
        expected = api.build_chat_response(result())
        tasks = BackgroundTasks()
        with patch.object(tasks, "add_task", side_effect=RuntimeError("SECRET")):
            with self.assertLogs(shadow.logger, level="WARNING") as logs:
                shadow.schedule_shadow_recall(tasks, expected, "query")
        self.assertNotIn("SECRET", " ".join(logs.output))
        self.assertEqual(expected, api.build_chat_response(result()))

    def test_background_errors_and_log_failure_are_contained(self):
        expected = api.build_chat_response(result())
        for log_fails in (False, True):
            with self.subTest(log_fails=log_fails):
                response, tasks = self.post(result())
                with patch.object(shadow, "recall", new=AsyncMock(side_effect=RuntimeError("SECRET"))):
                    if log_fails:
                        with patch.object(shadow, "append_observation", side_effect=OSError("SECRET")):
                            with self.assertLogs(shadow.logger, level="WARNING") as logs:
                                asyncio.run(tasks())
                        self.assertNotIn("SECRET", " ".join(logs.output))
                    else:
                        asyncio.run(tasks())
                self.assertEqual(response, expected)
        record = self.observations()[0]
        self.assertEqual(record["schema_version"], 1)
        self.assertTrue(record["recorded_at"].endswith("+00:00"))
        self.assertEqual((record["session_id"], record["user_message_id"], record["assistant_message_id"]),
                         ("test-session", 10, 11))
        self.assertEqual(record["query"], "query")
        self.assertEqual(record["corvus"], {"historical_message_ids": [1]})
        self.assertEqual(record["hindsight"]["status"], "ERROR")
        self.assertEqual(record["hindsight"]["error"], "UNEXPECTED_ERROR")
        self.assertNotIn("SECRET", json.dumps(record))
        self.assertEqual(len(store.load_recent_messages("old-session")), 1)

    def test_asgi_sends_normal_body_before_shadow_and_keeps_model_canonical(self):
        async def exercise():
            sent = []
            body_sent = asyncio.Event()
            http_started = asyncio.Event()
            release_http = asyncio.Event()
            retain_started = asyncio.Event()
            release_retain = asyncio.Event()
            model_messages = []
            old_row = store.load_recent_messages("old-session")[0]

            def generate(messages):
                model_messages.extend(deepcopy(messages))
                return "normal answer"

            async def handler(request):
                self.assertTrue(body_sent.is_set())
                if request.url.path == f"/v1/default/banks/{shadow.BANK}/memories":
                    self.assertEqual(len(self.observations()), 1)
                    self.assertEqual(self.observations()[0]["hindsight"]["status"], "OK")
                    retain_started.set()
                    await release_retain.wait()
                    return httpx.Response(200, json={
                        "success": True, "bank_id": shadow.BANK, "items_count": 1,
                        "async": False, "operation_id": "HINDSIGHT_ONLY_ID",
                    })
                self.assertEqual(request.url.path, f"/v1/default/banks/{shadow.BANK}/memories/recall")
                http_started.set()
                await release_http.wait()
                return httpx.Response(200, json={"results": [memory()]})

            request_body = json.dumps({"session_id": "asgi-session", "message": "query", "web_mode": "off"}).encode()
            received = False

            async def receive():
                nonlocal received
                if not received:
                    received = True
                    return {"type": "http.request", "body": request_body, "more_body": False}
                await asyncio.Future()

            async def send(message):
                sent.append(deepcopy(message))
                if message["type"] == "http.response.body":
                    body_sent.set()

            scope = {
                "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
                "method": "POST", "scheme": "http", "path": "/api/chat",
                "raw_path": b"/api/chat", "query_string": b"", "root_path": "",
                "headers": [(b"content-type", b"application/json")],
                "client": ("127.0.0.1", 1234), "server": ("127.0.0.1", 18096),
            }
            runtime = partial(
                process_turn, count_tokens_fn=lambda messages: sum(len(item["content"]) for item in messages),
                generate_fn=generate, dense_sync_fn=lambda ids: None, system_prompt_fn=lambda: "SYS",
            )
            with (
                patch.object(api, "process_turn", runtime),
                patch.object(historical, "hybrid_search", return_value=[old_row]) as active,
                patch.object(shadow.httpx, "AsyncHTTPTransport", return_value=httpx.MockTransport(handler)),
            ):
                task = asyncio.create_task(api.app(scope, receive, send))
                try:
                    await asyncio.wait_for(body_sent.wait(), 2)
                    await asyncio.wait_for(http_started.wait(), 2)
                    self.assertFalse(task.done())  # Shadow remains blocked; response is already sent.
                    response = json.loads(next(item["body"] for item in sent if item["type"] == "http.response.body"))
                    self.assertEqual(sent[0]["status"], 200)
                    self.assertEqual(response["reply"], "normal answer")
                    self.assertEqual(response["status"]["overall"], "OK")
                    self.assertEqual(response["status"]["persistence"], "NORMAL")
                    self.assertEqual(response["historical_message_ids"], [old_row["id"]])
                    self.assertEqual(response["retrieved_memories"][0]["content"], "CANONICAL_HIST")
                    self.assertNotIn("SHADOW_ONLY_TEXT", json.dumps(model_messages))
                    self.assertNotIn("provider-only-id", json.dumps(response))
                    self.assertIn("CANONICAL_HIST", model_messages[0]["content"])
                    active.assert_called_once()
                    self.assertFalse((self.directory / shadow.LOG_NAME).exists())
                    # The event loop can progress while the HTTP operation is suspended.
                    await asyncio.sleep(0)
                    release_http.set()
                    await asyncio.wait_for(retain_started.wait(), 2)
                    self.assertFalse(task.done())  # Retain is blocked after the reply and comparison.
                    self.assertEqual(response["reply"], "normal answer")
                    self.assertNotIn("HINDSIGHT_ONLY_ID", json.dumps(model_messages))
                    self.assertNotIn("HINDSIGHT_ONLY_ID", json.dumps(response))
                finally:
                    release_http.set()
                    release_retain.set()
                    await asyncio.wait_for(task, 2)
            record = self.observations()[0]
            self.assertEqual(record["hindsight"]["status"], "OK")
            self.assertEqual(record["hindsight"]["results"][0]["source_id"], "provider-only-id")
            self.assertEqual(record["hindsight"]["results"][0]["text"], "SHADOW_ONLY_TEXT")
            self.assertEqual(record["corvus"]["historical_message_ids"], response["historical_message_ids"])
            self.assertEqual(record["user_message_id"], response["user_message_id"])
            self.assertEqual(record["assistant_message_id"], response["assistant_message_id"])
            rows = store.load_recent_messages("asgi-session")
            self.assertEqual([(row["role"], row["content"]) for row in rows],
                             [("user", "query"), ("assistant", "normal answer")])
            self.assertEqual(len(self.observations()), 2)
            self.assertEqual(self.observations()[1]["record_type"], "retain_outcome")
            self.assertEqual(self.observations()[1]["retain"]["status"], "OK")

        asyncio.run(exercise())


class AppendTests(LabFixture):
    def test_concurrent_partial_appends_remain_complete_jsonl_records(self):
        real_write = shadow.os.write

        def partial_write(fd, data):
            time.sleep(0.0001)
            return real_write(fd, data[:31])

        records = [{"index": index, "text": "Unicode 雀\n" * 120} for index in range(12)]
        with patch.object(shadow.os, "write", side_effect=partial_write):
            with ThreadPoolExecutor(max_workers=4) as pool:
                list(pool.map(shadow.append_observation, records))
        written = self.observations()
        self.assertEqual(sorted(written, key=lambda row: row["index"]), records)
        self.assertEqual((self.directory / shadow.LOG_NAME).stat().st_mode & 0o777, 0o600)

    def test_append_refuses_non_lab_directory_and_symlink_destination(self):
        with patch.object(shadow, "DATA_DIR", self.directory / "other"):
            with self.assertRaises(ValueError):
                shadow.append_observation({"test": True})
        outside = self.directory / "untouched.jsonl"
        outside.write_text("unchanged")
        (self.directory / shadow.LOG_NAME).symlink_to(outside)
        with self.assertRaises(OSError):
            shadow.append_observation({"test": True})
        self.assertEqual(outside.read_text(), "unchanged")


if __name__ == "__main__":
    unittest.main()
