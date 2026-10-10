"""Feature-flagged Lab lifecycle with temporary evidence and mock HTTP only."""

import asyncio
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import AsyncMock, patch
import uuid

import httpx

from app import async_retain
from app import durable_jsonl as durable
from app import hindsight_shadow as shadow
from app import playground_api as api
from app.retain_ledger import RetainLedger
from app.retain_reconciliation import ReconciliationStatus
import memory.store as store


FLAG = "CORVUS_HINDSIGHT_ASYNC_RETAIN_ENABLED"
OPERATION = "b68777c5-6cae-4710-a879-0437145d7741"
SECOND = "12e0b399-409a-4975-be37-c0c9d8214559"
THIRD = "719994b0-a1b3-4da7-bb37-349a1fd60468"


class IntegrationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="corvus-async-integration-")
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.requests = []
        for patcher in (patch.object(shadow, "DATA_DIR", self.directory),
                        patch.object(shadow, "LAB_DATA_DIR", self.directory),
                        patch.object(store, "DB_PATH", self.directory / "corvus.db"),
                        patch.object(shadow, "HINDSIGHT_ASYNC_RETAIN_ENABLED", False),
                        patch.object(shadow.httpx, "AsyncHTTPTransport", return_value=httpx.MockTransport(self.handle))):
            patcher.start()
            self.addCleanup(patcher.stop)
        store.init_db()
        user = store.add_message("session", "user", "canonical user 雀")
        assistant = store.add_message("session", "assistant", "canonical answer")
        with store.connect() as conn:
            conn.execute("UPDATE messages SET created_at = '2026-10-07 10:00:00' WHERE id = ?", (user,))
            conn.execute("UPDATE messages SET created_at = '2026-10-07 10:00:02' WHERE id = ?", (assistant,))
        self.turn = shadow.ShadowTurn("session", user, assistant, "query", ())
        self.ledger = RetainLedger(self.directory / shadow.LOG_NAME)

    def handle(self, request):
        self.requests.append(request)
        if request.method == "GET":
            self.assertIn("/operations/", request.url.path)
            return httpx.Response(200, json={"operation_id": request.url.path.rsplit("/", 1)[1], "status": "pending"})
        self.assertEqual(request.method, "POST")
        if request.url.path.endswith("/memories/recall"):
            return httpx.Response(200, json={"results": []})
        self.assertEqual(request.url.path, f"/v1/default/banks/{shadow.BANK}/memories")
        body = json.loads(request.content)
        response = {"success": True, "async": body["async"], "bank_id": shadow.BANK, "items_count": 1}
        if body["async"]:
            response["operation_id"] = body["operation_id"]
        return httpx.Response(200, json=response)

    def records(self):
        return durable.read_jsonl(self.ledger.path)

    def outcome(self):
        return self.records()[-1]["retain"]

    async def enabled(self):
        with patch.object(shadow, "HINDSIGHT_ASYNC_RETAIN_ENABLED", True):
            await shadow.run_shadow_recall(self.turn)

    def runtime_result(self):
        return dict(session_id="session", user_message_id=self.turn.user_message_id,
                    assistant_message_id=self.turn.assistant_message_id, recent_message_ids=[],
                    historical_message_ids=[], input_tokens=100, retrieval_status="OK",
                    retrieval_error=None, model_status="OK", persistence_status="NORMAL",
                    dense_status="OK", reply="canonical answer", error=None)

    def intent(self, operation_id, recorded_at):
        return self.ledger.record_intent(operation_id=operation_id, user_message_id=self.turn.user_message_id,
                                         assistant_message_id=self.turn.assistant_message_id, session_id="session",
                                         bank=shadow.BANK, item=shadow._load_retain_item(self.turn), recorded_at=recorded_at)

    def test_configuration_default_false_and_explicit_true_false(self):
        with patch.dict(os.environ):
            os.environ.pop(FLAG, None)
            self.assertFalse(runpy.run_path("app/runtime_config.py")["HINDSIGHT_ASYNC_RETAIN_ENABLED"])
            for raw, expected in (("true", True), (" TRUE ", True), ("false", False), ("False", False)):
                os.environ[FLAG] = raw
                self.assertIs(runpy.run_path("app/runtime_config.py")["HINDSIGHT_ASYNC_RETAIN_ENABLED"], expected)
            os.environ[FLAG] = "invalid"
            with self.assertRaises(ValueError):
                runpy.run_path("app/runtime_config.py")

    async def test_flag_off_is_original_sync_contract_without_ledger_or_status_activity(self):
        with patch.object(async_retain, "submit_async_retain", new_callable=AsyncMock) as submit:
            await shadow.run_shadow_recall(self.turn)
            self.assertEqual(await shadow.reconcile_async_retain(), ())
        submit.assert_not_awaited()
        self.assertEqual(len(self.requests), 2)
        self.assertTrue(all(request.method == "POST" for request in self.requests))
        body = json.loads(self.requests[-1].content)
        self.assertEqual(body, {"items": [shadow._load_retain_item(self.turn)], "async": False})
        self.assertEqual(len(self.records()), 2)
        self.assertEqual(self.ledger.read(), {})
        self.assertEqual(self.outcome()["status"], "OK")
        self.assertNotIn("operation_id", self.outcome())

    async def test_enabled_ordering_fsync_before_submit_and_exact_provenance(self):
        events = []
        before = hashlib.sha256(store.DB_PATH.read_bytes()).hexdigest()
        real_fsync = durable.os.fsync

        def fsync(fd):
            real_fsync(fd)
            events.append("fsync")

        def handle(request):
            if request.url.path.endswith("/recall"):
                events.append("recall")
            else:
                self.assertEqual(events, ["recall", "fsync", "fsync", "fsync", "fsync"])
                records = self.records()
                self.assertNotIn("record_type", records[0])
                self.assertEqual(records[1]["event_type"], "RETAIN_INTENT")
                body = json.loads(request.content)
                self.assertEqual(body, {"items": [shadow._load_retain_item(self.turn)],
                                        "async": True, "operation_id": OPERATION})
                events.append("submit")
            return self.handle(request)

        with (patch.object(durable.os, "fsync", side_effect=fsync),
              patch.object(shadow.httpx, "AsyncHTTPTransport", return_value=httpx.MockTransport(handle)),
              patch.object(async_retain.uuid, "uuid4", return_value=uuid.UUID(OPERATION)) as generate):
            await self.enabled()
        generate.assert_called_once()
        self.assertEqual(events, ["recall", "fsync", "fsync", "fsync", "fsync", "submit",
                                  "fsync", "fsync", "fsync", "fsync"])
        self.assertEqual([record.get("event_type", record.get("record_type", "comparison"))
                          for record in self.records()],
                         ["comparison", "RETAIN_INTENT", "RETAIN_SUBMISSION_ACCEPTED", "retain_outcome"])
        outcome = self.outcome()
        self.assertEqual(outcome["status"], "ACCEPTED")
        self.assertEqual(outcome["mode"], "async_submission")
        self.assertEqual(outcome["operation_id"], OPERATION)
        self.assertTrue(outcome["outcome_durable"])
        self.assertEqual(self.ledger.read()[OPERATION].submission_state, "ACCEPTED")
        self.assertTrue(self.ledger.read()[OPERATION].unresolved)
        self.assertIsNone(self.ledger.read()[OPERATION].terminal_status)
        self.assertEqual(hashlib.sha256(store.DB_PATH.read_bytes()).hexdigest(), before)

    async def test_ambiguous_submission_records_stable_uuid_without_inline_retry_or_lookup(self):
        def handle(request):
            if request.url.path.endswith("/recall"):
                return self.handle(request)
            self.requests.append(request)
            raise httpx.ReadTimeout("private", request=request)

        with (patch.object(shadow.httpx, "AsyncHTTPTransport", return_value=httpx.MockTransport(handle)),
              patch.object(async_retain.uuid, "uuid4", return_value=uuid.UUID(OPERATION)) as generate,
              self.assertLogs(shadow.logger, level="WARNING")):
            await self.enabled()
        generate.assert_called_once()
        self.assertEqual(len(self.requests), 2)
        self.assertEqual(self.outcome()["status"], "AMBIGUOUS")
        self.assertEqual(self.outcome()["operation_id"], OPERATION)
        self.assertEqual(self.ledger.read()[OPERATION].submission_state, "AMBIGUOUS")
        self.assertTrue(self.ledger.read()[OPERATION].unresolved)
        self.assertNotIn("private", self.ledger.path.read_text())

    async def test_rejection_records_failure_without_replacement_uuid(self):
        def handle(request):
            if request.url.path.endswith("/recall"):
                return self.handle(request)
            self.requests.append(request)
            return httpx.Response(409, json={"detail": "private"})

        with (patch.object(shadow.httpx, "AsyncHTTPTransport", return_value=httpx.MockTransport(handle)),
              patch.object(async_retain.uuid, "uuid4", return_value=uuid.UUID(OPERATION)) as generate,
              self.assertLogs(shadow.logger, level="WARNING")):
            await self.enabled()
        generate.assert_called_once()
        self.assertEqual(len(self.requests), 2)
        self.assertEqual(self.outcome()["status"], "REJECTED")
        self.assertEqual(self.outcome()["http_status"], 409)
        self.assertEqual(list(self.ledger.read()), [OPERATION])
        self.assertEqual(self.ledger.read()[OPERATION].submission_state, "REJECTED")

    async def test_presend_failure_is_observable_and_never_retried(self):
        def handle(request):
            if request.url.path.endswith("/recall"):
                return self.handle(request)
            self.requests.append(request)
            raise httpx.ConnectError("private", request=request)

        with (patch.object(shadow.httpx, "AsyncHTTPTransport", return_value=httpx.MockTransport(handle)),
              self.assertLogs(shadow.logger, level="WARNING")):
            await self.enabled()
        self.assertEqual(self.outcome()["status"], "FAILED_TO_SUBMIT")
        state = next(iter(self.ledger.read().values()))
        self.assertEqual(state.submission_state, "FAILED_TO_SUBMIT")
        self.assertEqual(len(self.requests), 2)

    async def test_intent_fsync_failure_prevents_submission(self):
        real_fsync = durable.os.fsync
        calls = []

        def fsync(fd):
            calls.append(True)
            if len(calls) == 3:  # Comparison has already completed both fsyncs.
                raise OSError("private")
            return real_fsync(fd)

        with patch.object(durable.os, "fsync", side_effect=fsync), self.assertLogs(shadow.logger, level="WARNING"):
            await self.enabled()
        self.assertEqual(len(self.requests), 1)  # Recall only, never a retain POST.
        self.assertEqual(self.outcome()["status"], "INTENT_DURABILITY_FAILED")
        self.assertEqual(self.ledger.read(), {})
        self.assertNotIn("private", self.ledger.path.read_text())

    async def test_comparison_failure_prevents_intent_creation_and_submit(self):
        with (patch.object(shadow, "append_observation", side_effect=OSError("private")),
              patch.object(RetainLedger, "record_intent") as intent,
              patch.object(async_retain, "submit_async_retain", new_callable=AsyncMock) as submit,
              self.assertLogs(shadow.logger, level="WARNING")):
            await self.enabled()
        intent.assert_not_called()
        submit.assert_not_awaited()
        self.assertEqual(len(self.requests), 1)
        self.assertFalse(self.ledger.path.exists())

    async def test_comparison_fsync_failure_prevents_intent_and_submit(self):
        with (patch.object(durable.os, "fsync", side_effect=OSError("private")),
              patch.object(async_retain, "submit_async_retain", new_callable=AsyncMock) as submit,
              self.assertLogs(shadow.logger, level="WARNING")):
            await self.enabled()
        submit.assert_not_awaited()
        self.assertEqual(len(self.requests), 1)
        self.assertEqual(self.ledger.read(), {})

    async def test_outcome_durability_failure_does_not_change_accepted_into_completion(self):
        with (patch.object(RetainLedger, "record_submission_accepted", side_effect=OSError("private")),
              self.assertLogs(shadow.logger, level="WARNING") as logs):
            await self.enabled()
        self.assertEqual(self.outcome()["status"], "ACCEPTED")
        self.assertFalse(self.outcome()["outcome_durable"])
        self.assertEqual(self.outcome()["ledger_error"], "OSError")
        state = next(iter(self.ledger.read().values()))
        self.assertTrue(state.unresolved)
        self.assertEqual(state.submission_state, "NOT_ATTEMPTED")
        self.assertIn("completion not observed", " ".join(logs.output))
        self.assertNotIn("private", " ".join(logs.output))
        self.assertEqual(len(self.requests), 2)

    async def test_duplicate_ledger_events_remain_one_logical_operation(self):
        await self.enabled()
        state = next(iter(self.ledger.read().values()))
        intent = state.intent
        self.ledger.record_intent(operation_id=intent.operation_id, user_message_id=intent.user_message_id,
                                  assistant_message_id=intent.assistant_message_id, session_id=intent.session_id,
                                  bank=intent.bank, item=shadow._load_retain_item(self.turn))
        self.ledger.record_submission_accepted(intent.operation_id)
        self.assertEqual(len(self.ledger.read()), 1)
        self.assertTrue(self.ledger.read()[intent.operation_id].unresolved)
        self.assertEqual(len(self.requests), 2)

    async def test_disabled_reconciliation_has_no_ledger_or_http_side_effect(self):
        with patch.object(RetainLedger, "read", side_effect=AssertionError("must not read")):
            self.assertEqual(await shadow.reconcile_async_retain(transport=httpx.MockTransport(self.handle)), ())
        self.assertEqual(self.requests, [])
        self.assertFalse(self.ledger.path.exists())

    async def test_enabled_explicit_reconciliation_is_bounded_and_skips_terminal_work(self):
        self.intent(OPERATION, "2026-10-10T10:00:00Z")
        self.intent(SECOND, "2026-10-10T09:00:00Z")
        self.intent(THIRD, "2026-10-10T08:00:00Z")
        self.ledger.record_status(THIRD, "completed")
        with patch.object(shadow, "HINDSIGHT_ASYNC_RETAIN_ENABLED", True):
            results = await shadow.reconcile_async_retain(max_operations=1, transport=httpx.MockTransport(self.handle))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].operation_id, SECOND)
        self.assertEqual(results[0].status, ReconciliationStatus.PENDING)
        self.assertEqual(len(self.requests), 1)
        self.assertEqual(self.requests[0].method, "GET")
        self.assertFalse(self.ledger.read()[THIRD].unresolved)

    async def test_enabled_lifecycle_never_automatically_reconciles(self):
        with patch.object(shadow, "reconcile_async_retain", new_callable=AsyncMock) as reconcile:
            await self.enabled()
        reconcile.assert_not_awaited()
        self.assertTrue(all(request.method == "POST" for request in self.requests))

    async def test_explicit_reconciliation_observes_the_uuid_from_enabled_submission(self):
        await self.enabled()
        operation_id = next(iter(self.ledger.read()))
        self.assertTrue(self.ledger.read()[operation_id].unresolved)

        def completed(request):
            self.requests.append(request)
            self.assertEqual(request.method, "GET")
            self.assertTrue(request.url.path.endswith(operation_id))
            return httpx.Response(200, json={"operation_id": operation_id, "status": "completed"})

        with patch.object(shadow, "HINDSIGHT_ASYNC_RETAIN_ENABLED", True):
            results = await shadow.reconcile_async_retain(transport=httpx.MockTransport(completed))
        self.assertEqual([r.status for r in results], [ReconciliationStatus.COMPLETED])
        self.assertEqual(RetainLedger(self.ledger.path).read()[operation_id].terminal_status, "completed")
        self.assertEqual([request.method for request in self.requests], ["POST", "POST", "GET"])

    async def test_enabled_paths_cannot_use_non_lab_data(self):
        with (patch.object(shadow, "HINDSIGHT_ASYNC_RETAIN_ENABLED", True),
              patch.object(store, "DB_PATH", self.directory / "other.db")):
            await shadow.run_shadow_recall(self.turn)
            with self.assertRaises(ValueError):
                await shadow.reconcile_async_retain(transport=httpx.MockTransport(self.handle))
        self.assertEqual(self.outcome()["error"], "RETAIN_NOT_ELIGIBLE")
        self.assertEqual(self.ledger.read(), {})
        self.assertEqual(len(self.requests), 1)

    async def test_disabled_startup_does_not_contact_hindsight(self):
        with (patch.object(api, "start_foreground_publication"),
              patch.object(api, "stop_foreground_publication"),
              patch.object(api, "prepare_runtime_startup", return_value={"status": "NOT_RUN"}),
              patch.object(shadow, "reconcile_async_retain", new_callable=AsyncMock) as reconcile,
              patch.object(async_retain, "submit_async_retain", new_callable=AsyncMock) as submit):
            async with api.lifespan(api.app):
                pass
        reconcile.assert_not_awaited()
        submit.assert_not_awaited()
        self.assertEqual(self.requests, [])

    async def test_asgi_reply_is_sent_before_async_submission_and_no_completion_polling(self):
        body_sent, submit_started, release = asyncio.Event(), asyncio.Event(), asyncio.Event()
        sent = []

        async def handle(request):
            if request.url.path.endswith("/recall"):
                self.assertTrue(body_sent.is_set())
                return self.handle(request)
            self.assertEqual(request.method, "POST")
            self.assertTrue(body_sent.is_set())
            self.assertEqual(len(self.ledger.read()), 1)  # Intent already fsynced.
            submit_started.set()
            await release.wait()
            return self.handle(request)

        request_body = json.dumps({"session_id": "session", "message": "query", "web_mode": "off"}).encode()

        async def receive():
            return {"type": "http.request", "body": request_body, "more_body": False}

        async def send(message):
            sent.append(deepcopy(message))
            if message["type"] == "http.response.body":
                body_sent.set()

        scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
                 "method": "POST", "scheme": "http", "path": "/api/chat", "raw_path": b"/api/chat",
                 "query_string": b"", "root_path": "", "headers": [(b"content-type", b"application/json")],
                 "client": ("127.0.0.1", 1234), "server": ("127.0.0.1", 18096)}
        with (patch.object(shadow, "HINDSIGHT_ASYNC_RETAIN_ENABLED", True),
              patch.object(api, "process_turn", return_value=self.runtime_result()),
              patch.object(shadow.httpx, "AsyncHTTPTransport", return_value=httpx.MockTransport(handle))):
            task = asyncio.create_task(api.app(scope, receive, send))
            try:
                await asyncio.wait_for(submit_started.wait(), 5)
                self.assertTrue(body_sent.is_set())
                self.assertFalse(task.done())
                response = json.loads(next(item["body"] for item in sent if item["type"] == "http.response.body"))
                self.assertEqual(response["reply"], "canonical answer")
                self.assertEqual(response["user_message_id"], self.turn.user_message_id)
                self.assertEqual(response["assistant_message_id"], self.turn.assistant_message_id)
                self.assertNotIn("operation_id", response)
            finally:
                release.set()
                await asyncio.wait_for(task, 5)
        self.assertEqual(len(self.requests), 2)
        self.assertEqual(self.outcome()["status"], "ACCEPTED")
        self.assertTrue(next(iter(self.ledger.read().values())).unresolved)


if __name__ == "__main__":
    unittest.main()
