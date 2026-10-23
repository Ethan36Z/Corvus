"""W1.1 request-time date note: offline, stubbed model and storage."""
from datetime import datetime, timezone
import os
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

from app import conversation_runtime as runtime
from app.conversation_runtime import current_date_note, process_turn
from app.runtime_config import _timezone_env


LA = ZoneInfo("America/Los_Angeles")


class Turn:
    def __init__(self):
        self.prompts = []
        self.generated = 0
        self.added = []

    def add(self, session, role, text):
        self.added.append(role)
        return len(self.added)

    def context(self, *, system_prompt, current_user_content, **kwargs):
        self.prompts.append(system_prompt)
        return {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": current_user_content},
            ],
            "recent_message_ids": [], "historical_message_ids": [],
            "input_tokens": 10, "retrieval_status": "OK",
        }

    def generate(self, messages):
        self.generated += 1
        return "ok"

    def run(self, now_fn, **kwargs):
        return process_turn(
            "date-session", "今天几号？",
            add_message_fn=self.add, build_context_fn=self.context,
            count_tokens_fn=lambda messages: 10, generate_fn=self.generate,
            dense_sync_fn=lambda ids: None, system_prompt_fn=lambda: "PERSONA",
            now_fn=now_fn, **kwargs,
        )


class CurrentDateNoteTests(unittest.TestCase):
    def test_note_has_date_weekday_and_configured_zone(self):
        note = current_date_note(datetime(2026, 10, 22, 9, 0, tzinfo=LA))
        self.assertIn("2026-10-22 (Thursday)", note)
        self.assertIn("America/Los_Angeles", note)
        self.assertIn("UTC-07:00", note)

    def test_same_instant_uses_the_configured_zone_date(self):
        instant = datetime(2026, 10, 22, 20, 0, tzinfo=timezone.utc)
        self.assertIn("2026-10-22", current_date_note(instant.astimezone(LA)))
        shanghai = instant.astimezone(ZoneInfo("Asia/Shanghai"))
        self.assertIn("2026-10-23 (Friday)", current_date_note(shanghai))

    def test_naive_time_is_rejected(self):
        with self.assertRaises(ValueError):
            current_date_note(datetime(2026, 10, 22, 9, 0))

    def test_timezone_env_is_explicit_and_validated(self):
        with patch.dict(os.environ, {"CORVUS_TIMEZONE": "Asia/Shanghai"}):
            self.assertEqual(_timezone_env("CORVUS_TIMEZONE", "UTC").key, "Asia/Shanghai")
        with patch.dict(os.environ, {"CORVUS_TIMEZONE": "Not/AZone"}):
            with self.assertRaises(ValueError):
                _timezone_env("CORVUS_TIMEZONE", "UTC")


class CurrentDateRuntimeTests(unittest.TestCase):
    def test_date_is_computed_per_request_after_personality(self):
        turn = Turn()
        days = iter([
            datetime(2026, 10, 22, 9, 0, tzinfo=LA),
            datetime(2026, 10, 23, 9, 0, tzinfo=LA),
        ])
        first = turn.run(lambda: next(days))
        second = turn.run(lambda: next(days))
        self.assertEqual(first["model_status"], "OK")
        self.assertEqual(second["model_status"], "OK")
        self.assertTrue(turn.prompts[0].startswith("PERSONA\n\nCurrent date: 2026-10-22"))
        self.assertTrue(turn.prompts[1].startswith("PERSONA\n\nCurrent date: 2026-10-23"))
        # One generation and one user/assistant pair per turn.
        self.assertEqual(turn.generated, 2)
        self.assertEqual(turn.added, ["user", "assistant", "user", "assistant"])

    def test_default_clock_uses_configured_zone(self):
        turn = Turn()
        with patch.object(runtime, "TIMEZONE", ZoneInfo("Asia/Tokyo")):
            turn.run(runtime._current_time)
        self.assertIn("time zone Asia/Tokyo (UTC+09:00)", turn.prompts[0])

    def test_invalid_clock_fails_before_generation(self):
        turn = Turn()
        result = turn.run(lambda: datetime(2026, 10, 22, 9, 0))
        self.assertEqual(result["model_status"], "CONTEXT_INVALID")
        self.assertEqual(turn.generated, 0)
        self.assertEqual(turn.added, ["user"])


if __name__ == "__main__":
    unittest.main()
