from dataclasses import dataclass

from app.web_search import (
    SearchDiscovery,
    SearchDiscoveryError,
    search_web,
)
from app.web_search_routing import (
    SearchPlan,
)


@dataclass(
    frozen=True,
    slots=True,
)
class SearchAttemptOutcome:
    name: str
    status: str
    error_code: str | None = None


@dataclass(
    frozen=True,
    slots=True,
)
class SearchExecution:
    plan: SearchPlan
    selected_attempt: str | None
    discovery: SearchDiscovery | None
    outcomes: tuple[
        SearchAttemptOutcome,
        ...
    ]


def execute_search_plan(
    plan,
    *,
    provider_builder,
    limit=5,
):
    """
    Execute SearchPlan attempts in order.

    Provider failures and empty discoveries fall
    through to the next attempt.

    SearchResult validation remains owned by
    search_web().
    """

    if not isinstance(
        plan,
        SearchPlan,
    ):
        raise TypeError(
            "plan must be a SearchPlan"
        )

    outcomes = []

    for attempt in plan.attempts:
        provider = provider_builder(
            attempt
        )

        try:
            discovery = search_web(
                plan.query,
                provider=provider,
                limit=limit,
            )
        except SearchDiscoveryError as exc:
            if (
                exc.code
                != "WEB_SEARCH_PROVIDER_FAILED"
            ):
                raise

            outcomes.append(
                SearchAttemptOutcome(
                    name=attempt.name,
                    status="provider_failed",
                    error_code=exc.code,
                )
            )

            continue

        if not discovery.results:
            outcomes.append(
                SearchAttemptOutcome(
                    name=attempt.name,
                    status="empty",
                )
            )

            continue

        outcomes.append(
            SearchAttemptOutcome(
                name=attempt.name,
                status="success",
            )
        )

        return SearchExecution(
            plan=plan,
            selected_attempt=attempt.name,
            discovery=discovery,
            outcomes=tuple(outcomes),
        )

    return SearchExecution(
        plan=plan,
        selected_attempt=None,
        discovery=None,
        outcomes=tuple(outcomes),
    )
