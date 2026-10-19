"""Private-instance policy contracts; synthetic WAV and injected workers only."""
import asyncio
from contextlib import ExitStack
import io
import threading
from pathlib import Path
import unittest
from unittest.mock import patch
import wave

import httpx
from app import stt_bridge as bridge

TOKEN=b'SyntheticR6Credential012345678901234567890123456789'
ROOT=Path(__file__).resolve().parents[1]
def wav():
    b=io.BytesIO()
    with wave.open(b,'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000);w.writeframes(b'\0\0'*160)
    return b.getvalue()

class PrivateContracts(unittest.IsolatedAsyncioTestCase):
    def client(self, app):
        return httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://synthetic-bridge')

    async def post(self, client, data=None):
        return await client.post('/v1/transcribe',headers={'authorization':'Bearer '+TOKEN.decode(),'content-type':'audio/wav'},content=wav() if data is None else data)

    async def test_fixed_private_target_rejects_legacy_and_external(self):
        self.assertEqual(bridge.WHISPER_BASE,'http://corvus-whisper-dictation:8080')
        for url in ('http://corvus-whisper:8080/inference','https://external.invalid/inference'):
            with self.assertRaises(ValueError):bridge.whisper_opener(bridge.urllib.request.Request(url,data=b'synthetic'),25)
        with patch.object(bridge,'transcribe_audio_bytes',return_value='中文 English') as call:
            self.assertEqual(bridge.whisper_text(wav()),'中文 English')
            self.assertEqual(call.call_args.kwargs['base_url'],bridge.WHISPER_BASE)
            self.assertEqual(call.call_args.kwargs['timeout'],25)

    async def test_busy_rejected_before_body_and_release_after_success(self):
        started=asyncio.Event();finish=asyncio.Event();calls=[]
        async def work(fn,audio):
            calls.append(audio);started.set();await finish.wait();return '中文 English'
        app=bridge.create_app(token=TOKEN,transcriber=lambda _:None)
        with patch('starlette.concurrency.run_in_threadpool',work):
            async with self.client(app) as c:
                first=asyncio.create_task(self.post(c));await started.wait()
                read=[]
                async def chunks():read.append(True);yield wav()
                second=await c.post('/v1/transcribe',headers={'authorization':'Bearer '+TOKEN.decode(),'content-type':'audio/wav'},content=chunks())
                self.assertEqual(second.status_code,429);self.assertEqual(read,[]);self.assertEqual(len(calls),1)
                finish.set();self.assertEqual((await first).json(),{'text':'中文 English'})
                self.assertEqual((await self.post(c)).status_code,200)

    async def test_timeout_holds_slot_until_underlying_worker_settles(self):
        started=asyncio.Event();finish=asyncio.Event()
        async def work(fn,audio):started.set();await finish.wait();return 'late text'
        app=bridge.create_app(token=TOKEN,transcriber=lambda _:None)
        with patch('starlette.concurrency.run_in_threadpool',work),patch.object(bridge,'INFERENCE_SECONDS',.01):
            async with self.client(app) as c:
                first=await self.post(c);self.assertEqual(first.status_code,504)
                self.assertEqual((await self.post(c)).status_code,429)
                finish.set();await asyncio.sleep(.01)
                self.assertEqual((await self.post(c)).status_code,200)
                self.assertNotIn('late text',first.text)

    async def test_real_thread_remains_admitted_after_logical_timeout(self):
        loop=asyncio.get_running_loop();started=asyncio.Event();finish=threading.Event()
        def work(audio):
            loop.call_soon_threadsafe(started.set)
            if not finish.wait(2):raise RuntimeError('synthetic worker deadline')
            return 'synthetic text'
        app=bridge.create_app(token=TOKEN,transcriber=work)
        try:
            with patch.object(bridge,'INFERENCE_SECONDS',.01):
                async with self.client(app) as c:
                    first=asyncio.create_task(self.post(c));await started.wait()
                    self.assertEqual((await first).status_code,504)
                    self.assertEqual((await self.post(c)).status_code,429)
                    finish.set();await asyncio.sleep(.05)
                    self.assertEqual((await self.post(c)).status_code,200)
        finally:finish.set()

    async def test_asgi_cancellation_suppresses_result_and_holds_slot(self):
        started=asyncio.Event();finish=asyncio.Event()
        async def work(fn,audio):started.set();await finish.wait();return 'late text'
        app=bridge.create_app(token=TOKEN,transcriber=lambda _:None)
        with patch('starlette.concurrency.run_in_threadpool',work):
            async with self.client(app) as c:
                task=asyncio.create_task(self.post(c));await started.wait();task.cancel()
                with self.assertRaises(asyncio.CancelledError):await task
                self.assertEqual((await self.post(c)).status_code,429)
                finish.set();await asyncio.sleep(.01)
                self.assertEqual((await self.post(c)).status_code,200)

    async def test_disconnect_polling_no_late_transcript(self):
        from starlette.requests import Request
        started=asyncio.Event();finish=asyncio.Event()
        async def work(fn,audio):started.set();await finish.wait();return 'late text'
        app=bridge.create_app(token=TOKEN,transcriber=lambda _:None)
        async def disconnected(request):return started.is_set()
        with patch('starlette.concurrency.run_in_threadpool',work),patch.object(Request,'is_disconnected',disconnected):
            async with self.client(app) as c:
                response=await self.post(c);self.assertEqual(response.status_code,499)
                self.assertNotIn('late text',response.text)
                self.assertEqual((await self.post(c)).status_code,429)
                finish.set();await asyncio.sleep(.01)

    async def test_failure_and_invalid_body_release_slot_without_logging(self):
        calls=[]
        def fail(audio):calls.append(audio);raise ValueError('PRIVATE_SENTINEL')
        app=bridge.create_app(token=TOKEN,transcriber=fail)
        async with self.client(app) as c:
            self.assertEqual((await self.post(c,b'not WAV')).status_code,400)
            for _ in range(2):
                with self.assertNoLogs('app.stt_bridge'):
                    response=await self.post(c)
                self.assertEqual(response.status_code,502);self.assertNotIn('PRIVATE_SENTINEL',response.text)
            self.assertEqual(len(calls),2)

    async def test_exported_bridge_still_disabled(self):
        async with self.client(bridge.app) as c:self.assertEqual((await self.post(c)).status_code,503)

if __name__=='__main__':unittest.main()
