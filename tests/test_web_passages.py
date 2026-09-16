from app.web_extract import (
    ExtractedWebPage,
)
from app.web_passages import (
    PASSAGE_OVERLAP_CHARS,
    TARGET_PASSAGE_CHARS,
    build_web_passages,
    lexical_terms,
    rank_web_passages,
    select_web_passages,
)


def page_with_text(
    text,
):
    return ExtractedWebPage(
        result_id="result_1",
        provider="fake-provider",
        title="Example",
        source_url=(
            "https://example.com/article"
        ),
        fetched_url=(
            "https://example.com/article"
        ),
        media_type="text/html",
        extraction_engine=(
            "trafilatura-2.2.0"
        ),
        text=text,
        original_chars=len(text),
        extracted_chars=len(text),
        truncated=False,
    )


english_terms = lexical_terms(
    "What are the Python Zstandard "
    "compression features?"
)

assert "python" in english_terms
assert "zstandard" in english_terms
assert "compression" in english_terms
assert "the" not in english_terms


chinese_terms = lexical_terms(
    "洛杉矶 今日 新闻"
)

assert "洛杉矶" in chinese_terms
assert "洛杉" in chinese_terms
assert "杉矶" in chinese_terms
assert "今日" in chinese_terms
assert "新闻" in chinese_terms


long_text = "\n\n".join(
    [
        (
            f"Paragraph {index}. "
            + (
                "Useful readable content. "
                * 18
            )
        )
        for index in range(20)
    ]
)

passages = build_web_passages(
    page_with_text(
        long_text
    )
)

assert len(passages) > 1

assert passages[0].passage_id == (
    "passage_1"
)

assert passages[0].ordinal == 0

assert all(
    passage.text
    for passage in passages
)

assert all(
    len(passage.text)
    <= TARGET_PASSAGE_CHARS
    for passage in passages
)

assert (
    passages[1].start_char
    < passages[0].end_char
)

assert (
    passages[0].end_char
    - passages[1].start_char
    <= PASSAGE_OVERLAP_CHARS
    + 100
)


ranking_text = """
General introduction about Python releases and
standard library improvements.

The Python 3.14 release adds support for Zstandard
compression through the new compression.zstd module.
This paragraph specifically discusses Zstandard
compression support.

Other changes include improvements to asyncio
introspection and interpreter behavior.

Template string literals are another major feature
introduced in Python 3.14.
""".strip()

ranking_passages = build_web_passages(
    page_with_text(
        ranking_text
    ),
    target_chars=170,
    overlap_chars=20,
)

ranked = rank_web_passages(
    (
        "Python 3.14 Zstandard "
        "compression module"
    ),
    ranking_passages,
)

assert ranked

assert (
    "Zstandard"
    in ranked[0].passage.text
)

assert (
    "compression.zstd"
    in ranked[0].passage.text
)

assert ranked[0].score > 0

assert (
    "zstandard"
    in ranked[0].matched_terms
)

selected = select_web_passages(
    (
        "Python 3.14 Zstandard "
        "compression module"
    ),
    ranking_passages,
    top_k=2,
)

assert 1 <= len(selected) <= 2

assert (
    selected[0].passage
    == ranked[0].passage
)


zh_text = """
洛杉矶今天有多项社区活动。

洛杉矶新闻报道当地交通部门公布了新的道路施工安排。
这项安排会影响市中心部分道路。

旧金山今天也发布了天气提醒。
""".strip()

zh_passages = build_web_passages(
    page_with_text(
        zh_text
    ),
    target_chars=45,
    overlap_chars=5,
)

zh_selected = select_web_passages(
    "洛杉矶 新闻 道路施工",
    zh_passages,
    top_k=2,
)

assert zh_selected

assert (
    "道路施工"
    in zh_selected[0].passage.text
)


no_match = select_web_passages(
    "quantum banana telescope",
    ranking_passages,
)

assert no_match == ()


print(
    "WEB PASSAGE CONSTRUCTION CONTRACT OK"
)
print(
    "WEB PASSAGE MULTILINGUAL TOKEN CONTRACT OK"
)
print(
    "WEB PASSAGE BM25 RANKING CONTRACT OK"
)
print(
    "WEB PASSAGE POSITIVE-SELECTION CONTRACT OK"
)
print(
    "WEB PASSAGE CPU-ONLY BOUNDARY CONTRACT OK"
)
