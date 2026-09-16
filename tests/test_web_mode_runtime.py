from types import SimpleNamespace

from app.conversation_runtime import (
    process_turn,
)
from app.web_evidence_select import (
    UsedWebEvidence,
)


def make_evidence():
    excerpt = (
        "Python 3.14 includes the "
        "compression.zstd module."
    )

    return UsedWebEvidence(
        evidence_ref="web_1",
        ordinal=0,
        result_id="result_2",
        provider="fake-provider",
        source_url=(
            "https://example.org/python"
        ),
        source_title="Python Source",
        passage_id="passage_1",
        start_char=0,
        end_char=len(excerpt),
        excerpt=excerpt,
        score=12.0,
        matched_terms=(
            "python",
            "compression.zstd",
        ),
        exact_phrase_match=False,
    )


#
# Explicit Web mode success:
#
# canonical user commit
# -> Web grounding
# -> model
# -> assistant commit
# -> provenance persistence
# -> dense
#
events = []


def add_message(
    session_id,
    role,
    content,
):
    events.append(
        (
            "add",
            role,
            content,
        )
    )

    if role == "user":
        return 1001

    return 1002


def fake_provider_builder(
    attempt,
):
    raise AssertionError(
        "fake grounding owns provider handling"
    )



def identity_rewrite(
    query,
):
    return query


def prepare_grounding(
    query,
    *,
    provider_builder,
):
    events.append(
        (
            "ground",
            query,
        )
    )

    assert (
        provider_builder
        is fake_provider_builder
    )

    return SimpleNamespace(
        status="READY",
        selected_result_id="result_2",
        used_web_evidence=(
            make_evidence(),
        ),
    )


def pack_evidence(
    evidence,
):
    evidence = tuple(
        evidence
    )

    events.append(
        (
            "pack",
            len(evidence),
        )
    )

    assert len(evidence) == 1

    return SimpleNamespace(
        content=(
            "EXTERNAL WEB CONTEXT "
            "SOURCE [web_1] "
            + evidence[0].excerpt
        ),
        evidence_refs=(
            "web_1",
        ),
        packed_chars=100,
    )


def build_context(
    **kwargs,
):
    events.append(
        (
            "context",
            kwargs[
                "current_user_content"
            ],
        )
    )

    assert (
        "SOURCE [web_1]"
        in kwargs[
            "web_evidence_content"
        ]
    )

    return {
        "messages": [
            {
                "role": "system",
                "content": kwargs[
                    "web_evidence_content"
                ],
            },
            {
                "role": "user",
                "content": kwargs[
                    "current_user_content"
                ],
            },
        ],
        "recent_message_ids": [],
        "historical_message_ids": [],
        "input_tokens": 111,
        "retrieval_status": "OK",
        "retrieval_error": None,
    }


def generate(
    messages,
):
    events.append(
        (
            "generate",
        )
    )

    assert (
        "compression.zstd"
        in messages[0]["content"]
    )

    return (
        "Python 3.14 includes "
        "compression.zstd. [web_1]"
    )


def persist_web(
    assistant_message_id,
    evidence_items,
):
    evidence_items = tuple(
        evidence_items
    )

    events.append(
        (
            "persist_web",
            assistant_message_id,
            len(evidence_items),
        )
    )

    assert assistant_message_id == 1002
    assert len(evidence_items) == 1

    assert (
        evidence_items[0]["excerpt"]
        == make_evidence().excerpt
    )

    return [
        {
            "evidence_id": (
                "webev_runtime_mode_1"
            ),
            "assistant_message_id": (
                assistant_message_id
            ),
            **evidence_items[0],
        }
    ]


def dense_sync(
    message_ids,
):
    events.append(
        (
            "dense",
            tuple(message_ids),
        )
    )


result = process_turn(
    session_id="web-mode-success",
    user_content=(
        "What changed in Python 3.14?"
    ),
    add_message_fn=add_message,
    build_context_fn=build_context,
    count_tokens_fn=lambda messages: 0,
    generate_fn=generate,
    dense_sync_fn=dense_sync,
    system_prompt_fn=lambda: "SYS",
    pack_web_evidence_fn=(
        pack_evidence
    ),
    record_web_evidence_batch_fn=(
        persist_web
    ),
    web_mode="on",
    prepare_web_grounding_fn=(
        prepare_grounding
    ),
    web_provider_builder_fn=(
        fake_provider_builder
    ),
    web_query_rewrite_fn=(
        identity_rewrite
    ),
)


assert result["web_mode"] == "on"

assert (
    result["web_grounding_status"]
    == "READY"
)

assert (
    result[
        "web_grounding_selected_result_id"
    ]
    == "result_2"
)

assert (
    result["web_evidence_status"]
    == "PERSISTED"
)

assert (
    result[
        "web_evidence_persisted_count"
    ]
    == 1
)

assert (
    result["model_status"]
    == "OK"
)

assert events == [
    (
        "add",
        "user",
        "What changed in Python 3.14?",
    ),
    (
        "ground",
        "What changed in Python 3.14?",
    ),
    (
        "pack",
        1,
    ),
    (
        "context",
        "What changed in Python 3.14?",
    ),
    (
        "generate",
    ),
    (
        "add",
        "assistant",
        (
            "Python 3.14 includes "
            "compression.zstd. [web_1]"
        ),
    ),
    (
        "persist_web",
        1002,
        1,
    ),
    (
        "dense",
        (
            1001,
            1002,
        ),
    ),
]

print(
    "WEB MODE USER-COMMIT-BEFORE-GROUNDING CONTRACT OK"
)

print(
    "WEB MODE GROUNDING-TO-RUNTIME CONTRACT OK"
)

print(
    "WEB MODE EXACT-EVIDENCE PERSISTENCE CONTRACT OK"
)


#
# Default/off mode must never invoke Web orchestration.
#
off_calls = []


def must_not_ground(
    *args,
    **kwargs,
):
    off_calls.append(
        True
    )

    raise AssertionError(
        "Web grounding must not run "
        "when web_mode is off"
    )


off_result = process_turn(
    session_id="web-mode-off",
    user_content="Hello",
    add_message_fn=lambda *args: (
        2001
        if args[1] == "user"
        else 2002
    ),
    build_context_fn=lambda **kwargs: {
        "messages": [
            {
                "role": "system",
                "content": "SYS",
            },
            {
                "role": "user",
                "content": kwargs[
                    "current_user_content"
                ],
            },
        ],
        "recent_message_ids": [],
        "historical_message_ids": [],
        "input_tokens": 5,
        "retrieval_status": "OK",
        "retrieval_error": None,
    },
    count_tokens_fn=lambda messages: 0,
    generate_fn=lambda messages: "Hi",
    dense_sync_fn=lambda ids: None,
    system_prompt_fn=lambda: "SYS",
    prepare_web_grounding_fn=(
        must_not_ground
    ),
)

assert off_calls == []

assert off_result["web_mode"] == "off"

assert (
    off_result[
        "web_grounding_status"
    ]
    == "NOT_REQUESTED"
)

assert (
    off_result["web_evidence_status"]
    == "NOT_REQUESTED"
)

assert (
    off_result["model_status"]
    == "OK"
)

print(
    "WEB MODE OFF BACKWARD-COMPATIBILITY CONTRACT OK"
)


#
# Grounding failure occurs after the canonical user
# commit and before model inference.
#
failure_events = []


def failure_add_message(
    session_id,
    role,
    content,
):
    failure_events.append(
        (
            "add",
            role,
        )
    )

    if role != "user":
        raise AssertionError(
            "assistant must not be persisted"
        )

    return 3001


def fail_grounding(
    query,
    *,
    provider_builder,
):
    failure_events.append(
        (
            "ground",
            query,
        )
    )

    raise RuntimeError(
        "synthetic Web grounding failure"
    )


failure_result = process_turn(
    session_id="web-mode-failure",
    user_content="Search this",
    add_message_fn=(
        failure_add_message
    ),
    build_context_fn=lambda **kwargs: (
        (_ for _ in ()).throw(
            AssertionError(
                "context must not run"
            )
        )
    ),
    count_tokens_fn=lambda messages: 0,
    generate_fn=lambda messages: (
        (_ for _ in ()).throw(
            AssertionError(
                "model must not run"
            )
        )
    ),
    dense_sync_fn=lambda ids: (
        (_ for _ in ()).throw(
            AssertionError(
                "dense must not run"
            )
        )
    ),
    system_prompt_fn=lambda: "SYS",
    web_mode="on",
    prepare_web_grounding_fn=(
        fail_grounding
    ),
    web_provider_builder_fn=(
        fake_provider_builder
    ),
    web_query_rewrite_fn=(
        identity_rewrite
    ),
)

assert (
    failure_result[
        "user_message_id"
    ]
    == 3001
)

assert (
    failure_result[
        "assistant_message_id"
    ]
    is None
)

assert (
    failure_result[
        "model_status"
    ]
    == "NOT_CALLED"
)

assert (
    failure_result[
        "web_grounding_status"
    ]
    == "WEB_GROUNDING_FAILED"
)

assert (
    failure_result[
        "web_evidence_status"
    ]
    == "NOT_AVAILABLE"
)

assert (
    "synthetic Web grounding failure"
    in failure_result[
        "web_grounding_error"
    ]
)

assert failure_events == [
    (
        "add",
        "user",
    ),
    (
        "ground",
        "Search this",
    ),
]

print(
    "WEB MODE FAILURE PRESERVES USER EVIDENCE OK"
)

print(
    "WEB MODE FAILURE BLOCKS UNGROUNDED MODEL ANSWER OK"
)


#
# A valid orchestration run with no usable evidence
# also fails closed after user persistence.
#
no_evidence_events = []


def no_evidence_add_message(
    session_id,
    role,
    content,
):
    no_evidence_events.append(
        (
            "add",
            role,
        )
    )

    if role != "user":
        raise AssertionError(
            "assistant must not be persisted"
        )

    return 4001


def no_evidence_grounding(
    query,
    *,
    provider_builder,
):
    no_evidence_events.append(
        (
            "ground",
            query,
        )
    )

    return SimpleNamespace(
        status="NO_RESULTS",
        selected_result_id=None,
        used_web_evidence=(),
    )


no_evidence_result = process_turn(
    session_id="web-mode-no-evidence",
    user_content="Search impossible thing",
    add_message_fn=(
        no_evidence_add_message
    ),
    build_context_fn=lambda **kwargs: (
        (_ for _ in ()).throw(
            AssertionError(
                "context must not run"
            )
        )
    ),
    count_tokens_fn=lambda messages: 0,
    generate_fn=lambda messages: (
        (_ for _ in ()).throw(
            AssertionError(
                "model must not run"
            )
        )
    ),
    dense_sync_fn=lambda ids: None,
    system_prompt_fn=lambda: "SYS",
    web_mode="on",
    prepare_web_grounding_fn=(
        no_evidence_grounding
    ),
    web_provider_builder_fn=(
        fake_provider_builder
    ),
    web_query_rewrite_fn=(
        identity_rewrite
    ),
)

assert (
    no_evidence_result[
        "user_message_id"
    ]
    == 4001
)

assert (
    no_evidence_result[
        "assistant_message_id"
    ]
    is None
)

assert (
    no_evidence_result[
        "web_grounding_status"
    ]
    == "NO_RESULTS"
)

assert (
    no_evidence_result[
        "web_evidence_status"
    ]
    == "NOT_AVAILABLE"
)

assert (
    no_evidence_result[
        "model_status"
    ]
    == "NOT_CALLED"
)

assert no_evidence_events == [
    (
        "add",
        "user",
    ),
    (
        "ground",
        "Search impossible thing",
    ),
]

print(
    "WEB MODE NO-EVIDENCE FAIL-CLOSED CONTRACT OK"
)

print(
    "A3_4_WEB_MODE_RUNTIME_ACTIVATION=PASS"
)
