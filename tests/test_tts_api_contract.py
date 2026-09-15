from fastapi import HTTPException

import app.playground_api as api
from app.tts import TTSError


VALID_WAV = (
    b"RIFF"
    + b"\x00\x00\x00\x00"
    + b"WAVE"
    + b"fmt "
)


def fake_result():
    return {
        "audio": VALID_WAV,
        "media_type": "audio/wav",
        "speech_text": "Hello",
        "model": "kokoro",
        "voice": "af_mica",
        "language": "z",
        "speed": 0.95,
    }


def test_assistant_message_contract():
    captured = {}

    def load_message(message_id):
        assert message_id == 42

        return {
            "id": 42,
            "session_id": "s1",
            "role": "assistant",
            "content": (
                "你好，Ethan。"
                "我是 Corvus。"
            ),
            "created_at": "now",
        }

    def synthesize(text):
        captured["text"] = text
        return fake_result()

    result = (
        api.synthesize_message_audio(
            42,
            load_message_fn=load_message,
            synthesize_fn=synthesize,
        )
    )

    assert captured["text"] == (
        "你好，Ethan。我是 Corvus。"
    )

    assert result["audio"] == VALID_WAV

    print(
        "TTS ASSISTANT MESSAGE CONTRACT OK"
    )


def test_user_message_rejected():
    called = False

    def load_message(message_id):
        return {
            "id": message_id,
            "session_id": "s1",
            "role": "user",
            "content": "hello",
            "created_at": "now",
        }

    def synthesize(text):
        nonlocal called
        called = True
        return fake_result()

    try:
        api.synthesize_message_audio(
            7,
            load_message_fn=load_message,
            synthesize_fn=synthesize,
        )
    except HTTPException as exc:
        assert exc.status_code == 409
    else:
        raise AssertionError(
            "user message was accepted"
        )

    assert called is False

    print(
        "TTS USER MESSAGE REJECTION OK"
    )


def test_missing_message():
    try:
        api.synthesize_message_audio(
            999,
            load_message_fn=lambda _id: None,
            synthesize_fn=lambda _text: (
                fake_result()
            ),
        )
    except HTTPException as exc:
        assert exc.status_code == 404
    else:
        raise AssertionError(
            "missing message was accepted"
        )

    print(
        "TTS MISSING MESSAGE CONTRACT OK"
    )


def test_endpoint_response():
    original = (
        api.synthesize_message_audio
    )

    try:
        api.synthesize_message_audio = (
            lambda _id: fake_result()
        )

        response = api.get_tts_audio(
            42
        )

    finally:
        api.synthesize_message_audio = (
            original
        )

    assert response.body == VALID_WAV

    assert response.media_type == (
        "audio/wav"
    )

    assert (
        response.headers[
            "x-corvus-tts-voice"
        ]
        == "af_mica"
    )

    assert (
        response.headers[
            "cache-control"
        ]
        == "private, no-store"
    )

    print(
        "TTS API RESPONSE CONTRACT OK"
    )


def test_endpoint_tts_failure():
    original = (
        api.synthesize_message_audio
    )

    def fail(_id):
        raise TTSError(
            "TTS_UNAVAILABLE",
            "service unavailable",
        )

    try:
        api.synthesize_message_audio = fail

        try:
            api.get_tts_audio(42)
        except HTTPException as exc:
            assert exc.status_code == 503

            assert exc.detail["code"] == (
                "TTS_UNAVAILABLE"
            )
        else:
            raise AssertionError(
                "TTS failure was not exposed"
            )

    finally:
        api.synthesize_message_audio = (
            original
        )

    print(
        "TTS API FAILURE CONTRACT OK"
    )


def test_invalid_message_id():
    try:
        api.get_tts_audio(0)
    except HTTPException as exc:
        assert exc.status_code == 400
    else:
        raise AssertionError(
            "invalid message id was accepted"
        )

    print(
        "TTS MESSAGE ID CONTRACT OK"
    )


if __name__ == "__main__":
    test_assistant_message_contract()
    test_user_message_rejected()
    test_missing_message()
    test_endpoint_response()
    test_endpoint_tts_failure()
    test_invalid_message_id()

    print(
        "A3.3C TTS API CONTRACT: PASS"
    )
