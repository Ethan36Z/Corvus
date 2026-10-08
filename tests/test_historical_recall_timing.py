"""H1.5 timing/propagation contracts; no live inference or Hindsight HTTP."""

import asyncio
from copy import deepcopy
from functools import partial
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock, Mock, patch

from fastapi import BackgroundTasks

from app.conversation_runtime import process_turn
import app.hindsight_shadow as shadow
import app.playground_api as api
import app.working_context as working_context
import memory.store as store


def count_chars(messages):
    return sum(len(message["content"]) for message in messages)


class HistoricalRecallTimingTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="corvus-h15-timing-")
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        for patcher in (
            patch.object(store, "DB_PATH", self.directory / "corvus.db"),
            patch.object(shadow, "DATA_DIR", self.directory),
            patch.object(shadow, "LAB_DATA_DIR", self.directory),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        store.init_db()
        store.add_message("old", "user", "CANONICAL_HIST_A")
        store.add_message("old", "user", "CANONICAL_HIST_B")
        self.old_a, self.old_b = store.load_recent_messages("old")
        self.recent_ids = [
            store.add_message("current", "user", "recent question"),
            store.add_message("current", "assistant", "recent answer"),
        ]
        self.current_id = store.add_message("current", "user", "current query")

    def context(self, **kwargs):
        return working_context.build_working_context(
            session_id="current", current_user_message_id=self.current_id,
            current_user_content="current query", system_prompt="SYS",
            count_tokens=kwargs.pop("count_tokens", count_chars), **kwargs,
        )

    def test_success_times_only_historical_call_and_preserves_exclusions_order_and_context(self):
        clock = [0.0]

        def recent(**kwargs):
            clock[0] += 100
            return store.load_recent_messages(**kwargs)

        def tokens(messages):
            clock[0] += 10
            return count_chars(messages)

        rows = store.load_recent_messages("current")

        def search(query, limit, candidate_limit):
            self.assertEqual((query, limit, candidate_limit), ("current query", 8, 20))
            clock[0] += 0.03125
            return [rows[1], self.old_b, rows[2], self.old_a, rows[0]]

        with (
            patch.object(working_context, "load_recent_messages", side_effect=recent),
            patch.object(working_context, "perf_counter", side_effect=lambda: clock[0]) as timer,
        ):
            context = self.context(search_fn=search, count_tokens=tokens, historical_limit=2)
        self.assertEqual(timer.call_count, 2)
        self.assertEqual(context["historical_recall_elapsed_ms"], 31.25)
        self.assertGreater(clock[0], 100)
        self.assertEqual(context["retrieval_status"], "OK")
        self.assertIsNone(context["retrieval_error"])
        self.assertEqual(context["historical_message_ids"], [self.old_b["id"], self.old_a["id"]])
        self.assertEqual(context["historical_evidence"], [self.old_b, self.old_a])
        self.assertEqual(context["recent_message_ids"], self.recent_ids)
        self.assertEqual(context["messages"], [
            {"role": "system", "content": (
                "SYS\n\nRelevant historical evidence:\n"
                f'[memory #{self.old_b["id"]} role=user] CANONICAL_HIST_B\n'
                f'[memory #{self.old_a["id"]} role=user] CANONICAL_HIST_A\n'
                "Use this evidence only when it is relevant to the current request."
            )},
            {"role": "user", "content": "recent question"},
            {"role": "assistant", "content": "recent answer"},
            {"role": "user", "content": "current query"},
        ])

    def test_zero_duration_is_valid_and_wall_clock_is_not_used(self):
        with (
            patch.object(working_context, "perf_counter", return_value=17) as timer,
            patch("time.time", side_effect=AssertionError("wall clock must not measure recall")),
        ):
            context = self.context(search_fn=lambda query, **kwargs: [self.old_a])
        self.assertEqual(timer.call_count, 2)
        self.assertEqual(context["historical_recall_elapsed_ms"], 0)
        self.assertGreaterEqual(context["historical_recall_elapsed_ms"], 0)

    def test_failure_stops_timer_before_error_handling_and_keeps_degraded_context(self):
        clock = [0.0]

        class RetrievalFailure(RuntimeError):
            def __str__(self):
                clock[0] += 50
                return "synthetic recall failure"

        def search(query, **kwargs):
            clock[0] += 0.04
            raise RetrievalFailure()

        with patch.object(working_context, "perf_counter", side_effect=lambda: clock[0]) as timer:
            context = self.context(search_fn=search)
        self.assertEqual(timer.call_count, 2)
        self.assertEqual(context["historical_recall_elapsed_ms"], 40)
        self.assertEqual(context["retrieval_status"], "DEGRADED")
        self.assertEqual(context["retrieval_error"], "synthetic recall failure")
        self.assertEqual(context["historical_message_ids"], [])
        self.assertEqual(context["recent_message_ids"], self.recent_ids)
        self.assertEqual(context["messages"], [
            {"role": "system", "content": "SYS"},
            {"role": "user", "content": "recent question"},
            {"role": "assistant", "content": "recent answer"},
            {"role": "user", "content": "current query"},
        ])

    def test_context_budget_selection_is_unchanged_and_recent_ids_describe_final_context(self):
        with patch.object(working_context, "perf_counter", side_effect=[10, 10.05]):
            context = self.context(
                search_fn=lambda query, **kwargs: [self.old_b, self.old_a], input_token_budget=16,
            )
        self.assertEqual(context["historical_recall_elapsed_ms"], 50)
        self.assertEqual(context["retrieval_status"], "OK")
        self.assertEqual(context["historical_message_ids"], [])
        self.assertEqual(context["recent_message_ids"], [])
        self.assertEqual(context["messages"], [
            {"role": "system", "content": "SYS"},
            {"role": "user", "content": "current query"},
        ])

    def test_success_and_degraded_runtime_api_jsonl_propagation_and_shadow_order(self):
        async def exercise(fails):
            session = "runtime-degraded" if fails else "runtime-ok"
            recent_ids = [
                store.add_message(session, "user", "runtime recent question"),
                store.add_message(session, "assistant", "runtime recent answer"),
            ]
            events = []

            def search(query, **kwargs):
                events.append("active-recall")
                if fails:
                    raise RuntimeError("synthetic recall failure")
                return [self.old_b, self.old_a]

            generate = Mock(return_value="canonical runtime answer")
            runtime = partial(
                process_turn,
                build_context_fn=partial(working_context.build_working_context, search_fn=search),
                count_tokens_fn=count_chars, generate_fn=generate,
                dense_sync_fn=lambda ids: None, system_prompt_fn=lambda: "SYS",
            )
            tasks = BackgroundTasks()
            with (
                patch.object(api, "process_turn", runtime),
                patch.object(working_context, "perf_counter", side_effect=[100, 100.075]),
            ):
                response = api.post_chat(api.ChatRequest(session_id=session, message="query"), tasks)
            expected = {
                "historical_message_ids": [] if fails else [self.old_b["id"], self.old_a["id"]],
                "recent_message_ids": recent_ids,
                "historical_recall_elapsed_ms": 75,
                "retrieval_status": "DEGRADED" if fails else "OK",
                "retrieval_error": "synthetic recall failure" if fails else None,
            }
            self.assertEqual(response["historical_recall_elapsed_ms"], 75)
            self.assertEqual(response["historical_message_ids"], expected["historical_message_ids"])
            self.assertEqual(response["recent_message_ids"], recent_ids)
            self.assertEqual(response["status"]["retrieval"], expected["retrieval_status"])
            self.assertEqual(response["retrieval_error"], expected["retrieval_error"])
            self.assertEqual(response["reply"], "canonical runtime answer")
            self.assertEqual(response["status"]["persistence"], "NORMAL")
            self.assertEqual(response["status"]["model"], "OK")
            self.assertEqual(len(tasks.tasks), 1)
            model_messages = generate.call_args.args[0]
            self.assertEqual(model_messages[-1], {"role": "user", "content": "query"})
            self.assertNotIn("historical_recall_elapsed_ms", json.dumps(model_messages))
            self.assertNotIn("HINDSIGHT_ONLY", json.dumps(model_messages))
            before = deepcopy(response)
            real_append = shadow.append_observation

            async def recall(query):
                events.extend(["shadow-recall-start", "shadow-recall-complete"])
                return {"status": "OK", "results": [], "elapsed_ms": 1, "error": None}

            def append(record):
                real_append(record)
                events.append("outcome-appended" if record.get("record_type") else "comparison-appended")

            async def retain(turn):
                events.append("retain")
                self.assertEqual(events, [
                    "active-recall", "shadow-recall-start", "shadow-recall-complete",
                    "comparison-appended", "retain",
                ])
                record = json.loads((self.directory / shadow.LOG_NAME).read_text().splitlines()[-1])
                self.assertEqual(record["corvus"], expected)
                for text in ("CANONICAL_HIST_A", "CANONICAL_HIST_B", "runtime recent answer", "canonical runtime answer"):
                    self.assertNotIn(text, json.dumps(record))
                self.assertEqual([row["id"] for row in store.load_recent_messages(session)][-2:],
                                 [turn.user_message_id, turn.assistant_message_id])
                return {"status": "OK", "elapsed_ms": 1, "document_id": "HINDSIGHT_ONLY", "error": None}

            with (
                patch.object(shadow, "recall", new=AsyncMock(side_effect=recall)),
                patch.object(shadow, "append_observation", side_effect=append),
                patch.object(shadow, "retain_completed_turn", new=AsyncMock(side_effect=retain)),
            ):
                await tasks()
            self.assertEqual(events[-1], "outcome-appended")
            self.assertEqual(response, before)

        for fails in (False, True):
            with self.subTest(retrieval_degraded=fails):
                asyncio.run(exercise(fails))


if __name__ == "__main__":
    unittest.main()
