"""Offline retain contracts; canonical SQLite and JSONL live only in /tmp."""

import asyncio
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import BackgroundTasks
import httpx

import app.hindsight_shadow as shadow
import app.playground_api as api
import memory.store as store


def retain_response(**changes):
    return dict({"success": True, "bank_id": shadow.BANK, "items_count": 1, "async": False}, **changes)


class RetainTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="corvus-retain-")
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.requests = []
        for patcher in (
            patch.object(shadow, "DATA_DIR", self.directory),
            patch.object(shadow, "LAB_DATA_DIR", self.directory),
            patch.object(store, "DB_PATH", self.directory / "corvus.db"),
            patch.object(shadow.httpx, "AsyncHTTPTransport",
                         return_value=httpx.MockTransport(self.handle)),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        store.init_db()
        user = store.add_message("session", "user", "canonical user 雀")
        assistant = store.add_message("session", "assistant", "canonical answer")
        with store.connect() as conn:
            conn.execute("UPDATE messages SET created_at = '2026-10-07 10:00:00' WHERE id = ?", (user,))
            conn.execute("UPDATE messages SET created_at = '2026-10-07 10:00:02' WHERE id = ?", (assistant,))
        self.turn = shadow.ShadowTurn("session", user, assistant, "different query text", (99,))

    def handle(self, request):
        self.requests.append(request)
        # Fail closed for any unanticipated endpoint, including reflect.
        if request.url.path.endswith("/memories/recall"):
            return httpx.Response(200, json={"results": []})
        self.assertEqual(request.url.path, f"/v1/default/banks/{shadow.BANK}/memories")
        return httpx.Response(200, json=retain_response())

    def records(self):
        return [json.loads(line) for line in (self.directory / shadow.LOG_NAME).read_text().splitlines()]

    async def with_handler(self, handler):
        with patch.object(shadow.httpx, "AsyncHTTPTransport",
                          return_value=httpx.MockTransport(handler)) as factory:
            result = await shadow.retain_completed_turn(self.turn)
        factory.assert_called_once_with(retries=0)
        return result

    async def test_real_contract_canonical_content_identity_timestamp_and_read_only_history(self):
        before = hashlib.sha256(store.DB_PATH.read_bytes()).hexdigest()
        result = await shadow.retain_completed_turn(self.turn)
        self.assertEqual(result["status"], "OK")
        self.assertIsNone(result["error"])
        self.assertGreaterEqual(result["elapsed_ms"], 0)
        self.assertEqual(len(self.requests), 1)
        request = self.requests[0]
        self.assertEqual(request.method, "POST")
        self.assertEqual(str(request.url), f"{shadow.BASE_URL}/v1/default/banks/{shadow.BANK}/memories")
        self.assertEqual(json.loads(request.content), {
            "async": False,
            "items": [{
                "content": "User:\ncanonical user 雀\n\nAssistant:\ncanonical answer",
                "timestamp": "2026-10-07T10:00:02+00:00",
                "document_id": f"corvus-lab:turn:{self.turn.user_message_id}:{self.turn.assistant_message_id}",
                "metadata": {
                    "source": "corvus-lab", "session_id": "session",
                    "user_message_id": str(self.turn.user_message_id),
                    "assistant_message_id": str(self.turn.assistant_message_id),
                },
            }],
        })
        self.assertEqual(hashlib.sha256(store.DB_PATH.read_bytes()).hexdigest(), before)
        self.assertEqual(result["document_id"], json.loads(request.content)["items"][0]["document_id"])

    async def test_complete_flow_uses_only_recall_then_retain_without_reflect(self):
        await shadow.run_shadow_recall(self.turn)
        self.assertEqual([(request.method, request.url.path) for request in self.requests], [
            ("POST", f"/v1/default/banks/{shadow.BANK}/memories/recall"),
            ("POST", f"/v1/default/banks/{shadow.BANK}/memories"),
        ])
        self.assertEqual(self.records()[0]["hindsight"]["status"], "OK")
        self.assertEqual(self.records()[1]["retain"]["status"], "OK")

    async def test_terminal_recall_outcomes_and_durable_append_precede_retain(self):
        for status in ("OK", "TIMEOUT", "ERROR"):
            with self.subTest(status=status):
                events = []
                real_append = shadow.append_observation
                real_fsync = shadow.os.fsync

                async def recall(query):
                    events.append("recall-start")
                    await asyncio.sleep(0)
                    events.append("recall-complete")
                    return {"status": status, "results": [], "error": None, "elapsed_ms": 1}

                def fsync(fd):
                    events.append("fsync")
                    return real_fsync(fd)

                def append(record):
                    real_append(record)
                    events.append("outcome-appended" if record.get("record_type") else "comparison-appended")

                def handler(request):
                    self.assertEqual(events[:5], [
                        "recall-start", "recall-complete", "fsync", "fsync", "comparison-appended",
                    ])
                    self.assertEqual(self.records()[-1]["hindsight"]["status"], status)
                    events.append("retain")
                    return httpx.Response(200, json=retain_response())

                with (
                    patch.object(shadow, "recall", side_effect=recall),
                    patch.object(shadow, "append_observation", side_effect=append),
                    patch.object(shadow.os, "fsync", side_effect=fsync),
                    patch.object(shadow.httpx, "AsyncHTTPTransport", return_value=httpx.MockTransport(handler)),
                ):
                    await shadow.run_shadow_recall(self.turn)
                self.assertEqual(events[-4:], ["retain", "fsync", "fsync", "outcome-appended"])
                comparison, outcome = self.records()[-2:]
                self.assertEqual(comparison["retain"]["error"], "RETAIN_NOT_STARTED")
                self.assertEqual(outcome["retain"]["status"], "OK")
                self.assertGreaterEqual(outcome["retain"]["elapsed_ms"], 0)
                self.assertEqual(outcome["record_type"], "retain_outcome")
                self.assertNotIn("query", outcome)
                self.assertNotIn("hindsight", outcome)
                self.assertNotIn("canonical answer", json.dumps(outcome))

    async def test_comparison_append_or_durability_failure_never_calls_retain(self):
        for operation in ("append_observation", "fsync"):
            with self.subTest(operation=operation):
                target = shadow if operation == "append_observation" else shadow.os
                with (
                    patch.object(shadow, "recall", new=AsyncMock(return_value={"status": "OK", "results": []})),
                    patch.object(target, operation, side_effect=OSError("SECRET")),
                    patch.object(shadow, "retain_completed_turn", new_callable=AsyncMock) as retain,
                    self.assertLogs(shadow.logger, level="WARNING") as logs,
                ):
                    await shadow.run_shadow_recall(self.turn)
                retain.assert_not_awaited()
                self.assertIn("SKIPPED: COMPARISON_APPEND_FAILED", " ".join(logs.output))
                self.assertNotIn("SECRET", " ".join(logs.output))
        self.assertEqual(self.requests, [])

    async def test_partial_failed_append_rolls_back_and_incomplete_tail_blocks_retain(self):
        shadow.append_observation({"previous": True})
        before = (self.directory / shadow.LOG_NAME).read_bytes()
        real_write = shadow.os.write
        writes = []

        def failing_write(fd, data):
            writes.append(True)
            if len(writes) == 1:
                return real_write(fd, data[:10])
            raise OSError("SECRET")

        with (
            patch.object(shadow.os, "write", side_effect=failing_write),
            patch.object(shadow, "retain_completed_turn", new_callable=AsyncMock) as retain,
            self.assertLogs(shadow.logger, level="WARNING"),
        ):
            await shadow.run_shadow_recall(self.turn)
        retain.assert_not_awaited()
        self.assertEqual((self.directory / shadow.LOG_NAME).read_bytes(), before)
        shadow.append_observation({"next": True})
        self.assertEqual(self.records(), [{"previous": True}, {"next": True}])
        with (self.directory / shadow.LOG_NAME).open("ab") as log:
            log.write(b'{"incomplete":')
        with (
            patch.object(shadow, "retain_completed_turn", new_callable=AsyncMock) as retain,
            self.assertLogs(shadow.logger, level="WARNING") as logs,
        ):
            await shadow.run_shadow_recall(self.turn)
        retain.assert_not_awaited()
        self.assertIn("COMPARISON_APPEND_FAILED", " ".join(logs.output))
        self.assertTrue(all(request.url.path.endswith("/recall") for request in self.requests))

    async def test_total_deadline_cancels_one_request_without_retry(self):
        calls, cancelled = [], []

        async def handler(request):
            calls.append(request)
            try:
                await asyncio.sleep(60)
            finally:
                cancelled.append(True)

        self.assertEqual(shadow.RETAIN_DEADLINE_SECONDS, 390)
        self.assertEqual(shadow.DEADLINE_SECONDS, 10)
        with patch.object(shadow, "RETAIN_DEADLINE_SECONDS", 0.02):
            result = await self.with_handler(handler)
        self.assertEqual(result["status"], "TIMEOUT")
        self.assertEqual(result["error"], "DEADLINE_EXCEEDED_WRITE_COMPLETION_UNKNOWN")
        self.assertGreaterEqual(result["elapsed_ms"], 15)
        self.assertEqual(len(calls), 1)
        self.assertEqual(cancelled, [True])

    async def test_timeout_http_malformed_and_transport_failures_record_once_without_retry(self):
        cases = [
            ("timeout", "TIMEOUT", "DEADLINE_EXCEEDED_WRITE_COMPLETION_UNKNOWN"),
            ("transport", "ERROR", "TRANSPORT_ERROR"),
            ("json", "ERROR", "INVALID_RESPONSE"),
            (503, "ERROR", "HTTP_503"),
            (302, "ERROR", "HTTP_302"),
            ([], "ERROR", "INVALID_RESPONSE"),
            ({"success": False}, "ERROR", "INVALID_RESPONSE"),
            ({"bank_id": "other-bank"}, "ERROR", "INVALID_RESPONSE"),
            ({"async": True, "operation_id": "HINDSIGHT_ONLY"}, "ERROR", "INVALID_RESPONSE"),
            ({"items_count": True}, "ERROR", "INVALID_RESPONSE"),
            ({"items_count": 2}, "ERROR", "INVALID_RESPONSE"),
        ]
        for failure, status, error in cases:
            with self.subTest(failure=failure):
                calls = []

                def handler(request):
                    calls.append(request)
                    if failure == "timeout":
                        raise httpx.ReadTimeout("SECRET", request=request)
                    if failure == "transport":
                        raise httpx.ConnectError("SECRET", request=request)
                    if failure == "json":
                        return httpx.Response(200, content=b"SECRET invalid JSON")
                    if isinstance(failure, int):
                        return httpx.Response(failure, json={"detail": "SECRET"})
                    return httpx.Response(200, json=(dict(retain_response(), **failure)
                                                    if isinstance(failure, dict) else failure))

                with (
                    patch.object(shadow, "recall", new=AsyncMock(return_value={"status": "OK", "results": []})),
                    patch.object(shadow.httpx, "AsyncHTTPTransport", return_value=httpx.MockTransport(handler)),
                ):
                    await shadow.run_shadow_recall(self.turn)
                outcome = self.records()[-1]["retain"]
                self.assertEqual((outcome["status"], outcome["error"]), (status, error))
                self.assertGreaterEqual(outcome["elapsed_ms"], 0)
                self.assertEqual(len(calls), 1)
                self.assertNotIn("SECRET", json.dumps(outcome))
                self.assertNotIn("HINDSIGHT_ONLY", json.dumps(outcome))

    async def test_missing_or_inconsistent_canonical_data_skips_safely(self):
        changes = [
            ("DELETE FROM messages WHERE role='assistant'", ()),
            ("UPDATE messages SET session_id='other' WHERE role='assistant'", ()),
            ("UPDATE messages SET role='user' WHERE role='assistant'", ()),
            ("UPDATE messages SET content=' ' WHERE role='assistant'", ()),
            ("UPDATE messages SET created_at='invalid' WHERE role='user'", ()),
        ]
        for sql, args in changes:
            with self.subTest(sql=sql):
                with store.connect() as conn:
                    conn.execute(sql, args)
                    conn.commit()
                # Restore the entire isolated fixture after each case.
                with patch.object(shadow, "recall", new=AsyncMock(return_value={"status": "OK", "results": []})):
                    await shadow.run_shadow_recall(self.turn)
                outcome = self.records()[-1]["retain"]
                self.assertEqual((outcome["status"], outcome["error"]),
                                 ("SKIPPED", "MISSING_CANONICAL_TURN_DATA"))
                with store.connect() as conn:
                    conn.execute("DELETE FROM messages")
                    conn.executemany("INSERT INTO messages (id, session_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)", [
                        (self.turn.user_message_id, "session", "user", "canonical user 雀", "2026-10-07 10:00:00"),
                        (self.turn.assistant_message_id, "session", "assistant", "canonical answer", "2026-10-07 10:00:02"),
                    ])
        self.assertEqual(self.requests, [])

    async def test_absent_database_is_not_created_and_ineligible_retain_does_no_http(self):
        missing = self.directory / "missing" / "corvus.db"
        with (
            patch.object(shadow, "DATA_DIR", missing.parent),
            patch.object(shadow, "LAB_DATA_DIR", missing.parent),
            patch.object(store, "DB_PATH", missing),
        ):
            result = await shadow.retain_completed_turn(self.turn)
        self.assertEqual(result["error"], "MISSING_CANONICAL_TURN_DATA")
        self.assertFalse(missing.parent.exists())
        for patcher in (
            patch.object(shadow, "PROJECT_ROOT", Path("/production")),
            patch.object(store, "DB_PATH", self.directory / "other.db"),
        ):
            with patcher:
                result = await shadow.retain_completed_turn(self.turn)
            self.assertEqual((result["status"], result["error"]), ("SKIPPED", "RETAIN_NOT_ELIGIBLE"))
        self.assertEqual(self.requests, [])

    async def test_post_retain_logging_failure_and_unexpected_retain_failure_are_isolated(self):
        real_append = shadow.append_observation

        def append(record):
            if record.get("record_type") == "retain_outcome":
                raise OSError("SECRET")
            real_append(record)

        with (
            patch.object(shadow, "recall", new=AsyncMock(return_value={"status": "OK", "results": []})),
            patch.object(shadow, "append_observation", side_effect=append),
            self.assertLogs(shadow.logger, level="WARNING") as logs,
        ):
            await shadow.run_shadow_recall(self.turn)
        self.assertEqual(len(self.requests), 1)
        self.assertEqual(len(self.records()), 1)
        self.assertIn("status=OK", " ".join(logs.output))
        self.assertNotIn("SECRET", " ".join(logs.output))
        with (
            patch.object(shadow, "recall", new=AsyncMock(side_effect=RuntimeError("SECRET"))),
            patch.object(shadow, "retain_completed_turn", new=AsyncMock(side_effect=RuntimeError("SECRET"))),
        ):
            await shadow.run_shadow_recall(self.turn)
        self.assertEqual(self.records()[-2]["hindsight"]["status"], "ERROR")
        self.assertEqual(self.records()[-1]["retain"]["error"], "UNEXPECTED_ERROR")

    async def test_reply_and_canonical_ids_are_independent_of_every_retain_outcome(self):
        for status in ("OK", "TIMEOUT", "ERROR", "SKIPPED"):
            with self.subTest(status=status):
                runtime = {
                    "session_id": "session", "user_message_id": self.turn.user_message_id,
                    "assistant_message_id": self.turn.assistant_message_id, "recent_message_ids": [],
                    "historical_message_ids": [], "input_tokens": 100, "retrieval_status": "OK",
                    "retrieval_error": None, "model_status": "OK", "persistence_status": "NORMAL",
                    "dense_status": "OK", "reply": "canonical answer", "error": None,
                }
                tasks = BackgroundTasks()
                with patch.object(api, "process_turn", return_value=runtime):
                    response = api.post_chat(api.ChatRequest(session_id="session", message="query"), tasks)
                before = deepcopy(response)
                self.assertEqual(len(tasks.tasks), 1)
                with patch.object(shadow, "retain_completed_turn", new=AsyncMock(return_value={
                    "status": status, "elapsed_ms": 1, "document_id": "HINDSIGHT_ONLY", "error": None,
                })):
                    await tasks()
                self.assertEqual(response, before)
                self.assertNotIn("HINDSIGHT_ONLY", json.dumps(response))
                self.assertEqual([row["id"] for row in store.load_recent_messages("session")],
                                 [self.turn.user_message_id, self.turn.assistant_message_id])


if __name__ == "__main__":
    unittest.main()
