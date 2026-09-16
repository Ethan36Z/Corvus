from dataclasses import dataclass

from app.web_evidence_select import (
    UsedWebEvidence,
    WebEvidenceSelectionError,
    select_used_web_evidence,
)
from app.web_extract import (
    WebExtractionError,
    extract_web_page,
)
from app.web_fetch import (
    WebFetchError,
)
from app.web_passages import (
    WebPassageError,
    build_web_passages,
    rank_web_passages,
)
from app.web_search_execution import (
    SearchExecution,
    execute_search_plan,
)
from app.web_search_fetch import (
    SearchResultFetchError,
    fetch_search_result,
)
from app.web_search_routing import (
    build_search_plan,
)


DEFAULT_SEARCH_LIMIT = 5
DEFAULT_MAX_FETCH_CANDIDATES = 3


@dataclass(
    frozen=True,
    slots=True,
)
class WebCandidateOutcome:
    result_id: str
    status: str
    error_code: str | None = None


@dataclass(
    frozen=True,
    slots=True,
)
class WebGroundingPreparation:
    query: str
    status: str

    search_execution: SearchExecution

    selected_result_id: str | None

    used_web_evidence: tuple[
        UsedWebEvidence,
        ...
    ]

    candidate_outcomes: tuple[
        WebCandidateOutcome,
        ...
    ]


def _normalize_positive_int(
    value,
    *,
    name,
):
    try:
        value = int(
            value
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise ValueError(
            f"{name} must be an integer"
        ) from exc

    if value <= 0:
        raise ValueError(
            f"{name} must be positive"
        )

    return value


def prepare_web_grounding(
    query,
    *,
    provider_builder,
    search_limit=DEFAULT_SEARCH_LIMIT,
    max_fetch_candidates=(
        DEFAULT_MAX_FETCH_CANDIDATES
    ),
    build_search_plan_fn=build_search_plan,
    execute_search_plan_fn=(
        execute_search_plan
    ),
    fetch_search_result_fn=(
        fetch_search_result
    ),
    extract_web_page_fn=(
        extract_web_page
    ),
    build_web_passages_fn=(
        build_web_passages
    ),
    rank_web_passages_fn=(
        rank_web_passages
    ),
    select_used_web_evidence_fn=(
        select_used_web_evidence
    ),
):
    """
    Prepare current-turn Web grounding without
    model inference or persistence.

    Web v1 orchestration currently selects evidence
    from the first usable source page.

    Multiple SearchResults may be attempted for
    resilience, but evidence from different pages
    is not merged here. Global multi-source evidence
    merging requires its own reference / ordinal
    contract.
    """

    search_limit = (
        _normalize_positive_int(
            search_limit,
            name="search_limit",
        )
    )

    max_fetch_candidates = (
        _normalize_positive_int(
            max_fetch_candidates,
            name="max_fetch_candidates",
        )
    )

    plan = build_search_plan_fn(
        query
    )

    execution = (
        execute_search_plan_fn(
            plan,
            provider_builder=(
                provider_builder
            ),
            limit=search_limit,
        )
    )

    if execution.discovery is None:
        return WebGroundingPreparation(
            query=plan.query,
            status="NO_RESULTS",
            search_execution=execution,
            selected_result_id=None,
            used_web_evidence=(),
            candidate_outcomes=(),
        )

    outcomes = []

    candidates = (
        execution.discovery.results[
            :max_fetch_candidates
        ]
    )

    for result in candidates:
        try:
            fetched = (
                fetch_search_result_fn(
                    execution.discovery,
                    result.result_id,
                )
            )

        except (
            SearchResultFetchError,
            WebFetchError,
        ) as exc:
            outcomes.append(
                WebCandidateOutcome(
                    result_id=(
                        result.result_id
                    ),
                    status="FETCH_FAILED",
                    error_code=getattr(
                        exc,
                        "code",
                        None,
                    ),
                )
            )
            continue

        try:
            page = extract_web_page_fn(
                fetched
            )

        except WebExtractionError as exc:
            outcomes.append(
                WebCandidateOutcome(
                    result_id=(
                        result.result_id
                    ),
                    status=(
                        "EXTRACTION_FAILED"
                    ),
                    error_code=exc.code,
                )
            )
            continue

        try:
            passages = (
                build_web_passages_fn(
                    page
                )
            )

            ranked = (
                rank_web_passages_fn(
                    plan.query,
                    passages,
                )
            )

        except WebPassageError as exc:
            outcomes.append(
                WebCandidateOutcome(
                    result_id=(
                        result.result_id
                    ),
                    status="PASSAGE_FAILED",
                    error_code=exc.code,
                )
            )
            continue

        try:
            used_evidence = (
                select_used_web_evidence_fn(
                    page,
                    ranked,
                )
            )

        except WebEvidenceSelectionError as exc:
            outcomes.append(
                WebCandidateOutcome(
                    result_id=(
                        result.result_id
                    ),
                    status=(
                        "EVIDENCE_SELECTION_FAILED"
                    ),
                    error_code=exc.code,
                )
            )
            continue

        if not used_evidence:
            outcomes.append(
                WebCandidateOutcome(
                    result_id=(
                        result.result_id
                    ),
                    status=(
                        "NO_RELEVANT_EVIDENCE"
                    ),
                )
            )
            continue

        outcomes.append(
            WebCandidateOutcome(
                result_id=(
                    result.result_id
                ),
                status="SELECTED",
            )
        )

        return WebGroundingPreparation(
            query=plan.query,
            status="READY",
            search_execution=execution,
            selected_result_id=(
                result.result_id
            ),
            used_web_evidence=tuple(
                used_evidence
            ),
            candidate_outcomes=tuple(
                outcomes
            ),
        )

    return WebGroundingPreparation(
        query=plan.query,
        status="NO_USABLE_EVIDENCE",
        search_execution=execution,
        selected_result_id=None,
        used_web_evidence=(),
        candidate_outcomes=tuple(
            outcomes
        ),
    )
