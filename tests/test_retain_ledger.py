"""Offline ledger contracts: temporary files, no services or model requests."""

from copy import deepcopy
import hashlib
import json
import multiprocessing
from pathlib import Path
import sqlite3
import stat
import tempfile
import unittest
from unittest.mock import patch
import uuid

import app.durable_jsonl as durable
from app.retain_ledger import LedgerError, RetainLedger, payload_fingerprint, reduce_events


NOW = "2026-10-10T10:00:00+00:00"
BANK = "corvus-hindsight-lab-v1"
OPERATION = "b68777c5-6cae-4710-a879-0437145d7741"


def item(user=1, assistant=2):
    return {"content": "User:\ncanonical 雀\n\nAssistant:\ncanonical answer",
            "document_id": f"corvus-lab:turn:{user}:{assistant}",
            "timestamp": "2026-10-07T10:00:02+00:00", "context": "conversation",
            "metadata": {"source": "corvus-lab", "session_id": "session",
                         "user_message_id": str(user), "assistant_message_id": str(assistant)}}


def record(ledger, operation_id=OPERATION, user=1, assistant=2, **overrides):
    args = dict(user_message_id=user, assistant_message_id=assistant, session_id="session",
                bank=BANK, item=item(user, assistant), operation_id=operation_id, recorded_at=NOW)
    args.update(overrides)
    return ledger.record_intent(**args)


def append_process(path, number):
    ledger = RetainLedger(path)
    for index in range(12):
        operation_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"ledger-test:{number}:{index}"))
        record(ledger, operation_id)
        ledger.record_submission_accepted(operation_id)


class LedgerTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="corvus-retain-ledger-")
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.path = self.directory / "h1-shadow-recall.jsonl"
        self.ledger = RetainLedger(self.path)

    def state(self, operation_id=OPERATION):
        return RetainLedger(self.path).read()[operation_id]

    def test_construction_and_missing_read_do_not_create_files(self):
        self.assertFalse(self.path.exists())
        self.assertEqual(self.ledger.read(), {})
        self.assertFalse(self.path.exists())

    def test_intent_uuid_fingerprint_and_identity_survive_reopen_after_fsync(self):
        real_fsync = durable.os.fsync
        synced = []

        def fsync(fd):
            synced.append("directory" if stat.S_ISDIR(durable.os.fstat(fd).st_mode) else "file")
            real_fsync(fd)

        with patch.object(durable.os, "fsync", side_effect=fsync):
            intent = record(self.ledger)
        self.assertEqual(synced, ["file", "directory"])
        state = self.state()
        self.assertEqual(state.intent, intent)
        self.assertEqual(intent.operation_id, OPERATION)
        self.assertEqual(intent.payload_fingerprint, payload_fingerprint(BANK, item()))
        self.assertEqual((intent.user_message_id, intent.assistant_message_id), (1, 2))
        self.assertEqual((intent.session_id, intent.bank, intent.document_id),
                         ("session", BANK, "corvus-lab:turn:1:2"))
        self.assertEqual((intent.contract_version, intent.recorded_at), (1, NOW))
        self.assertEqual(state.submission_state, "NOT_ATTEMPTED")
        self.assertTrue(state.unresolved)
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o600)

    def test_generated_uuid_is_recoverable_without_caller_supplied_uuid(self):
        intent = record(self.ledger, operation_id=None)
        self.assertEqual(str(uuid.UUID(intent.operation_id)), intent.operation_id)
        self.assertEqual(self.state(intent.operation_id).intent, intent)

    def test_fingerprint_is_canonical_and_has_no_event_time_or_operation_uuid(self):
        original = item()
        reordered = dict(reversed(list(original.items())))
        reordered["metadata"] = dict(reversed(list(original["metadata"].items())))
        before = deepcopy(original)
        self.assertEqual(payload_fingerprint(BANK, original), payload_fingerprint(BANK, reordered))
        first = record(self.ledger)
        second = record(self.ledger, str(uuid.uuid4()), recorded_at="2026-10-11T12:00:00Z")
        self.assertEqual(first.payload_fingerprint, second.payload_fingerprint)
        self.assertEqual(original, before)

    def test_fingerprint_covers_all_submission_material(self):
        expected = payload_fingerprint(BANK, item())
        for field, changed in (("content", "different"), ("context", "other context"),
                               ("timestamp", "2026-10-08T10:00:02+00:00"),
                               ("document_id", "another-document"),
                               ("metadata", {"source": "other"}), ("tags", ["new tag"])):
            with self.subTest(field=field):
                candidate = dict(item(), **{field: changed})
                self.assertNotEqual(payload_fingerprint(BANK, candidate), expected)
        self.assertNotEqual(payload_fingerprint("other-bank", item()), expected)
        self.assertNotEqual(payload_fingerprint(BANK, item(), 2), expected)
        self.assertNotEqual(payload_fingerprint(BANK, dict(item(), context=None)), expected)

    def test_invalid_noncanonical_payload_and_intent_are_rejected_before_append(self):
        for changes in (dict(item={"content": "text"}), dict(item=dict(item(), metadata={1: "x"})),
                        dict(item=dict(item(), value=float("nan"))), dict(operation_id="bad"),
                        dict(user_message_id=True), dict(assistant_message_id=1),
                        dict(recorded_at="2026-10-10T10:00:00"), dict(session_id="")):
            with self.subTest(changes=changes), self.assertRaises(LedgerError):
                record(self.ledger, **changes)
        self.assertFalse(self.path.exists())

    def test_accepted_submission_is_reconstructed(self):
        record(self.ledger)
        self.ledger.record_submission_accepted(OPERATION, recorded_at=NOW)
        self.assertEqual(self.state().submission_state, "ACCEPTED")
        self.assertTrue(self.state().unresolved)

    def test_ambiguous_submission_remains_unresolved(self):
        record(self.ledger)
        self.ledger.record_submission_ambiguous(OPERATION, error="HTTP_TIMEOUT", recorded_at=NOW)
        state = self.state()
        self.assertEqual((state.submission_state, state.error), ("AMBIGUOUS", "HTTP_TIMEOUT"))
        self.assertTrue(state.unresolved)
        self.ledger.record_submission_accepted(OPERATION)
        self.ledger.record_submission_ambiguous(OPERATION, error="REPLAY_TIMEOUT")
        self.assertEqual(self.state().submission_state, "ACCEPTED")

    def test_pending_processing_and_parked_pending_remain_unresolved(self):
        record(self.ledger)
        for status in ("pending", "processing", "pending"):
            self.ledger.record_status(OPERATION, status, next_retry_at=NOW, retry_count=0)
            state = self.state()
            self.assertEqual(state.last_hindsight_status, status)
            self.assertEqual(state.next_retry_at, NOW)
            self.assertEqual(state.retry_count, 0)
            self.assertEqual(state.submission_state, "ACCEPTED")
            self.assertTrue(state.unresolved)

    def test_completed_is_terminal_and_not_found_cannot_erase_it(self):
        record(self.ledger)
        self.ledger.record_status(OPERATION, "completed", recorded_at=NOW)
        state = self.state()
        self.assertEqual((state.last_hindsight_status, state.terminal_status), ("completed", "completed"))
        self.assertFalse(state.unresolved)
        self.ledger.record_status(OPERATION, "not_found")
        self.assertEqual(self.state().terminal_status, "completed")
        self.assertFalse(self.state().unresolved)

    def test_failed_cancelled_are_terminal_and_observed_retry_can_reopen_failure(self):
        record(self.ledger)
        for status in ("failed", "cancelled"):
            self.ledger.record_status(OPERATION, status, error="CAUSE", recorded_at=NOW)
            self.assertEqual(self.state().terminal_status, status)
            self.assertFalse(self.state().unresolved)
        self.ledger.record_status(OPERATION, "pending")
        self.assertIsNone(self.state().terminal_status)
        self.assertTrue(self.state().unresolved)

    def test_not_found_does_not_invent_acceptance_or_completion(self):
        record(self.ledger)
        self.ledger.record_status(OPERATION, "not_found")
        self.assertEqual(self.state().submission_state, "NOT_ATTEMPTED")
        self.assertTrue(self.state().unresolved)

    def test_duplicate_events_reduce_to_one_logical_operation(self):
        record(self.ledger)
        record(self.ledger, recorded_at="2026-10-11T12:00:00Z")
        for _ in range(2):
            self.ledger.record_submission_accepted(OPERATION)
            self.ledger.record_status(OPERATION, "completed")
        self.assertEqual(len(self.ledger.read()), 1)
        self.assertEqual(self.state().intent.recorded_at, NOW)

    def test_two_operation_ids_are_independent(self):
        second = str(uuid.uuid4())
        record(self.ledger)
        record(self.ledger, second, user=3, assistant=4)
        self.ledger.record_status(OPERATION, "completed")
        self.ledger.record_submission_ambiguous(second)
        self.assertFalse(self.state().unresolved)
        self.assertTrue(self.state(second).unresolved)
        self.assertEqual(len(self.ledger.read()), 2)

    def test_uuid_reuse_for_changed_payload_is_untrustworthy(self):
        record(self.ledger)
        before = self.path.read_bytes()
        with self.assertRaises(LedgerError):
            record(self.ledger, item=dict(item(), content="different"))
        self.assertEqual(self.path.read_bytes(), before)
        damaged = durable.read_jsonl(self.path)[0]
        damaged["payload_fingerprint"] = payload_fingerprint(BANK, dict(item(), content="different"))
        durable.append_jsonl(self.path, damaged)
        with self.assertRaises(LedgerError):
            self.ledger.read()

    def test_legacy_records_remain_intact_and_cannot_imply_new_completion(self):
        legacy = [{"schema_version": 1, "user_message_id": 1, "retain": {"status": "OK"}},
                  {"schema_version": 1, "record_type": "retain_outcome", "retain": {"status": "OK"}}]
        for event in legacy:
            durable.append_jsonl(self.path, event)
        prefix = self.path.read_bytes()
        self.assertEqual(self.ledger.read(), {})
        record(self.ledger)
        self.assertEqual(self.path.read_bytes()[:len(prefix)], prefix)
        self.assertEqual(durable.read_jsonl(self.path)[:2], legacy)
        self.assertTrue(self.state().unresolved)

    def test_truncated_terminal_line_is_not_accepted_and_next_append_is_blocked(self):
        record(self.ledger)
        self.ledger.record_status(OPERATION, "completed")
        valid = self.path.read_bytes()
        self.path.write_bytes(valid[:-1])  # Valid JSON without the commit delimiter is incomplete.
        with self.assertRaises(ValueError):
            self.ledger.read()
        before = self.path.read_bytes()
        with self.assertRaises(ValueError):
            self.ledger.record_submission_accepted(OPERATION)
        self.assertEqual(self.path.read_bytes(), before)

    def test_malformed_terminal_records_fail_closed_without_partial_state(self):
        record(self.ledger)
        prefix = self.path.read_bytes()
        for tail in (b'{"event_type":"RETAIN_STATUS",\n', b'[]\n',
                     b'{"record_type":"retain_ledger","event_type":"RETAIN_STATUS","status":"completed"}\n',
                     b'{"record_type":"retain_ledger","record_type":"retain_outcome"}\n',
                     b'{"value":NaN}\n', b'\xff\n'):
            with self.subTest(tail=tail):
                self.path.write_bytes(prefix + tail)
                with self.assertRaises(ValueError):
                    self.ledger.read()

    def test_missing_intent_unknown_version_and_contradictory_completion_fail_closed(self):
        with self.assertRaises(LedgerError):
            self.ledger.record_submission_accepted(OPERATION)
        self.assertEqual(self.ledger.read(), {})
        self.path.unlink()
        record(self.ledger)
        events = durable.read_jsonl(self.path)
        damaged = deepcopy(events)
        damaged[0]["ledger_version"] = 99
        with self.assertRaises(LedgerError):
            reduce_events(damaged)
        self.ledger.record_status(OPERATION, "completed")
        with self.assertRaises(LedgerError):
            self.ledger.record_status(OPERATION, "processing")
        self.assertFalse(self.state().unresolved)

    def test_malformed_history_is_rejected_before_more_publication(self):
        record(self.ledger)
        with self.path.open("ab") as stream:
            stream.write(b'{"bad":}\n')
        before = self.path.read_bytes()
        with self.assertRaises(ValueError):
            self.ledger.record_status(OPERATION, "completed")
        self.assertEqual(self.path.read_bytes(), before)

    def test_ledger_records_cannot_disguise_themselves_as_legacy(self):
        record(self.ledger)
        event = durable.read_jsonl(self.path)[0]
        for record_type in (None, "retain_outcome"):
            damaged = dict(event, record_type=record_type)
            with self.subTest(record_type=record_type), self.assertRaises(LedgerError):
                reduce_events([damaged])

    def test_pure_reducer_and_read_do_not_modify_input_or_file(self):
        record(self.ledger)
        events = durable.read_jsonl(self.path)
        before = deepcopy(events)
        file_before = self.path.read_bytes()
        self.assertEqual(reduce_events(events), self.ledger.read())
        self.assertEqual(events, before)
        self.assertEqual(self.path.read_bytes(), file_before)

    def test_concurrent_process_appenders_do_not_corrupt_records(self):
        context = multiprocessing.get_context("fork")
        processes = [context.Process(target=append_process, args=(str(self.path), index))
                     for index in range(4)]
        try:
            for process in processes:
                process.start()
            for process in processes:
                process.join(timeout=15)
                self.assertEqual(process.exitcode, 0)
            states = self.ledger.read()
            self.assertEqual(len(states), 48)
            self.assertEqual(len(durable.read_jsonl(self.path)), 96)
            self.assertTrue(all(state.submission_state == "ACCEPTED" for state in states.values()))
        finally:
            for process in processes:
                if process.is_alive():
                    process.terminate()
                    process.join(timeout=5)

    def test_partial_write_failure_is_surfaced_and_rolls_back_own_append(self):
        record(self.ledger)
        before = self.path.read_bytes()
        real_write = durable.os.write
        calls = []

        def fail_after_partial(fd, data):
            calls.append(True)
            if len(calls) == 1:
                return real_write(fd, data[:8])
            raise OSError("write failure")

        with patch.object(durable.os, "write", side_effect=fail_after_partial), self.assertRaises(OSError):
            self.ledger.record_submission_accepted(OPERATION)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self.state().submission_state, "NOT_ATTEMPTED")

    def test_file_and_directory_fsync_failure_are_surfaced(self):
        record(self.ledger)
        before = self.path.read_bytes()
        real_fsync = durable.os.fsync
        for fail_on in ("file", "directory"):
            failed = []

            def fsync(fd):
                kind = "directory" if stat.S_ISDIR(durable.os.fstat(fd).st_mode) else "file"
                if kind == fail_on and not failed:
                    failed.append(True)
                    raise OSError("fsync failure")
                real_fsync(fd)

            with self.subTest(fail_on=fail_on):
                with patch.object(durable.os, "fsync", side_effect=fsync), self.assertRaises(OSError):
                    self.ledger.record_submission_accepted(OPERATION)
                self.assertEqual(self.path.read_bytes(), before)
                self.assertTrue(self.state().unresolved)

    def test_zero_write_and_unreadable_file_are_surfaced(self):
        with patch.object(durable.os, "write", return_value=0), self.assertRaises(OSError):
            record(self.ledger)
        self.assertEqual(self.ledger.read(), {})
        with patch.object(durable.os, "open", side_effect=PermissionError), self.assertRaises(PermissionError):
            self.ledger.read()

    def test_no_canonical_sqlite_mutation(self):
        canonical = self.directory / "corvus.db"
        with sqlite3.connect(canonical) as connection:
            connection.execute("CREATE TABLE messages(id INTEGER PRIMARY KEY, content TEXT)")
            connection.execute("INSERT INTO messages VALUES (1, 'canonical evidence')")
        before = hashlib.sha256(canonical.read_bytes()).hexdigest()
        record(self.ledger)
        self.ledger.record_submission_accepted(OPERATION)
        self.ledger.record_status(OPERATION, "completed")
        self.ledger.read()
        self.assertEqual(hashlib.sha256(canonical.read_bytes()).hexdigest(), before)
        self.assertEqual({p.name for p in self.directory.iterdir()}, {canonical.name, self.path.name})


if __name__ == "__main__":
    unittest.main()
