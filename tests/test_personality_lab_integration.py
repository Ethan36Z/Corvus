"""P0.4: current Lab runtime/Arena, stubbed model/storage; never live I/O."""
from datetime import datetime
from hashlib import sha256
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).parent))
import test_memory_arena as fixture
from app import arena, conversation_runtime, playground_api
from personality import PersonalityConfig, compile_personality_system_prompt


PROFILE_ENV = {
    "CORVUS_PERSONALITY_ENABLED": "TRUE",
    "CORVUS_PERSONALITY_PROFILE": "corvus-companion",
    "CORVUS_PERSONALITY_VERSION": "0.1.1",
}
FROZEN_NOW = datetime(2026, 10, 22, 12, 0, tzinfo=ZoneInfo("America/Los_Angeles"))


class LabPersonalityIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Reuse the existing fixture without inheriting/re-running its test suite.
        self.f = fixture.ArenaTurnTests("test_real_runtime_order_same_context_model_and_zero_shadow_writes")
        await self.f.asyncSetUp()
        self.addCleanup(self.f.doCleanups)
        self.f.personality.side_effect = compile_personality_system_prompt
        self.f.runtime.side_effect = lambda **kwargs: conversation_runtime.process_turn(
            **kwargs, add_message_fn=self.f.add, dense_sync_fn=self.f.dense,
            now_fn=lambda: FROZEN_NOW,
        )

    def normal_turn(self):
        before = len(self.f.rows)
        result = conversation_runtime.process_turn(
            "s", "query", add_message_fn=self.f.add,
            build_context_fn=self.f.builder, count_tokens_fn=self.f.tokens,
            generate_fn=self.f.generate, dense_sync_fn=self.f.dense,
            now_fn=lambda: FROZEN_NOW,
        )
        self.assertEqual(result["model_status"], "OK")
        self.assertEqual(len(self.f.rows), before + 2)
        return self.f.builder.call_args.kwargs["system_prompt"]

    def legacy(self):
        return compile_personality_system_prompt(config=PersonalityConfig())

    def assert_single_identity_and_rules(self, prompt):
        self.assertEqual(prompt.count("You are Corvus"), 1)
        self.assertEqual(prompt.count("Personality profile:"), 1)
        for line in self.legacy().splitlines():
            if line.startswith("- "):
                self.assertEqual(prompt.count(line[2:]), 1, line)
        self.assertIn("corvus-companion@0.1.1", prompt)
        self.assertIn("gender-neutral", prompt)
        self.assertIn("existing system and safety instructions take precedence", prompt)

    async def test_disabled_keeps_legacy_and_existing_date_note_exactly(self):
        with patch.dict(os.environ, {"CORVUS_PERSONALITY_ENABLED":"FALSE"}):
            with patch("personality.runtime.load_personality_profile", side_effect=AssertionError("disabled loaded profile")):
                actual = self.normal_turn()
        expected = self.legacy()+"\n\n"+conversation_runtime.current_date_note(FROZEN_NOW)
        self.assertEqual(actual, expected)

    async def test_enabled_uses_existing_default_callback_without_duplicates(self):
        with patch.dict(os.environ, PROFILE_ENV):
            expected = compile_personality_system_prompt()+"\n\n"+conversation_runtime.current_date_note(FROZEN_NOW)
            actual = self.normal_turn()
        self.assertEqual(actual, expected)
        self.assert_single_identity_and_rules(actual)
        self.assertTrue(actual.startswith(self.legacy()+"\n\n"))

    async def test_missing_and_invalid_selection_preserve_legacy(self):
        cases = [
            {"CORVUS_PERSONALITY_ENABLED":"TRUE"},
            {**PROFILE_ENV,"CORVUS_PERSONALITY_VERSION":"99.0.0"},
            {**PROFILE_ENV,"CORVUS_PERSONALITY_PROFILE":"../experimental"},
            {**PROFILE_ENV,"CORVUS_PERSONALITY_ENABLED":"invalid"},
        ]
        for env in cases:
            with self.subTest(env=env), patch.dict(os.environ, env, clear=True):
                actual = self.normal_turn()
                self.assertEqual(actual,self.legacy()+"\n\n"+conversation_runtime.current_date_note(FROZEN_NOW))

    async def assert_arena_uses_same_frozen_prompt(self, mutate_after_main=False):
        expected = compile_personality_system_prompt()+"\n\n"+conversation_runtime.current_date_note(FROZEN_NOW)
        if mutate_after_main:
            def generate(messages):
                result = self.f.generate(messages)
                if len(self.f.generated) == 1:
                    os.environ["CORVUS_PERSONALITY_VERSION"] = "99.0.0"
                    os.environ["CORVUS_PERSONALITY_ENABLED"] = "FALSE"
                return result
            self.f.generator.side_effect = generate
        response = await self.f.run_turn()
        self.f.personality.assert_called_once_with()
        self.assertEqual(len(self.f.generated), 2)
        main, shadow = self.f.generated
        captured_prompt = self.f.builder.call_args.kwargs["system_prompt"]
        self.assertEqual(captured_prompt, expected)
        # Evidence differs by design; compare the exact shared pre-evidence prefix.
        self.assertEqual(main[0]["content"].split("\n\nRelevant historical evidence:")[0],
                         shadow[0]["content"].split("\n\nRelevant historical evidence:")[0])
        self.assertTrue(main[0]["content"].startswith(expected))
        self.assertTrue(shadow[0]["content"].startswith(expected))
        self.assertEqual(main[1:],shadow[1:])
        self.assertEqual(response["personality_sha256"],sha256(expected.split("\n\nCurrent date:")[0].encode()).hexdigest())
        self.assertEqual([r["content"] for r in self.f.rows[-2:]],["query","RAG_REPLY"])
        self.assertEqual(self.f.dense_calls,[[4,5]])
        self.f.h1_retain.assert_not_awaited();self.f.h1_async.assert_not_awaited()
        self.assertEqual(response["evaluation"],{"status":"STORED","votable":True})
        return captured_prompt

    async def test_arena_enabled_freezes_one_profile_for_both_arms(self):
        with patch.dict(os.environ,PROFILE_ENV):
            actual = await self.assert_arena_uses_same_frozen_prompt()
        self.assert_single_identity_and_rules(actual)

    async def test_arena_config_change_between_arms_cannot_change_personality(self):
        with patch.dict(os.environ,PROFILE_ENV):
            await self.assert_arena_uses_same_frozen_prompt(mutate_after_main=True)

    async def test_arena_invalid_profile_uses_legacy(self):
        with patch.dict(os.environ,{**PROFILE_ENV,"CORVUS_PERSONALITY_VERSION":"missing"}):
            actual = await self.assert_arena_uses_same_frozen_prompt()
        self.assertEqual(actual,self.legacy()+"\n\n"+conversation_runtime.current_date_note(FROZEN_NOW))

    async def test_arena_disabled_profile_uses_legacy(self):
        with patch.dict(os.environ,{"CORVUS_PERSONALITY_ENABLED":"FALSE"}):
            actual = await self.assert_arena_uses_same_frozen_prompt()
        self.assertEqual(actual,self.legacy()+"\n\n"+conversation_runtime.current_date_note(FROZEN_NOW))

    async def test_api_has_no_client_control_for_profile_or_model_settings(self):
        fields = set(playground_api.ChatRequest.model_fields)
        self.assertFalse(fields & {"personality_profile","personality_version","system_prompt","enable_thinking"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
