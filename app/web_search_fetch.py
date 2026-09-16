from dataclasses import dataclass

from app.web_fetch import (
    fetch_public_page,
)
from app.web_search import (
    SearchDiscovery,
)


class SearchResultFetchError(
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


@dataclass(
    frozen=True,
    slots=True,
)
class FetchedSearchResult:
    result_id: str
    provider: str
    title: str | None
    source_url: str
    fetched_url: str
    status: int
    media_type: str
    text: str
    bytes_read: int
    redirects: tuple


def _raise(
    code,
    message,
):
    raise SearchResultFetchError(
        code,
        message,
    )


def fetch_search_result(
    discovery,
    result_id,
    *,
    fetcher=fetch_public_page,
):
    """
    Resolve one turn-local SearchResult ID and fetch
    its already-validated public URL through Corvus
    Safe Public Fetch.

    Callers do not supply an arbitrary URL.
    """

    if not isinstance(
        discovery,
        SearchDiscovery,
    ):
        _raise(
            "WEB_SEARCH_DISCOVERY_INVALID",
            (
                "discovery must be "
                "a SearchDiscovery"
            ),
        )

    if not isinstance(
        result_id,
        str,
    ):
        _raise(
            "WEB_SEARCH_RESULT_ID_INVALID",
            (
                "search result ID "
                "must be text"
            ),
        )

    result_id = result_id.strip()

    if not result_id:
        _raise(
            "WEB_SEARCH_RESULT_ID_INVALID",
            (
                "search result ID "
                "must not be empty"
            ),
        )

    result = discovery.result_by_id(
        result_id
    )

    if result is None:
        _raise(
            "WEB_SEARCH_RESULT_NOT_FOUND",
            (
                "search result ID "
                "does not exist in "
                "this discovery"
            ),
        )

    page = fetcher(
        result.url
    )

    if not isinstance(
        page,
        dict,
    ):
        _raise(
            "WEB_SEARCH_FETCH_RESPONSE_INVALID",
            (
                "Safe Public Fetch returned "
                "an invalid response"
            ),
        )

    required = (
        "url",
        "status",
        "media_type",
        "text",
        "bytes_read",
        "redirects",
    )

    missing = [
        key
        for key in required
        if key not in page
    ]

    if missing:
        _raise(
            "WEB_SEARCH_FETCH_RESPONSE_INVALID",
            (
                "Safe Public Fetch response "
                "is missing required fields"
            ),
        )

    return FetchedSearchResult(
        result_id=result.result_id,
        provider=result.provider,
        title=result.title,
        source_url=result.url,
        fetched_url=str(
            page["url"]
        ),
        status=int(
            page["status"]
        ),
        media_type=str(
            page["media_type"]
        ),
        text=str(
            page["text"]
        ),
        bytes_read=int(
            page["bytes_read"]
        ),
        redirects=tuple(
            page["redirects"]
        ),
    )
