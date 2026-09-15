from app.web_search_routing import (
    build_search_plan,
)


def names(plan):
    return tuple(
        attempt.name
        for attempt in plan.attempts
    )


english_general = build_search_plan(
    "Qwen3.5 llama.cpp"
)

assert english_general.query == (
    "Qwen3.5 llama.cpp"
)
assert english_general.language_family == (
    "default"
)
assert english_general.news_intent is False
assert names(english_general) == (
    "en-general",
)

assert (
    english_general.attempts[0].category
    == "general"
)

assert (
    english_general.attempts[0].engine_bang
    is None
)


english_news = build_search_plan(
    "OpenAI latest news"
)

assert english_news.language_family == (
    "default"
)
assert english_news.news_intent is True
assert names(english_news) == (
    "en-news",
    "en-general-fallback",
)

assert (
    english_news.attempts[0].category
    == "news"
)
assert (
    english_news.attempts[0].time_range
    == "day"
)
assert (
    english_news.attempts[1].category
    == "general"
)


chinese_general = build_search_plan(
    "洛杉矶餐馆"
)

assert chinese_general.language_family == (
    "zh"
)
assert chinese_general.news_intent is False
assert names(chinese_general) == (
    "zh-general-goc",
)

zh_general_attempt = (
    chinese_general.attempts[0]
)

assert (
    zh_general_attempt.category
    == "general"
)
assert (
    zh_general_attempt.language
    == "zh-CN"
)
assert (
    zh_general_attempt.engine_bang
    == "goc"
)
assert (
    zh_general_attempt.time_range
    is None
)


chinese_news = build_search_plan(
    "洛杉矶 今日 新闻"
)

assert chinese_news.language_family == (
    "zh"
)
assert chinese_news.news_intent is True
assert names(chinese_news) == (
    "zh-news",
    "zh-general-goc",
)

zh_news_primary = (
    chinese_news.attempts[0]
)
zh_news_fallback = (
    chinese_news.attempts[1]
)

assert (
    zh_news_primary.category
    == "news"
)
assert (
    zh_news_primary.language
    == "zh-CN"
)
assert (
    zh_news_primary.time_range
    == "day"
)

assert (
    zh_news_fallback.category
    == "general"
)
assert (
    zh_news_fallback.language
    == "zh-CN"
)
assert (
    zh_news_fallback.engine_bang
    == "goc"
)
assert (
    zh_news_fallback.time_range
    == "day"
)


traditional_chinese = build_search_plan(
    "洛杉磯最新消息"
)

assert traditional_chinese.language_family == (
    "zh"
)
assert traditional_chinese.news_intent is True


normalized = build_search_plan(
    "  OpenAI   today  "
)

assert normalized.query == (
    "OpenAI today"
)
assert normalized.news_intent is True


try:
    build_search_plan("   ")
except ValueError:
    pass
else:
    raise AssertionError(
        "empty query must fail"
    )


print(
    "WEB SEARCH ROUTING LANGUAGE CONTRACT OK"
)
print(
    "WEB SEARCH ROUTING NEWS INTENT CONTRACT OK"
)
print(
    "WEB SEARCH ROUTING FALLBACK CONTRACT OK"
)
print(
    "WEB SEARCH ROUTING PURE POLICY CONTRACT OK"
)
