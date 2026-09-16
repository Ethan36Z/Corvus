from app.ddgs_provider import DDGSProvider
from app.web_search import search_web


class FakeDDGS:
    def __init__(
        self,
        *,
        timeout,
    ):
        self.timeout = timeout
        self.calls = []

    def text(
        self,
        query,
        **kwargs,
    ):
        self.calls.append(
            (
                "text",
                query,
                kwargs,
            )
        )

        return [
            {
                "title": "  Python Docs  ",
                "href": (
                    "https://docs.python.org/"
                    "3.14/library/compression.zstd.html"
                ),
                "body": (
                    " Zstandard compression support. "
                ),
            },
            {
                "title": "Second",
                "href": (
                    "https://example.org/second"
                ),
                "body": "Second result",
            },
        ]

    def news(
        self,
        query,
        **kwargs,
    ):
        self.calls.append(
            (
                "news",
                query,
                kwargs,
            )
        )

        return [
            {
                "title": "Current News",
                "url": (
                    "https://example.com/news"
                ),
                "body": "Current news body",
            }
        ]


instances = []


def fake_factory(
    *,
    timeout,
):
    instance = FakeDDGS(
        timeout=timeout
    )
    instances.append(instance)
    return instance


provider = DDGSProvider(
    ddgs_factory=fake_factory,
    timeout_seconds=7,
)

discovery = search_web(
    "Python 3.14 compression.zstd",
    provider=provider,
    limit=1,
)

assert provider.name == "ddgs"
assert len(instances) == 1
assert instances[0].timeout == 7.0

method, query, kwargs = (
    instances[0].calls[0]
)

assert method == "text"
assert query == (
    "Python 3.14 compression.zstd"
)
assert kwargs["region"] == "us-en"
assert kwargs["safesearch"] == "moderate"
assert kwargs["timelimit"] is None
assert kwargs["max_results"] == 1
assert kwargs["backend"] == "auto"

assert discovery.provider == "ddgs"
assert len(discovery.results) == 1

result = discovery.results[0]

assert result.result_id == "result_1"
assert result.title == "Python Docs"
assert result.url == (
    "https://docs.python.org/"
    "3.14/library/compression.zstd.html"
)
assert result.snippet == (
    "Zstandard compression support."
)

print(
    "DDGS PROVIDER CONTRACT OK"
)
print(
    "DDGS SEARCH_WEB INTEGRATION OK"
)
print(
    "DDGS DISCOVERY-ONLY BOUNDARY OK"
)


news_provider = DDGSProvider(
    category="news",
    region="cn-zh",
    time_range="day",
    ddgs_factory=fake_factory,
)

news = search_web(
    "今日新闻",
    provider=news_provider,
    limit=1,
)

method, query, kwargs = (
    instances[-1].calls[0]
)

assert method == "news"
assert query == "今日新闻"
assert kwargs["region"] == "cn-zh"
assert kwargs["timelimit"] == "d"

assert news.results[0].url == (
    "https://example.com/news"
)

print(
    "DDGS NEWS ROUTING CONTRACT OK"
)
