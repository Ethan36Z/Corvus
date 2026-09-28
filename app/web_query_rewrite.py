from app.model_client import (
    ModelClientError,
    generate_chat_completion,
)
from app.web_search import (
    MAX_SEARCH_QUERY_CHARS,
)


WEB_QUERY_REWRITE_SYSTEM_PROMPT = (
    "Convert the current user request into one concise, "
    "standalone web search query.\n"
    "\n"
    "Rules:\n"
    "- The current user request is authoritative.\n"
    "- If recent conversation context is supplied, use it "
    "only to resolve omitted subjects, pronouns, references, "
    "or follow-up meaning.\n"
    "- If a current date is supplied, use it to resolve "
    "relative time such as today, this year, currently, "
    "or equivalent wording.\n"
    "- Include only the minimum contextual subject needed "
    "to make the search query standalone.\n"
    "- Do not copy unrelated personal or private details "
    "from conversation context into the search query.\n"
    "- Preserve exact product, API, class, module, version, "
    "person, organization, election, event, and source names.\n"
    "- Remove conversational wording and instructions that "
    "are not useful search terms.\n"
    "- Preserve source intent such as documentation, "
    "official site, paper, news, release notes, or polls.\n"
    "- Quote a distinctive exact identifier when that helps "
    "preserve it, such as an API or module name.\n"
    "- Do not answer the question.\n"
    "- Do not explain the rewrite.\n"
    "- Output exactly one search query and nothing else."
)


WEB_QUERY_RECENT_SCAN_LIMIT = 12
WEB_QUERY_CONTEXT_MESSAGE_CHAR_LIMIT = 700

_NON_SEMANTIC_CONTEXT_MESSAGES = {
    "[Voice message]",
}


def _normalize_query_context_text(
    value,
):
    if not isinstance(
        value,
        str,
    ):
        return ""

    return " ".join(
        value.split()
    )


def select_web_query_rewrite_context(
    recent_messages,
    current_user_content,
):
    """
    Select the newest completed semantic conversation
    turn for follow-up Web query resolution.

    Canonical evidence is never deleted or changed here.

    Incomplete failed attempts, transport placeholders,
    and duplicate retry messages simply do not become
    semantic query-rewrite context.
    """
    current = (
        _normalize_query_context_text(
            current_user_content
        )
    )

    semantic = []

    for message in list(
        recent_messages or ()
    ):
        if not isinstance(
            message,
            dict,
        ):
            continue

        role = str(
            message.get(
                "role",
                "",
            )
        ).strip().lower()

        if role not in {
            "user",
            "assistant",
        }:
            continue

        content = (
            _normalize_query_context_text(
                message.get(
                    "content"
                )
            )
        )

        if not content:
            continue

        if (
            content
            in _NON_SEMANTIC_CONTEXT_MESSAGES
        ):
            continue

        semantic.append(
            message
        )

    #
    # A failed previous attempt remains canonical but
    # should not become semantic context for its retry.
    #
    while (
        semantic
        and semantic[-1].get("role") == "user"
        and _normalize_query_context_text(
            semantic[-1].get(
                "content"
            )
        ) == current
    ):
        semantic.pop()

    #
    # Use only the newest completed user -> assistant
    # turn. This prevents unrelated older topics from
    # leaking into the standalone search query.
    #
    for index in range(
        len(semantic) - 2,
        -1,
        -1,
    ):
        first = semantic[index]
        second = semantic[
            index + 1
        ]

        if (
            first.get("role") == "user"
            and second.get("role")
            == "assistant"
        ):
            return [
                first,
                second,
            ]

    return []


def build_web_query_rewrite_input(
    user_query,
    recent_messages=None,
    *,
    current_date=None,
):
    """
    Build derived, ephemeral input for the local query
    rewriter.

    Recent canonical conversation is used only to resolve
    follow-up references.

    Only the final rewritten query is supplied to the Web
    discovery provider.
    """
    current = (
        _normalize_query_context_text(
            user_query
        )
    )

    if not current:
        raise ValueError(
            "user_query must not be empty"
        )

    context_lines = []

    for message in list(
        recent_messages or ()
    ):
        if not isinstance(
            message,
            dict,
        ):
            continue

        role = str(
            message.get(
                "role",
                "",
            )
        ).strip().lower()

        if role not in {
            "user",
            "assistant",
        }:
            continue

        content = (
            _normalize_query_context_text(
                message.get(
                    "content"
                )
            )
        )

        if not content:
            continue

        if (
            len(content)
            > WEB_QUERY_CONTEXT_MESSAGE_CHAR_LIMIT
        ):
            content = (
                content[
                    :WEB_QUERY_CONTEXT_MESSAGE_CHAR_LIMIT
                ].rstrip()
                + "…"
            )

        context_lines.append(
            f"{role.upper()}: {content}"
        )

    #
    # Preserve the old simple single-turn contract when
    # no follow-up context exists.
    #
    if not context_lines:
        return current

    sections = []

    if current_date is not None:
        current_date = str(
            current_date
        ).strip()

        if current_date:
            sections.append(
                f"Current date: {current_date}"
            )

    sections.append(
        (
            "Recent conversation context "
            "(use only to resolve the current request):\n"
            + "\n".join(
                context_lines
            )
        )
    )

    sections.append(
        (
            "Current user request:\n"
            + current
        )
    )

    return "\n\n".join(
        sections
    )


class WebQueryRewriteError(
    ValueError
):
    def __init__(
        self,
        code,
        message,
    ):
        super().__init__(
            message
        )
        self.code = str(
            code
        )


def _raise(
    code,
    message,
):
    raise WebQueryRewriteError(
        code,
        message,
    )


def rewrite_web_query(
    user_query,
    *,
    generate_fn=generate_chat_completion,
):
    """
    Convert a natural-language user request into a
    concise discovery-only Web search query.

    The rewrite is derived and ephemeral:
    - it is not canonical user evidence;
    - it does not replace the user's original text;
    - it is not persisted here.
    """

    if not isinstance(
        user_query,
        str,
    ):
        _raise(
            "WEB_QUERY_REWRITE_INPUT_INVALID",
            "Web query rewrite input must be text",
        )

    normalized_input = " ".join(
        user_query.split()
    )

    if not normalized_input:
        _raise(
            "WEB_QUERY_REWRITE_INPUT_INVALID",
            (
                "Web query rewrite input "
                "must not be empty"
            ),
        )

    messages = [
        {
            "role": "system",
            "content": (
                WEB_QUERY_REWRITE_SYSTEM_PROMPT
            ),
        },
        {
            "role": "user",
            "content": normalized_input,
        },
    ]

    try:
        rewritten = generate_fn(
            messages
        )
    except ModelClientError as exc:
        raise WebQueryRewriteError(
            "WEB_QUERY_REWRITE_MODEL_FAILED",
            str(exc),
        ) from exc
    except Exception as exc:
        raise WebQueryRewriteError(
            "WEB_QUERY_REWRITE_MODEL_FAILED",
            (
                "Web query rewrite model "
                f"failed: {exc}"
            ),
        ) from exc

    if not isinstance(
        rewritten,
        str,
    ):
        _raise(
            "WEB_QUERY_REWRITE_OUTPUT_INVALID",
            (
                "Web query rewrite output "
                "must be text"
            ),
        )

    rewritten = " ".join(
        rewritten.split()
    )

    if not rewritten:
        _raise(
            "WEB_QUERY_REWRITE_OUTPUT_INVALID",
            (
                "Web query rewrite output "
                "must not be empty"
            ),
        )

    if (
        len(rewritten)
        > MAX_SEARCH_QUERY_CHARS
    ):
        _raise(
            "WEB_QUERY_REWRITE_OUTPUT_TOO_LONG",
            (
                "Web query rewrite output exceeds "
                "the Web search query limit"
            ),
        )

    return rewritten
