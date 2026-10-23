"""W2 offline tests: timings (W2-a), retrieval reliability (W2-r),
evidence relevance (W2-b) and multi-source budget (W2-c)."""
from dataclasses import replace
import json
from pathlib import Path
import sys
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))

from test_web_acceptance import Harness, controlled
from app import model_client
from app.web_mvp import prepare_web_mvp


class TimingTests(unittest.TestCase):
    def test_retrieval_stages_are_timed_without_changing_the_result(self):
        h = Harness([controlled()])
        prepared = prepare_web_mvp("concurrent.futures", provider_builder=h.provider,
                                   fetch_search_result_fn=h.fetch, extract_web_page_fn=h.extract)
        t = prepared.timings
        self.assertEqual(prepared.outcome, "GROUNDED_ANSWER")
        self.assertEqual(len(t["search_ms"]), 1)
        self.assertGreaterEqual(len(t["fetch_ms"]), 1)
        self.assertGreaterEqual(len(t["extract_ms"]), 1)
        for key in ("retrieval_ms", "evidence_ms"):
            self.assertGreaterEqual(t[key], 0)
        self.assertNotIn("concurrent", json.dumps(t))  # numbers only, no content

    def test_model_client_keeps_server_timings_per_thread(self):
        body = {"choices": [{"message": {"content": "ok"}}],
                "timings": {"prompt_ms": 120.0, "predicted_ms": 380.0, "prompt_n": 50, "predicted_n": 20}}
        with patch.object(model_client, "_post_json", return_value=body):
            self.assertEqual(model_client.generate_chat_completion([{"role": "user", "content": "x"}]), "ok")
        self.assertEqual(model_client.take_last_generation_timings()["predicted_ms"], 380.0)
        self.assertIsNone(model_client.take_last_generation_timings())  # taken once

    def test_runtime_separates_model_compute_from_waiting(self):
        from app.conversation_runtime import process_turn
        evidence = NS(evidence_ref="web_1", excerpt="Qwen3 8B runs on 12 GB GPUs.", ordinal=0,
                      source_url="https://example.com/a", source_title=None)
        mvp = NS(status="READY", outcome="GROUNDED_ANSWER", evidence_status="EVIDENCE_RETRIEVED",
                 missing=("requirements_not_specified",), retrieval_status="RETRIEVAL_SUCCESS",
                 deterministic_reply=None, selected_result_id="r", answer_basis="RETRIEVED_EVIDENCE",
                 used_web_evidence=(evidence,), timings={"search_ms": [5.0], "retrieval_ms": 9.0},
                 sources=(NS(url="https://example.com/a", identity="i", refs=("web_1",),
                             verification="FETCHED_EXTRACTED"),))

        def generate(messages):
            model_client._LAST_GENERATION.timings = {"prompt_ms": 10.0, "predicted_ms": 20.0,
                                                     "prompt_n": 7, "predicted_n": 3}
            return "Qwen3 8B fits [web_1]."
        ids = iter([1, 2])
        with patch("app.web_mvp.source_section", return_value=""):
            result = process_turn(
                "s", "q", add_message_fn=lambda *a: next(ids),
                build_context_fn=lambda **k: {"messages": [], "recent_message_ids": [],
                                              "historical_message_ids": [], "input_tokens": 1},
                count_tokens_fn=lambda m: 1, dense_sync_fn=lambda ids: None,
                system_prompt_fn=lambda: "P", generate_fn=generate,
                record_web_evidence_batch_fn=lambda *a: [0], web_mode="on", web_mvp_enabled=True,
                prepare_web_mvp_fn=lambda *a, **k: mvp,
                pack_web_evidence_fn=lambda ev: NS(content="W", evidence_refs=("web_1",),
                                                   evidence_chars=1, packed_chars=1))
        t = result["web_timings_ms"]
        self.assertEqual(t["search_ms"], [5.0])
        self.assertEqual(t["model_compute_ms"], 30.0)
        self.assertEqual(t["model_wait_ms"], max(0.0, round(t["generation_ms"] - 30.0, 1)))
        self.assertEqual((t["prompt_tokens"], t["completion_tokens"]), (7, 3))
        for key in ("context_ms", "generation_ms", "answer_ready_ms"):
            self.assertIn(key, t)


class RetrievalReliabilityTests(unittest.TestCase):
    def test_version_questions_are_not_day_restricted_news(self):
        from app.web_search_routing import build_search_plan
        for query in ("Node.js 最新的 LTS 版本是多少？", "最新的 macOS 正式版是哪个？",
                      "latest Python release"):
            plan = build_search_plan(query)
            self.assertFalse(plan.news_intent, query)
            self.assertTrue(all(a.time_range is None for a in plan.attempts), query)
        self.assertTrue(build_search_plan("洛杉矶 今日 新闻").news_intent)

    def test_every_plan_ends_with_a_bounded_broad_fallback(self):
        from app.web_search_routing import MAX_SEARCH_ATTEMPTS, build_search_plan
        for query in ("洛杉矶 今日 新闻", "uv 和 pip 有什么区别", "OpenAI latest news", "Qwen3.5 llama.cpp"):
            plan = build_search_plan(query)
            last = plan.attempts[-1]
            self.assertEqual((last.category, last.time_range, last.engine_bang), ("general", None, None))
            self.assertLessEqual(len(plan.attempts), MAX_SEARCH_ATTEMPTS)

    def test_request_wording_is_removed_from_the_search_query(self):
        from app.web_mvp import clean_search_query as clean
        self.assertEqual(clean("请联网核实你刚才关于 Python 3.14 是否发布的说法。"), "Python 3.14 是否发布")
        self.assertEqual(clean("帮我查一下 uv 和 pip 有什么区别"), "uv 和 pip 有什么区别")
        self.assertEqual(clean("Please look up the latest Node.js LTS"), "the latest Node.js LTS")
        # Too little topic left: keep the original rather than search for nothing.
        self.assertEqual(clean("联网核实一下你刚才说的"), "联网核实一下你刚才说的")
        self.assertEqual(clean("Node.js 最新的 LTS 版本是多少？"), "Node.js 最新的 LTS 版本是多少？")

    def test_failed_first_attempt_then_fallback_success_is_not_partial_failure(self):
        p = controlled()
        attempts = []

        def builder(attempt):
            attempts.append(attempt.name)
            fixture = Harness([p]).provider(attempt)
            if len(attempts) == 1:
                class Failing:
                    name = "failing"
                    def search(self, query, *, limit):
                        raise RuntimeError("DDGS: No results found")
                return Failing()
            return fixture
        h = Harness([p])
        prepared = prepare_web_mvp("concurrent.futures 新特性", provider_builder=builder,
                                   fetch_search_result_fn=h.fetch, extract_web_page_fn=h.extract)
        self.assertGreaterEqual(len(attempts), 2)
        self.assertEqual(prepared.outcome, "GROUNDED_ANSWER")
        self.assertNotIn("provider_partial_failure", prepared.missing)
        self.assertEqual(len(prepared.timings["search_ms"]), len(attempts))


if __name__ == "__main__":
    unittest.main()
