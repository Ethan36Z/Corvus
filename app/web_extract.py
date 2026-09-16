from dataclasses import dataclass

from trafilatura import extract as trafilatura_extract

from app.web_search_fetch import (
    FetchedSearchResult,
)
from app.web_security import (
    MAX_EXTRACTED_TEXT_CHARS,
)


_HTML_MEDIA_TYPES = {
    "text/html",
    "application/xhtml+xml",
}

_PASSTHROUGH_APPLICATION_TYPES = {
    "application/json",
    "application/xml",
    "application/rss+xml",
    "application/atom+xml",
}


class WebExtractionError(
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
class ExtractedWebPage:
    result_id: str
    provider: str
    title: str | None
    source_url: str
    fetched_url: str
    media_type: str
    extraction_engine: str
    text: str
    original_chars: int
    extracted_chars: int
    truncated: bool


def _raise(
    code,
    message,
):
    raise WebExtractionError(
        code,
        message,
    )


def _normalize_text(
    value,
):
    if not isinstance(
        value,
        str,
    ):
        _raise(
            "WEB_EXTRACTION_TEXT_INVALID",
            (
                "extracted content "
                "must be text"
            ),
        )

    value = (
        value
        .replace(
            "\r\n",
            "\n",
        )
        .replace(
            "\r",
            "\n",
        )
    )

    lines = [
        line.strip()
        for line in value.split(
            "\n"
        )
    ]

    normalized = []
    blank_pending = False

    for line in lines:
        if line:
            if (
                blank_pending
                and normalized
            ):
                normalized.append(
                    ""
                )

            normalized.append(
                line
            )
            blank_pending = False
        elif normalized:
            blank_pending = True

    return "\n".join(
        normalized
    ).strip()


def _bound_text(
    text,
):
    original_chars = len(
        text
    )

    truncated = (
        original_chars
        > MAX_EXTRACTED_TEXT_CHARS
    )

    if truncated:
        text = text[
            :MAX_EXTRACTED_TEXT_CHARS
        ].rstrip()

    return (
        text,
        original_chars,
        truncated,
    )


def extract_web_page(
    fetched,
    *,
    html_extractor=trafilatura_extract,
):
    """
    Convert one already-fetched public resource into
    bounded readable text.

    This layer owns no networking, persistence,
    evidence selection, or model access.
    """

    if not isinstance(
        fetched,
        FetchedSearchResult,
    ):
        _raise(
            "WEB_EXTRACTION_INPUT_INVALID",
            (
                "input must be a "
                "FetchedSearchResult"
            ),
        )

    media_type = (
        fetched.media_type
        .strip()
        .lower()
    )

    if media_type in _HTML_MEDIA_TYPES:
        try:
            extracted = html_extractor(
                fetched.text,
                output_format="txt",
                include_comments=False,
                include_tables=False,
            )
        except Exception as exc:
            raise WebExtractionError(
                "WEB_EXTRACTION_ENGINE_FAILED",
                (
                    "HTML extraction "
                    "engine failed"
                ),
            ) from exc

        if extracted is None:
            _raise(
                "WEB_EXTRACTION_EMPTY",
                (
                    "HTML extraction produced "
                    "no readable content"
                ),
            )

        text = _normalize_text(
            extracted
        )

        engine = (
            "trafilatura-2.2.0"
        )

    elif (
        media_type.startswith(
            "text/"
        )
        or media_type
        in _PASSTHROUGH_APPLICATION_TYPES
    ):
        text = _normalize_text(
            fetched.text
        )

        engine = (
            "text-passthrough"
        )

    else:
        _raise(
            "WEB_EXTRACTION_MEDIA_TYPE_UNSUPPORTED",
            (
                "extraction received "
                f"unsupported media type: "
                f"{media_type}"
            ),
        )

    if not text:
        _raise(
            "WEB_EXTRACTION_EMPTY",
            (
                "extraction produced "
                "empty readable content"
            ),
        )

    (
        text,
        original_chars,
        truncated,
    ) = _bound_text(
        text
    )

    if not text:
        _raise(
            "WEB_EXTRACTION_EMPTY",
            (
                "bounded extraction "
                "contains no readable content"
            ),
        )

    return ExtractedWebPage(
        result_id=fetched.result_id,
        provider=fetched.provider,
        title=fetched.title,
        source_url=fetched.source_url,
        fetched_url=fetched.fetched_url,
        media_type=media_type,
        extraction_engine=engine,
        text=text,
        original_chars=original_chars,
        extracted_chars=len(
            text
        ),
        truncated=truncated,
    )
