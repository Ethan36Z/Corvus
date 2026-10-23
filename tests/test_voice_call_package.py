"""Voice V1 frontend overlay contracts, using explicit public source fixtures only."""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('voice_v1_prepare', ROOT/'deploy/lab/voice-call/prepare_frontend.py')
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)

class VoicePackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture = os.environ.get('CORVUS_VOICE_V1_SOURCE')
        if not fixture:
            raise unittest.SkipTest('Set CORVUS_VOICE_V1_SOURCE to the reviewed native STT source tree')
        cls.source = Path(fixture)
        cls.inputs = {p:(cls.source/p).read_text() for p in prepare.PINS}
        cls.output = prepare.patch_sources(cls.inputs)

    def test_exact_source_required_before_any_output(self):
        for name in prepare.PINS:
            with self.subTest(name=name):
                bad=dict(self.inputs);bad[name]+='\n'
                with self.assertRaisesRegex(ValueError,'Unreviewed'):
                    prepare.patch_sources(bad)

    def test_fresh_separate_output_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'overlay'
            proof=prepare.prepare(self.source,out)
            self.assertFalse(proof['default_enabled'])
            self.assertEqual(len(proof['output_sha256']),7)
            with self.assertRaises(ValueError):prepare.prepare(self.source,out)
            with self.assertRaises(ValueError):prepare.prepare(self.source,self.source/'nested')

    def test_only_frontend_call_seams_no_normalizer_chat_or_memory_replacement(self):
        self.assertEqual(set(self.output),set(prepare.PINS)|{
            'src/lib/components/chat/MessageInput/CorvusCall.svelte','src/lib/utils/corvus-call.ts'})
        for forbidden in ['Chat.svelte','corvus-normalize.ts','corvus-dictation.ts']:
            self.assertFalse(any(p.endswith('/'+forbidden) for p in self.output))
        panel=self.output['src/lib/components/chat/MessageInput/CorvusCall.svelte']
        self.assertIn('<VoiceRecording',panel)
        self.assertIn('submitPrompt(text, { _raw: true })',panel)
        self.assertIn('synthesizeOpenAISpeech',panel)
        self.assertNotIn('fetch(',panel)

    def test_target_gate_is_explicit_and_default_off(self):
        text=self.output[prepare.CALL]
        self.assertIn("import.meta.env.VITE_CORVUS_VOICE_CALL === 'true'",text)
        self.assertIn("const corvusMode = modelId === 'corvus_pipe';",text)
        self.assertEqual(text.count('if (corvusMode) return;'),2)
        self.assertIn('Corvus Voice Call is disabled',text)

    def test_other_models_retain_the_native_call_body(self):
        original=self.inputs[prepare.CALL]
        native_body=original.split('{#if $showCallOverlay}\n',1)[1].rstrip()[:-5]
        self.assertIn(native_body,self.output[prepare.CALL])
        self.assertIn('const stopAllAudio =',self.output[prepare.CALL])

    def test_both_layouts_share_history_and_remount_on_model_change(self):
        controls=self.output[prepare.CONTROLS]
        self.assertEqual(controls.count('{#key modelId}'),2)
        self.assertEqual(controls.count('{history}'),self.inputs[prepare.CONTROLS].count('{history}')+2)

    def test_dictation_default_unchanged_and_tts_extension_is_optional(self):
        voice=self.output[prepare.VOICE]
        self.assertIn('export let callMode = false;',voice)
        self.assertIn("if (callMode) dispatch('callphase');",voice)
        original=self.inputs[prepare.API];changed=self.output[prepare.API]
        marker='export const synthesizeOpenAISpeech ='
        self.assertEqual(original.split(marker)[0],changed.split(marker)[0])
        marker='interface AvailableModelsResponse'
        self.assertEqual(original.split(marker)[1],changed.split(marker)[1])
        self.assertIn('signal?: AbortSignal',changed)

    def test_corvus_launcher_avoids_legacy_mic_probe_and_browser_model(self):
        text=self.output[prepare.COMPOSER]
        guard=text.index("if (selectedModelIds.at(0) === 'corvus_pipe')")
        legacy=text.index("if ($config.audio.stt.engine === 'web')",guard)
        scoped=text[guard:legacy]
        self.assertIn("VITE_CORVUS_VOICE_CALL !== 'true'",scoped)
        self.assertIn('showCallOverlay.set(true);',scoped)
        self.assertIn('return;',scoped)
        self.assertNotIn('getUserMedia',scoped)
        self.assertNotIn('KokoroWorker',scoped)
        # Composer dictation/manual-send handler remains byte-identical.
        before=self.inputs[prepare.COMPOSER].split('on:confirm=')[1].split('/>')[0]
        after=text.split('on:confirm=')[1].split('/>')[0]
        self.assertEqual(before,after)

    def test_no_cancellation_retry_or_private_logging_in_new_call_code(self):
        for name in ['src/lib/utils/corvus-call.ts','src/lib/components/chat/MessageInput/CorvusCall.svelte']:
            text=self.output[name]
            for token in ['console.','fetch(','localStorage.setItem','stopResponse(','stopTask(','/api/chat','/v1/chat/completions']:
                self.assertNotIn(token,text)
        text=self.output['src/lib/utils/corvus-call.ts']
        self.assertIn('this.state.pending = true',text)
        self.assertIn('row.error',text)
        self.assertIn("row.model !== 'corvus_pipe'",text)

if __name__ == '__main__':unittest.main(verbosity=2)
