from app.conversation_runtime import (
    process_turn,
)
from app.web_evidence_prompt import (
    WebEvidencePromptError,
)
from app.web_evidence_select import (
    UsedWebEvidence,
)


def make_evidence():
    excerpt = (
        "The new compression.zstd module "
        "supports the Zstandard format."
    )

    return UsedWebEvidence(
        evidence_ref="web_1",
        ordinal=0,
        result_id="result_1",
        provider="fake-provider",
        source_url=(
            "https://example.com/article"
        ),
        source_title="Example Source",
        passage_id="passage_1",
        start_char=0,
        end_char=len(excerpt),
        excerpt=excerpt,
        score=10.0,
        matched_terms=(
            "compression",
            "zstandard",
        ),
        exact_phrase_match=False,
    )


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
        return 101

    return 102


def build_context(
    **kwargs,
):
    events.append(
        (
            "context",
            kwargs,
        )
    )

    web_content = kwargs[
        "web_evidence_content"
    ]

    return {
        "messages": [
            {
                "role": "system",
                "content": web_content,
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
        "input_tokens": 123,
        "retrieval_status": "OK",
        "retrieval_error": None,
    }


def generate(
    messages,
):
    events.append(
        (
            "generate",
            messages,
        )
    )

    system_content = (
        messages[0]["content"]
    )

    assert (
        "compression.zstd"
        in system_content
    )

    assert (
        "SOURCE [web_1]"
        in system_content
    )

    return (
        "Python 3.14 includes "
        "compression.zstd. [web_1]"
    )


def persist_web_evidence(
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
            evidence_items,
        )
    )

    assert len(
        evidence_items
    ) == 1

    item = evidence_items[0]

    expected = make_evidence()

    assert (
        item["ordinal"]
        == expected.ordinal
    )

    assert (
        item["source_url"]
        == expected.source_url
    )

    assert (
        item["source_title"]
        == expected.source_title
    )

    assert (
        item["excerpt"]
        == expected.excerpt
    )

    return [
        {
            "evidence_id": (
                "webev_runtime_1"
            ),
            "assistant_message_id": (
                assistant_message_id
            ),
            **item,
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
    session_id="session_1",
    user_content=(
        "Does Python 3.14 support Zstandard?"
    ),
    add_message_fn=add_message,
    build_context_fn=build_context,
    count_tokens_fn=lambda messages: 0,
    generate_fn=generate,
    dense_sync_fn=dense_sync,
    system_prompt_fn=lambda: "SYS",
    used_web_evidence=(
        make_evidence(),
    ),
    record_web_evidence_batch_fn=(
        persist_web_evidence
    ),
)

assert (
    result["user_message_id"]
    == 101
)

assert (
    result["assistant_message_id"]
    == 102
)

assert (
    result["model_status"]
    == "OK"
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
    result["web_evidence_refs"]
    == ["web_1"]
)

assert (
    result["web_evidence_prompt_chars"]
    > 0
)

assert (
    events[0][0:2]
    == (
        "add",
        "user",
    )
)

assert (
    events[1][0]
    == "context"
)

assert (
    events[2][0]
    == "generate"
)

assert (
    events[3][0:2]
    == (
        "add",
        "assistant",
    )
)

assert (
    events[4][0]
    == "persist_web"
)

assert (
    events[4][1]
    == 102
)

assert (
    events[4][2][0][
        "excerpt"
    ]
    == make_evidence().excerpt
)

assert (
    events[5]
    == (
        "dense",
        (
            101,
            102,
        ),
    )
)

print(
    "WEB RUNTIME SQLITE-FIRST CARRIER CONTRACT OK"
)
print(
    "WEB RUNTIME MODEL-INPUT CONTRACT OK"
)
print(
    "WEB RUNTIME EVIDENCE-REF CONTRACT OK"
)
print(
    "WEB RUNTIME EXACT-EVIDENCE "
    "PERSISTENCE CONTRACT OK"
)
print(
    "WEB RUNTIME ASSISTANT-BEFORE-PROVENANCE "
    "ORDER CONTRACT OK"
)


legacy_calls = []


def legacy_build_context(
    session_id,
    current_user_message_id,
    current_user_content,
    system_prompt,
    count_tokens,
):
    legacy_calls.append(
        True
    )

    return {
        "messages": [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": current_user_content,
            },
        ],
        "recent_message_ids": [],
        "historical_message_ids": [],
        "input_tokens": 10,
        "retrieval_status": "OK",
        "retrieval_error": None,
    }


legacy_result = process_turn(
    session_id="session_legacy",
    user_content="Hello",
    add_message_fn=lambda *args: (
        201
        if args[1] == "user"
        else 202
    ),
    build_context_fn=(
        legacy_build_context
    ),
    count_tokens_fn=lambda messages: 0,
    generate_fn=lambda messages: "Hi",
    dense_sync_fn=lambda ids: None,
    system_prompt_fn=lambda: "SYS",
)

assert legacy_calls == [True]

assert (
    legacy_result[
        "web_evidence_status"
    ]
    == "NOT_REQUESTED"
)

assert (
    legacy_result[
        "web_evidence_refs"
    ]
    == []
)

print(
    "NON-WEB RUNTIME BACKWARD-COMPATIBILITY CONTRACT OK"
)


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

    return 301


def fail_pack(
    evidence,
):
    failure_events.append(
        (
            "pack",
            len(evidence),
        )
    )

    raise WebEvidencePromptError(
        "WEB_EVIDENCE_PROMPT_TEST_FAILURE",
        "synthetic packing failure",
    )


failure_result = process_turn(
    session_id="session_failure",
    user_content="Use the Web",
    add_message_fn=failure_add_message,
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
    used_web_evidence=(
        make_evidence(),
    ),
    pack_web_evidence_fn=fail_pack,
)

assert (
    failure_result[
        "user_message_id"
    ]
    == 301
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
        "web_evidence_status"
    ]
    == (
        "WEB_EVIDENCE_PROMPT_TEST_FAILURE"
    )
)

assert failure_events == [
    (
        "add",
        "user",
    ),
    (
        "pack",
        1,
    ),
]

print(
    "WEB PACK FAILURE PRESERVES USER EVIDENCE OK"
)


persistence_failure_events = []


def persistence_failure_add_message(
    session_id,
    role,
    content,
):
    persistence_failure_events.append(
        (
            "add",
            role,
        )
    )

    if role == "user":
        return 401

    return 402


def persistence_failure_context(
    **kwargs,
):
    persistence_failure_events.append(
        (
            "context",
        )
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
        "input_tokens": 20,
        "retrieval_status": "OK",
        "retrieval_error": None,
    }


def persistence_failure_generate(
    messages,
):
    persistence_failure_events.append(
        (
            "generate",
        )
    )

    assert (
        "SOURCE [web_1]"
        in messages[0]["content"]
    )

    return (
        "Grounded reply [web_1]"
    )


def persistence_failure_store(
    assistant_message_id,
    evidence_items,
):
    evidence_items = tuple(
        evidence_items
    )

    persistence_failure_events.append(
        (
            "persist_web",
            assistant_message_id,
            len(evidence_items),
        )
    )

    assert assistant_message_id == 402
    assert len(evidence_items) == 1

    raise RuntimeError(
        "synthetic Web evidence "
        "persistence failure"
    )


def persistence_failure_dense(
    message_ids,
):
    persistence_failure_events.append(
        (
            "dense",
            tuple(message_ids),
        )
    )


persistence_failure_result = process_turn(
    session_id=(
        "session_persistence_failure"
    ),
    user_content=(
        "Use Web evidence"
    ),
    add_message_fn=(
        persistence_failure_add_message
    ),
    build_context_fn=(
        persistence_failure_context
    ),
    count_tokens_fn=lambda messages: 0,
    generate_fn=(
        persistence_failure_generate
    ),
    dense_sync_fn=(
        persistence_failure_dense
    ),
    system_prompt_fn=lambda: "SYS",
    used_web_evidence=(
        make_evidence(),
    ),
    record_web_evidence_batch_fn=(
        persistence_failure_store
    ),
)

assert (
    persistence_failure_result[
        "user_message_id"
    ]
    == 401
)

assert (
    persistence_failure_result[
        "assistant_message_id"
    ]
    == 402
)

assert (
    persistence_failure_result[
        "model_status"
    ]
    == "OK"
)

assert (
    persistence_failure_result[
        "web_evidence_status"
    ]
    == "USED_PERSISTENCE_FAILED"
)

assert (
    persistence_failure_result[
        "web_evidence_persisted_count"
    ]
    == 0
)

assert (
    persistence_failure_result[
        "persistence_status"
    ]
    == (
        "WEB_EVIDENCE_PERSISTENCE_DEGRADED"
    )
)

assert (
    "synthetic Web evidence persistence failure"
    in persistence_failure_result[
        "web_evidence_error"
    ]
)

assert (
    persistence_failure_result[
        "dense_status"
    ]
    == "OK"
)

assert persistence_failure_events == [
    (
        "add",
        "user",
    ),
    (
        "context",
    ),
    (
        "generate",
    ),
    (
        "add",
        "assistant",
    ),
    (
        "persist_web",
        402,
        1,
    ),
    (
        "dense",
        (
            401,
            402,
        ),
    ),
]

print(
    "WEB PERSISTENCE FAILURE "
    "PRESERVES ASSISTANT EVIDENCE OK"
)

print(
    "WEB PERSISTENCE FAILURE "
    "CONTINUES DENSE SYNC OK"
)

print(
    "A3_4C9D1_RUNTIME_WEB_CARRIER=PASS"
)

print(
    "A3_4C9D2B_RUNTIME_WEB_EVIDENCE_PERSISTENCE=PASS"
)
