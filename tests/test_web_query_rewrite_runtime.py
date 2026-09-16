from types import SimpleNamespace

from app.conversation_runtime import (
    process_turn,
)
from app.web_evidence_select import (
    UsedWebEvidence,
)


ORIGINAL = (
    "According to the current Python 3.14 "
    "documentation, what is the "
    "compression.zstd module? "
    "Use current Web evidence."
)

REWRITTEN = (
    "Python 3.14 documentation "
    "compression.zstd module"
)


def make_evidence():
    excerpt = (
        "compression.zstd provides APIs "
        "for the Zstandard format."
    )

    return UsedWebEvidence(
        evidence_ref="web_1",
        ordinal=0,
        result_id="result_1",
        provider="ddgs",
        source_url=(
            "https://docs.python.org/3/"
            "library/compression.zstd.html"
        ),
        source_title=(
            "compression.zstd — "
            "Python documentation"
        ),
        passage_id="passage_1",
        start_char=0,
        end_char=len(excerpt),
        excerpt=excerpt,
        score=10.0,
        matched_terms=(
            "compression.zstd",
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

    return (
        6001
        if role == "user"
        else 6002
    )


def rewrite(
    query,
):
    events.append(
        (
            "rewrite",
            query,
        )
    )

    assert query == ORIGINAL

    return REWRITTEN


def provider_builder(
    attempt,
):
    raise AssertionError(
        "fake grounding owns provider handling"
    )


def grounding(
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

    assert query == REWRITTEN

    return SimpleNamespace(
        status="READY",
        selected_result_id="result_1",
        used_web_evidence=(
            make_evidence(),
        ),
    )


def context(
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

    #
    # The model still receives the original user
    # request. Rewrite is discovery-only.
    #
    assert (
        kwargs[
            "current_user_content"
        ]
        == ORIGINAL
    )

    assert (
        "compression.zstd"
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
                "content": ORIGINAL,
            },
        ],
        "recent_message_ids": [],
        "historical_message_ids": [],
        "input_tokens": 100,
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
        messages[-1]["content"]
        == ORIGINAL
    )

    return (
        "It provides Zstandard "
        "compression APIs. [web_1]"
    )


def persist_web(
    assistant_message_id,
    evidence_items,
):
    events.append(
        (
            "persist_web",
            assistant_message_id,
        )
    )

    assert assistant_message_id == 6002

    return [
        {
            "evidence_id": "webev_1",
        }
    ]


def dense(
    message_ids,
):
    events.append(
        (
            "dense",
            tuple(message_ids),
        )
    )


result = process_turn(
    session_id="rewrite-runtime",
    user_content=ORIGINAL,
    add_message_fn=add_message,
    build_context_fn=context,
    count_tokens_fn=lambda messages: 0,
    generate_fn=generate,
    dense_sync_fn=dense,
    system_prompt_fn=lambda: "SYS",
    record_web_evidence_batch_fn=(
        persist_web
    ),
    web_mode="on",
    prepare_web_grounding_fn=(
        grounding
    ),
    web_provider_builder_fn=(
        provider_builder
    ),
    web_query_rewrite_fn=rewrite,
)


assert (
    result[
        "web_query_rewrite_status"
    ]
    == "OK"
)

assert (
    result["web_search_query"]
    == REWRITTEN
)

assert (
    result[
        "web_query_rewrite_error"
    ]
    is None
)

assert (
    result["web_grounding_status"]
    == "READY"
)

assert result["model_status"] == "OK"

assert events[0] == (
    "add",
    "user",
    ORIGINAL,
)

assert events[1] == (
    "rewrite",
    ORIGINAL,
)

assert events[2] == (
    "ground",
    REWRITTEN,
)

assert events[3] == (
    "context",
    ORIGINAL,
)

print(
    "WEB QUERY REWRITE SQLITE-FIRST ORDER CONTRACT OK"
)

print(
    "WEB QUERY REWRITE DISCOVERY-ONLY CONTRACT OK"
)

print(
    "WEB QUERY REWRITE ORIGINAL-USER-CONTENT CONTRACT OK"
)


#
# Rewrite degradation must fall back to the original
# query instead of taking Web mode down.
#

fallback_ground_queries = []


def fail_rewrite(
    query,
):
    raise RuntimeError(
        "synthetic rewrite failure"
    )


def fallback_grounding(
    query,
    *,
    provider_builder,
):
    fallback_ground_queries.append(
        query
    )

    return SimpleNamespace(
        status="READY",
        selected_result_id="result_1",
        used_web_evidence=(
            make_evidence(),
        ),
    )


fallback_result = process_turn(
    session_id="rewrite-fallback",
    user_content=ORIGINAL,
    add_message_fn=lambda *args: (
        7001
        if args[1] == "user"
        else 7002
    ),
    build_context_fn=context,
    count_tokens_fn=lambda messages: 0,
    generate_fn=lambda messages: (
        "Fallback grounded answer [web_1]"
    ),
    dense_sync_fn=lambda ids: None,
    system_prompt_fn=lambda: "SYS",
    record_web_evidence_batch_fn=(
        lambda assistant_id, items: [
            {
                "evidence_id": "webev_2",
            }
        ]
    ),
    web_mode="on",
    prepare_web_grounding_fn=(
        fallback_grounding
    ),
    web_provider_builder_fn=(
        provider_builder
    ),
    web_query_rewrite_fn=(
        fail_rewrite
    ),
)


assert (
    fallback_result[
        "web_query_rewrite_status"
    ]
    == "FALLBACK_ORIGINAL"
)

assert (
    fallback_result[
        "web_search_query"
    ]
    == ORIGINAL
)

assert (
    "synthetic rewrite failure"
    in fallback_result[
        "web_query_rewrite_error"
    ]
)

assert fallback_ground_queries == [
    ORIGINAL
]

assert (
    fallback_result["model_status"]
    == "OK"
)

print(
    "WEB QUERY REWRITE FALLBACK CONTRACT OK"
)

print(
    "A3_4_WEB_QUERY_REWRITE_RUNTIME=PASS"
)
