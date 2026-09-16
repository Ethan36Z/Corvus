from types import SimpleNamespace

from app.conversation_runtime import (
    process_turn,
)
from app.web_evidence_select import (
    UsedWebEvidence,
)
from app.web_intent_gate import (
    WebIntentDecision,
)


def context_without_web(
    **kwargs,
):
    assert (
        "web_evidence_content"
        not in kwargs
    )

    return {
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
        "input_tokens": 10,
        "retrieval_status": "OK",
        "retrieval_error": None,
    }


#
# AUTO -> NO_WEB:
# gate exactly once, grounding never runs,
# normal answer continues.
#
events = []


def add_no_web(
    session_id,
    role,
    content,
):
    events.append(
        (
            "add",
            role,
        )
    )

    return (
        1
        if role == "user"
        else 2
    )


def no_web_gate(
    query,
):
    events.append(
        (
            "gate",
            query,
        )
    )

    return WebIntentDecision(
        decision="NO_WEB",
        source="MODEL",
    )


def must_not_ground(
    *args,
    **kwargs,
):
    raise AssertionError(
        "grounding must not run "
        "for AUTO -> NO_WEB"
    )


def generate_no_web(
    messages,
):
    events.append(
        (
            "generate",
        )
    )

    return "Normal answer"


result = process_turn(
    session_id="auto-no-web",
    user_content="Explain JWT.",
    add_message_fn=add_no_web,
    build_context_fn=context_without_web,
    count_tokens_fn=lambda messages: 0,
    generate_fn=generate_no_web,
    dense_sync_fn=lambda ids: None,
    system_prompt_fn=lambda: "SYS",
    web_mode="auto",
    web_intent_decide_fn=no_web_gate,
    prepare_web_grounding_fn=must_not_ground,
)

assert result["web_mode"] == "auto"
assert (
    result["web_intent_decision"]
    == "NO_WEB"
)
assert (
    result["web_intent_source"]
    == "MODEL"
)
assert (
    result["web_grounding_status"]
    == "NOT_REQUESTED"
)
assert result["model_status"] == "OK"

assert events == [
    (
        "add",
        "user",
    ),
    (
        "gate",
        "Explain JWT.",
    ),
    (
        "generate",
    ),
    (
        "add",
        "assistant",
    ),
]

print(
    "AUTO WEB NO-WEB ONE-SHOT CONTRACT OK"
)


#
# AUTO -> WEB:
# gate exactly once, then existing bounded
# Web grounding path.
#
events = []


def make_evidence():
    excerpt = (
        "Current official documentation "
        "describes compression.zstd."
    )

    return UsedWebEvidence(
        evidence_ref="web_1",
        ordinal=0,
        result_id="result_1",
        provider="fake",
        source_url=(
            "https://example.org/docs"
        ),
        source_title="Docs",
        passage_id="p1",
        start_char=0,
        end_char=len(excerpt),
        excerpt=excerpt,
        score=1.0,
        matched_terms=("compression.zstd",),
        exact_phrase_match=True,
    )


def add_web(
    session_id,
    role,
    content,
):
    events.append(
        (
            "add",
            role,
        )
    )

    return (
        11
        if role == "user"
        else 12
    )


def web_gate(
    query,
):
    events.append(
        (
            "gate",
            query,
        )
    )

    return WebIntentDecision(
        decision="WEB",
        source="DETERMINISTIC",
        signal="current_documentation_en",
    )


def identity_rewrite(
    query,
):
    events.append(
        (
            "rewrite",
            query,
        )
    )

    return query


def ground(
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

    return SimpleNamespace(
        status="READY",
        selected_result_id="result_1",
        used_web_evidence=(
            make_evidence(),
        ),
    )


def pack(
    evidence,
):
    evidence = tuple(
        evidence
    )

    return SimpleNamespace(
        content=(
            "SOURCE [web_1] "
            + evidence[0].excerpt
        ),
        evidence_refs=("web_1",),
        packed_chars=80,
    )


def context_with_web(
    **kwargs,
):
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
        "input_tokens": 20,
        "retrieval_status": "OK",
        "retrieval_error": None,
    }


def generate_web(
    messages,
):
    events.append(
        (
            "generate",
        )
    )

    return "Grounded answer [web_1]"


def persist_web(
    assistant_message_id,
    evidence_items,
):
    items = tuple(
        evidence_items
    )

    assert assistant_message_id == 12
    assert len(items) == 1

    events.append(
        (
            "persist",
        )
    )

    return [
        {
            "evidence_id": "webev_auto_1",
            "assistant_message_id": 12,
            **items[0],
        }
    ]


result = process_turn(
    session_id="auto-web",
    user_content=(
        "According to the current documentation, "
        "what is compression.zstd?"
    ),
    add_message_fn=add_web,
    build_context_fn=context_with_web,
    count_tokens_fn=lambda messages: 0,
    generate_fn=generate_web,
    dense_sync_fn=lambda ids: None,
    system_prompt_fn=lambda: "SYS",
    web_mode="auto",
    web_intent_decide_fn=web_gate,
    web_query_rewrite_fn=identity_rewrite,
    prepare_web_grounding_fn=ground,
    web_provider_builder_fn=lambda attempt: None,
    pack_web_evidence_fn=pack,
    record_web_evidence_batch_fn=(
        persist_web
    ),
)

assert result["web_mode"] == "auto"
assert (
    result["web_intent_decision"]
    == "WEB"
)
assert (
    result["web_intent_source"]
    == "DETERMINISTIC"
)
assert (
    result["web_intent_signal"]
    == "current_documentation_en"
)
assert (
    result["web_grounding_status"]
    == "READY"
)
assert (
    result["web_evidence_status"]
    == "PERSISTED"
)

assert [
    event[0]
    for event in events
] == [
    "add",
    "gate",
    "rewrite",
    "ground",
    "generate",
    "add",
    "persist",
]

assert sum(
    1
    for event in events
    if event[0] == "gate"
) == 1

print(
    "AUTO WEB GROUNDING ONE-SHOT CONTRACT OK"
)


#
# Forced modes must bypass Auto gate.
#
def forbidden_gate(
    query,
):
    raise AssertionError(
        "forced mode must bypass "
        "Web Intent Gate"
    )


forced_off = process_turn(
    session_id="forced-off",
    user_content="Hello",
    add_message_fn=lambda s, r, c: (
        21
        if r == "user"
        else 22
    ),
    build_context_fn=context_without_web,
    count_tokens_fn=lambda messages: 0,
    generate_fn=lambda messages: "Hi",
    dense_sync_fn=lambda ids: None,
    system_prompt_fn=lambda: "SYS",
    web_mode="off",
    web_intent_decide_fn=forbidden_gate,
)

assert (
    forced_off[
        "web_intent_source"
    ]
    == "FORCED_OFF"
)

print(
    "FORCED WEB MODE BYPASS CONTRACT OK"
)

print(
    "A3_4_AUTO_WEB_RUNTIME=PASS"
)
