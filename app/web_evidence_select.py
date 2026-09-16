from dataclasses import dataclass

from app.web_extract import (
    ExtractedWebPage,
)
from app.web_passages import (
    RankedWebPassage,
)
from app.web_security import (
    validate_public_url,
)


DEFAULT_MAX_USED_EVIDENCE_ITEMS = 3
DEFAULT_MAX_USED_EVIDENCE_CHARS = 3600
DEFAULT_MAX_OVERLAP_RATIO = 0.50


class WebEvidenceSelectionError(
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
class UsedWebEvidence:
    evidence_ref: str
    ordinal: int

    result_id: str
    provider: str

    source_url: str
    source_title: str | None

    passage_id: str
    start_char: int
    end_char: int

    excerpt: str
    score: float

    matched_terms: tuple[str, ...]
    exact_phrase_match: bool


def _raise(
    code,
    message,
):
    raise WebEvidenceSelectionError(
        code,
        message,
    )


def _interval_overlap_ratio(
    first_start,
    first_end,
    second_start,
    second_end,
):
    overlap = max(
        0,
        min(
            first_end,
            second_end,
        )
        - max(
            first_start,
            second_start,
        ),
    )

    if overlap <= 0:
        return 0.0

    first_size = max(
        0,
        first_end - first_start,
    )

    second_size = max(
        0,
        second_end - second_start,
    )

    smaller = min(
        first_size,
        second_size,
    )

    if smaller <= 0:
        return 1.0

    return (
        overlap
        / smaller
    )


def _verified_excerpt(
    page,
    ranked,
):
    passage = ranked.passage

    start = int(
        passage.start_char
    )

    end = int(
        passage.end_char
    )

    if (
        start < 0
        or end <= start
        or end > len(page.text)
    ):
        _raise(
            "WEB_EVIDENCE_PASSAGE_RANGE_INVALID",
            (
                "passage character range "
                "is outside extracted page"
            ),
        )

    source_slice = page.text[
        start:end
    ].strip()

    if (
        source_slice
        != passage.text
    ):
        _raise(
            "WEB_EVIDENCE_PASSAGE_MISMATCH",
            (
                "passage text does not match "
                "its extracted-page source slice"
            ),
        )

    if not source_slice:
        _raise(
            "WEB_EVIDENCE_EXCERPT_EMPTY",
            (
                "used Web evidence "
                "must not be empty"
            ),
        )

    return source_slice


def select_used_web_evidence(
    page,
    ranked_passages,
    *,
    max_items=(
        DEFAULT_MAX_USED_EVIDENCE_ITEMS
    ),
    max_total_chars=(
        DEFAULT_MAX_USED_EVIDENCE_CHARS
    ),
    max_overlap_ratio=(
        DEFAULT_MAX_OVERLAP_RATIO
    ),
):
    """
    Select exact source excerpts from ranked Web
    passage candidates.

    This function owns no networking, persistence,
    model inference, embeddings, or GPU work.
    """

    if not isinstance(
        page,
        ExtractedWebPage,
    ):
        _raise(
            "WEB_EVIDENCE_PAGE_INVALID",
            (
                "page must be an "
                "ExtractedWebPage"
            ),
        )

    try:
        max_items = int(
            max_items
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise WebEvidenceSelectionError(
            "WEB_EVIDENCE_BUDGET_INVALID",
            "max_items must be an integer",
        ) from exc

    try:
        max_total_chars = int(
            max_total_chars
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise WebEvidenceSelectionError(
            "WEB_EVIDENCE_BUDGET_INVALID",
            (
                "max_total_chars "
                "must be an integer"
            ),
        ) from exc

    try:
        max_overlap_ratio = float(
            max_overlap_ratio
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise WebEvidenceSelectionError(
            "WEB_EVIDENCE_OVERLAP_INVALID",
            (
                "max_overlap_ratio "
                "must be numeric"
            ),
        ) from exc

    if max_items <= 0:
        _raise(
            "WEB_EVIDENCE_BUDGET_INVALID",
            "max_items must be positive",
        )

    if max_total_chars <= 0:
        _raise(
            "WEB_EVIDENCE_BUDGET_INVALID",
            (
                "max_total_chars "
                "must be positive"
            ),
        )

    if not (
        0.0
        <= max_overlap_ratio
        <= 1.0
    ):
        _raise(
            "WEB_EVIDENCE_OVERLAP_INVALID",
            (
                "max_overlap_ratio must "
                "be between 0 and 1"
            ),
        )

    source_url = validate_public_url(
        page.fetched_url
    )["url"]

    ranked_passages = tuple(
        ranked_passages
    )

    selected = []
    total_chars = 0

    for ranked in ranked_passages:
        if not isinstance(
            ranked,
            RankedWebPassage,
        ):
            _raise(
                "WEB_EVIDENCE_CANDIDATE_INVALID",
                (
                    "ranked candidates must "
                    "contain RankedWebPassage "
                    "records"
                ),
            )

        if ranked.score <= 0.0:
            continue

        excerpt = _verified_excerpt(
            page,
            ranked,
        )

        passage = ranked.passage

        redundant = any(
            _interval_overlap_ratio(
                passage.start_char,
                passage.end_char,
                item.start_char,
                item.end_char,
            )
            >= max_overlap_ratio
            for item in selected
        )

        if redundant:
            continue

        if (
            total_chars
            + len(excerpt)
            > max_total_chars
        ):
            continue

        ordinal = len(
            selected
        )

        selected.append(
            UsedWebEvidence(
                evidence_ref=(
                    f"web_{ordinal + 1}"
                ),
                ordinal=ordinal,
                result_id=page.result_id,
                provider=page.provider,
                source_url=source_url,
                source_title=page.title,
                passage_id=(
                    passage.passage_id
                ),
                start_char=(
                    passage.start_char
                ),
                end_char=(
                    passage.end_char
                ),
                excerpt=excerpt,
                score=float(
                    ranked.score
                ),
                matched_terms=tuple(
                    ranked.matched_terms
                ),
                exact_phrase_match=(
                    ranked
                    .exact_phrase_match
                ),
            )
        )

        total_chars += len(
            excerpt
        )

        if len(selected) >= max_items:
            break

    return tuple(
        selected
    )
