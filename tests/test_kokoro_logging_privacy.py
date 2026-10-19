"""Run in the pinned Kokoro image, network disabled, no deployed volumes.

Real route/chunk/text/codec code; model, phonemizer and managers are mocked.
Every privacy case is a fresh process because fd containment is irreversible.
"""
import asyncio
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[1]
PRIVACY = Path(os.environ.get('CORVUS_KOKORO_PRIVACY_ROOT', ROOT / 'deploy/kokoro/privacy'))
CANARY = 'PUBLIC_CANARY_中文_OnlySynthetic_271828'
PHONEMES = 'CANARY_PHONEMES_314159'


def scenario(name):
    sys.path.insert(0, str(PRIVACY))
    import guard
    guard.contain_output()
    guard.configure_logging()
    from loguru import logger
    import logging
    import warnings
    if name == 'direct':
        print(CANARY, flush=True)
        print(PHONEMES, file=sys.stderr, flush=True)
        os.write(1, CANARY.encode())
        os.write(2, PHONEMES.encode())
        subprocess.run([sys.executable, '-c', 'import os; os.write(2, '+repr(CANARY.encode())+')'], check=True)
        guard.emit('warning', 'WARNING')
    elif name == 'exceptions':
        try:
            try:
                raise ValueError(CANARY)
            except ValueError as e:
                raise RuntimeError(PHONEMES) from e
        except RuntimeError:
            logger.exception(CANARY)
            logging.getLogger('uvicorn.error').exception(PHONEMES)
            sys.excepthook(*sys.exc_info())
        warnings.warn(CANARY)
        class Evil:
            def __str__(self):
                raise AssertionError('logging must not format args')
        logging.error('%s', Evil())
        # A library's new handler cannot escape through raw stderr either.
        handler = logging.StreamHandler()
        logging.getLogger('dependency').addHandler(handler)
        logging.getLogger('dependency').error(CANARY)
    elif name == 'metadata':
        for level in ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'):
            logger.log(level, CANARY, private=PHONEMES)
        guard.emit(CANARY, CANARY, CANARY, line=CANARY, status=CANARY, elapsed_ms=CANARY)
    elif name.startswith('route_'):
        import httpx
        import numpy as np
        from fastapi import FastAPI
        from api.src.routers import openai_compatible as router
        from api.src.inference.base import AudioChunk
        guard.configure_logging()  # Kokoro package import resets its own logger.
        mode = name.removeprefix('route_')
        fake = AsyncMock()
        fake.list_voices.return_value = ['af_mica']
        fake.generate_audio.return_value = AudioChunk(np.zeros(240, dtype=np.int16))
        async def stream(**kw):
            yield AudioChunk(np.zeros(240, dtype=np.int16), output=b'RIFFfixture')
        fake.generate_audio_stream = stream
        if mode in ('value', 'runtime', 'unexpected'):
            error = {'value': ValueError, 'runtime': RuntimeError, 'unexpected': KeyError}[mode]
            fake.generate_audio.side_effect = error(CANARY)
        app = FastAPI()
        app.include_router(router.router, prefix='/v1')
        router._tts_service = fake
        async def call():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=guard.Outcomes(app)), base_url='http://fixture') as c:
                response = await c.post('/v1/audio/speech', json={
                    'model': 'kokoro', 'input': CANARY, 'voice': 'af_mica',
                    'lang_code': 'z', 'speed': 0.95, 'response_format': 'wav',
                    'stream': mode == 'stream', 'return_download_link': False,
                })
                expected = 400 if mode == 'value' else 500 if mode in ('runtime', 'unexpected') else 200
                assert response.status_code == expected
                if mode in ('success', 'stream'):
                    assert response.headers['content-type'] == 'audio/wav'
                    assert response.content.startswith(b'RIFF')
                if mode != 'stream':
                    kw = fake.generate_audio.call_args.kwargs
                    assert kw['text'] == CANARY and kw['voice'] == 'af_mica'
                    assert kw['lang_code'] == 'z' and kw['speed'] == 0.95
                if mode == 'success':
                    assert response.content[8:12] == b'WAVE'
        asyncio.run(call())
    elif name.startswith('chunk_'):
        from types import SimpleNamespace
        import numpy as np
        from api.src.services import tts_service as mod
        from api.src.inference.base import AudioChunk
        guard.configure_logging()
        service = mod.TTSService()
        service.model_manager = SimpleNamespace(get_backend=lambda: object())
        service._get_voices_path = AsyncMock(return_value=('af_mica', '/fixture/voice.pt'))
        mode = name.removeprefix('chunk_')
        async def split(*args, **kw):
            assert args[0] == CANARY and kw['lang_code'] == 'z'
            yield CANARY, [1], None
        async def chunk(*args, **kw):
            if not kw['is_last']:
                if mode == 'error':
                    raise RuntimeError(CANARY)
                yield AudioChunk(np.array([], dtype=np.int16), output=None)
        service._process_chunk = chunk
        async def consume():
            with patch.object(mod, 'smart_split', split):
                async for _ in service.generate_audio_stream(CANARY, 'af_mica', None, lang_code='z'):
                    pass
        asyncio.run(consume())
    elif name.startswith('text_'):
        from api.src.services.text_processing import text_processor as mod
        guard.configure_logging()
        if name == 'text_error':
            with patch.object(mod, 'phonemize', side_effect=ValueError(CANARY)):
                try:
                    mod.process_text_chunk(CANARY, 'z')
                except ValueError:
                    logger.exception(PHONEMES)
                else:
                    raise AssertionError('expected text error')
        else:
            with patch.object(mod, 'phonemize', return_value=PHONEMES), patch.object(mod, 'tokenize', return_value=[1, 2]):
                assert mod.process_text_chunk(CANARY, 'z') == [1, 2]
                assert asyncio.run(mod.yield_chunk(CANARY, [1, 2], 1)) == (CANARY, [1, 2])
    elif name.startswith('backend_'):
        from types import SimpleNamespace
        import torch
        from api.src.inference import kokoro_v1 as mod
        guard.configure_logging()
        backend = object.__new__(mod.KokoroV1)
        backend._model = object()
        backend._device = 'cpu'
        def pipeline(text, **kw):
            assert text == CANARY and kw['speed'] == 0.95
            if name == 'backend_error':
                raise RuntimeError(CANARY)
            yield SimpleNamespace(audio=torch.zeros(240), pred_dur=[1],
                tokens=[SimpleNamespace(text=CANARY, start_ts=0, end_ts=0.01)])
        backend._get_pipeline = lambda lang: pipeline if lang == 'z' else None
        async def consume():
            with patch.object(mod.paths, 'load_voice_tensor', AsyncMock(return_value=object())), patch.object(mod.paths, 'save_voice_tensor', AsyncMock()):
                try:
                    result = [x async for x in backend.generate(CANARY, ('af_mica', '/fixture/voice.pt'), speed=0.95, lang_code='z', return_timestamps=True)]
                    assert name == 'backend_success' and len(result) == 1
                    assert result[0].word_timestamps[0].word == CANARY
                except RuntimeError:
                    assert name == 'backend_error'
        asyncio.run(consume())
    elif name == 'launch':
        import runpy
        import types
        fake_main = types.ModuleType('api.src.main')
        fake_main.app = object()
        fake_uvicorn = types.ModuleType('uvicorn')
        called = []
        def run(app, **kw):
            assert isinstance(app, guard.Outcomes) and app.app is fake_main.app
            assert kw == dict(host='0.0.0.0', port=8880, log_config=None, access_log=False, log_level='debug')
            called.append(True)
        fake_uvicorn.run = run
        with patch.dict(sys.modules, {'api.src.main': fake_main, 'uvicorn': fake_uvicorn}), patch.dict(os.environ, {'DOWNLOAD_MODEL': 'true'}), patch('subprocess.run') as download:
            download.return_value.returncode = 0
            runpy.run_path(str(PRIVACY / 'launch.py'))
            assert called == [True]
            assert download.call_args.args[0] == [sys.executable, 'download_model.py', '--output', 'api/src/models/v1_1_zh', '--voices-output', 'api/src/voices/v1_1_zh']
            assert download.call_args.kwargs == {'check': False}
    elif name == 'asgi_failure':
        async def fail(scope, receive, send):
            raise RuntimeError(CANARY)
        async def call():
            try:
                await guard.Outcomes(fail)({'type': 'http'}, None, None)
            except RuntimeError as e:
                assert str(e) == CANARY  # Preserve error/control flow; do not swallow.
            else:
                raise AssertionError('exception swallowed')
        asyncio.run(call())
    elif name == 'cancel':
        async def fail(scope, receive, send):
            raise asyncio.CancelledError(CANARY)
        async def call():
            try:
                await guard.Outcomes(fail)({'type': 'http'}, None, None)
            except asyncio.CancelledError:
                pass
            else:
                raise AssertionError('cancellation swallowed')
        asyncio.run(call())
    else:
        raise AssertionError('unknown test scenario')
    guard.emit('exit', status=200)


class PrivacyTests(unittest.TestCase):
    def test_image_source_lock_and_tamper_rejection(self):
        import tempfile
        spec = importlib.util.spec_from_file_location('source_verify', PRIVACY / 'verify.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.verify('/app/api/src', PRIVACY / 'source-lock.json')
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, 'main.py').write_text('changed = True')
            with self.assertRaisesRegex(SystemExit, 'source mismatch'):
                module.verify(tmp, PRIVACY / 'source-lock.json')

    def test_installed_model_configuration_unchanged(self):
        text = Path('/app/api/src/core/config.py').read_text()
        self.assertIn('hexgrad/Kokoro-82M-v1.1-zh', text)
        self.assertIn('v1_1_zh/kokoro-v1_1-zh.pth', text)
        for name in ('guard.py', 'launch.py', 'verify.py', 'source-lock.json'):
            self.assertEqual((PRIVACY / name).read_bytes(), (ROOT / 'deploy/kokoro/privacy' / name).read_bytes())

    def run_case(self, name, level=None, event=None):
        result = subprocess.run([sys.executable, '-B', __file__, '--scenario', name],
                                capture_output=True, timeout=90)
        self.assertEqual(result.returncode, 0, 'isolated scenario failed: ' + name)
        self.assertEqual(result.stdout, b'')
        raw = result.stderr.decode()
        self.assertNotIn(CANARY, raw)
        self.assertNotIn(PHONEMES, raw)
        self.assertNotIn('Traceback', raw)
        records = [json.loads(line) for line in raw.splitlines()]
        self.assertTrue(any(r['event'] == 'exit' and r['status'] == 200 for r in records))
        for record in records:
            self.assertEqual(set(record), {'event','level','component','line','status','elapsed_ms'})
        if level:
            self.assertTrue(any(r['level'] == level for r in records), level)
        if event:
            self.assertTrue(any(r['event'] == event for r in records), event)
        return records

    def test_direct_native_and_child_output(self): self.run_case('direct', level='WARNING')
    def test_chained_exceptions_framework_and_warnings(self): self.run_case('exceptions', level='ERROR', event='unhandled')
    def test_metadata_only_all_severities(self): self.run_case('metadata', level='CRITICAL')
    def test_real_nonstream_route_and_wav_codec(self): self.run_case('route_success', event='request')
    def test_real_stream_route_contract(self): self.run_case('route_stream', event='request')
    def test_real_route_value_error(self): self.run_case('route_value', level='WARNING')
    def test_real_route_processing_error(self): self.run_case('route_runtime', level='ERROR')
    def test_real_route_unexpected_error(self): self.run_case('route_unexpected', level='ERROR')
    def test_real_chunk_warning(self): self.run_case('chunk_warning', level='WARNING')
    def test_real_chunk_error(self): self.run_case('chunk_error', level='ERROR')
    def test_real_text_processing_success(self): self.run_case('text_success', level='DEBUG')
    def test_real_text_processing_failure(self): self.run_case('text_error', level='ERROR')
    def test_unhandled_asgi_failure_propagates(self): self.run_case('asgi_failure', event='unhandled')
    def test_backend_success_timestamps(self): self.run_case('backend_success', level='DEBUG')
    def test_backend_exception(self): self.run_case('backend_error', level='ERROR')
    def test_launcher_preserves_startup_contract(self): self.run_case('launch', event='startup')
    def test_cancellation_propagates(self): self.run_case('cancel', event='cancelled')


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--scenario':
        scenario(sys.argv[2])
    else:
        unittest.main()
