"""Small offline contracts for the existing personality package's version selector."""
from dataclasses import FrozenInstanceError
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from personality import (
    PersonalityConfig, PersonalityProfileError, compile_personality_system_prompt,
    load_personality_profile, render_personality_instructions,
)
from personality import profiles


LEGACY_SHA256 = "1c146488ec8fc5a5993e66f2c33f130d06b747aecf75c5e4a5417b36882110e9"
BASE = "  Existing system safety instructions.\nDo not disclose secrets.\n"
SELECTED = PersonalityConfig(True, "corvus-companion", "0.1.0")


class PersonalityProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.data = json.loads((profiles.PROFILES_DIR / "corvus-companion/0.1.0.json").read_text())

    def write(self, data=None, version="0.1.0"):
        target = self.directory / "corvus-companion" / (version + ".json")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.data if data is None else data))
        return target

    def test_exact_profile_load_and_immutable_identity_expression(self):
        profile = load_personality_profile("corvus-companion", "0.1.0")
        self.assertEqual((profile.profile_id, profile.version), ("corvus-companion", "0.1.0"))
        self.assertIsInstance(profile.core_identity, tuple)
        self.assertIsInstance(profile.expression, tuple)
        self.assertIn("gender-neutral", " ".join(profile.core_identity))
        self.assertIn("Voice is separately configurable", " ".join(profile.core_identity))
        with self.assertRaises(FrozenInstanceError):
            profile.version = "0.2.0"

    def test_renderer_is_stable_and_does_not_load_or_call_services(self):
        profile = load_personality_profile("corvus-companion", "0.1.0")
        expected = render_personality_instructions(profile)
        with patch.object(Path, "open", side_effect=AssertionError("renderer performed I/O")):
            self.assertEqual(render_personality_instructions(profile), expected)
        self.assertIn("Core identity:", expected)
        self.assertNotIn("Expression:", expected)
        self.assertIn("existing system and safety instructions take precedence", expected)

    def test_noarg_default_is_byte_identical_to_existing_pers_a(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(hashlib.sha256(compile_personality_system_prompt().encode()).hexdigest(), LEGACY_SHA256)

    def test_disabled_does_not_load_and_preserves_all_base_bytes(self):
        with patch("personality.runtime.load_personality_profile", side_effect=AssertionError("must not load")):
            self.assertEqual(compile_personality_system_prompt(base_system_prompt=BASE, config=PersonalityConfig(False, "../bad", "latest")), BASE)

    def test_enable_appends_without_replacing_safety(self):
        result = compile_personality_system_prompt(base_system_prompt=BASE, config=SELECTED)
        self.assertTrue(result.startswith(BASE + "\n\n"))
        self.assertIn("corvus-companion@0.1.0", result)
        self.assertEqual(result.count(BASE), 1)

    def test_combined_prompt_contains_each_legacy_expression_rule_once(self):
        legacy_rules = (
            'Care about the user without turning ordinary sharing into a problem to solve.',
            'Maintain independent judgment and revise it when evidence changes. Disagree only when it matters.',
            'Be conversational rather than theatrical. Use structure only when it improves clarity. Keep humor, emoji, names, nicknames, praise, and empathy situational and non-repetitive.',
            "Use the shortest response that fully serves the user's current intent.",
            'Ask questions only when they materially improve the answer or naturally advance the conversation.',
            'Technical work should be precise, conclusion-forward, and operationally useful.',
            'Low-mood conversation should be warm, non-clinical, and presence-first unless help is requested or risk requires action.',
        )
        original = compile_personality_system_prompt(config=PersonalityConfig())
        combined = compile_personality_system_prompt(config=SELECTED)
        self.assertTrue(combined.startswith(original + "\n\n"))
        for rule in legacy_rules:
            with self.subTest(rule=rule):
                self.assertEqual(original.count(rule), 1)
                self.assertEqual(combined.count(rule), 1)
        self.assertIn("corvus-companion@0.1.0", combined)
        self.assertIn("gender-neutral", combined)

    def test_environment_requires_explicit_enable_id_and_version(self):
        valid = {"CORVUS_PERSONALITY_ENABLED":"TRUE", "CORVUS_PERSONALITY_PROFILE":"corvus-companion", "CORVUS_PERSONALITY_VERSION":"0.1.0"}
        with patch.dict("os.environ", valid, clear=True):
            self.assertIn("corvus-companion@0.1.0", compile_personality_system_prompt(base_system_prompt=BASE))
        for missing in valid:
            env = dict(valid); del env[missing]
            with self.subTest(missing=missing), patch.dict("os.environ", env, clear=True):
                self.assertEqual(compile_personality_system_prompt(base_system_prompt=BASE), BASE)

    def test_invalid_enable_flags_and_config_types_fail_closed(self):
        for enabled in ("yes", "1", "invalid", "", None, 1, True):
            cfg = PersonalityConfig.from_env({"CORVUS_PERSONALITY_ENABLED":enabled})
            self.assertFalse(cfg.enabled)
        for cfg in ({"enabled":True}, "TRUE", PersonalityConfig("TRUE", "corvus-companion", "0.1.0")):
            self.assertEqual(compile_personality_system_prompt(base_system_prompt=BASE, config=cfg), BASE)

    def test_missing_version_and_invalid_selectors_fail_safely(self):
        for profile_id, version in (("corvus-companion", "99.0.0"), ("../docs", "0.1.0"),
                                    ("corvus-companion", "latest"), (None, None),
                                    ("corvus-companion", "0.1.0/../x")):
            with self.subTest(profile_id=profile_id,version=version):
                with self.assertRaises(PersonalityProfileError):
                    load_personality_profile(profile_id, version)
                self.assertEqual(compile_personality_system_prompt(base_system_prompt=BASE,config=PersonalityConfig(True,profile_id,version)),BASE)

    def test_malformed_file_and_unavailable_file_fall_back(self):
        target = self.write(); target.write_text("{broken")
        with patch.object(profiles, "PROFILES_DIR", self.directory):
            self.assertEqual(compile_personality_system_prompt(base_system_prompt=BASE,config=SELECTED),BASE)
        with patch("personality.runtime.load_personality_profile", side_effect=PermissionError("unreadable")):
            self.assertEqual(compile_personality_system_prompt(base_system_prompt=BASE,config=SELECTED),BASE)

    def test_schema_id_version_and_instruction_types_are_validated(self):
        variants = [dict(self.data,format_version=True), dict(self.data,version="0.2.0"),
                    dict(self.data,profile_id="other"), dict(self.data,core_identity=[]),
                    dict(self.data,expression=[123]), dict(self.data,expression=[" "]),
                    dict(self.data,chat_template_kwargs={"enable_thinking":True})]
        for data in variants:
            self.write(data)
            with self.subTest(data=data), self.assertRaises(PersonalityProfileError):
                load_personality_profile("corvus-companion","0.1.0",profiles_dir=self.directory)
        self.write().write_bytes(b"\xff")
        with self.assertRaises(PersonalityProfileError):
            load_personality_profile("corvus-companion","0.1.0",profiles_dir=self.directory)

    def test_oversized_file_and_external_symlink_are_rejected(self):
        target = self.write(); target.write_text(" "*32769)
        with self.assertRaises(PersonalityProfileError):
            load_personality_profile("corvus-companion","0.1.0",profiles_dir=self.directory)
        outside = self.directory / "outside.json";outside.write_text(json.dumps(self.data))
        selected = self.directory / "trusted/corvus-companion/0.1.0.json"
        selected.parent.mkdir(parents=True);selected.symlink_to(outside)
        with self.assertRaises(PersonalityProfileError):
            load_personality_profile("corvus-companion","0.1.0",profiles_dir=self.directory/"trusted")

    def test_unresolvable_profile_path_falls_back(self):
        with patch.object(Path, "resolve", side_effect=RuntimeError("symlink loop")):
            with self.assertRaises(PersonalityProfileError):
                load_personality_profile("corvus-companion", "0.1.0")
            self.assertEqual(compile_personality_system_prompt(base_system_prompt=BASE,config=SELECTED),BASE)

    def test_version_switch_and_rollback_are_exact_not_latest(self):
        self.write()
        self.write(dict(self.data,version="0.1.1",expression=["Second test expression."]),version="0.1.1")
        with patch.object(profiles,"PROFILES_DIR",self.directory):
            original = compile_personality_system_prompt(base_system_prompt=BASE,config=SELECTED)
            newer = compile_personality_system_prompt(base_system_prompt=BASE,config=PersonalityConfig(True,"corvus-companion","0.1.1"))
            self.assertNotEqual(original,newer)
            self.assertIn("Expression:\n- Second test expression.",newer)
            self.assertEqual(compile_personality_system_prompt(base_system_prompt=BASE,config=SELECTED),original)
            self.assertEqual(compile_personality_system_prompt(base_system_prompt=BASE,config=PersonalityConfig()),BASE)

    def test_module_is_model_transport_and_memory_independent(self):
        with patch("socket.socket.connect",side_effect=AssertionError("network not allowed")):
            text = compile_personality_system_prompt(base_system_prompt=BASE,config=SELECTED)
        for token in ("Qwen", "enable_thinking", "chat_template_kwargs", "127.0.0.1", "8095"):
            self.assertNotIn(token,text)
        # No provider/Thinking/TTS controls can enter through the profile schema.
        self.assertEqual(set(self.data),{"format_version","profile_id","version","core_identity","expression"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
