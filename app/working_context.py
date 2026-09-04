from memory.hybrid_search import hybrid_search
from memory.store import load_recent_messages


def _to_chat_messages(messages):
    return [
        {
            "role": message["role"],
            "content": message["content"],
        }
        for message in messages
    ]



def retrieve_historical_evidence(
    query,
    exclude_message_ids=None,
    limit=5,
    search_fn=hybrid_search,
):
    """
    Retrieve A0 historical evidence while excluding canonical messages that
    are already present in the active Working Context.
    """
    limit = int(limit)

    if limit <= 0:
        raise ValueError("limit must be positive")

    excluded = {
        int(message_id)
        for message_id in (exclude_message_ids or [])
    }

    fetch_limit = min(
        100,
        max(
            limit * 4,
            limit + len(excluded),
        ),
    )

    results = search_fn(
        query,
        limit=fetch_limit,
        candidate_limit=max(20, fetch_limit),
    )

    selected = []

    for result in results:
        message_id = int(result["id"])

        if message_id in excluded:
            continue

        selected.append(result)

        if len(selected) >= limit:
            break

    return selected

def build_recent_context(
    session_id,
    before_message_id,
    token_budget,
    count_tokens,
    page_size=64,
):
    """
    Build a token-bounded Recent Conversation Context from canonical SQLite
    history.

    Selection prefers the newest prior messages, while the returned result
    remains in chronological order for the model.
    """
    token_budget = int(token_budget)
    page_size = int(page_size)

    if token_budget <= 0:
        raise ValueError("token_budget must be positive")

    if page_size <= 0:
        raise ValueError("page_size must be positive")

    selected = []
    cursor = before_message_id

    while True:
        page = load_recent_messages(
            session_id=session_id,
            limit=page_size,
            before_message_id=cursor,
        )

        if not page:
            break

        for message in reversed(page):
            candidate = [message, *selected]

            token_count = count_tokens(
                _to_chat_messages(candidate)
            )

            if token_count > token_budget:
                return selected

            selected = candidate

        if len(page) < page_size:
            break

        cursor = page[0]["id"]

    return selected



def _historical_system_message(evidence):
    lines = [
        "Relevant historical evidence:",
    ]

    for row in evidence:
        lines.append(
            f'[memory #{row["id"]} role={row["role"]}] '
            f'{row["content"]}'
        )

    lines.append(
        "Use this evidence only when it is relevant to the current request."
    )

    return {
        "role": "system",
        "content": "\n".join(lines),
    }


def _compose_working_messages(
    system_prompt,
    historical_evidence,
    recent_messages,
    current_user_content,
):
    messages = [
        {
            "role": "system",
            "content": system_prompt,
        }
    ]

    if historical_evidence:
        messages.append(
            _historical_system_message(
                historical_evidence
            )
        )

    messages.extend(
        _to_chat_messages(
            recent_messages
        )
    )

    messages.append(
        {
            "role": "user",
            "content": current_user_content,
        }
    )

    return messages


def build_working_context(
    session_id,
    current_user_message_id,
    current_user_content,
    system_prompt,
    count_tokens,
    recent_token_budget=4096,
    historical_token_budget=2048,
    input_token_budget=7168,
    historical_limit=5,
    page_size=64,
    search_fn=hybrid_search,
):
    """
    Combine bounded recent conversation context and A0 historical evidence
    into the final token-bounded model input for one turn.
    """
    recent_messages = build_recent_context(
        session_id=session_id,
        before_message_id=current_user_message_id,
        token_budget=recent_token_budget,
        count_tokens=count_tokens,
        page_size=page_size,
    )

    excluded_ids = {
        current_user_message_id,
        *(
            message["id"]
            for message in recent_messages
        ),
    }

    retrieval_status = "OK"
    retrieval_error = None

    try:
        historical_candidates = retrieve_historical_evidence(
            query=current_user_content,
            exclude_message_ids=excluded_ids,
            limit=historical_limit,
            search_fn=search_fn,
        )
    except Exception as exc:
        retrieval_status = "DEGRADED"
        retrieval_error = str(exc)
        historical_candidates = []

    historical_evidence = []

    for row in historical_candidates:
        candidate = [
            *historical_evidence,
            row,
        ]

        candidate_tokens = count_tokens(
            [
                _historical_system_message(
                    candidate
                )
            ]
        )

        if candidate_tokens > historical_token_budget:
            break

        historical_evidence = candidate

    messages = _compose_working_messages(
        system_prompt=system_prompt,
        historical_evidence=historical_evidence,
        recent_messages=recent_messages,
        current_user_content=current_user_content,
    )

    input_tokens = count_tokens(messages)

    while (
        input_tokens > input_token_budget
        and historical_evidence
    ):
        historical_evidence.pop()

        messages = _compose_working_messages(
            system_prompt=system_prompt,
            historical_evidence=historical_evidence,
            recent_messages=recent_messages,
            current_user_content=current_user_content,
        )

        input_tokens = count_tokens(messages)

    while (
        input_tokens > input_token_budget
        and recent_messages
    ):
        recent_messages.pop(0)

        messages = _compose_working_messages(
            system_prompt=system_prompt,
            historical_evidence=historical_evidence,
            recent_messages=recent_messages,
            current_user_content=current_user_content,
        )

        input_tokens = count_tokens(messages)

    if input_tokens > input_token_budget:
        raise ValueError(
            "required system prompt and current user message exceed "
            "input token budget"
        )

    return {
        "messages": messages,
        "recent_messages": recent_messages,
        "historical_evidence": historical_evidence,
        "recent_message_ids": [
            row["id"]
            for row in recent_messages
        ],
        "historical_message_ids": [
            row["id"]
            for row in historical_evidence
        ],
        "input_tokens": input_tokens,
        "retrieval_status": retrieval_status,
        "retrieval_error": retrieval_error,
    }
