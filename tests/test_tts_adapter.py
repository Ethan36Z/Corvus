import json
import socket
import urllib.error

from app.tts import (
    TTSError,
    prepare_speech_text,
    synthesize_speech,
)


class FakeResponse:
    def __init__(self, body):
        self.body = body

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type,
        exc,
        traceback,
    ):
        return False


VALID_WAV = (
    b"RIFF"
    + b"\x00\x00\x00\x00"
    + b"WAVE"
    + b"fmt "
)


def test_prepare_speech_text():
    prepared = prepare_speech_text(
        "  你好，Ethan。\n"
        "我是 Corvus。  "
    )

    assert prepared == (
        "你好，Ethan。 我是 Corvus。"
    )

    print(
        "TTS PRESENTATION TEXT CONTRACT OK"
    )


def test_request_contract():
    captured = {}

    def opener(request, timeout):
        captured["url"] = (
            request.full_url
        )
        captured["timeout"] = timeout
        captured["headers"] = dict(
            request.header_items()
        )
        captured["payload"] = (
            json.loads(
                request.data.decode(
                    "utf-8"
                )
            )
        )

        return FakeResponse(
            VALID_WAV
        )

    result = synthesize_speech(
        "你好，Ethan。我是 Corvus。",
        base_url=(
            "http://127.0.0.1:8105"
        ),
        timeout=17,
        model="kokoro",
        voice="af_mica",
        language="z",
        speed=0.95,
        opener=opener,
    )

    assert captured["url"] == (
        "http://127.0.0.1:8105"
        "/v1/audio/speech"
    )

    assert captured["timeout"] == 17

    assert captured["payload"] == {
        "model": "kokoro",
        "input": (
            "你好，Ethan。我是 Corvus。"
        ),
        "voice": "af_mica",
        "response_format": "wav",
        "speed": 0.95,
        "lang_code": "z",
    }

    assert result["audio"] == (
        VALID_WAV
    )

    assert result["media_type"] == (
        "audio/wav"
    )

    assert result["speech_text"] == (
        "你好，Ethan。我是 Corvus。"
    )

    print(
        "TTS ADAPTER CONTRACT OK"
    )


def test_invalid_audio():
    def opener(request, timeout):
        return FakeResponse(
            b'{"error":"bad"}'
        )

    try:
        synthesize_speech(
            "hello",
            opener=opener,
        )
    except TTSError as exc:
        assert exc.code == (
            "TTS_RESPONSE_INVALID"
        )
    else:
        raise AssertionError(
            "invalid audio was accepted"
        )

    print(
        "TTS INVALID RESPONSE CONTRACT OK"
    )


def test_timeout():
    def opener(request, timeout):
        raise socket.timeout()

    try:
        synthesize_speech(
            "hello",
            opener=opener,
        )
    except TTSError as exc:
        assert exc.code == (
            "TTS_TIMEOUT"
        )
    else:
        raise AssertionError(
            "timeout was not converted"
        )

    print(
        "TTS TIMEOUT CONTRACT OK"
    )


def test_unavailable():
    def opener(request, timeout):
        raise urllib.error.URLError(
            "connection refused"
        )

    try:
        synthesize_speech(
            "hello",
            opener=opener,
        )
    except TTSError as exc:
        assert exc.code == (
            "TTS_UNAVAILABLE"
        )
    else:
        raise AssertionError(
            "unavailable server "
            "was not converted"
        )

    print(
        "TTS UNAVAILABLE CONTRACT OK"
    )


if __name__ == "__main__":
    test_prepare_speech_text()
    test_request_contract()
    test_invalid_audio()
    test_timeout()
    test_unavailable()

    print(
        "A3.3C TTS ADAPTER: PASS"
    )
