"""Mock-only contracts for the reused A3 Whisper transport; no real audio/I/O."""
import contextlib
from email import policy
from email.parser import BytesParser
import io
import json
import socket
import unittest
from unittest.mock import Mock, patch
import urllib.error

from app import transcription


class Response:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *unused):
        return False

    def read(self):
        return self.payload


def response(text):
    return Response(json.dumps({'text': text}, ensure_ascii=False).encode('utf-8'))


class TransportContracts(unittest.TestCase):
    def setUp(self):
        stack = self.enterContext(contextlib.ExitStack())
        forbidden = AssertionError('pure transport accessed persistence or files')
        # Forbid both imported aliases and underlying persistence entry points.
        for target in (
            'app.transcription.get_attachment',
            'app.transcription.read_attachment_bytes',
            'app.transcription.add_attachment_artifact',
            'memory.attachments.get_attachment',
            'memory.attachments.read_attachment_bytes',
            'memory.attachments.store_attachment_bytes',
            'memory.attachments.store_attachment_stream',
            'memory.attachments.add_attachment_artifact',
            'memory.attachments.link_attachment_to_message',
            'memory.store.connect',
            'memory.store.add_message',
            'sqlite3.connect',
            'builtins.open',
            'os.open',
        ):
            stack.enter_context(patch(target, side_effect=forbidden))

    def transcribe(self, opener, **kwargs):
        return transcription.transcribe_audio_bytes(
            b'\x00synthetic-audio\xff', filename='../voice.m4a',
            media_type='audio/mp4', opener=opener, **kwargs)

    def test_chinese_english_text_and_no_canonical_io(self):
        for text in ('我们今天测试语音。', 'This is an English sentence.', '中文 and English.'):
            with self.subTest(text=text):
                opener = Mock(return_value=response('  ' + text + '\n'))
                with contextlib.redirect_stdout(io.StringIO()) as stdout, contextlib.redirect_stderr(io.StringIO()) as stderr:
                    self.assertEqual(self.transcribe(opener), text)
                self.assertEqual(stdout.getvalue(), '')
                self.assertEqual(stderr.getvalue(), '')
                opener.assert_called_once()

    def test_existing_multipart_protocol_and_overrides(self):
        opener = Mock(return_value=response('recognized text'))
        self.transcribe(opener, language='zh', prompt='词汇 vocabulary',
                        base_url='http://127.0.0.1:8104/', timeout=17)
        request = opener.call_args.args[0]
        self.assertEqual(request.full_url, 'http://127.0.0.1:8104/inference')
        self.assertEqual(request.method, 'POST')
        self.assertEqual(opener.call_args.kwargs, {'timeout': 17})
        message = BytesParser(policy=policy.default).parsebytes(
            ('Content-Type: ' + request.get_header('Content-type') + '\r\n\r\n').encode() + request.data)
        parts = {p.get_param('name', header='content-disposition'): p for p in message.iter_parts()}
        self.assertEqual(set(parts), {'file', 'language', 'response_format', 'prompt'})
        self.assertEqual(parts['file'].get_filename(), 'voice.m4a')
        self.assertEqual(parts['file'].get_content_type(), 'audio/mp4')
        self.assertEqual(parts['file'].get_payload(decode=True), b'\x00synthetic-audio\xff')
        self.assertEqual(parts['language'].get_payload(decode=True), b'zh')
        self.assertEqual(parts['response_format'].get_payload(decode=True), b'json')
        self.assertEqual(parts['prompt'].get_payload(decode=True).decode(), '词汇 vocabulary')

    def test_existing_defaults_and_optional_prompt(self):
        opener = Mock(return_value=response('text'))
        self.transcribe(opener)
        request = opener.call_args.args[0]
        self.assertEqual(opener.call_args.kwargs['timeout'], transcription.STT_TIMEOUT_SECONDS)
        self.assertEqual(request.full_url, transcription.STT_BASE_URL + '/inference')
        self.assertIn(b'name="language"\r\n\r\nauto\r\n', request.data)
        self.assertIn(transcription.STT_PROMPT.encode(), request.data)
        for prompt in ('', None):
            with self.subTest(prompt=prompt):
                opener = Mock(return_value=response('text'))
                self.transcribe(opener, language='en', prompt=prompt)
                self.assertNotIn(b'name="prompt"', opener.call_args.args[0].data)

    def test_existing_timeout_and_http_errors(self):
        cases = (
            (socket.timeout('synthetic timeout'), 'TRANSCRIPTION_TIMEOUT', 'STT request timed out'),
            (TimeoutError('synthetic timeout'), 'TRANSCRIPTION_TIMEOUT', 'STT request timed out'),
            (urllib.error.URLError(socket.timeout('synthetic timeout')), 'TRANSCRIPTION_TIMEOUT', 'STT request timed out'),
            (urllib.error.HTTPError('http://example.invalid', 503, 'unavailable', {}, None),
             'TRANSCRIPTION_HTTP_ERROR', 'STT server returned HTTP 503'),
            (urllib.error.URLError('synthetic unavailable'), 'TRANSCRIPTION_UNAVAILABLE',
             'STT server unavailable: synthetic unavailable'),
        )
        for error, code, message in cases:
            with self.subTest(code=code, error=type(error).__name__):
                opener = Mock(side_effect=error)
                with self.assertRaises(transcription.TranscriptionError) as caught:
                    self.transcribe(opener)
                self.assertEqual(caught.exception.code, code)
                self.assertEqual(str(caught.exception), message)
                opener.assert_called_once()  # Preserve no-retry behavior.

    def test_response_read_timeout(self):
        reply = Response(b'')
        reply.read = Mock(side_effect=TimeoutError('synthetic read timeout'))
        with self.assertRaises(transcription.TranscriptionError) as caught:
            self.transcribe(Mock(return_value=reply))
        self.assertEqual(caught.exception.code, 'TRANSCRIPTION_TIMEOUT')

    def test_invalid_json_and_utf8(self):
        for raw in (b'not json', b'\xff'):
            with self.subTest(raw=raw):
                with self.assertRaises(transcription.TranscriptionError) as caught:
                    self.transcribe(Mock(return_value=Response(raw)))
                self.assertEqual(caught.exception.code, 'TRANSCRIPTION_RESPONSE_INVALID')
                self.assertEqual(str(caught.exception), 'STT server returned invalid JSON')

    def test_empty_or_non_text_response(self):
        for payload in ({}, {'text': None}, {'text': ''}, {'text': '  \n'}, {'text': 3}):
            with self.subTest(payload=payload):
                with self.assertRaises(transcription.TranscriptionError) as caught:
                    self.transcribe(Mock(return_value=Response(json.dumps(payload).encode())))
                self.assertEqual(caught.exception.code, 'TRANSCRIPTION_EMPTY')
                self.assertEqual(str(caught.exception), 'STT server returned no usable transcript')


class AttachmentDelegation(unittest.TestCase):
    def test_shared_transport_precedes_single_attributed_artifact(self):
        events = []
        original = b'synthetic-retained-original'
        opener = object()
        def transport(data, **metadata):
            events.append('transport')
            self.assertIs(data, original)
            self.assertEqual(metadata, {'filename': 'original.m4a', 'media_type': 'audio/mp4',
                'language': 'en', 'prompt': 'vocabulary', 'base_url': 'http://127.0.0.1:8104',
                'timeout': 19, 'opener': opener})
            return 'derived text'
        def artifact(attachment_id, **kwargs):
            events.append('artifact')
            self.assertEqual(attachment_id, 'attachment-1')
            self.assertEqual(kwargs, {'artifact_kind': 'TRANSCRIPT', 'content': 'derived text',
                'producer': transcription.STT_PRODUCER,
                'producer_version': transcription.STT_PRODUCER_VERSION or None})
            return 77
        with patch.object(transcription, 'get_attachment', return_value={
                'media_type': ' Audio/MP4 ', 'original_filename': 'original.m4a'}), \
             patch.object(transcription, 'read_attachment_bytes', return_value=original), \
             patch.object(transcription, 'transcribe_audio_bytes', side_effect=transport) as shared:
            result = transcription.transcribe_attachment(' attachment-1 ', language='en',
                prompt='vocabulary', base_url='http://127.0.0.1:8104', timeout=19,
                opener=opener, add_artifact_fn=artifact)
        self.assertEqual(events, ['transport', 'artifact'])
        shared.assert_called_once()
        self.assertEqual(result, {'attachment_id': 'attachment-1', 'artifact_id': 77,
            'transcript': 'derived text', 'producer': transcription.STT_PRODUCER,
            'producer_version': transcription.STT_PRODUCER_VERSION or None})
        self.assertEqual(original, b'synthetic-retained-original')

    def test_transport_failure_does_not_create_artifact(self):
        error = transcription.TranscriptionError('TRANSCRIPTION_TIMEOUT', 'STT request timed out')
        artifact = Mock()
        with patch.object(transcription, 'get_attachment', return_value={
                'media_type': 'audio/mp4', 'original_filename': 'original.m4a'}), \
             patch.object(transcription, 'read_attachment_bytes', return_value=b'synthetic'), \
             patch.object(transcription, 'transcribe_audio_bytes', side_effect=error):
            with self.assertRaises(transcription.TranscriptionError) as caught:
                transcription.transcribe_attachment('attachment-1', add_artifact_fn=artifact)
        self.assertIs(caught.exception, error)
        artifact.assert_not_called()


if __name__ == '__main__':
    unittest.main()
