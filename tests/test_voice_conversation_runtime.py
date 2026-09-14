from app.conversation_runtime import process_turn
from app.transcription import TranscriptionError


TRANSCRIPT = (
    "我们今天测试Corvus的语音功能\n"
    "This is an English sentence.\n"
    "I hope Corvus can understand Chinese and English."
)


#
# Successful voice turn:
# canonical marker -> attachment link ->
# transcription -> context -> model ->
# assistant -> dense.
#
events = []


def add_message(
    session_id,
    role,
    content,
):
    events.append(
        f"add:{role}"
    )

    if role == "user":
        assert content == "[Voice message]"
        return 501

    assert content == "voice reply"
    return 502


def link_attachment(
    message_id,
    attachment_id,
    *,
    ordinal,
):
    events.append("link")

    assert message_id == 501
    assert attachment_id == "voice-att-1"
    assert ordinal == 0


def transcribe(attachment_id):
    events.append("transcribe")

    assert attachment_id == "voice-att-1"

    return {
        "attachment_id": attachment_id,
        "artifact_id": 77,
        "transcript": TRANSCRIPT,
        "producer": "whisper.cpp",
        "producer_version": (
            "small-multilingual"
        ),
    }


def build_context(**kwargs):
    events.append("context")

    assert (
        kwargs["current_user_message_id"]
        == 501
    )

    assert (
        kwargs["current_user_content"]
        == TRANSCRIPT
    )

    system_prompt = kwargs[
        "system_prompt"
    ]

    assert (
        "received by Corvus as spoken audio"
        in system_prompt
    )

    assert (
        "possible transcription errors"
        in system_prompt
    )

    assert (
        "cannot process audio"
        in system_prompt
    )

    return {
        "messages": [
            {
                "role": "system",
                "content": "system",
            },
            {
                "role": "user",
                "content": TRANSCRIPT,
            },
        ],
        "recent_message_ids": [],
        "historical_message_ids": [],
        "input_tokens": 20,
        "retrieval_status": "OK",
        "retrieval_error": None,
    }


def should_not_build_vision(
    *args,
    **kwargs,
):
    raise AssertionError(
        "voice turn entered vision adapter"
    )


def generate(messages):
    events.append("generate")

    assert (
        messages[-1]["content"]
        == TRANSCRIPT
    )

    return "voice reply"


def dense_sync(message_ids):
    events.append("dense")

    assert message_ids == [
        501,
        502,
    ]


result = process_turn(
    session_id="voice-session",
    user_content="[Voice message]",
    attachment_id="voice-att-1",
    attachment_mode="voice",
    add_message_fn=add_message,
    build_context_fn=build_context,
    count_tokens_fn=lambda messages: 0,
    generate_fn=generate,
    dense_sync_fn=dense_sync,
    system_prompt_fn=lambda: "system",
    link_attachment_fn=link_attachment,
    build_vision_messages_fn=(
        should_not_build_vision
    ),
    transcribe_attachment_fn=transcribe,
)

assert events == [
    "add:user",
    "link",
    "transcribe",
    "context",
    "generate",
    "add:assistant",
    "dense",
]

assert (
    result["attachment_status"]
    == "LINKED"
)

assert (
    result["transcription_status"]
    == "OK"
)

assert (
    result["transcript"]
    == TRANSCRIPT
)

assert (
    result["transcript_artifact_id"]
    == 77
)

assert (
    result["model_status"]
    == "OK"
)

assert (
    result["dense_status"]
    == "OK"
)

print(
    "VOICE SQLITE-FIRST ORDER OK"
)
print(
    "VOICE TRANSCRIPT PERCEPTION OK"
)
print(
    "VOICE CURRENT-TURN MODEL INPUT OK"
)


#
# STT failure must happen only after
# canonical message + raw attachment link.
#
events = []


def failure_add(
    session_id,
    role,
    content,
):
    events.append(
        f"add:{role}"
    )

    assert role == "user"
    assert content == "[Voice message]"

    return 601


def failure_link(
    message_id,
    attachment_id,
    *,
    ordinal,
):
    events.append("link")

    assert message_id == 601
    assert attachment_id == "voice-att-fail"


def failure_transcribe(
    attachment_id,
):
    events.append("transcribe")

    raise TranscriptionError(
        "TRANSCRIPTION_UNAVAILABLE",
        "STT server unavailable",
    )


failure_result = process_turn(
    session_id="voice-failure",
    user_content="[Voice message]",
    attachment_id="voice-att-fail",
    attachment_mode="voice",
    add_message_fn=failure_add,
    build_context_fn=lambda **kwargs: (
        (_ for _ in ()).throw(
            AssertionError(
                "context ran after STT failure"
            )
        )
    ),
    count_tokens_fn=lambda messages: 0,
    generate_fn=lambda messages: (
        (_ for _ in ()).throw(
            AssertionError(
                "model ran after STT failure"
            )
        )
    ),
    dense_sync_fn=lambda ids: (
        (_ for _ in ()).throw(
            AssertionError(
                "dense ran after STT failure"
            )
        )
    ),
    system_prompt_fn=lambda: "system",
    link_attachment_fn=failure_link,
    build_vision_messages_fn=(
        should_not_build_vision
    ),
    transcribe_attachment_fn=(
        failure_transcribe
    ),
)

assert events == [
    "add:user",
    "link",
    "transcribe",
]

assert (
    failure_result["user_message_id"]
    == 601
)

assert (
    failure_result["attachment_status"]
    == "LINKED"
)

assert (
    failure_result["transcription_status"]
    == "TRANSCRIPTION_UNAVAILABLE"
)

assert (
    failure_result["assistant_message_id"]
    is None
)

assert (
    failure_result["model_status"]
    == "NOT_CALLED"
)

assert (
    failure_result["dense_status"]
    == "NOT_RUN"
)

print(
    "STT FAILURE PRESERVES RAW EVIDENCE OK"
)

print(
    "A3.3 VOICE CONVERSATION RUNTIME: PASS"
)
