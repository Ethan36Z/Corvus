import app.conversation_runtime as runtime

from app.ddgs_provider import DDGSProvider
from app.searxng_provider import SearXNGProvider
from app.web_search_routing import SearchAttempt


original_provider = runtime.WEB_PROVIDER

try:
    #
    # Default production provider.
    #
    runtime.WEB_PROVIDER = "DDGS"

    en_attempt = SearchAttempt(
        name="en-general",
        category="general",
    )

    en_provider = (
        runtime._build_default_web_provider(
            en_attempt
        )
    )

    assert isinstance(
        en_provider,
        DDGSProvider,
    )

    assert en_provider.name == "ddgs"
    assert en_provider.category == "general"
    assert en_provider.region == "us-en"
    assert en_provider.time_range is None

    print(
        "WEB DEFAULT DDGS PROVIDER CONTRACT OK"
    )


    #
    # Existing Chinese routing becomes a DDGS
    # region hint. SearXNG-specific engine_bang
    # does not escape into DDGS.
    #
    zh_attempt = SearchAttempt(
        name="zh-general-goc",
        category="general",
        language="zh-CN",
        engine_bang="goc",
    )

    zh_provider = (
        runtime._build_default_web_provider(
            zh_attempt
        )
    )

    assert isinstance(
        zh_provider,
        DDGSProvider,
    )

    assert zh_provider.region == "cn-zh"

    print(
        "WEB DDGS LANGUAGE ROUTING CONTRACT OK"
    )


    #
    # News route remains discovery-only and
    # preserves the time-range hint.
    #
    news_attempt = SearchAttempt(
        name="en-news",
        category="news",
        time_range="day",
    )

    news_provider = (
        runtime._build_default_web_provider(
            news_attempt
        )
    )

    assert isinstance(
        news_provider,
        DDGSProvider,
    )

    assert news_provider.category == "news"
    assert news_provider.time_range == "day"

    print(
        "WEB DDGS NEWS ROUTING CONTRACT OK"
    )


    #
    # SearXNG remains available as the explicit
    # self-hosted provider.
    #
    runtime.WEB_PROVIDER = "SEARXNG"

    searx_attempt = SearchAttempt(
        name="zh-general-goc",
        category="general",
        language="zh-CN",
        engine_bang="goc",
        time_range="day",
    )

    searx_provider = (
        runtime._build_default_web_provider(
            searx_attempt
        )
    )

    assert isinstance(
        searx_provider,
        SearXNGProvider,
    )

    assert (
        searx_provider.name
        == "searxng-local"
    )

    assert searx_provider.category == "general"
    assert searx_provider.language == "zh-CN"
    assert searx_provider.engine_bang == "goc"
    assert searx_provider.time_range == "day"

    print(
        "WEB OPTIONAL SEARXNG PROVIDER CONTRACT OK"
    )

finally:
    runtime.WEB_PROVIDER = original_provider


print(
    "WEB_PROVIDER_WIRING_COMPLETE: PASS"
)
