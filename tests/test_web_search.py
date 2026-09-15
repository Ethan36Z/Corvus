from app.web_search import (
    MAX_SEARCH_RESULTS,
    SearchDiscoveryError,
    search_web,
)


class FakeProvider:
    name = "test-provider"

    def __init__(
        self,
        results,
    ):
        self.results = results
        self.calls = []

    def search(
        self,
        query,
        *,
        limit,
    ):
        self.calls.append(
            {
                "query": query,
                "limit": limit,
            }
        )

        return self.results


def expect_error(
    code,
    fn,
):
    try:
        fn()
    except SearchDiscoveryError as exc:
        assert exc.code == code, (
            exc.code,
            code,
        )
    else:
        raise AssertionError(
            f"expected {code}"
        )


provider = FakeProvider(
    [
        {
            "url": (
                "https://example.com/"
                "news#section"
            ),
            "title": (
                "  Example   News  "
            ),
            "snippet": (
                " A useful   snippet. "
            ),
        },
        {
            "url": (
                "https://example.com/"
                "news"
            ),
            "title": "duplicate",
        },
        {
            "url": (
                "http://127.0.0.1/"
            ),
            "title": "blocked",
        },
        {
            "url": (
                "ftp://example.net/file"
            ),
            "title": "wrong scheme",
        },
        {
            "url": (
                "https://example.org/"
                "story"
            ),
            "title": " Second result ",
            "snippet": (
                " Another   snippet "
            ),
        },
    ]
)

discovery = search_web(
    "  corvus   latest   news  ",
    provider=provider,
    limit=5,
)

assert discovery.query == (
    "corvus latest news"
)

assert discovery.provider == (
    "test-provider"
)

assert provider.calls == [
    {
        "query": (
            "corvus latest news"
        ),
        "limit": 5,
    }
]

assert len(
    discovery.results
) == 2

assert discovery.rejected_count == 3

first = discovery.results[0]
second = discovery.results[1]

assert first.result_id == (
    "result_1"
)

assert first.rank == 1

assert first.url == (
    "https://example.com/news"
)

assert first.hostname == (
    "example.com"
)

assert first.title == (
    "Example News"
)

assert first.snippet == (
    "A useful snippet."
)

assert second.result_id == (
    "result_2"
)

assert second.rank == 2

assert second.url == (
    "https://example.org/story"
)

assert second.title == (
    "Second result"
)

assert second.snippet == (
    "Another snippet"
)

assert (
    discovery.result_by_id(
        "result_2"
    )
    == second
)

assert (
    discovery.result_by_id(
        "missing"
    )
    is None
)

# Search results remain ordinary in-memory
# objects. This layer imports no memory store
# and performs no persistence operation.
assert (
    "memory.store"
    not in __import__(
        "sys"
    ).modules
)


expect_error(
    "WEB_SEARCH_QUERY_INVALID",
    lambda: search_web(
        "   ",
        provider=provider,
    ),
)

expect_error(
    "WEB_SEARCH_QUERY_TOO_LONG",
    lambda: search_web(
        "x" * 513,
        provider=provider,
    ),
)

expect_error(
    "WEB_SEARCH_LIMIT_INVALID",
    lambda: search_web(
        "test",
        provider=provider,
        limit=0,
    ),
)

expect_error(
    "WEB_SEARCH_LIMIT_INVALID",
    lambda: search_web(
        "test",
        provider=provider,
        limit=(
            MAX_SEARCH_RESULTS
            + 1
        ),
    ),
)


class InvalidProvider:
    name = "invalid-provider"

    def search(
        self,
        query,
        *,
        limit,
    ):
        return {
            "not": "a result list"
        }


expect_error(
    "WEB_SEARCH_RESPONSE_INVALID",
    lambda: search_web(
        "test",
        provider=InvalidProvider(),
    ),
)


class FailingProvider:
    name = "failing-provider"

    def search(
        self,
        query,
        *,
        limit,
    ):
        raise RuntimeError(
            "provider unavailable"
        )


expect_error(
    "WEB_SEARCH_PROVIDER_FAILED",
    lambda: search_web(
        "test",
        provider=FailingProvider(),
    ),
)


print(
    "WEB SEARCH EPHEMERAL CONTRACT OK"
)
print(
    "WEB SEARCH RESULT SAFETY CONTRACT OK"
)
print(
    "WEB SEARCH RESULT-ID CONTRACT OK"
)
print(
    "WEB SEARCH DEDUP CONTRACT OK"
)
print(
    "WEB SEARCH BOUNDARY CONTRACT OK"
)
