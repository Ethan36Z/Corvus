import app.working_context as working_context


RECENT_MESSAGES = [
    {
        "id": 90,
        "session_id": "session_1",
        "role": "user",
        "content": "U" * 40,
    },
    {
        "id": 91,
        "session_id": "session_1",
        "role": "assistant",
        "content": "A" * 40,
    },
]


def count_chars(
    messages,
):
    total = 0

    for message in messages:
        content = message["content"]

        if not isinstance(
            content,
            str,
        ):
            raise AssertionError(
                "test expects text-only messages"
            )

        total += len(
            content
        )

    return total


def load_recent_messages(
    session_id,
    limit,
    before_message_id=None,
):
    assert session_id == "session_1"

    return list(
        RECENT_MESSAGES
    )


def search_history(
    query,
    limit,
    candidate_limit,
):
    return [
        {
            "id": 10,
            "session_id": "old_session",
            "role": "user",
            "content": "H" * 500,
        }
    ]


original_loader = (
    working_context.load_recent_messages
)

working_context.load_recent_messages = (
    load_recent_messages
)

try:
    web_block = (
        "WEB_EVIDENCE_BLOCK:"
        + "W" * 80
    )

    context = (
        working_context.build_working_context(
            session_id="session_1",
            current_user_message_id=100,
            current_user_content="CURRENT",
            system_prompt="SYS",
            count_tokens=count_chars,
            web_evidence_content=web_block,
            recent_token_budget=1000,
            historical_token_budget=5000,
            input_token_budget=250,
            historical_limit=5,
            search_fn=search_history,
        )
    )

    assert (
        context["input_tokens"]
        <= 250
    )

    assert (
        context["historical_evidence"]
        == []
    )

    assert (
        context["recent_message_ids"]
        == [90, 91]
    )

    assert (
        web_block
        in context["messages"][0]["content"]
    )

    assert (
        context["web_evidence_included"]
        is True
    )

    assert (
        context[
            "web_evidence_prompt_chars"
        ]
        == len(web_block)
    )

    print(
        "WEB CONTEXT HISTORICAL-FIRST EVICTION CONTRACT OK"
    )

    larger_web_block = (
        "WEB_EVIDENCE_BLOCK:"
        + "W" * 140
    )

    context = (
        working_context.build_working_context(
            session_id="session_1",
            current_user_message_id=100,
            current_user_content="CURRENT",
            system_prompt="SYS",
            count_tokens=count_chars,
            web_evidence_content=larger_web_block,
            recent_token_budget=1000,
            historical_token_budget=5000,
            input_token_budget=190,
            historical_limit=5,
            search_fn=search_history,
        )
    )

    assert (
        context["historical_evidence"]
        == []
    )

    assert (
        context["recent_messages"]
        == []
    )

    assert (
        larger_web_block
        in context["messages"][0]["content"]
    )

    assert (
        context["messages"][-1]["role"]
        == "user"
    )

    print(
        "WEB CONTEXT RECENT-TURN EVICTION CONTRACT OK"
    )

    try:
        working_context.build_working_context(
            session_id="session_1",
            current_user_message_id=100,
            current_user_content="CURRENT",
            system_prompt="SYS",
            count_tokens=count_chars,
            web_evidence_content=(
                "WEB:"
                + "W" * 250
            ),
            recent_token_budget=1000,
            historical_token_budget=5000,
            input_token_budget=100,
            historical_limit=5,
            search_fn=search_history,
        )
    except ValueError as exc:
        assert (
            "Web evidence"
            in str(exc)
        )
    else:
        raise AssertionError(
            (
                "mandatory oversized Web context "
                "must fail explicitly"
            )
        )

    print(
        "WEB CONTEXT MANDATORY-BUDGET FAILURE CONTRACT OK"
    )

    no_web = (
        working_context.build_working_context(
            session_id="session_1",
            current_user_message_id=100,
            current_user_content="CURRENT",
            system_prompt="SYS",
            count_tokens=count_chars,
            recent_token_budget=1000,
            historical_token_budget=1,
            input_token_budget=1000,
            historical_limit=5,
            search_fn=lambda **kwargs: [],
        )
    )

    assert (
        no_web["web_evidence_included"]
        is False
    )

    assert (
        no_web[
            "web_evidence_prompt_chars"
        ]
        == 0
    )

    print(
        "NON-WEB WORKING CONTEXT COMPATIBILITY CONTRACT OK"
    )

finally:
    working_context.load_recent_messages = (
        original_loader
    )


print(
    "A3_4C9C_UNIFIED_WORKING_CONTEXT_CONTRACT=PASS"
)
