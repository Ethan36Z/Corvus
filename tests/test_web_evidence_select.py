from app.web_evidence_select import (
    DEFAULT_MAX_USED_EVIDENCE_CHARS,
    DEFAULT_MAX_USED_EVIDENCE_ITEMS,
    WebEvidenceSelectionError,
    select_used_web_evidence,
)
from app.web_extract import (
    ExtractedWebPage,
)
from app.web_passages import (
    RankedWebPassage,
    WebPassage,
    build_web_passages,
    rank_web_passages,
)


def page_with_text(
    text,
):
    return ExtractedWebPage(
        result_id="result_1",
        provider="fake-provider",
        title="Example Source",
        source_url=(
            "https://example.com/original"
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


text = """
Python 3.14 introduces several standard library
improvements and interpreter changes.

The new compression.zstd module provides compression
and decompression APIs for the Zstandard format.
Zstandard is designed to provide high compression
ratios with fast decompression.

Python 3.14 also improves asyncio introspection and
adds several developer-facing debugging capabilities.

Template string literals are another major language
feature introduced in Python 3.14.

The standard library continues to receive usability
and correctness improvements throughout the release.
""".strip()

page = page_with_text(
    text
)

passages = build_web_passages(
    page,
    target_chars=180,
    overlap_chars=30,
)

ranked = rank_web_passages(
    (
        "Python 3.14 Zstandard "
        "compression module"
    ),
    passages,
)

selected = select_used_web_evidence(
    page,
    ranked,
)

assert selected

assert (
    len(selected)
    <= DEFAULT_MAX_USED_EVIDENCE_ITEMS
)

assert (
    sum(
        len(item.excerpt)
        for item in selected
    )
    <= DEFAULT_MAX_USED_EVIDENCE_CHARS
)

selected_text = "\n\n".join(
    item.excerpt
    for item in selected
)

assert (
    "Zstandard"
    in selected_text
)

assert (
    "compression.zstd"
    in selected_text
)

assert (
    selected[0].passage_id
    == ranked[0].passage.passage_id
)

for index, item in enumerate(
    selected,
):
    assert item.evidence_ref == (
        f"web_{index + 1}"
    )

    assert item.ordinal == index

    assert item.source_url == (
        "https://example.com/article"
    )

    assert item.source_title == (
        "Example Source"
    )

    assert (
        page.text[
            item.start_char:
            item.end_char
        ].strip()
        == item.excerpt
    )


top = ranked[0]

duplicate_selection = (
    top,
    top,
)

deduplicated = select_used_web_evidence(
    page,
    duplicate_selection,
)

assert len(
    deduplicated
) == 1


single_budget = select_used_web_evidence(
    page,
    ranked,
    max_items=1,
    max_total_chars=(
        len(
            ranked[0]
            .passage
            .text
        )
        + 1
    ),
)

assert len(
    single_budget
) == 1


too_small_budget = (
    len(
        ranked[0]
        .passage
        .text
    )
    - 1
)

nothing_fits = select_used_web_evidence(
    page,
    (
        ranked[0],
    ),
    max_total_chars=(
        too_small_budget
    ),
)

assert nothing_fits == ()


foreign_passage = WebPassage(
    passage_id="foreign",
    ordinal=999,
    start_char=0,
    end_char=10,
    text="not-source",
)

foreign_ranked = RankedWebPassage(
    passage=foreign_passage,
    score=10.0,
    matched_terms=(
        "python",
    ),
    exact_phrase_match=False,
)

try:
    select_used_web_evidence(
        page,
        (
            foreign_ranked,
        ),
    )
except WebEvidenceSelectionError as exc:
    assert exc.code == (
        "WEB_EVIDENCE_PASSAGE_MISMATCH"
    )
else:
    raise AssertionError(
        (
            "foreign passage text "
            "must be rejected"
        )
    )


print(
    "WEB USED-EVIDENCE EXACT-SLICE CONTRACT OK"
)
print(
    "WEB USED-EVIDENCE BUDGET CONTRACT OK"
)
print(
    "WEB USED-EVIDENCE OVERLAP CONTRACT OK"
)
print(
    "WEB USED-EVIDENCE SOURCE-PROVENANCE CONTRACT OK"
)
print(
    "WEB USED-EVIDENCE NO-MODEL BOUNDARY CONTRACT OK"
)
