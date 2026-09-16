from app.web_search import (
    search_web,
)
from app.web_search_fetch import (
    SearchResultFetchError,
    fetch_search_result,
)


class FakeProvider:
    name = "fake-provider"

    def search(
        self,
        query,
        *,
        limit,
    ):
        return [
            {
                "url": (
                    "https://example.com/"
                    "article"
                ),
                "title": (
                    "Example Article"
                ),
                "snippet": (
                    "Example snippet"
                ),
            },
            {
                "url": (
                    "https://example.org/"
                    "second"
                ),
                "title": (
                    "Second Result"
                ),
            },
        ]


discovery = search_web(
    "example query",
    provider=FakeProvider(),
    limit=2,
)


fetch_calls = []


def fake_fetcher(
    url,
):
    fetch_calls.append(
        url
    )

    return {
        "url": (
            "https://example.com/"
            "final"
        ),
        "status": 200,
        "media_type": (
            "text/html"
        ),
        "text": (
            "<html>hello</html>"
        ),
        "bytes_read": 18,
        "resolved_ip": (
            "1.1.1.1"
        ),
        "redirects": (
            {
                "status": 302,
                "from_url": (
                    "https://example.com/"
                    "article"
                ),
                "to_url": (
                    "https://example.com/"
                    "final"
                ),
            },
        ),
    }


fetched = fetch_search_result(
    discovery,
    "result_1",
    fetcher=fake_fetcher,
)

assert fetch_calls == [
    "https://example.com/article"
]

assert fetched.result_id == (
    "result_1"
)

assert fetched.provider == (
    "fake-provider"
)

assert fetched.title == (
    "Example Article"
)

assert fetched.source_url == (
    "https://example.com/article"
)

assert fetched.fetched_url == (
    "https://example.com/final"
)

assert fetched.status == 200

assert fetched.media_type == (
    "text/html"
)

assert fetched.text == (
    "<html>hello</html>"
)

assert fetched.bytes_read == 18

assert len(
    fetched.redirects
) == 1


missing_calls = []


def must_not_fetch(
    url,
):
    missing_calls.append(
        url
    )
    raise AssertionError(
        "fetcher must not run"
    )


try:
    fetch_search_result(
        discovery,
        "result_999",
        fetcher=must_not_fetch,
    )
except SearchResultFetchError as exc:
    assert exc.code == (
        "WEB_SEARCH_RESULT_NOT_FOUND"
    )
else:
    raise AssertionError(
        "unknown result ID must fail"
    )

assert missing_calls == []


try:
    fetch_search_result(
        discovery,
        "",
        fetcher=must_not_fetch,
    )
except SearchResultFetchError as exc:
    assert exc.code == (
        "WEB_SEARCH_RESULT_ID_INVALID"
    )
else:
    raise AssertionError(
        "empty result ID must fail"
    )


def invalid_fetcher(
    url,
):
    return {
        "url": url,
    }


try:
    fetch_search_result(
        discovery,
        "result_1",
        fetcher=invalid_fetcher,
    )
except SearchResultFetchError as exc:
    assert exc.code == (
        "WEB_SEARCH_FETCH_RESPONSE_INVALID"
    )
else:
    raise AssertionError(
        "invalid fetch response must fail"
    )


print(
    "WEB SEARCH RESULT-ID FETCH CONTRACT OK"
)
print(
    "WEB SEARCH NO-ARBITRARY-URL CONTRACT OK"
)
print(
    "WEB SEARCH SAFE-FETCH BRIDGE CONTRACT OK"
)
print(
    "WEB SEARCH FETCH RESPONSE CONTRACT OK"
)
