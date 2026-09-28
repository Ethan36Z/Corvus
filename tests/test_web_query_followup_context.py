from types import SimpleNamespace

from app.conversation_runtime import (
    process_turn,
)
from app.web_evidence_select import (
    UsedWebEvidence,
)
from app.web_query_rewrite import (
    WEB_QUERY_RECENT_SCAN_LIMIT,
    build_web_query_rewrite_input,
    rewrite_web_query,
    select_web_query_rewrite_context,
)


CURRENT = (
    "那你查一下目前民调吧"
)


RECENT = [
    {
        "id": 163,
        "session_id": "followup",
        "role": "user",
        "content": (
            "现在你能帮我查一下接下来7天的天气吗"
        ),
    },
    {
        "id": 164,
        "session_id": "followup",
        "role": "assistant",
        "content": (
            "我无法直接联网查询未来7天实时天气。"
        ),
    },
    {
        "id": 173,
        "session_id": "followup",
        "role": "user",
        "content": "[Voice message]",
    },
    {
        "id": 174,
        "session_id": "followup",
        "role": "user",
        "content": (
            "你觉得今年美国中期选举谁会赢呢"
        ),
    },
    {
        "id": 175,
        "session_id": "followup",
        "role": "assistant",
        "content": (
            "我无法预测选举结果。"
        ),
    },
    {
        "id": 176,
        "session_id": "followup",
        "role": "user",
        "content": CURRENT,
    },
]


selected = (
    select_web_query_rewrite_context(
        RECENT,
        CURRENT,
    )
)

assert [
    item["id"]
    for item in selected
] == [
    174,
    175,
]

print(
    "WEB FOLLOW-UP CONTEXT SELECTION CONTRACT OK"
)


rewrite_input = (
    build_web_query_rewrite_input(
        CURRENT,
        selected,
        current_date="2026-09-16",
    )
)

assert (
    rewrite_input.startswith(
        "Current date: 2026-09-16"
    )
)

assert (
    "美国中期选举"
    in rewrite_input
)

assert (
    "7天的天气"
    not in rewrite_input
)

assert (
    rewrite_input.count(
        CURRENT
    )
    == 1
)

print(
    "WEB FOLLOW-UP DATE-ANCHOR CONTRACT OK"
)


generated_messages = []


def fake_generate(
    messages,
):
    generated_messages.append(
        messages
    )

    return (
        "2026 US midterm election polls"
    )


rewritten = rewrite_web_query(
    rewrite_input,
    generate_fn=fake_generate,
)

assert rewritten == (
    "2026 US midterm election polls"
)

assert (
    "Current date: 2026-09-16"
    in generated_messages[0][1][
        "content"
    ]
)

print(
    "WEB FOLLOW-UP REWRITE MODEL CONTRACT OK"
)


#
# Standalone queries retain the previous compact input
# shape and do not gain unnecessary context/date text.
#
assert (
    build_web_query_rewrite_input(
        "Python 3.14 documentation",
        [],
        current_date="2026-09-16",
    )
    == "Python 3.14 documentation"
)

print(
    "WEB STANDALONE REWRITE BACKWARD CONTRACT OK"
)


def make_evidence():
    excerpt = (
        "Current polling evidence."
    )

    return UsedWebEvidence(
        evidence_ref="web_1",
        ordinal=0,
        result_id="result_1",
        provider="fake",
        source_url=(
            "https://example.com/polls"
        ),
        source_title="Polls",
        passage_id="p1",
        start_char=0,
        end_char=len(excerpt),
        excerpt=excerpt,
        score=1.0,
        matched_terms=(
            "polls",
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
        )
    )

    return (
        177
        if role == "user"
        else 178
    )


def load_recent(
    *,
    session_id,
    limit,
    before_message_id,
):
    assert session_id == "followup"
    assert (
        limit
        == WEB_QUERY_RECENT_SCAN_LIMIT
    )
    assert before_message_id == 177

    events.append(
        (
            "recent",
        )
    )

    return RECENT


def rewrite(
    query,
):
    events.append(
        (
            "rewrite",
        )
    )

    assert (
        "Current date:"
        in query
    )

    assert (
        "美国中期选举"
        in query
    )

    assert (
        "7天的天气"
        not in query
    )

    assert (
        query.count(
            CURRENT
        )
        == 1
    )

    return (
        "2026 US midterm election polls"
    )


def ground(
    query,
    *,
    provider_builder,
):
    events.append(
        (
            "ground",
        )
    )

    assert query == (
        "2026 US midterm election polls"
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
    items = tuple(
        evidence
    )

    return SimpleNamespace(
        content=(
            "[web_1] "
            + items[0].excerpt
        ),
        evidence_refs=(
            "web_1",
        ),
        packed_chars=40,
    )


def context(
    **kwargs,
):
    assert (
        kwargs["current_user_content"]
        == CURRENT
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
                "content": CURRENT,
            },
        ],
        "recent_message_ids": [],
        "historical_message_ids": [],
        "input_tokens": 20,
        "retrieval_status": "OK",
        "retrieval_error": None,
    }


result = process_turn(
    session_id="followup",
    user_content=CURRENT,
    add_message_fn=add_message,
    build_context_fn=context,
    count_tokens_fn=lambda messages: 0,
    generate_fn=lambda messages: (
        "Grounded response [web_1]"
    ),
    dense_sync_fn=lambda ids: None,
    system_prompt_fn=lambda: "SYS",
    web_mode="on",
    web_query_recent_loader_fn=(
        load_recent
    ),
    web_query_rewrite_fn=rewrite,
    prepare_web_grounding_fn=ground,
    web_provider_builder_fn=(
        lambda attempt: None
    ),
    pack_web_evidence_fn=pack,
    record_web_evidence_batch_fn=(
        lambda assistant_id, items: [
            {
                "evidence_id": "webev_1",
            }
        ]
    ),
)

assert (
    result["web_search_query"]
    == "2026 US midterm election polls"
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
    "recent",
    "rewrite",
    "ground",
    "add",
]

print(
    "WEB FOLLOW-UP RUNTIME POLICY CONTRACT OK"
)

print(
    "WEB_QUERY_FOLLOWUP_CONTEXT=PASS"
)
