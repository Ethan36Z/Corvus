from app.web_search_execution import (
    execute_search_plan,
)
from app.web_search_routing import (
    build_search_plan,
)


class FakeProvider:
    def __init__(
        self,
        *,
        name,
        results=None,
        fail=False,
    ):
        self.name = name
        self.results = (
            []
            if results is None
            else results
        )
        self.fail = fail

    def search(
        self,
        query,
        *,
        limit,
    ):
        if self.fail:
            raise RuntimeError(
                "provider unavailable"
            )

        return self.results[:limit]


calls = []


def fallback_builder(
    attempt,
):
    calls.append(
        attempt.name
    )

    if attempt.name == "zh-news":
        return FakeProvider(
            name="fake-zh-news",
            results=[],
        )

    return FakeProvider(
        name="fake-zh-general",
        results=[
            {
                "url": (
                    "https://example.com/"
                    "zh-news"
                ),
                "title": "Fallback result",
                "snippet": "Fallback worked",
            }
        ],
    )


plan = build_search_plan(
    "洛杉矶 今日 新闻"
)

execution = execute_search_plan(
    plan,
    provider_builder=fallback_builder,
    limit=5,
)

assert calls == [
    "zh-news",
    "zh-general-goc",
]

assert execution.selected_attempt == (
    "zh-general-goc"
)

assert execution.discovery is not None

assert len(
    execution.discovery.results
) == 1

assert tuple(
    outcome.status
    for outcome in execution.outcomes
) == (
    "empty",
    "success",
)


failure_calls = []


def failure_builder(
    attempt,
):
    failure_calls.append(
        attempt.name
    )

    if attempt.name == "en-news":
        return FakeProvider(
            name="fake-en-news",
            fail=True,
        )

    return FakeProvider(
        name="fake-en-general",
        results=[
            {
                "url": (
                    "https://example.org/"
                    "latest"
                ),
                "title": "Latest",
            }
        ],
    )


failure_plan = build_search_plan(
    "OpenAI latest news"
)

failure_execution = (
    execute_search_plan(
        failure_plan,
        provider_builder=(
            failure_builder
        ),
    )
)

assert failure_calls == [
    "en-news",
    "en-general-fallback",
]

assert (
    failure_execution.selected_attempt
    == "en-general-fallback"
)

assert tuple(
    outcome.status
    for outcome
    in failure_execution.outcomes
) == (
    "provider_failed",
    "success",
)


def empty_builder(
    attempt,
):
    return FakeProvider(
        name="fake-empty",
        results=[],
    )


empty_execution = execute_search_plan(
    plan,
    provider_builder=empty_builder,
)

assert empty_execution.selected_attempt is None
assert empty_execution.discovery is None

assert tuple(
    outcome.status
    for outcome
    in empty_execution.outcomes
) == (
    "empty",
    "empty",
)


print(
    "WEB SEARCH ROUTE EXECUTION CONTRACT OK"
)
print(
    "WEB SEARCH EMPTY FALLBACK CONTRACT OK"
)
print(
    "WEB SEARCH PROVIDER FAILURE FALLBACK CONTRACT OK"
)
print(
    "WEB SEARCH ALL-ROUTES-EXHAUSTED CONTRACT OK"
)
