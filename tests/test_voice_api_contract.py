import app.playground_api as api


original_process_turn = api.process_turn


def runtime_result(
    *,
    session_id,
    user_message_id,
    assistant_message_id,
    attachment_id=None,
    attachment_status="NOT_REQUESTED",
    transcription_status="NOT_REQUESTED",
    transcript_artifact_id=None,
    transcript=None,
):
    return {
        "session_id": session_id,
        "user_message_id": user_message_id,
        "assistant_message_id": assistant_message_id,
        "attachment_id": attachment_id,
        "attachment_status": attachment_status,
        "attachment_error": None,
        "transcription_status": (
            transcription_status
        ),
        "transcription_error": None,
        "transcript_artifact_id": (
            transcript_artifact_id
        ),
        "transcript": transcript,
        "recent_message_ids": [],
        "historical_message_ids": [],
        "input_tokens": 42,
        "retrieval_status": "OK",
        "retrieval_error": None,
        "model_status": "OK",
        "dense_status": "OK",
        "persistence_status": "NORMAL",
        "reply": "API reply",
        "error": None,
    }


try:
    #
    # Voice API must overwrite any client-side
    # message text with the canonical voice marker.
    #
    captured = {}

    def fake_voice_process_turn(**kwargs):
        captured.update(kwargs)

        return runtime_result(
            session_id=kwargs["session_id"],
            user_message_id=701,
            assistant_message_id=702,
            attachment_id=kwargs[
                "attachment_id"
            ],
            attachment_status="LINKED",
            transcription_status="OK",
            transcript_artifact_id=88,
            transcript=(
                "我们今天测试Corvus的语音功能"
            ),
        )

    api.process_turn = (
        fake_voice_process_turn
    )

    voice_response = api.post_chat(
        api.ChatRequest(
            session_id="voice-api-test",
            message=(
                "THIS CLIENT TEXT MUST "
                "NOT BECOME CANONICAL"
            ),
            attachment_id="audio-att-1",
            attachment_mode="voice",
        )
    )

    assert (
        captured["session_id"]
        == "voice-api-test"
    )

    assert (
        captured["user_content"]
        == "[Voice message]"
    )

    assert (
        captured["attachment_id"]
        == "audio-att-1"
    )

    assert (
        captured["attachment_mode"]
        == "voice"
    )

    assert (
        voice_response[
            "transcription_status"
        ]
        == "OK"
    )

    assert (
        voice_response[
            "transcript_artifact_id"
        ]
        == 88
    )

    assert (
        voice_response["transcript"]
        == "我们今天测试Corvus的语音功能"
    )

    assert (
        voice_response["status"][
            "transcription"
        ]
        == "OK"
    )

    print(
        "VOICE API CANONICAL MARKER OK"
    )
    print(
        "VOICE API TRANSCRIPTION RESPONSE OK"
    )

    #
    # Existing text behavior remains unchanged.
    #
    captured = {}

    def fake_text_process_turn(**kwargs):
        captured.update(kwargs)

        return runtime_result(
            session_id=kwargs["session_id"],
            user_message_id=801,
            assistant_message_id=802,
        )

    api.process_turn = (
        fake_text_process_turn
    )

    text_response = api.post_chat(
        api.ChatRequest(
            session_id="text-api-test",
            message="hello Corvus",
        )
    )

    assert (
        captured["user_content"]
        == "hello Corvus"
    )

    assert (
        captured["attachment_id"]
        is None
    )

    assert (
        captured["attachment_mode"]
        == "vision"
    )

    assert (
        text_response[
            "transcription_status"
        ]
        == "NOT_REQUESTED"
    )

    print(
        "TEXT API BACKWARD COMPATIBILITY OK"
    )

finally:
    api.process_turn = (
        original_process_turn
    )


print(
    "A3.3 VOICE API CONTRACT: PASS"
)
