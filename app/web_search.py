from dataclasses import dataclass
from typing import Protocol

from app.web_security import (
    WebSecurityError,
    validate_public_url,
)


MAX_SEARCH_QUERY_CHARS = 512
MAX_SEARCH_RESULTS = 8
MAX_SEARCH_TITLE_CHARS = 300
MAX_SEARCH_SNIPPET_CHARS = 1200


class SearchDiscoveryError(ValueError):
    def __init__(
        self,
        code,
        message,
    ):
        super().__init__(message)
        self.code = str(code)


class SearchProvider(Protocol):
    name: str

    def search(
        self,
        query,
        *,
        limit,
    ):
        ...


@dataclass(
    frozen=True,
    slots=True,
)
class SearchResult:
    result_id: str
    rank: int
    title: str | None
    url: str
    hostname: str
    snippet: str | None
    provider: str

    def as_dict(self):
        return {
            "result_id": self.result_id,
            "rank": self.rank,
            "title": self.title,
            "url": self.url,
            "hostname": self.hostname,
            "snippet": self.snippet,
            "provider": self.provider,
        }


@dataclass(
    frozen=True,
    slots=True,
)
class SearchDiscovery:
    query: str
    provider: str
    results: tuple[SearchResult, ...]
    rejected_count: int

    def result_by_id(
        self,
        result_id,
    ):
        for result in self.results:
            if (
                result.result_id
                == result_id
            ):
                return result

        return None


def _raise(
    code,
    message,
):
    raise SearchDiscoveryError(
        code,
        message,
    )


def _normalize_query(
    query,
):
    if not isinstance(query, str):
        _raise(
            "WEB_SEARCH_QUERY_INVALID",
            "search query must be text",
        )

    query = " ".join(
        query.split()
    )

    if not query:
        _raise(
            "WEB_SEARCH_QUERY_INVALID",
            (
                "search query must "
                "not be empty"
            ),
        )

    if (
        len(query)
        > MAX_SEARCH_QUERY_CHARS
    ):
        _raise(
            "WEB_SEARCH_QUERY_TOO_LONG",
            (
                "search query exceeds "
                "the Web v1 limit"
            ),
        )

    return query


def _normalize_provider_name(
    provider,
):
    name = getattr(
        provider,
        "name",
        None,
    )

    if not isinstance(name, str):
        _raise(
            "WEB_SEARCH_PROVIDER_INVALID",
            (
                "search provider must "
                "have a text name"
            ),
        )

    name = name.strip()

    if not name:
        _raise(
            "WEB_SEARCH_PROVIDER_INVALID",
            (
                "search provider name "
                "must not be empty"
            ),
        )

    return name


def _optional_text(
    value,
    *,
    max_chars,
):
    if value is None:
        return None

    value = " ".join(
        str(value).split()
    )

    if not value:
        return None

    return value[:max_chars]


def _validate_limit(
    limit,
):
    try:
        limit = int(limit)
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise SearchDiscoveryError(
            "WEB_SEARCH_LIMIT_INVALID",
            "search result limit is invalid",
        ) from exc

    if (
        limit < 1
        or limit > MAX_SEARCH_RESULTS
    ):
        _raise(
            "WEB_SEARCH_LIMIT_INVALID",
            (
                "search result limit must "
                f"be between 1 and "
                f"{MAX_SEARCH_RESULTS}"
            ),
        )

    return limit


def search_web(
    query,
    *,
    provider,
    limit=5,
):
    """
    Execute one ephemeral Web discovery operation.

    Search activity is intentionally not persisted here.

    Provider output is treated as untrusted external
    data. Every URL must pass the Corvus public-Web
    URL policy before becoming a SearchResult.

    SearchResult IDs are turn-local handles. Future
    fetch logic should resolve these handles inside
    the Corvus runtime instead of accepting arbitrary
    model-supplied URLs.
    """
    query = _normalize_query(
        query
    )

    limit = _validate_limit(
        limit
    )

    provider_name = (
        _normalize_provider_name(
            provider
        )
    )

    try:
        raw_results = provider.search(
            query,
            limit=limit,
        )
    except SearchDiscoveryError:
        raise
    except Exception as exc:
        raise SearchDiscoveryError(
            "WEB_SEARCH_PROVIDER_FAILED",
            (
                "search provider request "
                f"failed: {exc}"
            ),
        ) from exc

    if not isinstance(
        raw_results,
        (list, tuple),
    ):
        _raise(
            "WEB_SEARCH_RESPONSE_INVALID",
            (
                "search provider returned "
                "an invalid result collection"
            ),
        )

    accepted = []
    seen_urls = set()
    rejected_count = 0

    for raw_result in raw_results:
        if len(accepted) >= limit:
            break

        if not isinstance(
            raw_result,
            dict,
        ):
            rejected_count += 1
            continue

        raw_url = raw_result.get(
            "url"
        )

        try:
            validated = (
                validate_public_url(
                    raw_url
                )
            )
        except (
            WebSecurityError,
            TypeError,
        ):
            rejected_count += 1
            continue

        canonical_url = validated[
            "url"
        ]

        if canonical_url in seen_urls:
            rejected_count += 1
            continue

        seen_urls.add(
            canonical_url
        )

        title = _optional_text(
            raw_result.get(
                "title"
            ),
            max_chars=(
                MAX_SEARCH_TITLE_CHARS
            ),
        )

        snippet = _optional_text(
            raw_result.get(
                "snippet"
            ),
            max_chars=(
                MAX_SEARCH_SNIPPET_CHARS
            ),
        )

        rank = len(accepted) + 1

        accepted.append(
            SearchResult(
                result_id=(
                    f"result_{rank}"
                ),
                rank=rank,
                title=title,
                url=canonical_url,
                hostname=validated[
                    "hostname"
                ],
                snippet=snippet,
                provider=provider_name,
            )
        )

    return SearchDiscovery(
        query=query,
        provider=provider_name,
        results=tuple(
            accepted
        ),
        rejected_count=(
            rejected_count
        ),
    )
