from app.model_client import (
    ModelClientError,
    generate_chat_completion,
)
from app.web_search import (
    MAX_SEARCH_QUERY_CHARS,
)


WEB_QUERY_REWRITE_SYSTEM_PROMPT = (
    "Convert the user's request into one concise "
    "web search query.\n"
    "\n"
    "Rules:\n"
    "- Preserve exact product, API, class, module, "
    "version, person, organization, and source names.\n"
    "- Remove conversational wording and instructions "
    "that are not useful search terms.\n"
    "- Preserve source intent such as documentation, "
    "official site, paper, news, or release notes.\n"
    "- Quote a distinctive exact identifier when that "
    "helps preserve it, such as an API or module name.\n"
    "- Do not answer the question.\n"
    "- Do not explain the rewrite.\n"
    "- Output exactly one search query and nothing else."
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
