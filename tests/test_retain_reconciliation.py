"""No real HTTP: temporary canonical evidence/ledger and fake status responses."""

import asyncio
from copy import deepcopy
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import uuid

import httpx

from app import durable_jsonl as durable
from app import hindsight_shadow as shadow
from app import retain_reconciliation as reconciliation
from app.retain_ledger import LedgerError, RetainLedger
import memory.store as store


OPERATION = "b68777c5-6cae-4710-a879-0437145d7741"
SECOND = "12e0b399-409a-4975-be37-c0c9d8214559"
THIRD = "719994b0-a1b3-4da7-bb37-349a1fd60468"
NOW = "2026-10-10T10:00:00+00:00"
S = reconciliation.ReconciliationStatus


class ReconciliationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="corvus-retain-reconcile-")
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        patcher = patch.object(store, "DB_PATH", self.directory / "corvus.db")
        patcher.start()
        self.addCleanup(patcher.stop)
        store.init_db()
        user = store.add_message("session", "user", "canonical user 雀")
        assistant = store.add_message("session", "assistant", "canonical answer")
        with store.connect() as conn:
            conn.execute("UPDATE messages SET created_at = '2026-10-07 10:00:00' WHERE id = ?", (user,))
            conn.execute("UPDATE messages SET created_at = '2026-10-07 10:00:02' WHERE id = ?", (assistant,))
        self.turn = shadow.ShadowTurn("session", user, assistant, "", ())
        self.path = self.directory / shadow.LOG_NAME
        self.ledger = RetainLedger(self.path)
        self.requests = []
        self.server_status = "pending"
        self.record()

    def record(self, operation_id=OPERATION, recorded_at=NOW):
        return self.ledger.record_intent(
            user_message_id=self.turn.user_message_id, assistant_message_id=self.turn.assistant_message_id,
            session_id=self.turn.session_id, bank=shadow.BANK, item=shadow._load_retain_item(self.turn),
            operation_id=operation_id, recorded_at=recorded_at,
        )

    def handle(self, request):
        self.requests.append(request)
        self.assertEqual(request.method, "GET")
        self.assertEqual(request.url.params, httpx.QueryParams())
        operation_id = request.url.path.rsplit("/", 1)[1]
        self.assertEqual(str(request.url), f"{shadow.BASE_URL}/v1/default/banks/{shadow.BANK}/operations/{operation_id}")
        self.assertEqual(request.content, b"")
        return httpx.Response(200, json={"operation_id": operation_id, "status": self.server_status})

    async def reconcile(self, handler=None, operation_id=OPERATION, **kwargs):
        return await reconciliation.reconcile_operation(
            operation_id, self.ledger, transport=httpx.MockTransport(handler or self.handle), **kwargs)

    def state(self, operation_id=OPERATION):
        return RetainLedger(self.path).read()[operation_id]

    async def test_pending_and_processing_remain_unresolved_with_minimal_optional_contract(self):
        for status in ("pending", "processing"):
            self.server_status = status
            result = await self.reconcile()
            self.assertEqual(result.status, S(status.upper()))
            self.assertTrue(result.outcome_durable)
            self.assertEqual(self.state().submission_state, "ACCEPTED")
            self.assertTrue(self.state().unresolved)
            self.assertEqual(self.state().status_observation, {"operation_id": OPERATION, "status": status})
        self.assertEqual(len(self.requests), 2)

    async def test_completed_is_retain_terminal_not_consolidation_completion(self):
        self.server_status = "completed"
        result = await self.reconcile()
        self.assertEqual(result.status, S.COMPLETED)
        self.assertEqual(self.state().terminal_status, "completed")
        self.assertFalse(self.state().unresolved)
        self.assertNotIn("consolidation", repr(result))

    async def test_failed_and_cancelled_are_terminal_with_error_preserved(self):
        for status in ("failed", "cancelled"):
            def handle(request):
                self.requests.append(request)
                return httpx.Response(200, json={"operation_id": OPERATION, "status": status,
                                                "error_message": "worker extraction failed"})

            # A separate fresh ledger represents each terminal case.
            self.path = self.directory / f"{status}.jsonl"
            self.ledger = RetainLedger(self.path)
            self.record()
            result = await self.reconcile(handle)
            self.assertEqual(result.status, S(status.upper()))
            self.assertEqual(result.error, "worker extraction failed")
            self.assertEqual(self.state().error, "worker extraction failed")
            self.assertEqual(self.state().terminal_status, status)
            self.assertFalse(self.state().unresolved)

    async def test_not_found_requires_verified_original_payload_before_replay_needed(self):
        self.server_status = "not_found"
        with patch.object(reconciliation.uuid, "uuid4", side_effect=AssertionError("no new UUID")):
            result = await self.reconcile()
        self.assertEqual(result.status, S.REPLAY_NEEDED)
        self.assertTrue(result.outcome_durable)
        self.assertEqual(result.operation_id, OPERATION)
        self.assertEqual(self.state().last_hindsight_status, "not_found")
        self.assertEqual(self.state().submission_state, "NOT_ATTEMPTED")
        self.assertTrue(self.state().unresolved)
        self.assertEqual(len(self.requests), 1)

    async def test_not_found_on_accepted_or_ambiguous_submission_always_uses_same_uuid(self):
        for kind in ("accepted", "ambiguous"):
            self.path = self.directory / f"{kind}.jsonl"
            self.ledger = RetainLedger(self.path)
            self.record()
            getattr(self.ledger, f"record_submission_{kind}")(OPERATION)
            self.server_status = "not_found"
            result = await self.reconcile()
            self.assertEqual(result.status, S.REPLAY_NEEDED)
            self.assertEqual(result.operation_id, OPERATION)
            self.assertTrue(self.state().unresolved)
        self.assertEqual([r.url.path.rsplit("/", 1)[1] for r in self.requests], [OPERATION, OPERATION])

    async def test_pre_submit_accepted_and_ambiguous_intents_discover_existing_server_work(self):
        for kind in (None, "accepted", "ambiguous"):
            self.path = self.directory / f"found-{kind}.jsonl"
            self.ledger = RetainLedger(self.path)
            self.record()
            if kind:
                getattr(self.ledger, f"record_submission_{kind}")(OPERATION)
            self.server_status = "processing"
            with patch.object(reconciliation.uuid, "uuid4", side_effect=AssertionError("no UUID")):
                result = await self.reconcile()
            self.assertEqual(result.status, S.PROCESSING)
            self.assertEqual(self.state().submission_state, "ACCEPTED")
        self.assertEqual(len(self.requests), 3)

    async def test_capture_full_server_timing_retry_progress_and_child_metadata(self):
        body = {
            "operation_id": OPERATION, "status": "pending", "operation_type": "batch_retain",
            "error_message": "previous attempt", "retry_count": 2, "next_retry_at": "2026-10-10T10:05:00Z",
            "created_at": NOW, "updated_at": "2026-10-10T10:02:00Z", "completed_at": None,
            "progress": {"stage": "processing_batch", "at": NOW, "processed": 1, "total": 2,
                         "detail": {"observations_created": 1}},
            "child_operations": [{"operation_id": SECOND, "status": "pending", "sub_batch_index": 0,
                                  "items_count": 1, "error_message": None}],
        }

        def handle(request):
            self.requests.append(request)
            return httpx.Response(200, json=dict(body, task_payload={"private": "ignored"},
                                                result_metadata={"unstable": "ignored"}))

        result = await self.reconcile(handle)
        self.assertEqual(result.status, S.PENDING)
        self.assertEqual(result.observation, body)
        state = self.state()
        self.assertEqual(state.status_observation, body)
        self.assertEqual(state.retry_count, 2)
        self.assertEqual(state.next_retry_at, "2026-10-10T10:05:00+00:00")
        self.assertEqual(state.error, "previous attempt")
        self.assertTrue(state.unresolved)  # Future next_retry_at is parked pending, not terminal.
        self.assertNotIn("private", self.path.read_text())
        self.assertNotIn("unstable", self.path.read_text())

    async def test_optional_nulls_empty_error_and_children_are_not_corruption(self):
        body = {"operation_id": OPERATION, "status": "pending", "error_message": "",
                "retry_count": None, "next_retry_at": None, "created_at": None,
                "updated_at": None, "completed_at": None, "progress": None, "child_operations": []}
        result = await self.reconcile(lambda request: httpx.Response(200, json=body))
        self.assertEqual(result.status, S.PENDING)
        self.assertEqual(self.state().status_observation, body)
        self.assertEqual(self.state().error, "")

    async def test_status_transport_ambiguity_keeps_intent_unresolved_and_does_not_retry(self):
        before = self.path.read_bytes()
        for exception in (httpx.ReadTimeout, httpx.ConnectError, httpx.ReadError):
            def handle(request):
                self.requests.append(request)
                raise exception("private details", request=request)

            result = await self.reconcile(handle)
            self.assertEqual(result.status, S.STATUS_AMBIGUOUS)
            self.assertFalse(result.outcome_durable)
            self.assertEqual(result.operation_id, OPERATION)
            self.assertTrue(self.state().unresolved)
            self.assertEqual(self.path.read_bytes(), before)
            self.assertNotIn("private", repr(result))
        self.assertEqual(len(self.requests), 3)

    async def test_http_errors_including_404_are_not_json_not_found_or_replay(self):
        for code in (401, 403, 404, 409, 500, 503, 302):
            def handle(request):
                self.requests.append(request)
                return httpx.Response(code, json={"detail": "private"}, headers={"location": "http://other.test"})

            result = await self.reconcile(handle)
            self.assertEqual(result.status, S.STATUS_ERROR)
            self.assertEqual(result.http_status, code)
            self.assertEqual(result.error, f"HTTP_{code}")
            self.assertIsNone(self.state().last_hindsight_status)
        self.assertEqual(len(self.requests), 7)

    async def test_invalid_api_response_cannot_fabricate_completion(self):
        bodies = [{"operation_id": SECOND, "status": "completed"}, {"status": "completed"},
                  {"operation_id": OPERATION, "status": "unknown"},
                  {"operation_id": OPERATION, "status": "completed", "operation_type": "consolidation"},
                  {"operation_id": OPERATION, "status": "completed", "retry_count": True},
                  {"operation_id": OPERATION, "status": "completed", "bank_id": "other"},
                  {"operation_id": OPERATION, "status": "completed", "progress": []},
                  {"operation_id": OPERATION, "status": "completed", "child_operations": [{"status": "completed"}]},
                  {"operation_id": OPERATION, "status": "completed", "next_retry_at": 1}, []]
        for body in bodies:
            with self.subTest(body=body):
                result = await self.reconcile(lambda request: httpx.Response(200, json=body))
                self.assertEqual(result.status, S.STATUS_ERROR)
                self.assertEqual(result.error, "INVALID_STATUS_RESPONSE")
                self.assertIsNone(self.state().terminal_status)
        result = await self.reconcile(lambda request: httpx.Response(200, content=b"not-json"))
        self.assertEqual(result.status, S.STATUS_ERROR)
        duplicate = '{"operation_id":"' + OPERATION + '","status":"pending","status":"completed"}'
        result = await self.reconcile(lambda request: httpx.Response(200, content=duplicate))
        self.assertEqual(result.status, S.STATUS_ERROR)
        self.assertIsNone(self.state().terminal_status)

    async def test_fingerprint_mismatch_is_operator_error_never_actionable_replay(self):
        self.server_status = "not_found"
        with store.connect() as conn:
            conn.execute("UPDATE messages SET content = 'changed' WHERE id = ?", (self.turn.assistant_message_id,))
        result = await self.reconcile()
        self.assertEqual(result.status, S.STATUS_ERROR)
        self.assertEqual(result.error, "REPLAY_PAYLOAD_UNRECOVERABLE")
        self.assertTrue(result.outcome_durable)  # The not_found observation is still durable.
        self.assertEqual(self.state().last_hindsight_status, "not_found")
        self.assertTrue(self.state().unresolved)
        self.assertEqual(len(self.requests), 1)

    async def test_missing_source_or_unsupported_contract_blocks_replay_actionability(self):
        self.server_status = "not_found"
        with patch.object(shadow, "_load_retain_item", return_value=None):
            self.assertEqual((await self.reconcile()).error, "REPLAY_PAYLOAD_UNRECOVERABLE")
        self.path = self.directory / "version-2.jsonl"
        self.ledger = RetainLedger(self.path)
        self.ledger.record_intent(operation_id=OPERATION, user_message_id=self.turn.user_message_id,
                                  assistant_message_id=self.turn.assistant_message_id, session_id="session",
                                  bank=shadow.BANK, item=shadow._load_retain_item(self.turn), contract_version=2)
        self.assertEqual((await self.reconcile()).error, "REPLAY_PAYLOAD_UNRECOVERABLE")

    async def test_terminal_operations_skipped_in_scan_and_direct_lookup(self):
        self.record(SECOND)
        self.record(THIRD)
        for operation_id, status in ((OPERATION, "completed"), (SECOND, "failed"), (THIRD, "cancelled")):
            self.ledger.record_status(operation_id, status)
            self.assertEqual((await self.reconcile(operation_id=operation_id)).status, S(status.upper()))
        results = await reconciliation.reconcile_unresolved(self.ledger, transport=httpx.MockTransport(self.handle))
        self.assertEqual(results, ())
        self.assertEqual(self.requests, [])

    async def test_bounded_scan_oldest_first_instant_order_and_deterministic_uuid_ties(self):
        self.record(SECOND, recorded_at="2026-10-10T09:00:00+00:00")
        self.record(THIRD, recorded_at="2026-10-10T12:00:00+02:00")  # Same instant as first.
        results = await reconciliation.reconcile_unresolved(
            self.ledger, max_operations=2, transport=httpx.MockTransport(self.handle))
        self.assertEqual([r.operation_id for r in results], [SECOND, min(OPERATION, THIRD)])
        self.assertEqual(len(self.requests), 2)
        remaining = reconciliation.select_unresolved(self.ledger.read(), 3)
        self.assertEqual([i.operation_id for i in remaining], [SECOND, min(OPERATION, THIRD), max(OPERATION, THIRD)])

    async def test_invalid_bounds_and_zero_do_not_send_http(self):
        self.assertEqual(await reconciliation.reconcile_unresolved(
            self.ledger, max_operations=0, transport=httpx.MockTransport(self.handle)), ())
        for limit in (-1, True, 1.5):
            with self.assertRaises(ValueError):
                await reconciliation.reconcile_unresolved(self.ledger, max_operations=limit,
                                                          transport=httpx.MockTransport(self.handle))
        self.assertEqual(self.requests, [])

    async def test_reopen_and_duplicate_observations_preserve_one_operation(self):
        await self.reconcile()
        await self.reconcile()
        self.record(SECOND)
        self.server_status = "completed"
        await self.reconcile(operation_id=SECOND)
        self.ledger = RetainLedger(self.path)
        states = self.ledger.read()
        self.assertEqual(len(states), 2)
        self.assertTrue(states[OPERATION].unresolved)
        self.assertFalse(states[SECOND].unresolved)
        self.assertEqual(states[SECOND].terminal_status, "completed")

    async def test_malformed_tail_blocks_lookup_and_scan_without_partial_completion(self):
        with self.path.open("ab") as stream:
            stream.write(b'{"record_type":"retain_ledger","status":"completed"')
        self.assertEqual((await self.reconcile()).status, S.STATUS_ERROR)
        with self.assertRaises(ValueError):
            await reconciliation.reconcile_unresolved(self.ledger, transport=httpx.MockTransport(self.handle))
        self.assertEqual(self.requests, [])

    async def test_mismatched_observation_cannot_be_recorded_as_completion(self):
        before = self.path.read_bytes()
        for observation in ({"operation_id": SECOND, "status": "completed"},
                            {"operation_id": OPERATION, "status": "pending"}):
            with self.assertRaises(LedgerError):
                self.ledger.record_status(OPERATION, "completed", observation=observation)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertTrue(self.state().unresolved)

    async def test_ledger_fsync_failure_does_not_claim_durable_completion(self):
        self.server_status = "completed"
        with patch.object(durable.os, "fsync", side_effect=OSError("private")):
            result = await self.reconcile()
        self.assertEqual(result.status, S.STATUS_ERROR)
        self.assertEqual(result.error, "STATUS_DURABILITY_FAILED")
        self.assertFalse(result.outcome_durable)
        self.assertTrue(self.state().unresolved)
        self.assertIsNone(self.state().terminal_status)

    async def test_concurrent_completion_is_not_erased_or_returned_as_replay_needed(self):
        def handle(request):
            self.requests.append(request)
            self.ledger.record_status(OPERATION, "completed")
            return httpx.Response(200, json={"operation_id": OPERATION, "status": "not_found"})

        result = await self.reconcile(handle)
        self.assertEqual(result.status, S.COMPLETED)
        self.assertEqual(self.state().terminal_status, "completed")

    async def test_bounded_timeout_and_default_transport_have_no_retries(self):
        async def handle(request):
            self.requests.append(request)
            await asyncio.sleep(60)

        result = await self.reconcile(handle, deadline_seconds=0.02)
        self.assertEqual(result.status, S.STATUS_AMBIGUOUS)
        self.assertEqual(len(self.requests), 1)
        with patch.object(reconciliation.httpx, "AsyncHTTPTransport", return_value=httpx.MockTransport(self.handle)) as factory:
            result = await reconciliation.reconcile_operation(OPERATION, self.ledger)
        factory.assert_called_once_with(retries=0)
        self.assertEqual(result.status, S.PENDING)
        self.assertEqual(len(self.requests), 2)

    async def test_scan_reports_one_status_error_then_continues_within_bound(self):
        self.record(SECOND, recorded_at="2026-10-10T09:00:00Z")

        def handle(request):
            if request.url.path.endswith(SECOND):
                self.requests.append(request)
                return httpx.Response(503)
            return self.handle(request)

        results = await reconciliation.reconcile_unresolved(
            self.ledger, max_operations=2, transport=httpx.MockTransport(handle))
        self.assertEqual([r.status for r in results], [S.STATUS_ERROR, S.PENDING])
        self.assertEqual(len(self.requests), 2)

    async def test_completion_during_payload_reconstruction_prevents_replay_needed(self):
        self.server_status = "not_found"
        original = shadow._load_retain_item

        def load(turn):
            self.ledger.record_status(OPERATION, "completed")
            return original(turn)

        with patch.object(shadow, "_load_retain_item", side_effect=load):
            result = await self.reconcile()
        self.assertEqual(result.status, S.COMPLETED)
        self.assertEqual(self.state().terminal_status, "completed")

    async def test_unknown_intent_and_invalid_status_client_do_not_send_http(self):
        self.assertEqual((await self.reconcile(operation_id=SECOND)).status, S.STATUS_ERROR)
        for kwargs in (dict(base_url="http://localhost/wrong"), dict(deadline_seconds=0)):
            result = await self.reconcile(**kwargs)
            self.assertEqual(result.status, S.STATUS_ERROR)
            self.assertEqual(result.error, "INVALID_STATUS_REQUEST")
        self.assertEqual(self.requests, [])

    async def test_selection_and_status_lookup_do_not_mutate_canonical_evidence_or_source_state(self):
        before = hashlib.sha256(store.DB_PATH.read_bytes()).hexdigest()
        states = self.ledger.read()
        original = deepcopy(states)
        reconciliation.select_unresolved(states, 1)
        self.assertEqual(states, original)
        self.server_status = "not_found"
        self.assertEqual((await self.reconcile()).status, S.REPLAY_NEEDED)
        self.assertEqual(hashlib.sha256(store.DB_PATH.read_bytes()).hexdigest(), before)
        self.assertTrue(all(r.method == "GET" for r in self.requests))


if __name__ == "__main__":
    unittest.main()
