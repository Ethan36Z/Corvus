"""HTTP Arena contracts via in-process ASGI, without startup or live services."""

from copy import deepcopy
from datetime import date
import unittest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import httpx

from app import arena, hindsight_shadow, playground_api as api


def canonical():
    return {"session_id": "s", "user_message_id": 10, "assistant_message_id": 11,
            "reply": "main", "recent_message_ids": [], "historical_message_ids": [],
            "status": {"overall": "OK", "model": "OK", "persistence": "NORMAL",
                       "retrieval": "OK"}}


class ArenaApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.network = patch("socket.socket.connect", side_effect=AssertionError("No live network"))
        self.network.start()
        self.addCleanup(self.network.stop)
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=api.app), base_url="http://test")
        self.addAsyncCleanup(self.client.aclose)

    async def test_chat_schema_rejects_unsupported_or_nontext_input_without_work(self):
        valid = {"session_id": "s", "message": "q"}
        invalid = [{}, dict(valid, message=" "), dict(valid, session_id=" "),
                   dict(valid, message=[{"type": "text", "text": "q"}]),
                   dict(valid, message=3), dict(valid, session_id=3)]
        invalid.extend(dict(valid, **{key: value}) for key, value in (
            ("attachment_id", "x"), ("attachment_mode", "voice"), ("web_mode", "off"),
            ("files", []), ("messages", []), ("model", "other"),
        ))
        with patch.object(arena, "run_arena_turn", new=AsyncMock()) as run:
            for payload in invalid:
                with self.subTest(payload=payload):
                    response = await self.client.post("/api/arena/chat", json=payload)
                    self.assertEqual(response.status_code, 422)
            run.assert_not_awaited()

    async def test_outside_lab_fails_before_recall_runtime_or_storage(self):
        with (patch.object(hindsight_shadow, "_retain_eligible", return_value=False),
              patch.object(arena, "run_arena_turn", new=AsyncMock()) as run,
              patch.object(arena, "append_jsonl") as append):
            for path, payload in (
                ("/api/arena/chat", {"session_id": "s", "message": "q"}),
                ("/api/arena/vote", {"trial_id": str(uuid4()), "choice": "rag"}),
            ):
                self.assertEqual((await self.client.post(path, json=payload)).status_code, 404)
            run.assert_not_awaited()
            append.assert_not_called()

    async def test_storage_unavailable_still_returns_main_and_schedules_h1(self):
        main = canonical()
        outcome = {"main": main, "shadow": {"status": "OK", "reply": "shadow"},
                   "evaluation": {"status": "UNAVAILABLE", "votable": False}}
        worker = AsyncMock()
        with (patch.object(hindsight_shadow, "_retain_eligible", return_value=True),
              patch.object(hindsight_shadow, "lab_shadow_enabled", return_value=True),
              patch.object(arena, "run_arena_turn", new=AsyncMock(return_value=outcome)) as run,
              patch.object(hindsight_shadow, "run_shadow_recall", new=worker)):
            response = await self.client.post("/api/arena/chat", json={"session_id": " s ", "message": " q "})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["main"], main)
        self.assertEqual(response.json()["evaluation"]["status"], "UNAVAILABLE")
        self.assertEqual(run.await_args.args[0].message, "q")
        worker.assert_awaited_once()
        self.assertEqual(worker.await_args.args[0].assistant_message_id, 11)
        self.assertEqual(worker.await_args.args[0].query, "q")

    async def test_failed_canonical_turn_does_not_schedule_h1(self):
        main = canonical()
        main["status"]["model"] = "MODEL_TIMEOUT"
        main["assistant_message_id"] = None
        with (patch.object(hindsight_shadow, "_retain_eligible", return_value=True),
              patch.object(hindsight_shadow, "lab_shadow_enabled", return_value=True),
              patch.object(arena, "run_arena_turn", new=AsyncMock(return_value={"main": main})),
              patch.object(hindsight_shadow, "run_shadow_recall", new=AsyncMock()) as worker):
            response = await self.client.post("/api/arena/chat", json={"session_id": "s", "message": "q"})
        self.assertEqual(response.status_code, 200)
        worker.assert_not_awaited()

    async def test_runtime_exception_returns_hard_failure_without_retry_or_background(self):
        with (patch.object(hindsight_shadow, "_retain_eligible", return_value=True),
              patch.object(arena, "run_arena_turn", new=AsyncMock(side_effect=RuntimeError("synthetic"))) as run,
              patch.object(api, "schedule_shadow_recall") as schedule):
            response = await self.client.post("/api/arena/chat", json={"session_id": "s", "message": "q"})
        self.assertEqual(response.status_code, 500)
        run.assert_awaited_once()
        schedule.assert_not_called()

    async def test_vote_schema_and_response(self):
        trial_id = str(uuid4())
        with patch.object(arena, "record_arena_vote", return_value={"trial_id": trial_id, "choice": "tie"}) as vote:
            response = await self.client.post("/api/arena/vote", json={"trial_id": trial_id, "choice": "tie"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(vote.call_args.args[0].choice, "tie")
            for payload in ({"trial_id": trial_id, "choice": "llm"},
                            {"trial_id": "bad", "choice": "rag"},
                            {"trial_id": trial_id, "choice": "rag", "comment": "x"}):
                self.assertEqual((await self.client.post("/api/arena/vote", json=payload)).status_code, 422)
            self.assertEqual(vote.call_count, 1)

    async def test_daily_preferences_contract(self):
        expected = {"date": "2026-10-16", "rag": 2, "hindsight": 1, "total_votes": 3}
        route = next(r for r in api.app.routes if r.path == "/api/arena/preferences/daily")
        self.assertEqual(route.methods, {"GET"})
        with patch.object(arena, "daily_preferences", return_value=expected) as aggregate:
            response = api.get_arena_daily_preferences(date.fromisoformat("2026-10-16"),
                                                       "America/Los_Angeles")
        self.assertEqual(response, expected)
        self.assertEqual(aggregate.call_args.args[0].isoformat(), "2026-10-16")
        self.assertEqual(aggregate.call_args.args[1], "America/Los_Angeles")

    async def test_normal_chat_retains_original_forwarding_and_never_calls_arena(self):
        result = {"synthetic": "runtime result"}
        main = canonical()
        original = deepcopy(main)
        with (patch.object(api, "process_turn", return_value=result) as process,
              patch.object(api, "build_chat_response", return_value=main),
              patch.object(api, "schedule_shadow_recall") as schedule,
              patch.object(arena, "run_arena_turn", new=AsyncMock()) as run):
            response = await self.client.post("/api/chat", json={"session_id": "s", "message": " q "})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), original)
        process.assert_called_once_with(session_id="s", user_content="q", attachment_id=None,
                                        attachment_mode="vision", web_mode="auto")
        run.assert_not_awaited()
        self.assertEqual(schedule.call_args.args[1:], (main, "q"))


if __name__ == "__main__":
    unittest.main()
