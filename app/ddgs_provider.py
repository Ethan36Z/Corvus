from ddgs import DDGS


DEFAULT_DDGS_TIMEOUT_SECONDS = 8
DEFAULT_DDGS_REGION = "us-en"
DEFAULT_DDGS_SAFESEARCH = "moderate"
DEFAULT_DDGS_BACKEND = "auto"

_TIME_RANGE_MAP = {
    None: None,
    "day": "d",
    "month": "m",
    "year": "y",
}


class DDGSProvider:
    """
    Thin discovery-only adapter from DDGS into the
    Corvus SearchProvider protocol.

    DDGS owns search discovery and result ranking.

    Corvus still owns:
    - public URL validation,
    - Safe Fetch,
    - extraction,
    - UsedWebEvidence,
    - provenance,
    - persistence.

    DDGS extraction is intentionally not used.
    """

    name = "ddgs"

    def __init__(
        self,
        *,
        category="general",
        region=DEFAULT_DDGS_REGION,
        safesearch=DEFAULT_DDGS_SAFESEARCH,
        time_range=None,
        backend=DEFAULT_DDGS_BACKEND,
        timeout_seconds=DEFAULT_DDGS_TIMEOUT_SECONDS,
        ddgs_factory=DDGS,
    ):
        category = str(category).strip().lower()

        if category not in {
            "general",
            "news",
        }:
            raise ValueError(
                "DDGS category must be general or news"
            )

        region = str(region).strip()

        if not region:
            raise ValueError(
                "DDGS region must not be empty"
            )

        safesearch = str(
            safesearch
        ).strip().lower()

        if safesearch not in {
            "on",
            "moderate",
            "off",
        }:
            raise ValueError(
                "DDGS safesearch is invalid"
            )

        if time_range not in _TIME_RANGE_MAP:
            raise ValueError(
                "DDGS time range is invalid"
            )

        backend = str(backend).strip()

        if not backend:
            raise ValueError(
                "DDGS backend must not be empty"
            )

        timeout_seconds = float(
            timeout_seconds
        )

        if timeout_seconds <= 0:
            raise ValueError(
                "DDGS timeout must be positive"
            )

        self.category = category
        self.region = region
        self.safesearch = safesearch
        self.time_range = time_range
        self.backend = backend
        self.timeout_seconds = timeout_seconds
        self._ddgs_factory = ddgs_factory

    def search(
        self,
        query,
        *,
        limit,
    ):
        client = self._ddgs_factory(
            timeout=self.timeout_seconds
        )

        kwargs = {
            "region": self.region,
            "safesearch": self.safesearch,
            "timelimit": _TIME_RANGE_MAP[
                self.time_range
            ],
            "max_results": int(limit),
            "backend": self.backend,
        }

        if self.category == "news":
            raw_results = client.news(
                query,
                **kwargs,
            )
        else:
            raw_results = client.text(
                query,
                **kwargs,
            )

        if not isinstance(
            raw_results,
            (list, tuple),
        ):
            raise RuntimeError(
                "DDGS returned an invalid "
                "result collection"
            )

        normalized = []

        for item in raw_results:
            if not isinstance(item, dict):
                continue

            normalized.append(
                {
                    "url": (
                        item.get("href")
                        or item.get("url")
                    ),
                    "title": item.get("title"),
                    "snippet": (
                        item.get("body")
                        or item.get("snippet")
                        or item.get("content")
                    ),
                }
            )

            if len(normalized) >= int(limit):
                break

        return normalized
