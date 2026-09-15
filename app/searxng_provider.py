import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen


DEFAULT_SEARXNG_BASE_URL = (
    "http://127.0.0.1:8110"
)

DEFAULT_SEARXNG_TIMEOUT_SECONDS = 10

MAX_SEARXNG_RESPONSE_BYTES = (
    2 * 1024 * 1024
)


def _fetch_json(
    url,
    *,
    timeout,
):
    request = Request(
        url,
        method="GET",
        headers={
            "Accept": "application/json",
            "User-Agent": (
                "Corvus-SearXNG-Adapter/1"
            ),
        },
    )

    with urlopen(
        request,
        timeout=timeout,
    ) as response:
        body = response.read(
            MAX_SEARXNG_RESPONSE_BYTES
            + 1
        )

    if (
        len(body)
        > MAX_SEARXNG_RESPONSE_BYTES
    ):
        raise RuntimeError(
            "SearXNG response exceeds "
            "the adapter limit"
        )

    try:
        payload = json.loads(
            body.decode("utf-8")
        )
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:
        raise RuntimeError(
            "SearXNG returned invalid JSON"
        ) from exc

    return payload


class SearXNGProvider:
    """
    Thin adapter from the local SearXNG JSON API
    to the Corvus SearchProvider protocol.

    This adapter performs discovery only.

    It does not:
    - persist search activity,
    - fetch discovered public pages,
    - bypass Corvus Web URL validation,
    - expose arbitrary network destinations
      to the model.
    """

    name = "searxng-local"

    def __init__(
        self,
        *,
        base_url=DEFAULT_SEARXNG_BASE_URL,
        timeout_seconds=(
            DEFAULT_SEARXNG_TIMEOUT_SECONDS
        ),
        fetch_json=None,
        category="general",
        language=None,
        engine_bang=None,
        time_range=None,
    ):
        if not isinstance(
            base_url,
            str,
        ):
            raise ValueError(
                "SearXNG base URL must "
                "be text"
            )

        base_url = base_url.strip().rstrip(
            "/"
        )

        if not base_url:
            raise ValueError(
                "SearXNG base URL must "
                "not be empty"
            )

        self.base_url = base_url
        self.timeout_seconds = float(
            timeout_seconds
        )

        if self.timeout_seconds <= 0:
            raise ValueError(
                "SearXNG timeout must "
                "be positive"
            )

        self._fetch_json = (
            fetch_json
            if fetch_json is not None
            else _fetch_json
        )

        category = str(
            category
        ).strip()

        if not category:
            raise ValueError(
                "SearXNG category must not be empty"
            )

        self.category = category

        if language is None:
            self.language = None
        else:
            language = str(
                language
            ).strip()

            self.language = (
                language
                if language
                else None
            )

        if engine_bang is None:
            self.engine_bang = None
        else:
            engine_bang = str(
                engine_bang
            ).strip()

            if engine_bang.startswith("!"):
                engine_bang = (
                    engine_bang[1:]
                )

            if (
                not engine_bang
                or any(
                    char.isspace()
                    for char in engine_bang
                )
            ):
                raise ValueError(
                    "SearXNG engine bang is invalid"
                )

            self.engine_bang = (
                engine_bang
            )

        if time_range not in (
            None,
            "day",
            "month",
            "year",
        ):
            raise ValueError(
                "SearXNG time range is invalid"
            )

        self.time_range = time_range

    def with_route(
        self,
        *,
        category,
        language=None,
        engine_bang=None,
        time_range=None,
    ):
        return SearXNGProvider(
            base_url=self.base_url,
            timeout_seconds=(
                self.timeout_seconds
            ),
            fetch_json=self._fetch_json,
            category=category,
            language=language,
            engine_bang=engine_bang,
            time_range=time_range,
        )

    def search(
        self,
        query,
        *,
        limit,
    ):
        routed_query = query

        if self.engine_bang:
            routed_query = (
                f"!{self.engine_bang} "
                f"{query}"
            )

        params = {
            "q": routed_query,
            "format": "json",
            "categories": self.category,
        }

        if self.language:
            params["language"] = (
                self.language
            )

        if self.time_range:
            params["time_range"] = (
                self.time_range
            )

        endpoint = (
            self.base_url
            + "/search?"
            + urlencode(params)
        )

        payload = self._fetch_json(
            endpoint,
            timeout=self.timeout_seconds,
        )

        if not isinstance(
            payload,
            dict,
        ):
            raise RuntimeError(
                "SearXNG response must "
                "be a JSON object"
            )

        results = payload.get(
            "results"
        )

        if not isinstance(
            results,
            list,
        ):
            raise RuntimeError(
                "SearXNG response is missing "
                "a result list"
            )

        normalized = []

        for item in results:
            if not isinstance(
                item,
                dict,
            ):
                continue

            normalized.append(
                {
                    "url": item.get(
                        "url"
                    ),
                    "title": item.get(
                        "title"
                    ),
                    "snippet": item.get(
                        "content"
                    ),
                }
            )

            if (
                len(normalized)
                >= limit
            ):
                break

        return normalized
