"""Activity tracking contracts with fake generation, clocks, and HTTP responses."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError
from io import BytesIO
from threading import Event
import unittest
from unittest.mock import patch

import app.foreground_activity as activity
from app.conversation_runtime import process_turn
from app.model_client import ModelClientError, generate_chat_completion


class TrackerTests(unittest.TestCase):
    def setUp(self):
        self.now = [10.0]
        self.tracker = activity.ForegroundActivityTracker(clock=lambda: self.now[0])

    def test_initial_state_is_idle_and_snapshot_is_read_only(self):
        state = self.tracker.snapshot()
        self.assertEqual(state.active_foreground_count, 0)
        self.assertIsNone(state.last_foreground_started_at)
        self.assertIsNone(state.last_foreground_finished_at)
        with self.assertRaises(FrozenInstanceError):
            state.active_foreground_count = 1

    def test_completion_balances_count_and_advances_finished_timestamp(self):
        with self.tracker.generation():
            active = self.tracker.snapshot()
            self.assertEqual(active.active_foreground_count, 1)
            self.assertEqual(active.last_foreground_started_at, 10.0)
            self.assertIsNone(active.last_foreground_finished_at)
            self.now[0] = 11.0
        finished = self.tracker.snapshot()
        self.assertEqual(finished.active_foreground_count, 0)
        self.assertEqual(finished.last_foreground_finished_at, 11.0)
        self.assertEqual(active.active_foreground_count, 1)  # Detached copy.

        self.now[0] = 12.0
        with self.tracker.generation():
            self.now[0] = 13.0
        latest = self.tracker.snapshot()
        self.assertEqual(latest.active_foreground_count, 0)
        self.assertEqual(latest.last_foreground_started_at, 12.0)
        self.assertGreater(latest.last_foreground_finished_at, finished.last_foreground_finished_at)

    def test_exception_and_base_exception_balance_count(self):
        for error_type in (RuntimeError, KeyboardInterrupt):
            with self.subTest(error_type=error_type):
                with self.assertRaises(error_type):
                    with self.tracker.generation():
                        self.assertEqual(self.tracker.snapshot().active_foreground_count, 1)
                        self.now[0] += 1.0
                        raise error_type("synthetic failure")
                self.assertEqual(self.tracker.snapshot().active_foreground_count, 0)
                self.assertEqual(self.tracker.snapshot().last_foreground_finished_at, self.now[0])

    def test_module_context_and_snapshot_share_one_tracker(self):
        with patch.object(activity, "_tracker", self.tracker):
            self.assertEqual(activity.snapshot().active_foreground_count, 0)
            with activity.track_foreground_generation():
                self.assertEqual(activity.snapshot().active_foreground_count, 1)
            self.assertEqual(activity.snapshot().active_foreground_count, 0)


class ConversationActivityTests(unittest.TestCase):
    def setUp(self):
        self.now = [10.0]
        self.tracker = activity.ForegroundActivityTracker(clock=lambda: self.now[0])
        patcher = patch.object(activity, "_tracker", self.tracker)
        patcher.start()
        self.addCleanup(patcher.stop)

    def run_turn(self, generate, **overrides):
        ids = iter((1, 2))
        kwargs = {
            "session_id": "foreground-test",
            "user_content": "hello",
            "add_message_fn": lambda *args: next(ids),
            "build_context_fn": lambda **args: {
                "messages": [{"role": "user", "content": "hello"}],
                "recent_message_ids": [], "historical_message_ids": [],
                "input_tokens": 1, "retrieval_status": "OK", "retrieval_error": None,
            },
            "count_tokens_fn": lambda messages: 1,
            "generate_fn": generate,
            "dense_sync_fn": lambda ids: None,
            "system_prompt_fn": lambda: "SYS",
        }
        kwargs.update(overrides)
        return process_turn(**kwargs)

    def test_only_reply_generation_is_active(self):
        events = []

        def add_message(session_id, role, content):
            self.assertEqual(activity.snapshot().active_foreground_count, 0)
            events.append(role)
            return 1 if role == "user" else 2

        def context(**kwargs):
            self.assertEqual(activity.snapshot().active_foreground_count, 0)
            events.append("context")
            return {
                "messages": [{"role": "user", "content": "hello"}],
                "recent_message_ids": [], "historical_message_ids": [],
                "input_tokens": 1, "retrieval_status": "OK", "retrieval_error": None,
            }

        def generate(messages):
            state = activity.snapshot()
            self.assertEqual(state.active_foreground_count, 1)
            self.assertEqual(state.last_foreground_started_at, 10.0)
            events.append("generate")
            self.now[0] = 11.0
            return "reply"

        def dense(ids):
            self.assertEqual(activity.snapshot().active_foreground_count, 0)
            events.append("dense")

        result = self.run_turn(generate, add_message_fn=add_message,
                               build_context_fn=context, dense_sync_fn=dense)
        self.assertEqual(result["reply"], "reply")
        self.assertEqual(result["model_status"], "OK")
        self.assertEqual(events, ["user", "context", "generate", "assistant", "dense"])
        self.assertEqual(activity.snapshot().active_foreground_count, 0)
        self.assertEqual(activity.snapshot().last_foreground_finished_at, 11.0)

    def test_model_error_returns_idle_without_changing_error_contract(self):
        def generate(messages):
            self.assertEqual(activity.snapshot().active_foreground_count, 1)
            raise ModelClientError("MODEL_TIMEOUT", "synthetic timeout")

        result = self.run_turn(generate)
        self.assertEqual(result["model_status"], "MODEL_TIMEOUT")
        self.assertEqual(result["error"], "synthetic timeout")
        self.assertIsNone(result["assistant_message_id"])
        self.assertEqual(activity.snapshot().active_foreground_count, 0)
        self.assertIsNotNone(activity.snapshot().last_foreground_finished_at)

    def test_unexpected_generation_error_propagates_but_returns_idle(self):
        def generate(messages):
            self.assertEqual(activity.snapshot().active_foreground_count, 1)
            raise RuntimeError("synthetic generation failure")

        with self.assertRaisesRegex(RuntimeError, "synthetic generation failure"):
            self.run_turn(generate)
        self.assertEqual(activity.snapshot().active_foreground_count, 0)
        self.assertIsNotNone(activity.snapshot().last_foreground_finished_at)

    def test_two_overlapping_turns_finish_independently(self):
        entered = [Event(), Event()]
        release = [Event(), Event()]

        def generate(index):
            def blocked(messages):
                entered[index].set()
                if not release[index].wait(timeout=5):
                    raise AssertionError("test generation was not released")
                return "reply"
            return blocked

        with ThreadPoolExecutor(max_workers=2) as executor:
            try:
                first = executor.submit(self.run_turn, generate(0))
                self.assertTrue(entered[0].wait(timeout=5))
                self.assertEqual(activity.snapshot().active_foreground_count, 1)
                self.now[0] = 11.0
                second = executor.submit(self.run_turn, generate(1))
                self.assertTrue(entered[1].wait(timeout=5))
                self.assertEqual(activity.snapshot().active_foreground_count, 2)
                self.assertEqual(activity.snapshot().last_foreground_started_at, 11.0)

                self.now[0] = 12.0
                release[0].set()
                self.assertEqual(first.result(timeout=5)["reply"], "reply")
                one_active = activity.snapshot()
                self.assertEqual(one_active.active_foreground_count, 1)
                self.assertEqual(one_active.last_foreground_finished_at, 12.0)

                self.now[0] = 13.0
                release[1].set()
                self.assertEqual(second.result(timeout=5)["reply"], "reply")
                idle = activity.snapshot()
                self.assertEqual(idle.active_foreground_count, 0)
                self.assertGreater(idle.last_foreground_finished_at, one_active.last_foreground_finished_at)
            finally:
                for event in release:
                    event.set()

    def test_failure_before_generation_does_not_record_activity(self):
        with self.assertRaises(ValueError):
            self.run_turn(lambda messages: self.fail("generation must not run"),
                          attachment_mode="invalid")
        self.assertEqual(activity.snapshot(), activity.ForegroundActivitySnapshot(0, None, None))

    def test_direct_shared_model_client_call_is_not_foreground_activity(self):
        def fake_opener(request, timeout):
            self.assertEqual(activity.snapshot(), activity.ForegroundActivitySnapshot(0, None, None))
            return BytesIO(b'{"choices":[{"message":{"content":"reply"}}]}')

        reply = generate_chat_completion([{"role": "user", "content": "hello"}],
                                         opener=fake_opener)
        self.assertEqual(reply, "reply")
        self.assertEqual(activity.snapshot(), activity.ForegroundActivitySnapshot(0, None, None))


if __name__ == "__main__":
    unittest.main()
