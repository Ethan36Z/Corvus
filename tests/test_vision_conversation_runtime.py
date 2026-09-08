import inspect

from app.conversation_runtime import (
    process_turn,
)
from app.vision_input import (
    VisionInputError,
)


#
# Existing positional dependency-injection
# boundary must not move.
#
parameter_names = list(
    inspect.signature(
        process_turn
    ).parameters
)

assert parameter_names[:8] == [
    "session_id",
    "user_content",
    "add_message_fn",
    "build_context_fn",
    "count_tokens_fn",
    "generate_fn",
    "dense_sync_fn",
    "system_prompt_fn",
]

print(
    "RUNTIME BACKWARD SIGNATURE CONTRACT OK"
)


def context_result(user_content):
    return {
        "messages": [
            {
                "role": "system",
                "content": "system",
            },
            {
                "role": "user",
                "content": user_content,
            },
        ],
        "recent_message_ids": [],
        "historical_message_ids": [],
        "input_tokens": 12,
        "retrieval_status": "OK",
        "retrieval_error": None,
    }


#
# Text-only conversation remains unchanged.
#
events = []


def text_add_message(
    session_id,
    role,
    content,
):
    events.append(
        f"add:{role}"
    )

    if role == "user":
        assert content == "hello"
        return 101

    assert content == "text reply"
    return 102


def text_build_context(**kwargs):
    events.append("context")

    assert (
        kwargs["current_user_message_id"]
        == 101
    )

    assert (
        kwargs["current_user_content"]
        == "hello"
    )

    return context_result(
        "hello"
    )


def text_generate(messages):
    events.append("generate")

    assert (
        messages[-1]["content"]
        == "hello"
    )

    return "text reply"


def should_not_link(*args, **kwargs):
    raise AssertionError(
        "text turn attempted attachment link"
    )


def should_not_build_vision(
    *args,
    **kwargs,
):
    raise AssertionError(
        "text turn attempted vision conversion"
    )


def text_dense(message_ids):
    events.append("dense")

    assert message_ids == [
        101,
        102,
    ]


text_result = process_turn(
    session_id="text-session",
    user_content="hello",
    add_message_fn=text_add_message,
    build_context_fn=text_build_context,
    count_tokens_fn=lambda messages: 0,
    generate_fn=text_generate,
    dense_sync_fn=text_dense,
    system_prompt_fn=lambda: "system",
    link_attachment_fn=should_not_link,
    build_vision_messages_fn=(
        should_not_build_vision
    ),
)

assert events == [
    "add:user",
    "context",
    "generate",
    "add:assistant",
    "dense",
]

assert (
    text_result["attachment_status"]
    == "NOT_REQUESTED"
)

assert text_result["model_status"] == "OK"
assert text_result["dense_status"] == "OK"

print(
    "TEXT TURN REGRESSION CONTRACT OK"
)


#
# Vision turn order:
# canonical text -> attachment provenance ->
# text Working Context -> transient multimodal
# input -> model -> assistant -> dense.
#
events = []


def vision_add_message(
    session_id,
    role,
    content,
):
    events.append(
        f"add:{role}"
    )

    if role == "user":
        assert (
            content
            == "What is in this image?"
        )
        return 201

    assert content == "vision reply"
    return 202


def vision_link(
    message_id,
    attachment_id,
    *,
    ordinal,
):
    events.append("link")

    assert message_id == 201
    assert attachment_id == "att-vision-1"
    assert ordinal == 0


def vision_build_context(**kwargs):
    events.append("context")

    assert (
        kwargs["current_user_message_id"]
        == 201
    )

    assert (
        kwargs["current_user_content"]
        == "What is in this image?"
    )

    return context_result(
        "What is in this image?"
    )


def vision_convert(
    messages,
    attachment_id,
):
    events.append("vision")

    assert attachment_id == "att-vision-1"

    #
    # Working Context reaching the adapter
    # is still pure text.
    #
    assert isinstance(
        messages[-1]["content"],
        str,
    )

    converted = [
        dict(message)
        for message in messages
    ]

    converted[-1] = {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": (
                    "What is in this image?"
                ),
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": (
                        "data:image/png;base64,"
                        "TEST"
                    ),
                },
            },
        ],
    }

    return {
        "messages": converted,
        "attachment": {
            "id": attachment_id,
        },
    }


def vision_generate(messages):
    events.append("generate")

    parts = messages[-1]["content"]

    assert isinstance(parts, list)

    assert (
        parts[0]["text"]
        == "What is in this image?"
    )

    assert (
        parts[1]["type"]
        == "image_url"
    )

    return "vision reply"


def vision_dense(message_ids):
    events.append("dense")

    assert message_ids == [
        201,
        202,
    ]


vision_result = process_turn(
    session_id="vision-session",
    user_content="What is in this image?",
    add_message_fn=vision_add_message,
    build_context_fn=vision_build_context,
    count_tokens_fn=lambda messages: 0,
    generate_fn=vision_generate,
    dense_sync_fn=vision_dense,
    system_prompt_fn=lambda: "system",
    attachment_id="att-vision-1",
    link_attachment_fn=vision_link,
    build_vision_messages_fn=vision_convert,
)

assert events == [
    "add:user",
    "link",
    "context",
    "vision",
    "generate",
    "add:assistant",
    "dense",
]

assert (
    vision_result["attachment_status"]
    == "USED"
)

assert (
    vision_result["attachment_id"]
    == "att-vision-1"
)

assert vision_result["model_status"] == "OK"
assert vision_result["dense_status"] == "OK"

print(
    "VISION TURN ORDER CONTRACT OK"
)


#
# Attachment-link failure must not erase
# the canonical user message.
#
events = []


def link_failure_add(
    session_id,
    role,
    content,
):
    events.append(
        f"add:{role}"
    )

    assert role == "user"
    return 301


def link_failure(
    message_id,
    attachment_id,
    *,
    ordinal,
):
    events.append("link")

    raise RuntimeError(
        "attachment link failed"
    )


link_failure_result = process_turn(
    session_id="link-failure",
    user_content="keep this evidence",
    add_message_fn=link_failure_add,
    build_context_fn=lambda **kwargs: (
        (_ for _ in ()).throw(
            AssertionError(
                "context ran after link failure"
            )
        )
    ),
    count_tokens_fn=lambda messages: 0,
    generate_fn=lambda messages: (
        (_ for _ in ()).throw(
            AssertionError(
                "model ran after link failure"
            )
        )
    ),
    dense_sync_fn=lambda ids: None,
    system_prompt_fn=lambda: "system",
    attachment_id="missing",
    link_attachment_fn=link_failure,
    build_vision_messages_fn=vision_convert,
)

assert events == [
    "add:user",
    "link",
]

assert (
    link_failure_result["user_message_id"]
    == 301
)

assert (
    link_failure_result[
        "assistant_message_id"
    ]
    is None
)

assert (
    link_failure_result["attachment_status"]
    == "LINK_FAILED"
)

assert (
    link_failure_result["model_status"]
    == "NOT_CALLED"
)

assert (
    link_failure_result["dense_status"]
    == "NOT_RUN"
)

print(
    "LINK FAILURE PRESERVES USER EVIDENCE OK"
)


#
# Vision validation failure happens only
# after canonical text + provenance link.
#
events = []


def invalid_vision_add(
    session_id,
    role,
    content,
):
    events.append(
        f"add:{role}"
    )

    assert role == "user"
    return 401


def invalid_vision_link(
    message_id,
    attachment_id,
    *,
    ordinal,
):
    events.append("link")


def invalid_vision_context(**kwargs):
    events.append("context")

    return context_result(
        "inspect this"
    )


def invalid_vision_convert(
    messages,
    attachment_id,
):
    events.append("vision")

    raise VisionInputError(
        "unsupported image"
    )


invalid_result = process_turn(
    session_id="invalid-vision",
    user_content="inspect this",
    add_message_fn=invalid_vision_add,
    build_context_fn=invalid_vision_context,
    count_tokens_fn=lambda messages: 0,
    generate_fn=lambda messages: (
        (_ for _ in ()).throw(
            AssertionError(
                "model ran after invalid vision"
            )
        )
    ),
    dense_sync_fn=lambda ids: None,
    system_prompt_fn=lambda: "system",
    attachment_id="att-invalid",
    link_attachment_fn=invalid_vision_link,
    build_vision_messages_fn=(
        invalid_vision_convert
    ),
)

assert events == [
    "add:user",
    "link",
    "context",
    "vision",
]

assert invalid_result[
    "user_message_id"
] == 401

assert (
    invalid_result["attachment_status"]
    == "VISION_INPUT_FAILED"
)

assert (
    invalid_result["model_status"]
    == "VISION_INPUT_INVALID"
)

assert (
    invalid_result["assistant_message_id"]
    is None
)

assert (
    invalid_result["dense_status"]
    == "NOT_RUN"
)

print(
    "VISION FAILURE PRESERVES CANONICAL EVIDENCE OK"
)

print(
    "A3 VISION CONVERSATION RUNTIME: PASS"
)
