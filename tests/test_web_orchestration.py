from app.web_fetch import (
    WebFetchError,
)
from app.web_orchestration import (
    prepare_web_grounding,
)
from app.web_search_fetch import (
    fetch_search_result,
)


class FakeProvider:
    name = "fake-orchestration-provider"

    def __init__(
        self,
        results,
    ):
        self.results = list(
            results
        )

    def search(
        self,
        query,
        *,
        limit,
    ):
        return self.results[
            :limit
        ]


route_calls = []


def provider_builder(
    attempt,
):
    route_calls.append(
        (
            attempt.name,
            attempt.category,
        )
    )

    return FakeProvider(
        [
            {
                "url": (
                    "https://example.com/"
                    "first"
                ),
                "title": "First Result",
                "snippet": (
                    "First candidate"
                ),
            },
            {
                "url": (
                    "https://example.org/"
                    "second"
                ),
                "title": "Second Result",
                "snippet": (
                    "Python compression result"
                ),
            },
        ]
    )


fetch_calls = []


def orchestration_fetch(
    discovery,
    result_id,
):
    def fake_fetcher(
        url,
    ):
        fetch_calls.append(
            url
        )

        if url == (
            "https://example.com/first"
        ):
            raise WebFetchError(
                "WEB_FETCH_TEST_FAILURE",
                "synthetic first-result failure",
            )

        text = (
            "Python 3.14 includes the "
            "compression.zstd module. "
            "The compression.zstd module "
            "supports the Zstandard format."
        )

        return {
            "url": url,
            "status": 200,
            "media_type": "text/plain",
            "text": text,
            "bytes_read": len(
                text.encode("utf-8")
            ),
            "resolved_ip": "1.1.1.1",
            "redirects": (),
        }

    return fetch_search_result(
        discovery,
        result_id,
        fetcher=fake_fetcher,
    )


result = prepare_web_grounding(
    (
        "Does Python 3.14 support "
        "compression.zstd?"
    ),
    provider_builder=provider_builder,
    search_limit=5,
    max_fetch_candidates=3,
    fetch_search_result_fn=(
        orchestration_fetch
    ),
)


assert result.status == "READY"

assert (
    result.selected_result_id
    == "result_2"
)

assert len(
    result.used_web_evidence
) >= 1

first_evidence = (
    result.used_web_evidence[0]
)

assert (
    first_evidence.evidence_ref
    == "web_1"
)

assert (
    first_evidence.ordinal
    == 0
)

assert (
    first_evidence.result_id
    == "result_2"
)

assert (
    first_evidence.source_url
    == "https://example.org/second"
)

assert (
    "compression.zstd"
    in first_evidence.excerpt
)

assert [
    item.status
    for item in result.candidate_outcomes
] == [
    "FETCH_FAILED",
    "SELECTED",
]

assert (
    result.candidate_outcomes[
        0
    ].error_code
    == "WEB_FETCH_TEST_FAILURE"
)

assert fetch_calls == [
    "https://example.com/first",
    "https://example.org/second",
]

print(
    "WEB ORCHESTRATION SEARCH-TO-EVIDENCE CONTRACT OK"
)

print(
    "WEB ORCHESTRATION RESULT FALLBACK CONTRACT OK"
)


def empty_provider_builder(
    attempt,
):
    return FakeProvider(
        []
    )


empty_result = (
    prepare_web_grounding(
        "example query",
        provider_builder=(
            empty_provider_builder
        ),
    )
)

assert (
    empty_result.status
    == "NO_RESULTS"
)

assert (
    empty_result.selected_result_id
    is None
)

assert (
    empty_result.used_web_evidence
    == ()
)

assert (
    empty_result.candidate_outcomes
    == ()
)

print(
    "WEB ORCHESTRATION NO-RESULT CONTRACT OK"
)


def unrelated_provider_builder(
    attempt,
):
    return FakeProvider(
        [
            {
                "url": (
                    "https://example.net/"
                    "unrelated"
                ),
                "title": "Unrelated",
            }
        ]
    )


def unrelated_fetch(
    discovery,
    result_id,
):
    def fake_fetcher(
        url,
    ):
        text = (
            "Gardening soil moisture "
            "and tomato planting notes."
        )

        return {
            "url": url,
            "status": 200,
            "media_type": "text/plain",
            "text": text,
            "bytes_read": len(
                text.encode("utf-8")
            ),
            "resolved_ip": "1.1.1.1",
            "redirects": (),
        }

    return fetch_search_result(
        discovery,
        result_id,
        fetcher=fake_fetcher,
    )


unrelated_result = (
    prepare_web_grounding(
        (
            "Python 3.14 "
            "compression.zstd"
        ),
        provider_builder=(
            unrelated_provider_builder
        ),
        fetch_search_result_fn=(
            unrelated_fetch
        ),
    )
)

assert (
    unrelated_result.status
    == "NO_USABLE_EVIDENCE"
)

assert (
    unrelated_result.selected_result_id
    is None
)

assert (
    unrelated_result.used_web_evidence
    == ()
)

assert [
    item.status
    for item in (
        unrelated_result
        .candidate_outcomes
    )
] == [
    "NO_RELEVANT_EVIDENCE",
]

print(
    "WEB ORCHESTRATION NO-USABLE-EVIDENCE CONTRACT OK"
)

print(
    "A3_4_WEB_ORCHESTRATION_FOUNDATION=PASS"
)
