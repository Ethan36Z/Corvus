from app.web_extract import (
    WebExtractionError,
    extract_web_page,
)
from app.web_search_fetch import (
    FetchedSearchResult,
)
from app.web_security import (
    MAX_EXTRACTED_TEXT_CHARS,
)


def fetched(
    *,
    media_type,
    text,
):
    return FetchedSearchResult(
        result_id="result_1",
        provider="fake-provider",
        title="Example",
        source_url=(
            "https://example.com/article"
        ),
        fetched_url=(
            "https://example.com/article"
        ),
        status=200,
        media_type=media_type,
        text=text,
        bytes_read=len(
            text.encode("utf-8")
        ),
        redirects=(),
    )


html = """
<!doctype html>
<html>
  <head>
    <title>Example</title>
  </head>

  <body>
    <nav>
      Home About Contact
    </nav>

    <main>
      <article>
        <h1>
          Corvus Extraction Test
        </h1>

        <p>
          This is the useful article body.
        </p>

        <p>
          External evidence will be selected
          in a later layer.
        </p>
      </article>
    </main>

    <footer>
      Footer navigation
    </footer>
  </body>
</html>
"""

page = extract_web_page(
    fetched(
        media_type="text/html",
        text=html,
    )
)

assert page.result_id == (
    "result_1"
)

assert page.provider == (
    "fake-provider"
)

assert page.extraction_engine == (
    "trafilatura-2.2.0"
)

assert (
    "Corvus Extraction Test"
    in page.text
)

assert (
    "useful article body"
    in page.text
)

assert (
    "External evidence"
    in page.text
)

assert page.truncated is False

assert page.extracted_chars == len(
    page.text
)


plain = extract_web_page(
    fetched(
        media_type="text/plain",
        text=(
            "  first line  \r\n"
            "\r\n"
            "  second line  "
        ),
    )
)

assert plain.extraction_engine == (
    "text-passthrough"
)

assert plain.text == (
    "first line\n\nsecond line"
)


json_page = extract_web_page(
    fetched(
        media_type=(
            "application/json"
        ),
        text=(
            '{"status": "ok"}'
        ),
    )
)

assert json_page.text == (
    '{"status": "ok"}'
)


huge_text = (
    "A"
    * (
        MAX_EXTRACTED_TEXT_CHARS
        + 500
    )
)

bounded = extract_web_page(
    fetched(
        media_type="text/plain",
        text=huge_text,
    )
)

assert bounded.truncated is True

assert bounded.original_chars == (
    MAX_EXTRACTED_TEXT_CHARS
    + 500
)

assert bounded.extracted_chars == (
    MAX_EXTRACTED_TEXT_CHARS
)

assert len(
    bounded.text
) == MAX_EXTRACTED_TEXT_CHARS


extractor_calls = []


def huge_html_extractor(
    html,
    **kwargs,
):
    extractor_calls.append(
        {
            "html": html,
            "kwargs": kwargs,
        }
    )

    return (
        "B"
        * (
            MAX_EXTRACTED_TEXT_CHARS
            + 1000
        )
    )


bounded_html = extract_web_page(
    fetched(
        media_type="text/html",
        text="<html></html>",
    ),
    html_extractor=(
        huge_html_extractor
    ),
)

assert len(
    extractor_calls
) == 1

assert (
    extractor_calls[0]["kwargs"][
        "output_format"
    ]
    == "txt"
)

assert (
    extractor_calls[0]["kwargs"][
        "include_comments"
    ]
    is False
)

assert (
    extractor_calls[0]["kwargs"][
        "include_tables"
    ]
    is False
)

assert bounded_html.truncated is True

assert bounded_html.extracted_chars == (
    MAX_EXTRACTED_TEXT_CHARS
)


def empty_extractor(
    html,
    **kwargs,
):
    return None


try:
    extract_web_page(
        fetched(
            media_type="text/html",
            text="<html></html>",
        ),
        html_extractor=empty_extractor,
    )
except WebExtractionError as exc:
    assert exc.code == (
        "WEB_EXTRACTION_EMPTY"
    )
else:
    raise AssertionError(
        "empty HTML extraction must fail"
    )


try:
    extract_web_page(
        fetched(
            media_type="image/png",
            text="not actually an image",
        )
    )
except WebExtractionError as exc:
    assert exc.code == (
        "WEB_EXTRACTION_MEDIA_TYPE_UNSUPPORTED"
    )
else:
    raise AssertionError(
        "unsupported media type must fail"
    )


print(
    "WEB EXTRACTION HTML CONTRACT OK"
)
print(
    "WEB EXTRACTION TEXT CONTRACT OK"
)
print(
    "WEB EXTRACTION SIZE BOUNDARY CONTRACT OK"
)
print(
    "WEB EXTRACTION EMPTY CONTRACT OK"
)
print(
    "WEB EXTRACTION NO-NETWORK BOUNDARY CONTRACT OK"
)
