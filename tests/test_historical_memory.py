"""Historical recall seam contracts with isolated SQLite and fake inference."""

from functools import partial
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from app.conversation_runtime import process_turn
from app.playground_api import build_chat_response
import app.working_context as working_context
import memory.historical_memory as historical_memory
import memory.hybrid_search as hybrid
import memory.store as store


def count_chars(messages):
    return sum(len(message["content"]) for message in messages)


class HistoricalMemoryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="corvus-recall-")
        self.addCleanup(temporary.cleanup)
        patcher = patch.object(store, "DB_PATH", Path(temporary.name) / "corvus.db")
        patcher.start()
        self.addCleanup(patcher.stop)
        store.init_db()
        self.old_id = store.add_message("old-session", "user", "historical fact")
        self.recent_user_id = store.add_message("current-session", "user", "prior question")
        self.recent_assistant_id = store.add_message("current-session", "assistant", "prior answer")
        self.current_id = store.add_message("current-session", "user", "current query")
        self.rows = store.load_recent_messages("current-session")
        self.old_row = store.load_recent_messages("old-session")[0]

    def context(self, **kwargs):
        return working_context.build_working_context(
            session_id="current-session",
            current_user_message_id=self.current_id,
            current_user_content="current query",
            system_prompt="SYS",
            count_tokens=count_chars,
            **kwargs,
        )

    def test_recall_delegates_arguments_and_returns_hybrid_rows_unchanged(self):
        rows = [dict(self.old_row, rrf_score=0.25, dense_rank=1, sparse_rank=2)]
        with patch.object(historical_memory, "hybrid_search", return_value=rows) as search:
            self.assertIs(historical_memory.recall("exact query", limit=7, candidate_limit=31), rows)
        search.assert_called_once_with("exact query", limit=7, candidate_limit=31)

    def test_default_context_reaches_hybrid_and_matches_prior_direct_path(self):
        dense_row = {
            "message_id": self.old_id,
            "session_id": self.old_row["session_id"],
            "role": self.old_row["role"],
            "content": self.old_row["content"],
            "created_at": self.old_row["created_at"],
            "distance": 0.1,
        }
        with (
            patch.object(hybrid, "search_dense_messages", return_value=[dense_row]) as dense,
            patch.object(hybrid, "sparse_search", return_value=[dict(self.old_row, score=-1)]) as sparse,
            patch.object(historical_memory, "hybrid_search", wraps=hybrid.hybrid_search) as provider,
        ):
            current = self.context()
            provider.assert_called_once_with("current query", limit=20, candidate_limit=20)
            dense.assert_called_once_with("current query", limit=20, session_id=None, role=None)
            sparse.assert_called_once_with("current query", limit=20, session_id=None, role=None)
            previous = self.context(search_fn=hybrid.hybrid_search)
        self.assertEqual(current, previous)
        self.assertEqual(current["retrieval_status"], "OK")
        self.assertEqual(current["historical_message_ids"], [self.old_id])

    def test_injected_provider_receives_query_and_excludes_current_and_recent(self):
        # Rank excluded rows first so incorrect selection cannot silently pass.
        provider = Mock(return_value=[self.rows[-1], *self.rows[:-1], self.old_row])
        with patch.object(historical_memory, "hybrid_search") as default:
            context = self.context(search_fn=provider, historical_limit=1)
        default.assert_not_called()
        provider.assert_called_once_with("current query", limit=4, candidate_limit=20)
        self.assertEqual(context["historical_evidence"], [self.old_row])
        self.assertEqual(context["historical_message_ids"], [self.old_id])
        self.assertEqual(context["recent_message_ids"], [self.recent_user_id, self.recent_assistant_id])
        self.assertEqual(context["messages"][0]["content"], (
            "SYS\n\nRelevant historical evidence:\n"
            f'[memory #{self.old_id} role=user] historical fact\n'
            "Use this evidence only when it is relevant to the current request."
        ))

    def test_provider_failure_keeps_sqlite_recent_context_and_usable_messages(self):
        provider = Mock(side_effect=RuntimeError("synthetic recall failure"))
        with patch.object(working_context, "load_recent_messages", wraps=store.load_recent_messages) as recent:
            context = self.context(search_fn=provider)
        recent.assert_called_once_with(
            session_id="current-session", limit=64, before_message_id=self.current_id,
        )
        self.assertEqual(context["retrieval_status"], "DEGRADED")
        self.assertEqual(context["retrieval_error"], "synthetic recall failure")
        self.assertEqual(context["historical_evidence"], [])
        self.assertEqual(context["historical_message_ids"], [])
        self.assertEqual(context["recent_messages"], self.rows[:-1])
        self.assertEqual(context["messages"], [
            {"role": "system", "content": "SYS"},
            {"role": "user", "content": "prior question"},
            {"role": "assistant", "content": "prior answer"},
            {"role": "user", "content": "current query"},
        ])

    def test_runtime_commits_user_before_recall_and_assistant_before_dense(self):
        # A second connection in recall proves canonical user commit is visible.
        for fails in (False, True):
            with self.subTest(provider_fails=fails):
                events = []
                session_id = "runtime-failure" if fails else "runtime-success"

                def provider(query, limit, candidate_limit):
                    events.append("recall")
                    self.assertEqual(query, "runtime query")
                    self.assertEqual(store.load_recent_messages(session_id)[0]["content"], query)
                    if fails:
                        raise RuntimeError("synthetic recall failure")
                    return [self.old_row]

                def generate(messages):
                    events.append("model")
                    self.assertEqual(messages[-1], {"role": "user", "content": "runtime query"})
                    return "runtime reply"

                def dense_sync(message_ids):
                    events.append("dense")
                    rows = store.load_recent_messages(session_id)
                    self.assertEqual([row["id"] for row in rows], message_ids)
                    self.assertEqual([(row["role"], row["content"]) for row in rows], [
                        ("user", "runtime query"), ("assistant", "runtime reply"),
                    ])

                result = process_turn(
                    session_id=session_id,
                    user_content="runtime query",
                    build_context_fn=partial(working_context.build_working_context, search_fn=provider),
                    count_tokens_fn=count_chars,
                    generate_fn=generate,
                    dense_sync_fn=dense_sync,
                    system_prompt_fn=lambda: "SYS",
                )
                self.assertEqual(events, ["recall", "model", "dense"])
                self.assertEqual(result["persistence_status"], "NORMAL")
                self.assertEqual(result["model_status"], "OK")
                self.assertEqual(result["retrieval_status"], "DEGRADED" if fails else "OK")
                response = build_chat_response(result)
                self.assertEqual(response["reply"], "runtime reply")
                self.assertEqual(response["historical_message_ids"], [] if fails else [self.old_id])
                self.assertEqual(response["retrieved_memories"], [] if fails else [dict(self.old_row, rank=1)])


if __name__ == "__main__":
    unittest.main()
