"""Async submission contracts using temporary SQLite/JSONL and mock HTTP only."""

import asyncio
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
import uuid

import httpx

from app import async_retain as submission
from app import durable_jsonl as durable
from app import hindsight_shadow as shadow
from app.retain_ledger import LedgerError, RetainLedger, payload_fingerprint
import memory.store as store


OPERATION = "b68777c5-6cae-4710-a879-0437145d7741"
S = submission.SubmissionStatus


def acknowledgement(request, **changes):
    return dict(success=True, **{"async": True}, bank_id=shadow.BANK, items_count=1,
                operation_id=json.loads(request.content)["operation_id"]) | changes


class AsyncSubmissionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="corvus-async-retain-")
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        for patcher in (patch.object(store, "DB_PATH", self.directory / "corvus.db"),
                        patch.object(shadow, "DATA_DIR", self.directory),
                        patch.object(shadow, "LAB_DATA_DIR", self.directory)):
            patcher.start()
            self.addCleanup(patcher.stop)
        store.init_db()
        user = store.add_message("session", "user", "canonical user 雀")
        assistant = store.add_message("session", "assistant", "canonical answer")
        with store.connect() as conn:
            conn.execute("UPDATE messages SET created_at = '2026-10-07 10:00:00' WHERE id = ?", (user,))
            conn.execute("UPDATE messages SET created_at = '2026-10-07 10:00:02' WHERE id = ?", (assistant,))
        self.turn = shadow.ShadowTurn("session", user, assistant, "not retain content", (99,))
        self.path = self.directory / shadow.LOG_NAME
        self.ledger = RetainLedger(self.path)
        self.requests = []

    def handle(self, request):
        self.requests.append(request)
        self.assertEqual(request.method, "POST")
        self.assertEqual(str(request.url), f"{shadow.BASE_URL}/v1/default/banks/{shadow.BANK}/memories")
        return httpx.Response(200, json=acknowledgement(request))

    async def submit(self, handler=None, **kwargs):
        return await submission.submit_async_retain(
            self.turn, self.ledger, operation_id=OPERATION,
            transport=httpx.MockTransport(handler or self.handle), **kwargs,
        )

    async def replay(self, handler=None, **kwargs):
        return await submission.replay_async_retain(
            OPERATION, self.ledger, transport=httpx.MockTransport(handler or self.handle), **kwargs,
        )

    def state(self):
        return RetainLedger(self.path).read()[OPERATION]

    def record_intent(self):
        return self.ledger.record_intent(
            operation_id=OPERATION, user_message_id=self.turn.user_message_id,
            assistant_message_id=self.turn.assistant_message_id, session_id=self.turn.session_id,
            bank=shadow.BANK, item=shadow._load_retain_item(self.turn),
        )

    async def test_intent_file_and_directory_fsync_precede_http_and_acceptance_is_not_completion(self):
        events = []
        real_fsync = durable.os.fsync

        def fsync(fd):
            real_fsync(fd)
            events.append("fsync")

        def handle(request):
            self.assertEqual(events, ["fsync", "fsync"])
            state = self.state()
            self.assertEqual(state.submission_state, "NOT_ATTEMPTED")
            self.assertEqual(state.intent.payload_fingerprint,
                             payload_fingerprint(shadow.BANK, json.loads(request.content)["items"][0]))
            events.append("POST")
            return self.handle(request)

        with patch.object(durable.os, "fsync", side_effect=fsync):
            result = await self.submit(handle)
        self.assertEqual(events, ["fsync", "fsync", "POST", "fsync", "fsync"])
        self.assertEqual(result.status, S.ACCEPTED)
        self.assertTrue(result.outcome_durable)
        self.assertEqual(result.operation_id, OPERATION)
        self.assertEqual(self.state().submission_state, "ACCEPTED")
        self.assertTrue(self.state().unresolved)
        self.assertIsNone(self.state().last_hindsight_status)
        self.assertIsNone(self.state().terminal_status)

    async def test_intent_append_and_fsync_failure_prevent_http(self):
        for target, name in ((self.ledger, "record_intent"), (durable.os, "fsync")):
            with self.subTest(name=name), patch.object(target, name, side_effect=OSError("private")):
                result = await self.submit()
            self.assertEqual(result.status, S.INTENT_DURABILITY_FAILED)
            self.assertEqual(result.operation_id, OPERATION)
            self.assertEqual(self.requests, [])
            self.assertNotIn("private", repr(result))

    async def test_request_item_is_identical_to_sync_contract_and_sqlite_is_unchanged(self):
        before = hashlib.sha256(store.DB_PATH.read_bytes()).hexdigest()
        sync_requests = []

        def sync_handler(request):
            sync_requests.append(request)
            return httpx.Response(200, json={"success": True, "async": False,
                                            "bank_id": shadow.BANK, "items_count": 1})

        with patch.object(shadow.httpx, "AsyncHTTPTransport", return_value=httpx.MockTransport(sync_handler)):
            sync_result = await shadow.retain_completed_turn(self.turn)
        self.assertEqual(sync_result["status"], "OK")
        self.assertFalse(self.path.exists())  # Sync helper does not create a ledger intent.
        self.assertEqual((await self.submit()).status, S.ACCEPTED)
        old = json.loads(sync_requests[0].content)
        new = json.loads(self.requests[0].content)
        self.assertIs(old["async"], False)
        self.assertEqual(new, {"items": old["items"], "async": True, "operation_id": OPERATION})
        item = new["items"][0]
        self.assertEqual(item["document_id"], f"corvus-lab:turn:{self.turn.user_message_id}:{self.turn.assistant_message_id}")
        self.assertEqual(item["content"], "User:\ncanonical user 雀\n\nAssistant:\ncanonical answer")
        self.assertEqual(item["timestamp"], "2026-10-07T10:00:02+00:00")
        self.assertNotIn("context", item)
        self.assertEqual(hashlib.sha256(store.DB_PATH.read_bytes()).hexdigest(), before)

    async def test_invalid_ack_is_rejected_but_remote_acceptance_remains_ambiguous(self):
        cases = [dict(operation_id=str(uuid.uuid4())), dict(operation_id="invalid"),
                 dict(bank_id="other"), {"async": False}, dict(success=False),
                 dict(items_count=True), dict(items_count=2), dict(operation_ids=[str(uuid.uuid4())]),
                 "invalid-json", "not-an-object"]
        for index, changes in enumerate(cases):
            self.ledger = RetainLedger(self.directory / f"invalid-{index}.jsonl")

            def handle(request):
                self.requests.append(request)
                if changes == "invalid-json":
                    return httpx.Response(200, content=b"not-json-private")
                if changes == "not-an-object":
                    return httpx.Response(200, json=[])
                return httpx.Response(200, json=acknowledgement(request, **changes))

            with self.subTest(changes=changes):
                result = await self.submit(handle)
                self.assertEqual(result.status, S.REJECTED)
                self.assertTrue(result.acceptance_unknown)
                self.assertTrue(result.outcome_durable)
                state = self.ledger.read()[OPERATION]
                self.assertEqual(state.submission_state, "AMBIGUOUS")
                self.assertTrue(state.unresolved)
        self.assertEqual(len(self.requests), len(cases))

    async def test_definitive_api_rejection_records_http_error_not_retain_failure(self):
        for code in (401, 409, 422):
            self.ledger = RetainLedger(self.directory / f"rejected-{code}.jsonl")

            def handle(request):
                self.requests.append(request)
                return httpx.Response(code, json={"detail": "private response"})

            result = await self.submit(handle)
            self.assertEqual(result.status, S.REJECTED)
            self.assertFalse(result.acceptance_unknown)
            self.assertEqual(result.http_status, code)
            state = RetainLedger(self.ledger.path).read()[OPERATION]
            self.assertEqual((state.submission_state, state.http_status, state.error),
                             ("REJECTED", code, f"HTTP_{code}"))
            self.assertTrue(state.unresolved)
            self.assertIsNone(state.terminal_status)
            self.assertNotIn("private response", self.ledger.path.read_text())
        self.assertEqual(len(self.requests), 3)

    async def test_server_failure_timeout_and_redirect_are_ambiguous_without_retry(self):
        for code in (408, 500, 503, 302):
            self.ledger = RetainLedger(self.directory / f"unknown-{code}.jsonl")

            def handle(request):
                self.requests.append(request)
                return httpx.Response(code, headers={"location": "http://other.test"})

            result = await self.submit(handle)
            self.assertEqual(result.status, S.AMBIGUOUS)
            self.assertTrue(result.acceptance_unknown)
            self.assertEqual(self.ledger.read()[OPERATION].submission_state, "AMBIGUOUS")
        self.assertEqual(len(self.requests), 4)

    async def test_transport_timeout_and_connection_loss_keep_stable_identity(self):
        for exception in (httpx.ReadTimeout, httpx.ReadError, httpx.WriteError):
            self.ledger = RetainLedger(self.directory / f"{exception.__name__}.jsonl")

            def handle(request):
                self.requests.append(request)
                raise exception("private", request=request)

            result = await self.submit(handle)
            self.assertEqual((result.status, result.operation_id), (S.AMBIGUOUS, OPERATION))
            self.assertTrue(result.acceptance_unknown)
            self.assertEqual(RetainLedger(self.ledger.path).read()[OPERATION].submission_state, "AMBIGUOUS")
            self.assertNotIn("private", self.ledger.path.read_text())
        self.assertEqual(len(self.requests), 3)

    async def test_known_pre_send_transport_failure_is_distinct(self):
        for exception in (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout):
            self.ledger = RetainLedger(self.directory / f"{exception.__name__}.jsonl")

            def handle(request):
                self.requests.append(request)
                raise exception("private", request=request)

            result = await self.submit(handle)
            self.assertEqual(result.status, S.FAILED_TO_SUBMIT)
            self.assertFalse(result.acceptance_unknown)
            self.assertEqual(self.ledger.read()[OPERATION].submission_state, "FAILED_TO_SUBMIT")
        self.assertEqual(len(self.requests), 3)

    async def test_bounded_deadline_cancels_only_one_post(self):
        cancelled = []

        async def handle(request):
            self.requests.append(request)
            try:
                await asyncio.sleep(60)
            finally:
                cancelled.append(True)

        result = await self.submit(handle, deadline_seconds=0.02)
        self.assertEqual(result.status, S.AMBIGUOUS)
        self.assertEqual(len(self.requests), 1)
        self.assertEqual(cancelled, [True])
        self.assertEqual(self.state().submission_state, "AMBIGUOUS")

    async def test_default_transport_explicitly_disables_retries(self):
        with patch.object(submission.httpx, "AsyncHTTPTransport", return_value=httpx.MockTransport(self.handle)) as factory:
            result = await submission.submit_async_retain(self.turn, self.ledger, operation_id=OPERATION)
        factory.assert_called_once_with(retries=0)
        self.assertEqual(result.status, S.ACCEPTED)
        self.assertEqual(len(self.requests), 1)

    async def test_replay_after_ambiguous_send_reuses_body_uuid_and_fingerprint(self):
        def timeout(request):
            self.requests.append(request)
            raise httpx.ReadTimeout("timeout", request=request)

        self.assertEqual((await self.submit(timeout)).status, S.AMBIGUOUS)
        original = self.state().intent
        self.ledger = RetainLedger(self.path)  # Reopen after process-local state is gone.
        with patch.object(submission.uuid, "uuid4", side_effect=AssertionError("must reuse UUID")):
            self.assertEqual((await self.replay()).status, S.ACCEPTED)
        self.assertEqual(self.requests[0].content, self.requests[1].content)
        self.assertEqual(self.state().intent, original)
        self.assertEqual(self.state().submission_state, "ACCEPTED")
        self.assertTrue(self.state().unresolved)

    async def test_duplicate_accepted_events_and_explicit_resubmission_are_one_operation(self):
        self.assertEqual((await self.submit()).status, S.ACCEPTED)
        self.assertEqual((await self.replay()).status, S.ACCEPTED)
        self.assertEqual((await self.submit()).status, S.ACCEPTED)
        self.assertEqual(len(self.ledger.read()), 1)
        self.assertEqual(len(self.requests), 3)  # Only caller-requested attempts, never internal retries.
        self.assertTrue(all(json.loads(r.content)["operation_id"] == OPERATION for r in self.requests))
        self.assertEqual(len([e for e in durable.read_jsonl(self.path)
                              if e["event_type"] == "RETAIN_SUBMISSION_ACCEPTED"]), 3)

    async def test_replay_changed_content_and_date_are_refused_before_post(self):
        self.record_intent()
        for column, value in (("content", "changed canonical answer"),
                              ("created_at", "2026-10-08 10:00:02")):
            with store.connect() as conn:
                conn.execute(f"UPDATE messages SET {column} = ? WHERE id = ?", (value, self.turn.assistant_message_id))
            result = await self.replay()
            self.assertEqual(result.status, S.FAILED_TO_SUBMIT)
            self.assertEqual(result.operation_id, OPERATION)
            self.assertEqual(self.requests, [])
        self.assertEqual(len(self.ledger.read()), 1)

    async def test_replay_builder_refuses_bank_metadata_context_and_version_changes(self):
        intent = self.record_intent()
        original = shadow._load_retain_item(self.turn)
        for field, value in (("content", "different"), ("metadata", {"source": "other"}),
                             ("context", "new"), ("document_id", "different")):
            changed = deepcopy(original)
            changed[field] = value
            with self.subTest(field=field), self.assertRaises(LedgerError):
                submission.build_async_request(intent, changed)
        from dataclasses import replace
        for changed in (replace(intent, bank="other"), replace(intent, contract_version=2)):
            with self.assertRaises(LedgerError):
                submission.build_async_request(changed, original)

    async def test_replay_missing_canonical_source_is_refused(self):
        self.record_intent()
        with store.connect() as conn:
            conn.execute("DELETE FROM messages WHERE id = ?", (self.turn.assistant_message_id,))
        self.assertEqual((await self.replay()).status, S.FAILED_TO_SUBMIT)
        self.assertEqual(self.requests, [])

    async def test_unknown_or_malformed_intent_cannot_submit_or_fabricate_completion(self):
        self.assertEqual((await self.replay()).status, S.INTENT_DURABILITY_FAILED)
        self.record_intent()
        with self.path.open("ab") as stream:
            stream.write(b'{"event_type":"RETAIN_STATUS","status":"completed"')
        self.assertEqual((await self.replay()).status, S.INTENT_DURABILITY_FAILED)
        self.assertEqual((await self.submit()).status, S.INTENT_DURABILITY_FAILED)
        self.assertEqual(self.requests, [])
        with self.assertRaises(ValueError):
            self.ledger.read()

    async def test_invalid_client_and_canonical_item_are_pre_send_failures_without_intents(self):
        for kwargs in (dict(base_url="file:///tmp/no"), dict(base_url="http://localhost/x"),
                       dict(deadline_seconds=0), dict(deadline_seconds=True)):
            self.assertEqual((await self.submit(**kwargs)).status, S.FAILED_TO_SUBMIT)
        with patch.object(shadow, "_load_retain_item", return_value=None):
            self.assertEqual((await self.submit()).status, S.FAILED_TO_SUBMIT)
        self.assertEqual(self.requests, [])
        self.assertFalse(self.path.exists())

    async def test_outcome_fsync_failure_preserves_durable_intent_and_reports_failure(self):
        original = self.ledger.record_submission_accepted

        def fail(operation_id):
            with patch.object(durable.os, "fsync", side_effect=OSError("private")):
                original(operation_id)

        with patch.object(self.ledger, "record_submission_accepted", side_effect=fail):
            result = await self.submit()
        self.assertEqual(result.status, S.ACCEPTED)  # Valid ACK, not a claim of local outcome durability.
        self.assertFalse(result.outcome_durable)
        self.assertEqual(result.ledger_error, "OSError")
        self.assertEqual(self.state().submission_state, "NOT_ATTEMPTED")
        self.assertEqual(self.state().intent.operation_id, OPERATION)
        self.assertTrue(self.state().unresolved)
        self.assertEqual(len(self.requests), 1)

    async def test_outcome_append_is_outside_http_deadline(self):
        original = self.ledger.record_submission_failed

        def slow(*args, **kwargs):
            time.sleep(0.03)
            original(*args, **kwargs)

        def handle(request):
            self.requests.append(request)
            return httpx.Response(422)

        with patch.object(self.ledger, "record_submission_failed", side_effect=slow):
            result = await self.submit(handle, deadline_seconds=0.01)
        self.assertEqual(result.status, S.REJECTED)
        self.assertFalse(result.acceptance_unknown)
        self.assertTrue(result.outcome_durable)
        self.assertEqual(self.state().submission_state, "REJECTED")

    async def test_valid_ack_survives_transport_close_failure(self):
        class CloseFailure(httpx.MockTransport):
            async def aclose(self):
                raise httpx.ReadError("close failed")

        result = await submission.submit_async_retain(
            self.turn, self.ledger, operation_id=OPERATION, transport=CloseFailure(self.handle))
        self.assertEqual(result.status, S.ACCEPTED)
        self.assertEqual(self.state().submission_state, "ACCEPTED")
        self.assertEqual(len(self.requests), 1)

    async def test_terminal_operation_requires_reconciliation_not_replacement_submission(self):
        self.record_intent()
        for status in ("failed", "cancelled", "completed"):
            self.ledger.record_status(OPERATION, status)
            self.assertEqual((await self.replay()).status, S.FAILED_TO_SUBMIT)
            self.assertEqual(self.state().terminal_status, status)
        self.assertEqual(self.requests, [])

    async def test_generated_uuid_is_durable_before_post(self):
        result = await submission.submit_async_retain(
            self.turn, self.ledger, transport=httpx.MockTransport(self.handle))
        self.assertEqual(str(uuid.UUID(result.operation_id)), result.operation_id)
        self.assertEqual(self.ledger.read()[result.operation_id].intent.operation_id, result.operation_id)
        self.assertEqual(json.loads(self.requests[0].content)["operation_id"], result.operation_id)

    async def test_existing_uuid_with_changed_intent_is_refused_before_http(self):
        self.record_intent()
        with store.connect() as conn:
            conn.execute("UPDATE messages SET content = 'changed' WHERE id = ?", (self.turn.assistant_message_id,))
        result = await self.submit()
        self.assertEqual((result.status, result.operation_id), (S.INTENT_DURABILITY_FAILED, OPERATION))
        self.assertEqual(self.requests, [])
        self.assertEqual(len(self.ledger.read()), 1)

    async def test_rejection_then_explicit_same_uuid_replay_can_establish_acceptance(self):
        def handle(request):
            self.requests.append(request)
            return httpx.Response(422)

        self.assertEqual((await self.submit(handle)).status, S.REJECTED)
        self.assertEqual((await self.replay()).status, S.ACCEPTED)
        state = self.state()
        self.assertEqual(state.submission_state, "ACCEPTED")
        self.assertIsNone(state.http_status)
        self.assertIsNone(state.error)
        self.assertTrue(state.unresolved)
        self.assertEqual(self.requests[0].content, self.requests[1].content)

    async def test_client_cancellation_preserves_ambiguous_intent_and_propagates(self):
        entered = asyncio.Event()

        async def handle(request):
            self.requests.append(request)
            entered.set()
            await asyncio.sleep(60)

        task = asyncio.create_task(self.submit(handle))
        await asyncio.wait_for(entered.wait(), 5)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(self.state().submission_state, "AMBIGUOUS")
        self.assertEqual(len(self.requests), 1)


if __name__ == "__main__":
    unittest.main()
