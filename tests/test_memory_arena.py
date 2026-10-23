"""Arena unit contracts: fake inference/retrieval, in-memory canonical rows, temp JSONL."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from copy import deepcopy
from datetime import date
from functools import partial
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi import BackgroundTasks, HTTPException

from app import arena, conversation_runtime, foreground_activity, hindsight_shadow
from app import playground_api as api, working_context
from app.durable_jsonl import read_jsonl
from app.model_client import ModelClientError
from memory import historical_memory, store


def recall_result(status="OK", results=None):
    return {"provider": "hindsight", "bank": hindsight_shadow.BANK, "status": status,
            "elapsed_ms": 1.25, "error": None if status == "OK" else "DEADLINE_EXCEEDED",
            "results": ([{"source_id": "00123", "text": "HINDSIGHT_HISTORY", "rank": 1,
                          "score": 0.9, "metadata": {"document_id": "old-turn"}}]
                        if results is None else results)}


class ArenaTurnTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.directory = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.events = []
        self.rows = [{"id": 1, "session_id": "old", "role": "user", "content": "RAG_HISTORY"},
                     {"id": 2, "session_id": "s", "role": "user", "content": "previous question"},
                     {"id": 3, "session_id": "s", "role": "assistant", "content": "previous reply"}]
        self.generated = []
        self.contexts = []
        self.dense_calls = []
        self.tracker = foreground_activity.ForegroundActivityTracker()
        self.stack.enter_context(patch.object(foreground_activity, "_tracker", self.tracker))
        for target, name, value in (
            (hindsight_shadow, "DATA_DIR", self.directory),
            (hindsight_shadow, "LAB_DATA_DIR", self.directory),
            (store, "DB_PATH", self.directory / "corvus.db"),
        ):
            self.stack.enter_context(patch.object(target, name, value))
        self.stack.enter_context(patch("socket.socket.connect", side_effect=AssertionError("No live network")))
        self.stack.enter_context(patch.object(working_context, "load_recent_messages", self.recent))
        self.rag = self.stack.enter_context(patch.object(
            historical_memory, "hybrid_search", side_effect=self.search,
        ))
        self.personality = self.stack.enter_context(patch.object(
            arena, "compile_personality_system_prompt", return_value="FROZEN_PERSONALITY",
        ))
        self.stack.enter_context(patch.object(arena, "count_input_tokens", self.tokens))
        self.generator = self.stack.enter_context(patch.object(
            arena, "generate_chat_completion", side_effect=self.generate,
        ))
        self.recall = self.stack.enter_context(patch.object(
            hindsight_shadow, "recall", new=AsyncMock(side_effect=self.recall_hindsight),
        ))
        self.runtime = self.stack.enter_context(patch.object(
            arena, "process_turn", side_effect=self.process,
        ))
        self.h1_retain = self.stack.enter_context(patch.object(
            hindsight_shadow, "retain_completed_turn", new=AsyncMock(),
        ))
        self.h1_async = self.stack.enter_context(patch.object(
            hindsight_shadow, "_submit_durable_retain", new=AsyncMock(),
        ))
        original_builder = arena.build_working_context

        def build(**kwargs):
            result = original_builder(**kwargs)
            self.contexts.append(result)
            return result

        self.builder = self.stack.enter_context(patch.object(arena, "build_working_context", side_effect=build))
        self.build_response = partial(api.build_chat_response, load_messages_fn=self.hydrate)

    @staticmethod
    def tokens(messages):
        return sum(len(message["content"]) for message in messages)

    def recent(self, session_id, limit, before_message_id):
        self.events.append("recent")
        return deepcopy([row for row in self.rows
                         if row["session_id"] == session_id and row["id"] < before_message_id][-limit:])

    def hydrate(self, ids):
        return [deepcopy(row) for message_id in ids for row in self.rows if row["id"] == message_id]

    def search(self, query, **kwargs):
        self.events.append("rag")
        return [deepcopy(self.rows[0])]

    async def recall_hindsight(self, query):
        self.events.append("hindsight")
        return recall_result()

    def add(self, session, role, content):
        self.events.append(role)
        message_id = len(self.rows) + 1
        self.rows.append({"id": message_id, "session_id": session, "role": role, "content": content})
        return message_id

    def dense(self, ids):
        self.events.append("dense")
        self.dense_calls.append(list(ids))

    def generate(self, messages):
        self.assertEqual(self.tracker.snapshot().active_foreground_count, 1)
        self.generated.append(deepcopy(messages))
        self.events.append("main_model" if len(self.generated) == 1 else "shadow_model")
        return "RAG_REPLY" if len(self.generated) == 1 else "SHADOW_REPLY"

    def process(self, **kwargs):
        self.assertEqual(kwargs["system_prompt_fn"](), "FROZEN_PERSONALITY")
        self.assertEqual(kwargs["system_prompt_fn"](), "FROZEN_PERSONALITY")
        return conversation_runtime.process_turn(
            **kwargs, add_message_fn=self.add, dense_sync_fn=self.dense,
        )

    async def run_turn(self):
        return await arena.run_arena_turn(
            arena.ArenaChatRequest(session_id="s", message=" query "), build_response=self.build_response,
        )

    async def test_real_runtime_order_same_context_model_and_zero_shadow_writes(self):
        response = await self.run_turn()
        self.assertEqual(self.events, ["hindsight", "user", "recent", "rag", "main_model",
                                       "assistant", "dense", "shadow_model"])
        self.runtime.assert_called_once()
        self.personality.assert_called_once_with()
        self.builder.assert_called_once()
        kwargs = self.builder.call_args.kwargs
        self.assertEqual(set(kwargs), {"session_id", "current_user_message_id",
                                      "current_user_content", "system_prompt", "count_tokens"})
        self.assertEqual(kwargs["current_user_message_id"], 4)
        self.rag.assert_called_once_with("query", limit=20, candidate_limit=20)
        self.assertEqual(self.generator.call_count, 2)
        self.assertEqual(self.contexts[0]["messages"], self.generated[0])
        self.assertEqual(self.generated[0][1:], self.generated[1][1:])
        self.assertIn("RAG_HISTORY", self.generated[0][0]["content"])
        self.assertNotIn("RAG_HISTORY", self.generated[1][0]["content"])
        self.assertIn("memory #hindsight:00123", self.generated[1][0]["content"])
        self.assertNotIn("memory #00123", self.generated[1][0]["content"])
        self.assertTrue(all(messages[0]["content"].startswith("FROZEN_PERSONALITY")
                            for messages in self.generated))
        # Fairness: both arms receive the same effective system prompt
        # (personality + the per-request date note), then their own memory.
        effective = kwargs["system_prompt"]
        self.assertTrue(effective.startswith("FROZEN_PERSONALITY\n\nCurrent date: "))
        self.assertTrue(all(messages[0]["content"].startswith(effective)
                            for messages in self.generated))
        self.assertEqual([row["content"] for row in self.rows[-2:]], ["query", "RAG_REPLY"])
        self.assertEqual(self.dense_calls, [[4, 5]])
        self.h1_retain.assert_not_awaited()
        self.h1_async.assert_not_awaited()
        self.assertEqual(self.tracker.snapshot().active_foreground_count, 0)
        self.assertEqual(response["fairness"], "BEST_EFFORT_PRE_TURN")
        self.assertEqual(response["shadow"]["reply"], "SHADOW_REPLY")
        self.assertEqual(response["shadow"]["evidence"][0]["source_id"], "00123")
        self.assertNotIn("id", response["shadow"]["evidence"][0])
        self.assertEqual(response["evaluation"], {"status": "STORED", "votable": True})
        records = read_jsonl(self.directory / arena.LOG_NAME)
        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(record["personality_sha256"], sha256(b"FROZEN_PERSONALITY").hexdigest())
        self.assertNotIn("FROZEN_PERSONALITY", json.dumps(record))
        self.assertEqual(record["recent_message_ids"], [2, 3])
        self.assertEqual(set(path.name for path in self.directory.iterdir()), {arena.LOG_NAME})

    async def test_uses_final_recent_context_after_canonical_budget_pruning(self):
        self.rows[1]["content"] = "old pair " * 1100
        self.rows.append({"id": 4, "session_id": "s", "role": "user", "content": "new pair"})
        self.rows.append({"id": 5, "session_id": "s", "role": "assistant", "content": "new answer"})
        response = await self.run_turn()
        self.assertEqual(self.contexts[0]["recent_message_ids"], [4, 5])
        self.assertEqual(self.generated[0][1:], self.generated[1][1:])
        self.assertEqual(response["main"]["recent_message_ids"], [4, 5])

    async def test_storage_failure_keeps_successful_canonical_turn_and_shadow(self):
        with patch.object(arena, "append_arena_trial", side_effect=OSError("disk full")):
            response = await self.run_turn()
        self.assertEqual(response["main"]["reply"], "RAG_REPLY")
        self.assertEqual(response["main"]["status"]["persistence"], "NORMAL")
        self.assertEqual(response["shadow"]["reply"], "SHADOW_REPLY")
        self.assertEqual(response["evaluation"], {"status": "UNAVAILABLE", "votable": False})

    async def test_damaged_evaluation_log_does_not_invalidate_canonical_turn(self):
        path = self.directory / arena.LOG_NAME
        path.write_bytes(b'{"incomplete":')
        response = await self.run_turn()
        self.assertEqual(response["main"]["reply"], "RAG_REPLY")
        self.assertEqual(response["shadow"]["reply"], "SHADOW_REPLY")
        self.assertEqual(response["evaluation"], {"status": "UNAVAILABLE", "votable": False})
        self.assertEqual(path.read_bytes(), b'{"incomplete":')

    async def test_recall_timeout_or_unexpected_error_keeps_main_and_skips_shadow(self):
        for observation in (recall_result("TIMEOUT", []), RuntimeError("private details")):
            with self.subTest(observation=type(observation).__name__):
                self.recall.side_effect = observation if isinstance(observation, Exception) else None
                self.recall.return_value = observation
                self.generator.reset_mock()
                response = await self.run_turn()
                self.assertEqual(response["main"]["status"]["model"], "OK")
                self.assertEqual(self.generator.call_count, 1)
                self.assertEqual(response["shadow"]["status"], "SKIPPED")
                self.assertFalse(response["evaluation"]["votable"])
                self.assertNotIn("private details", json.dumps(response))

    async def test_successful_empty_recall_generates_without_history(self):
        self.recall.side_effect = None
        self.recall.return_value = recall_result(results=[])
        response = await self.run_turn()
        self.assertEqual(response["shadow"]["status"], "OK")
        self.assertEqual(response["shadow"]["evidence"], [])
        self.assertEqual(self.generated[1][0]["content"],
                         self.builder.call_args.kwargs["system_prompt"])
        self.assertTrue(self.generated[1][0]["content"].startswith("FROZEN_PERSONALITY\n\n"))

    async def test_shadow_error_is_contained_and_foreground_returns_idle(self):
        def generate(messages):
            if self.generator.call_count == 2:
                raise ModelClientError("MODEL_TIMEOUT", "private error")
            return self.generate(messages)

        self.generator.side_effect = generate
        response = await self.run_turn()
        self.assertEqual(response["main"]["reply"], "RAG_REPLY")
        self.assertEqual(response["shadow"]["status"], "ERROR")
        self.assertIsNone(response["shadow"]["reply"])
        self.assertFalse(response["evaluation"]["votable"])
        self.assertEqual(self.tracker.snapshot().active_foreground_count, 0)
        self.assertEqual(self.dense_calls, [[4, 5]])

    async def test_tokenizer_failure_in_shadow_keeps_canonical_reply(self):
        with patch.object(arena, "build_shadow_messages", side_effect=ValueError("tokenizer")):
            response = await self.run_turn()
        self.assertEqual(response["main"]["reply"], "RAG_REPLY")
        self.assertEqual(response["shadow"]["status"], "ERROR")
        self.assertEqual(self.generator.call_count, 1)

    async def test_failed_main_does_not_generate_shadow_or_sync_dense(self):
        self.generator.side_effect = ModelClientError("MODEL_TIMEOUT", "synthetic")
        response = await self.run_turn()
        self.assertEqual(response["main"]["status"]["overall"], "FAILED")
        self.assertEqual(response["shadow"]["error"], "CANONICAL_TURN_FAILED")
        self.assertEqual(self.generator.call_count, 1)
        self.assertEqual(self.dense_calls, [])
        self.assertEqual(self.rows[-1]["role"], "user")

    async def test_rag_failure_does_not_switch_canonical_provider(self):
        self.rag.side_effect = RuntimeError("synthetic RAG error")
        response = await self.run_turn()
        self.assertEqual(response["main"]["status"]["retrieval"], "DEGRADED")
        self.assertEqual(response["main"]["reply"], "RAG_REPLY")
        self.assertEqual(self.generated[0][0]["content"],
                         self.builder.call_args.kwargs["system_prompt"])
        self.assertTrue(self.generated[0][0]["content"].startswith("FROZEN_PERSONALITY\n\n"))
        self.assertEqual(response["shadow"]["status"], "OK")

    async def test_unchanged_h1_task_runs_after_response_with_duplicate_recall(self):
        tasks = BackgroundTasks()
        with patch.object(api, "build_chat_response", self.build_response):
            response = await api.post_arena_chat(arena.ArenaChatRequest(session_id="s", message="query"), tasks)
        self.assertEqual(len(tasks.tasks), 1)
        self.assertIs(tasks.tasks[0].func, hindsight_shadow.run_shadow_recall)
        turn = tasks.tasks[0].args[0]
        self.assertEqual((turn.user_message_id, turn.assistant_message_id), (4, 5))
        self.assertEqual(turn.query, "query")
        self.h1_async.assert_not_awaited()
        self.recall.assert_awaited_once()

        async def retain(turn):
            self.events.append("h1_retain")
            self.assertEqual(self.rows[-1]["content"], "RAG_REPLY")
            return {"status": "ACCEPTED"}

        self.h1_async.side_effect = retain
        with (patch.object(hindsight_shadow, "HINDSIGHT_ASYNC_RETAIN_ENABLED", True),
              patch.object(hindsight_shadow, "append_observation",
                           side_effect=lambda record: self.events.append(record.get("record_type", "comparison")))):
            await tasks()
        self.assertEqual(self.recall.await_count, 2)
        self.assertEqual(self.events[-4:], ["hindsight", "comparison", "h1_retain", "retain_outcome"])
        self.h1_retain.assert_not_awaited()
        self.assertEqual(response["shadow"]["reply"], "SHADOW_REPLY")


class CompositionTests(unittest.TestCase):
    def test_budget_trims_history_only_and_does_not_mutate_inputs(self):
        recent = [{"role": "user", "content": "recent"}, {"role": "assistant", "content": "answer"}]
        evidence = recall_result()["results"] * 2
        original = deepcopy((recent, evidence))
        baseline = ArenaTurnTests.tokens(working_context._compose_working_messages("SYS", [], [], "q"))
        messages, used, tokens = arena.build_shadow_messages(
            "SYS", recent, "q", evidence, count_tokens=ArenaTurnTests.tokens,
            historical_token_budget=0, input_token_budget=baseline + 12,
        )
        self.assertEqual(used, [])
        self.assertEqual(messages[1:-1], recent)
        self.assertLessEqual(tokens, baseline + 12)
        self.assertEqual((recent, evidence), original)

    def test_total_budget_discards_evidence_without_dropping_recent(self):
        recent = [{"role": "user", "content": "recent"}]
        messages, used, tokens = arena.build_shadow_messages(
            "SYS", recent, "q", recall_result()["results"], count_tokens=ArenaTurnTests.tokens,
            historical_token_budget=2048, input_token_budget=10,
        )
        self.assertEqual(used, [])
        self.assertEqual(messages[1:-1], recent)
        self.assertEqual(tokens, 10)

    def test_impossible_frozen_context_fails_instead_of_trimming_recent(self):
        with self.assertRaises(ValueError):
            arena.build_shadow_messages("SYS", [{"role": "user", "content": "long"}], "q", [],
                                        count_tokens=ArenaTurnTests.tokens,
                                        historical_token_budget=2048, input_token_budget=1)


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.directory = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.path = self.directory / arena.LOG_NAME
        for target, name, value in (
            (hindsight_shadow, "DATA_DIR", self.directory),
            (hindsight_shadow, "LAB_DATA_DIR", self.directory),
            (store, "DB_PATH", self.directory / "corvus.db"),
        ):
            self.stack.enter_context(patch.object(target, name, value))
        self.trial_id = str(uuid4())
        self.trial = {"schema_version": 1, "record_type": "trial",
                      "trial_id": self.trial_id, "votable": True}

    def vote(self, choice="rag"):
        return arena.record_arena_vote(arena.ArenaVoteRequest(trial_id=self.trial_id, choice=choice))

    def test_votes_append_and_latest_vote_is_effective(self):
        arena.append_arena_trial(self.trial)
        for choice in ("rag", "hindsight", "tie", "neither"):
            self.assertEqual(self.vote(choice)["choice"], choice)
        records = read_jsonl(self.path)
        self.assertEqual(records[0], self.trial)
        self.assertEqual(records[-1]["choice"], "neither")
        self.assertEqual(len(records), 5)
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)

    def test_daily_preferences_only_latest_actual_votes(self):
        arena.append_arena_trial(self.trial)
        self.assertEqual(arena.daily_preferences(date(2026, 10, 16), "America/Los_Angeles"),
                         {"date": "2026-10-16", "rag": 0, "hindsight": 0, "total_votes": 0})
        with patch.object(arena, "append_jsonl", side_effect=OSError("failed vote")):
            with self.assertRaises(HTTPException):
                self.vote("rag")
        self.assertEqual(arena.daily_preferences(date(2026, 10, 16), "America/Los_Angeles")["total_votes"], 0)
        second = str(uuid4())
        arena.append_arena_trial(dict(self.trial, trial_id=second))
        for trial_id, choice, timestamp in (
            (self.trial_id, "rag", "2026-10-16T07:30:00+00:00"),
            (self.trial_id, "hindsight", "2026-10-16T08:00:00+00:00"),
            (second, "rag", "2026-10-16T08:30:00+00:00"),
        ):
            with patch.object(arena, "_now", return_value=timestamp):
                arena.record_arena_vote(arena.ArenaVoteRequest(trial_id=trial_id, choice=choice))
        self.assertEqual(arena.daily_preferences(date(2026, 10, 16), "America/Los_Angeles"),
                         {"date": "2026-10-16", "rag": 1, "hindsight": 1, "total_votes": 2})
        with patch.object(arena, "_now", return_value="2026-10-17T07:30:00+00:00"):
            self.vote("tie")
        self.assertEqual(arena.daily_preferences(date(2026, 10, 16), "America/Los_Angeles"),
                         {"date": "2026-10-16", "rag": 1, "hindsight": 0, "total_votes": 1})
        self.assertEqual(arena.daily_preferences(date(2026, 10, 17), "America/Los_Angeles"),
                         {"date": "2026-10-17", "rag": 0, "hindsight": 0, "total_votes": 0})

    def test_daily_preferences_dst_fall_back_uses_local_vote_day(self):
        arena.append_arena_trial(self.trial)
        second = str(uuid4())
        arena.append_arena_trial(dict(self.trial, trial_id=second))
        for trial_id, choice, timestamp in (
            (self.trial_id, "rag", "2026-11-01T08:30:00+00:00"),  # 01:30 PDT
            (self.trial_id, "hindsight", "2026-11-01T09:30:00+00:00"),  # 01:30 PST
            (second, "rag", "2026-11-02T07:30:00+00:00"),  # Nov 1, 23:30 PST
        ):
            with patch.object(arena, "_now", return_value=timestamp):
                arena.record_arena_vote(arena.ArenaVoteRequest(trial_id=trial_id, choice=choice))
        zone = "America/Los_Angeles"
        self.assertEqual(arena.daily_preferences(date(2026, 11, 1), zone),
                         {"date": "2026-11-01", "rag": 1, "hindsight": 1, "total_votes": 2})
        self.assertEqual(arena.daily_preferences(date(2026, 11, 2), zone)["total_votes"], 0)
        with patch.object(arena, "_now", return_value="2026-11-02T08:30:00+00:00"):
            arena.record_arena_vote(arena.ArenaVoteRequest(trial_id=second, choice="hindsight"))
        self.assertEqual(arena.daily_preferences(date(2026, 11, 1), zone),
                         {"date": "2026-11-01", "rag": 0, "hindsight": 1, "total_votes": 1})
        self.assertEqual(arena.daily_preferences(date(2026, 11, 2), zone),
                         {"date": "2026-11-02", "rag": 0, "hindsight": 1, "total_votes": 1})

    def test_concurrent_votes_are_complete_and_linked(self):
        arena.append_arena_trial(self.trial)
        with ThreadPoolExecutor(max_workers=4) as executor:
            list(executor.map(lambda _: self.vote(), range(16)))
        records = read_jsonl(self.path)
        self.assertEqual(len(records), 17)
        self.assertTrue(all(row["trial_id"] == self.trial_id for row in records))

    def test_unknown_and_ineligible_trials_reject_votes(self):
        with self.assertRaises(HTTPException) as unknown:
            self.vote()
        self.assertEqual(unknown.exception.status_code, 404)
        arena.append_arena_trial(dict(self.trial, votable=False))
        before = self.path.read_bytes()
        with self.assertRaises(HTTPException) as ineligible:
            self.vote()
        self.assertEqual(ineligible.exception.status_code, 409)
        self.assertEqual(self.path.read_bytes(), before)

    def test_corruption_and_io_failure_are_503_without_repair(self):
        self.path.write_bytes(b'{"incomplete":')
        with self.assertRaises(HTTPException) as corrupt:
            self.vote()
        self.assertEqual(corrupt.exception.status_code, 503)
        self.assertEqual(self.path.read_bytes(), b'{"incomplete":')
        with patch.object(arena, "append_jsonl", side_effect=OSError("private path")):
            with self.assertRaises(HTTPException) as failed:
                self.vote()
        self.assertEqual(failed.exception.status_code, 503)
        self.assertNotIn("private", failed.exception.detail)

    def test_duplicate_trials_rejected(self):
        arena.append_arena_trial(self.trial)
        with self.assertRaises(ValueError):
            arena.append_arena_trial(self.trial)
        self.assertEqual(len(read_jsonl(self.path)), 1)

    def test_reuses_h1_lab_guard_and_rejects_other_canonical_store(self):
        with patch.object(hindsight_shadow, "_retain_eligible", return_value=False) as guard:
            with self.assertRaises(HTTPException) as error:
                arena.append_arena_trial(self.trial)
            guard.assert_called_once_with()
            self.assertEqual(error.exception.status_code, 404)
        with patch.object(store, "DB_PATH", self.directory / "other.db"):
            with self.assertRaises(HTTPException):
                self.vote()
        self.assertFalse(self.path.exists())


if __name__ == "__main__":
    unittest.main()
