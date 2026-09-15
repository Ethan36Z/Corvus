from urllib.parse import (
    parse_qs,
    urlparse,
)

from app.searxng_provider import (
    SearXNGProvider,
)
from app.web_search import (
    search_web,
)


calls = []


def fake_fetch_json(
    url,
    *,
    timeout,
):
    calls.append(
        {
            "url": url,
            "timeout": timeout,
        }
    )

    return {
        "results": [
            {
                "url": (
                    "https://example.com/"
                    "first"
                ),
                "title": (
                    "  First   Result  "
                ),
                "content": (
                    " Useful   snippet. "
                ),
                "engines": [
                    "google cse",
                ],
            },
            {
                "url": (
                    "https://example.org/"
                    "second"
                ),
                "title": "Second Result",
                "content": "Second snippet",
            },
        ]
    }


provider = SearXNGProvider(
    base_url=(
        "http://127.0.0.1:8110/"
    ),
    timeout_seconds=7,
    fetch_json=fake_fetch_json,
)

discovery = search_web(
    "  qwen   llama.cpp  ",
    provider=provider,
    limit=1,
)

assert provider.name == (
    "searxng-local"
)

assert len(calls) == 1

call = calls[0]

assert call["timeout"] == 7.0

parsed = urlparse(
    call["url"]
)

assert parsed.scheme == "http"
assert parsed.hostname == "127.0.0.1"
assert parsed.port == 8110
assert parsed.path == "/search"

params = parse_qs(
    parsed.query
)

assert params["q"] == [
    "qwen llama.cpp"
]

assert params["format"] == [
    "json"
]

assert params["categories"] == [
    "general"
]

assert discovery.provider == (
    "searxng-local"
)

assert discovery.query == (
    "qwen llama.cpp"
)

assert len(
    discovery.results
) == 1

result = discovery.results[0]

assert result.result_id == (
    "result_1"
)

assert result.url == (
    "https://example.com/first"
)

assert result.title == (
    "First Result"
)

assert result.snippet == (
    "Useful snippet."
)

assert result.provider == (
    "searxng-local"
)


def invalid_payload(
    url,
    *,
    timeout,
):
    return []


bad_provider = SearXNGProvider(
    fetch_json=invalid_payload,
)

try:
    search_web(
        "test",
        provider=bad_provider,
    )
except Exception as exc:
    assert getattr(
        exc,
        "code",
        None,
    ) == (
        "WEB_SEARCH_PROVIDER_FAILED"
    )
else:
    raise AssertionError(
        "invalid SearXNG payload "
        "must fail"
    )


print(
    "SEARXNG PROVIDER CONTRACT OK"
)
print(
    "SEARXNG SEARCH_WEB INTEGRATION OK"
)
print(
    "SEARXNG EPHEMERAL BOUNDARY OK"
)
