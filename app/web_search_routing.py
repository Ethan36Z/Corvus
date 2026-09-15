from dataclasses import dataclass


ZH_NEWS_TERMS = (
    "新闻",
    "最新",
    "今天",
    "今日",
    "刚刚",
    "刚才",
    "近期",
)

EN_NEWS_TERMS = (
    "news",
    "latest",
    "today",
    "breaking",
    "current news",
    "recent news",
)


@dataclass(
    frozen=True,
    slots=True,
)
class SearchAttempt:
    name: str
    category: str
    language: str | None = None
    engine_bang: str | None = None
    time_range: str | None = None


@dataclass(
    frozen=True,
    slots=True,
)
class SearchPlan:
    query: str
    language_family: str
    news_intent: bool
    attempts: tuple[SearchAttempt, ...]


def _normalize_query(
    query,
):
    if not isinstance(query, str):
        raise ValueError(
            "search routing query must be text"
        )

    query = " ".join(
        query.split()
    )

    if not query:
        raise ValueError(
            "search routing query must not be empty"
        )

    return query


def _contains_han(
    text,
):
    return any(
        (
            "\u3400" <= char <= "\u4dbf"
            or "\u4e00" <= char <= "\u9fff"
            or "\uf900" <= char <= "\ufaff"
        )
        for char in text
    )


def _has_news_intent(
    query,
    *,
    chinese,
):
    lowered = query.casefold()

    terms = (
        ZH_NEWS_TERMS
        if chinese
        else EN_NEWS_TERMS
    )

    return any(
        term.casefold() in lowered
        for term in terms
    )


def build_search_plan(
    query,
):
    """
    Build a deterministic Web-search routing plan.

    This function performs no network access and no
    persistence. It only decides which discovery routes
    should be attempted and in what order.
    """

    query = _normalize_query(
        query
    )

    chinese = _contains_han(
        query
    )

    news_intent = _has_news_intent(
        query,
        chinese=chinese,
    )

    if chinese:
        if news_intent:
            attempts = (
                SearchAttempt(
                    name="zh-news",
                    category="news",
                    language="zh-CN",
                    time_range="day",
                ),
                SearchAttempt(
                    name="zh-general-goc",
                    category="general",
                    language="zh-CN",
                    engine_bang="goc",
                    time_range="day",
                ),
            )
        else:
            attempts = (
                SearchAttempt(
                    name="zh-general-goc",
                    category="general",
                    language="zh-CN",
                    engine_bang="goc",
                ),
            )

        language_family = "zh"

    else:
        if news_intent:
            attempts = (
                SearchAttempt(
                    name="en-news",
                    category="news",
                    time_range="day",
                ),
                SearchAttempt(
                    name="en-general-fallback",
                    category="general",
                    time_range="day",
                ),
            )
        else:
            attempts = (
                SearchAttempt(
                    name="en-general",
                    category="general",
                ),
            )

        language_family = "default"

    return SearchPlan(
        query=query,
        language_family=language_family,
        news_intent=news_intent,
        attempts=attempts,
    )
