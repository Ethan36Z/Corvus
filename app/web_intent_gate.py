import re
from dataclasses import dataclass

from app.model_client import (
    ModelClientError,
    generate_chat_completion,
)


WEB_INTENT_SYSTEM_PROMPT = """
You are a routing classifier for Corvus.

Question:
Does answering this user request well require
current external public Web information?

Output exactly one token:

WEB

or:

NO_WEB

Use WEB when:
- the user explicitly asks to search, check, browse,
  look up, or use current Web information;
- the answer depends on changing current public
  information such as weather, news, prices,
  live status, scores, schedules, current officials,
  recent software releases, or current documentation;
- the user asks to verify whether a potentially recent
  external event, release, or claim has actually happened.

Use NO_WEB when:
- the user explicitly says not to search or browse;
- the answer should come from conversation memory;
- the user supplied the relevant text, code, or image;
- it is creative writing, emotional conversation,
  reasoning, translation, or stable general knowledge.

Do not answer the user's request.
Do not explain your decision.
""".strip()


@dataclass(
    frozen=True,
)
class WebIntentDecision:
    decision: str
    source: str
    signal: str | None = None
    error: str | None = None


_NO_WEB_PATTERNS = (
    (
        "explicit_no_web_en",
        re.compile(
            r"\b(?:do\s+not|don['’]?t|never)\s+"
            r"(?:search|browse|look\s+up|"
            r"use\s+(?:the\s+)?web)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "explicit_no_web_zh",
        re.compile(
            r"(?:不要|别)"
            r"(?:查|搜索|联网|浏览)"
            r"(?:网页|网络|web)?",
            re.IGNORECASE,
        ),
    ),
    (
        "conversation_memory_en",
        re.compile(
            r"\b(?:what\s+did\s+i\s+tell\s+you|"
            r"what\s+do\s+you\s+remember)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "conversation_memory_zh",
        re.compile(
            r"昨天我跟你说",
            re.IGNORECASE,
        ),
    ),
)


_WEB_PATTERNS = (
    (
        "explicit_search_en",
        re.compile(
            r"\b(?:search\s+(?:the\s+)?web|"
            r"look\s+up|browse\s+(?:the\s+)?web)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "explicit_search_zh",
        re.compile(
            r"(?:帮我查一下|查一下|搜索一下)",
            re.IGNORECASE,
        ),
    ),
    (
        "current_dynamic_en",
        re.compile(
            r"\b(?:current|latest|right\s+now|"
            r"today['’]?s?)\b"
            r".{0,80}"
            r"\b(?:weather|news|price|score|schedule|"
            r"status|president|prime\s+minister|mayor|"
            r"governor|version|release|lts)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "dynamic_current_en",
        re.compile(
            r"\b(?:weather|news|price|score|schedule|"
            r"status)\b"
            r".{0,80}"
            r"\b(?:today|tomorrow|this\s+weekend|"
            r"right\s+now|currently)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "forecast_en",
        re.compile(
            r"\b(?:will\s+it\s+rain|will\s+it\s+snow)\b"
            r".{0,80}"
            r"\b(?:today|tomorrow|this\s+weekend|"
            r"this\s+week)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "current_dynamic_zh",
        re.compile(
            r"(?:今天|现在|目前|最新)"
            r".{0,40}"
            r"(?:天气|新闻|消息|比分|价格|版本|发布)",
            re.IGNORECASE,
        ),
    ),
    (
        "dynamic_current_zh",
        re.compile(
            r"(?:天气|新闻|消息|比分|价格|版本|发布)"
            r".{0,40}"
            r"(?:今天|现在|目前|最新)",
            re.IGNORECASE,
        ),
    ),
    (
        "forecast_zh",
        re.compile(
            r"(?:天气预报|会下雨|会下雪)"
            r".{0,40}"
            r"(?:今天|明天|周末|这周)",
            re.IGNORECASE,
        ),
    ),
    (
        "current_documentation_en",
        re.compile(
            r"\b(?:current|latest|up[- ]to[- ]date)\b"
            r".{0,80}"
            r"\b(?:documentation|docs?|official\s+docs?|"
            r"official\s+documentation|source)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "current_documentation_zh",
        re.compile(
            r"(?:当前|最新|现在)"
            r".{0,40}"
            r"(?:文档|官方文档|官方资料|资料)",
            re.IGNORECASE,
        ),
    ),
    (
        "recent_claim_verification_en",
        re.compile(
            r"\b(?:has|have)\b"
            r".{0,100}"
            r"\bactually\b"
            r".{0,60}"
            r"\b(?:happened|released|launched|shipped)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "release_verification_en",
        re.compile(
            r"\b(?:is|are)\b"
            r".{0,100}"
            r"\b(?:out|released|available)\b"
            r".{0,40}"
            r"\b(?:yet|now|currently)\b",
            re.IGNORECASE,
        ),
    ),
)


# Release / feature questions. A feature word alone is not enough: it must
# co-occur with a concrete subject or a recency word, so that casual chat or
# questions about Corvus itself ("你有什么新功能？") stay off the Web.
_RELEASE_TERMS_EN = re.compile(
    r"\b(?:new\s+features?|what['’]?s\s+new|release\s+notes?|changelog|"
    r"released?|release\s+date|latest\s+version)\b",
    re.IGNORECASE,
)
_RELEASE_TERMS_ZH = re.compile(
    r"新特性|新功能|更新了什么|有什么新|有哪些新|发布日期|什么时候发布|"
    r"最新版本|版本号|更新日志|发行说明"
)
_VERSION = re.compile(r"(?<![\w.])v?\d+(?:\.\d+)*(?![\w.])", re.IGNORECASE)
_RECENCY = re.compile(
    r"最新|最近|今年|目前|现在|\b(?:latest|current|recent|this\s+year)\b",
    re.IGNORECASE,
)
_ASCII_WORD = re.compile(r"[A-Za-z][A-Za-z0-9.+#-]*[A-Za-z0-9+#]")
_DOTTED_NAME = re.compile(r"\b[A-Za-z]+\.[A-Za-z]+\b")
# Corvus itself and generic words are never an external subject.
_SELF_OR_GENERIC = {
    "corvus", "you", "your", "i", "my", "we", "it", "this", "that", "app",
}


def _external_subject_en(query):
    if _DOTTED_NAME.search(query):
        return True
    # A capitalized word that does not start a sentence.
    sentence_start = True
    for word in re.findall(r"[A-Za-z][A-Za-z0-9+#'’-]*|[.!?]", query):
        if word in ".!?":
            sentence_start = True
            continue
        if (not sentence_start and word[0].isupper()
                and word.lower() not in _SELF_OR_GENERIC):
            return True
        sentence_start = False
    return False


def _external_subject_zh(query):
    return any(
        word.lower() not in _SELF_OR_GENERIC
        for word in _ASCII_WORD.findall(query)
    )


# Requests to create, write or design something ("给组件加个新功能",
# "Write release notes for v1.4") share the release/feature vocabulary but are
# not lookups. Only concrete authoring phrasing counts; possessives such as
# "我的" / "my" do not, so "我的设备能否升级到最新版本" still goes to Web.
# A match only withdraws this rule: the model classifier still decides.
_AUTHORING_REQUEST = re.compile(
    r"(?:加|添加|增加|新增)(?:一个|个|一些|几个|点)|给.{0,24}(?:加|添加|增加)|"
    r"写(?:了|个|一个|一份|一篇|篇)|帮我写|编写|起草|撰写|"
    r"实现(?:一个|个|这个|那个)|设计(?:一下|一个|个)|构思|想法|点子|头脑风暴|"
    r"\b(?:add|adding|implement(?:ing)?|write|writing|draft(?:ing)?|"
    r"create|creating|design(?:ing)?|brainstorm(?:ing)?|ideas?)\b",
    re.IGNORECASE,
)


def _release_feature_signal(query):
    if _AUTHORING_REQUEST.search(query):
        return None
    anchored = _VERSION.search(query) or _RECENCY.search(query)
    if _RELEASE_TERMS_ZH.search(query) and (anchored or _external_subject_zh(query)):
        return "release_feature_zh"
    if _RELEASE_TERMS_EN.search(query) and (anchored or _external_subject_en(query)):
        return "release_feature_en"
    return None


def _normalized_text(
    user_query,
):
    if not isinstance(
        user_query,
        str,
    ):
        return ""

    return " ".join(
        user_query.split()
    )


def detect_deterministic_web_intent(
    user_query,
):
    """
    Return a high-confidence deterministic decision,
    or None when semantic classification is required.

    Explicit NO_WEB signals are checked first.
    """
    query = _normalized_text(
        user_query
    )

    if not query:
        return WebIntentDecision(
            decision="NO_WEB",
            source="DETERMINISTIC",
            signal="empty_input",
        )

    for signal, pattern in _NO_WEB_PATTERNS:
        if pattern.search(
            query
        ):
            return WebIntentDecision(
                decision="NO_WEB",
                source="DETERMINISTIC",
                signal=signal,
            )

    for signal, pattern in _WEB_PATTERNS:
        if pattern.search(
            query
        ):
            return WebIntentDecision(
                decision="WEB",
                source="DETERMINISTIC",
                signal=signal,
            )

    signal = _release_feature_signal(
        query
    )
    if signal is not None:
        return WebIntentDecision(
            decision="WEB",
            source="DETERMINISTIC",
            signal=signal,
        )

    return None


def decide_web_intent(
    user_query,
    *,
    generate_fn=generate_chat_completion,
):
    """
    Decide whether this turn needs current public Web
    evidence.

    Deterministic high-confidence signals are evaluated
    first. Only ambiguous turns invoke the model.

    Model failure or invalid classifier output fails
    closed to NO_WEB.
    """
    deterministic = (
        detect_deterministic_web_intent(
            user_query
        )
    )

    if deterministic is not None:
        return deterministic

    query = _normalized_text(
        user_query
    )

    messages = [
        {
            "role": "system",
            "content": (
                WEB_INTENT_SYSTEM_PROMPT
            ),
        },
        {
            "role": "user",
            "content": query,
        },
    ]

    try:
        raw = generate_fn(
            messages
        )
    except ModelClientError as exc:
        return WebIntentDecision(
            decision="NO_WEB",
            source="MODEL_FAILED",
            error=str(exc),
        )
    except Exception as exc:
        return WebIntentDecision(
            decision="NO_WEB",
            source="MODEL_FAILED",
            error=str(exc),
        )

    if not isinstance(
        raw,
        str,
    ):
        return WebIntentDecision(
            decision="NO_WEB",
            source="MODEL_INVALID",
            error=(
                "Web intent classifier "
                "returned non-text output"
            ),
        )

    decision = raw.strip().upper()

    if decision not in {
        "WEB",
        "NO_WEB",
    }:
        return WebIntentDecision(
            decision="NO_WEB",
            source="MODEL_INVALID",
            error=(
                "Web intent classifier returned "
                f"invalid output: {raw!r}"
            ),
        )

    return WebIntentDecision(
        decision=decision,
        source="MODEL",
    )
