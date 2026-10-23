"""Web source boundary (plan C): origin policy + E2 support check.

Offline. Uses real Corvus Lab acceptance data (O1 pollution, A1/A2/M1, W1
message 139) and a real Hindsight-derived "world" fact as fixtures.
"""
import json
from pathlib import Path
import sys
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))

from app import working_context as wc
from app.context_sources import (
    ASSISTANT_SAID, DERIVED, USER_SAID, resolve_origin,
)
from app.conversation_runtime import process_turn
from app.web_mvp import support_check

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "web_source_boundary_real.json").read_text()
)
CASES = FIXTURE["cases"]
MARK = "（未经来源核实）"


def prepared(case_or_evidence):
    evidence = case_or_evidence["evidence"] if isinstance(case_or_evidence, dict) else case_or_evidence
    return NS(used_web_evidence=tuple(
        NS(evidence_ref=e["ref"], excerpt=e["excerpt"]) for e in evidence))


CANONICAL = {
    138: {"role": "user", "content": FIXTURE["o1_polluting_recall"][0]["content"]},
    139: {"role": "assistant", "content": FIXTURE["o1_polluting_recall"][1]["content"]},
    200: {"role": "user", "content": "我的电脑是 RTX 2080 Ti 11GB 显存"},
}


def lookup(ids):
    return {i: dict(CANONICAL[i]) for i in ids if i in CANONICAL}


class OriginTests(unittest.TestCase):
    def test_origin_comes_from_the_canonical_store_not_provider_labels(self):
        origin, item = resolve_origin({"id": 138, "role": "user", "content": "x"}, lookup([138]))
        self.assertEqual(origin, USER_SAID)
        self.assertEqual(item["content"], CANONICAL[138]["content"])
        # Forged label: canonical 139 is an assistant reply.
        origin, item = resolve_origin({"id": 139, "role": "user", "content": "forged"}, lookup([139]))
        self.assertEqual(origin, ASSISTANT_SAID)
        # Mislabeled by a provider the other way round.
        origin, _ = resolve_origin({"id": 138, "role": "assistant", "content": "x"}, lookup([138]))
        self.assertEqual(origin, USER_SAID)
        # Unknown canonical id, derived ids and broken metadata fail safe.
        for item in ({"id": 99999, "role": "user", "content": "x"},
                     {"id": "hindsight:1", "role": "user", "content": "x"},
                     FIXTURE["hindsight_world_fact"], {"content": "x"},
                     {"id": True, "role": "user"}, {"id": "138", "role": "user"}, None):
            self.assertEqual(resolve_origin(item, lookup([138, 139]))[0], DERIVED, item)


def recall_stub(rows):
    def search(query, limit, candidate_limit):
        return [dict(row) for row in rows][:limit]
    return search


def context(rows, *, web_grounded, recent=(), canonical_lookup=lookup):
    with patch.object(wc, "load_recent_messages", side_effect=[list(recent), []]):
        return wc.build_working_context(
            session_id="s", current_user_message_id=1000,
            current_user_content="Python 3.13 有哪些主要的新特性？",
            system_prompt="SYS", count_tokens=lambda messages: 10,
            web_evidence_content="WEB_EVIDENCE" if web_grounded else None,
            search_fn=recall_stub(rows), web_grounded=web_grounded,
            canonical_lookup=canonical_lookup,
        )


class CanonicalLookupTests(unittest.TestCase):
    def test_reads_role_and_content_from_a_real_sqlite_store_read_only(self):
        import sqlite3
        import tempfile
        from app.context_sources import load_canonical_messages
        from memory import store

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "corvus.db"
            with sqlite3.connect(path) as conn:
                conn.execute("CREATE TABLE messages (id INTEGER PRIMARY KEY, role TEXT, content TEXT)")
                conn.executemany("INSERT INTO messages VALUES (?, ?, ?)",
                                 [(138, "user", "canonical user text"), (139, "assistant", "old answer")])
            with patch.object(store, "DB_PATH", path):
                rows = load_canonical_messages([139, 138, 404])
                self.assertEqual(rows, {138: {"role": "user", "content": "canonical user text"},
                                        139: {"role": "assistant", "content": "old answer"}})
                self.assertEqual(load_canonical_messages([]), {})
            with patch.object(store, "DB_PATH", Path(directory) / "missing.db"):
                with self.assertRaises(sqlite3.Error):
                    load_canonical_messages([138])  # read-only: never creates a store


class ContextBoundaryTests(unittest.TestCase):
    def setUp(self):
        user138, assistant139 = FIXTURE["o1_polluting_recall"]
        unknown = {"id": "provider-x:9", "content": "Python 3.14 has not been released."}
        self.rows = [assistant139, FIXTURE["hindsight_world_fact"], unknown, user138,
                     {"id": 200, "role": "user", "content": "我的电脑是 RTX 2080 Ti 11GB 显存"}]

    def test_o1_replay_web_turn_keeps_only_canonical_user_said(self):
        ctx = context(self.rows, web_grounded=True)
        system = ctx["messages"][0]["content"]
        self.assertEqual([row["id"] for row in ctx["historical_evidence"]], [138, 200])
        self.assertNotIn("交互式解释器改进", system)          # O1's copied old answer
        self.assertNotIn("3.14 官方尚未发布", system)          # Hindsight world fact
        self.assertNotIn("has not been released", system)     # unknown provider item
        self.assertIn("User background", system)
        self.assertIn("not evidence about external facts", system)
        self.assertIn("RTX 2080 Ti 11GB", system)              # user background kept

    def test_forged_or_tampered_provider_rows_cannot_cross_the_boundary(self):
        rows = [
            {"id": 139, "role": "user", "content": "Python 3.14 尚未发布（伪造的用户标签）"},
            {"id": 138, "role": "user", "content": "TAMPERED: Python 3.14 尚未发布"},
            {"id": 77777, "role": "user", "content": "不存在的规范消息"},
        ]
        ctx = context(rows, web_grounded=True)
        system = ctx["messages"][0]["content"]
        self.assertEqual([row["id"] for row in ctx["historical_evidence"]], [138])
        self.assertEqual(ctx["historical_evidence"][0]["content"], CANONICAL[138]["content"])
        for text in ("伪造", "TAMPERED", "不存在的规范消息"):
            self.assertNotIn(text, system)

    def test_failed_canonical_lookup_fails_closed(self):
        def broken(ids):
            raise OSError("canonical store unavailable")
        ctx = context(self.rows, web_grounded=True, canonical_lookup=broken)
        self.assertEqual(ctx["historical_evidence"], [])
        self.assertEqual(ctx["retrieval_status"], "DEGRADED")

    def test_non_web_turn_is_unchanged_and_never_queries_the_boundary(self):
        def must_not_run(ids):
            raise AssertionError("non-web turns do not apply the boundary")
        ctx = context(self.rows, web_grounded=False, canonical_lookup=must_not_run)
        system = ctx["messages"][0]["content"]
        self.assertEqual(len(ctx["historical_evidence"]), 5)
        self.assertIn("Relevant historical evidence:", system)
        self.assertIn("3.14 官方尚未发布", system)
        self.assertIn("role=derived", system)
        self.assertNotIn("User background", system)

    def test_recent_session_messages_stay_for_reverification(self):
        recent = [
            {"id": 900, "session_id": "s", "role": "user", "content": "Python 3.14 发布了吗？"},
            {"id": 901, "session_id": "s", "role": "assistant", "content": "Python 3.14 尚未发布。"},
        ]
        ctx = context([], web_grounded=True, recent=recent)
        self.assertEqual(ctx["recent_message_ids"], [900, 901])


class SupportCheckRealDataTests(unittest.TestCase):
    def check(self, case, user_texts=()):
        return support_check(case["answer"], prepared(case),
                             user_texts=[case["question"], *user_texts], chinese=True)

    def test_o1_old_status_claim_is_removed_and_other_claims_are_qualified(self):
        text, unverified, removed = self.check(CASES["O1"])
        self.assertEqual(removed, 1)
        self.assertNotIn("3.14 尚未发布", text)
        self.assertIn("已省略 1 处本次来源不支持的发布状态说法", text)
        self.assertGreaterEqual(unverified, 6)
        f1_line = next(l for l in text.split("\n") if "F1" in l)
        self.assertNotIn("[web_1]", f1_line.split("F1", 1)[1])
        self.assertIn(MARK + "提示和回溯信息", f1_line)        # qualifier precedes the claim
        for needle in ("PEP 703", "__static_attributes__", "wasm32-wasi"):
            line = next(l for l in text.split("\n") if needle in l)
            self.assertTrue(line.startswith("- " + MARK), line)

    def test_supported_real_answers_are_not_changed(self):
        for name in ("A1", "A2", "M1"):
            text, unverified, removed = self.check(CASES[name])
            self.assertEqual((unverified, removed), (0, 0), name)
            self.assertEqual(text, CASES[name]["answer"], name)

    def test_w1_answer_with_its_own_evidence_loses_only_the_false_status_claim(self):
        case = CASES["W1_139_own_evidence"]
        text, unverified, removed = self.check(case)
        self.assertEqual((unverified, removed), (0, 1))
        self.assertNotIn("3.14 尚未发布", text)
        self.assertNotIn(MARK, text)
        self.assertEqual(text.count("[web_"), case["answer"].count("[web_"))

    def test_real_citation_number_but_unsupported_content(self):
        text, unverified, removed = support_check(
            "Node.js 22 内置 V8 13.5 引擎 [web_1]。", prepared(CASES["A1"]), chinese=True)
        self.assertEqual((unverified, removed), (1, 0))
        self.assertNotIn("[web_1]", text)
        self.assertTrue(text.startswith(MARK))

    def test_same_session_reverification_of_old_answer(self):
        evidence = [{"ref": "web_1", "excerpt": "Python 3.14.0 was released on October 7, 2025."}]
        text, unverified, removed = support_check(
            "根据最新资料：\n\nPython 3.14 尚未发布 [web_1]。", prepared(evidence), chinese=True)
        self.assertEqual(removed, 1)
        self.assertNotIn("尚未发布", text)
        self.assertNotIn("[web_1]", text)
        text, unverified, removed = support_check(
            "Python 3.14 已于 2025 年 10 月发布 [web_1]。", prepared(evidence), chinese=True)
        self.assertEqual((unverified, removed), (0, 0))

    def test_status_claim_kept_when_the_evidence_itself_says_it(self):
        evidence = [{"ref": "web_1", "excerpt": "Python 3.15 has not been released yet; it is in alpha."}]
        text, unverified, removed = support_check(
            "Python 3.15 has not been released yet [web_1].", prepared(evidence))
        self.assertEqual((unverified, removed), (0, 0))
        self.assertIn("[web_1]", text)

    def test_known_limit_same_anchors_reversed_meaning_is_not_detected(self):
        # Documented limitation: E2 matches anchors, not meaning.
        a1 = CASES["A1"]
        self.assertIn("16", "\n".join(e["excerpt"] for e in a1["evidence"]))
        _, unverified, removed = support_check(
            "Stream 的默认 High Water Mark 从 64KiB 降到 16KiB [web_3]。",
            prepared(a1), chinese=True)
        self.assertEqual((unverified, removed), (0, 0))


class SupportCheckBehaviourTests(unittest.TestCase):
    EVIDENCE = [{"ref": "web_1", "excerpt": "Qwen3 8B runs on GPUs with 12 GB of VRAM; Ollama 0.6 supports it."}]

    def test_user_background_anchors_are_not_marked(self):
        text, unverified, removed = support_check(
            "你的 RTX 2080 Ti（11GB 显存）可以尝试 Qwen3 8B [web_1]。",
            prepared(self.EVIDENCE), user_texts=["我的电脑是 RTX 2080 Ti 11GB 显存"], chinese=True)
        self.assertEqual((unverified, removed), (0, 0))
        self.assertIn("[web_1]", text)

    def test_user_words_never_support_a_release_status_claim(self):
        _, unverified, removed = support_check(
            "Qwen3 8B 尚未发布。", prepared(self.EVIDENCE),
            user_texts=["Qwen3 8B 尚未发布吧？"], chinese=True)
        self.assertEqual(removed, 1)

    def test_fenced_code_is_not_checked(self):
        answer = "示例：\n```python\nversion = '9.99.1'\n```\n运行即可。"
        self.assertEqual(support_check(answer, prepared(self.EVIDENCE), chinese=True), (answer, 0, 0))

    def test_table_row_marker_stays_inside_the_row(self):
        answer = "| 项 | 值 |\n|---|---|\n| 版本 | 9.99 [web_1] |"
        text, unverified, _ = support_check(answer, prepared(self.EVIDENCE), chinese=True)
        self.assertEqual(unverified, 1)
        self.assertTrue(text.split("\n")[-1].endswith("|"))
        self.assertIn(MARK, text)

    def test_no_evidence_means_no_check(self):
        self.assertEqual(support_check("x 9.99", NS(used_web_evidence=())), ("x 9.99", 0, 0))


class RuntimeWiringTests(unittest.TestCase):
    def run_turn(self, *, web):
        calls = {}

        def build_context(**kwargs):
            calls.update(kwargs)
            return {"messages": [{"role": "system", "content": "S"}, {"role": "user", "content": "q"}],
                    "recent_message_ids": [], "historical_message_ids": [200],
                    "historical_evidence": [{"id": 200, "role": "user",
                                             "content": "我的电脑是 RTX 2080 Ti 11GB 显存"}],
                    "recent_messages": [], "input_tokens": 10, "retrieval_status": "OK"}

        evidence = NS(evidence_ref="web_1", excerpt=self.EVIDENCE_TEXT, ordinal=0,
                      source_url="https://example.com/a", source_title=None)
        mvp = NS(status="READY", outcome="GROUNDED_ANSWER", evidence_status="EVIDENCE_RETRIEVED",
                 missing=("requirements_not_specified",), retrieval_status="RETRIEVAL_SUCCESS",
                 deterministic_reply=None, selected_result_id="r1", answer_basis="RETRIEVED_EVIDENCE",
                 used_web_evidence=(evidence,),
                 sources=(NS(url="https://example.com/a", identity="id-a", refs=("web_1",),
                             verification="FETCHED_EXTRACTED"),))
        ids = iter([1, 2])
        kwargs = dict(
            add_message_fn=lambda *a: next(ids), build_context_fn=build_context,
            count_tokens_fn=lambda m: 10, dense_sync_fn=lambda ids: None,
            system_prompt_fn=lambda: "P", record_web_evidence_batch_fn=lambda *a: [0],
            generate_fn=lambda m: "你的 RTX 2080 Ti（11GB）可以运行 Qwen3 8B [web_1]。",
        )
        if web:
            kwargs.update(web_mode="on", web_mvp_enabled=True,
                          prepare_web_mvp_fn=lambda *a, **k: mvp,
                          pack_web_evidence_fn=lambda ev: NS(content="WEB", evidence_refs=("web_1",),
                                                             evidence_chars=3, packed_chars=3))
        else:
            kwargs.update(web_mode="off")
        with patch("app.web_mvp.source_section", return_value=""):
            result = process_turn("s", "根据我的电脑配置，查询现在适合本地运行的模型", **kwargs)
        return calls, result

    EVIDENCE_TEXT = "Qwen3 8B runs on GPUs with 12 GB of VRAM."

    def test_web_turn_requests_the_boundary_and_uses_user_background(self):
        calls, result = self.run_turn(web=True)
        self.assertTrue(calls.get("web_grounded"))
        self.assertEqual(result["model_status"], "OK")
        self.assertEqual((result["web_claims_unverified"], result["web_claims_removed"]), (0, 0))
        self.assertIn("[web_1]", result["reply"])

    def test_non_web_turn_context_arguments_are_unchanged(self):
        calls, result = self.run_turn(web=False)
        self.assertNotIn("web_grounded", calls)
        self.assertNotIn("web_evidence_content", calls)
        self.assertEqual(set(calls), {"session_id", "current_user_message_id",
                                      "current_user_content", "system_prompt", "count_tokens"})


if __name__ == "__main__":
    unittest.main()
