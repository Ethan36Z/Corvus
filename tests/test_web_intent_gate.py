from app.web_intent_gate import (
    decide_web_intent,
    detect_deterministic_web_intent,
)


def must_not_generate(
    messages,
):
    raise AssertionError(
        "model classifier must not run "
        "for deterministic input"
    )


deterministic_cases = [
    (
        "帮我查一下 Ontario, California "
        "接下来 7 天的天气。",
        "WEB",
    ),
    (
        "Search the web for the latest Node.js LTS.",
        "WEB",
    ),
    (
        "According to the current Python 3.14 "
        "documentation, what is compression.zstd?",
        "WEB",
    ),
    (
        "I saw people saying Node.js 30 is out. "
        "Has that actually happened?",
        "WEB",
    ),
    (
        "Will it rain in Ontario, California "
        "this weekend?",
        "WEB",
    ),
    (
        "Don't search the web; explain JWT.",
        "NO_WEB",
    ),
    (
        "不要查网页。解释一下 JWT。",
        "NO_WEB",
    ),
    (
        "What did I tell you yesterday "
        "about my car?",
        "NO_WEB",
    ),
    (
        "昨天我跟你说我的车哪里坏了？",
        "NO_WEB",
    ),
]


for query, expected in deterministic_cases:
    result = decide_web_intent(
        query,
        generate_fn=must_not_generate,
    )

    assert result.decision == expected
    assert result.source == "DETERMINISTIC"
    assert result.signal

print(
    "WEB INTENT DETERMINISTIC CONTRACT OK"
)


ambiguous = (
    "Explain what JWT is."
)

assert (
    detect_deterministic_web_intent(
        ambiguous
    )
    is None
)


model_calls = []


def classify_no_web(
    messages,
):
    model_calls.append(
        messages
    )

    return "NO_WEB"


result = decide_web_intent(
    ambiguous,
    generate_fn=classify_no_web,
)

assert result.decision == "NO_WEB"
assert result.source == "MODEL"
assert len(model_calls) == 1

print(
    "WEB INTENT ONE-SHOT MODEL FALLBACK CONTRACT OK"
)


def invalid_classifier(
    messages,
):
    return "Here is the translation."


result = decide_web_intent(
    "Translate this sentence into Chinese.",
    generate_fn=invalid_classifier,
)

assert result.decision == "NO_WEB"
assert result.source == "MODEL_INVALID"
assert result.error

print(
    "WEB INTENT INVALID MODEL OUTPUT FAIL-CLOSED CONTRACT OK"
)


def failing_classifier(
    messages,
):
    raise RuntimeError(
        "synthetic classifier failure"
    )


result = decide_web_intent(
    "Explain a difficult ambiguous question.",
    generate_fn=failing_classifier,
)

assert result.decision == "NO_WEB"
assert result.source == "MODEL_FAILED"
assert (
    "synthetic classifier failure"
    in result.error
)

print(
    "WEB INTENT MODEL FAILURE FAIL-CLOSED CONTRACT OK"
)


precedence = decide_web_intent(
    (
        "Don't search the web. "
        "Tell me today's latest news as a fictional story."
    ),
    generate_fn=must_not_generate,
)

assert precedence.decision == "NO_WEB"

print(
    "WEB INTENT EXPLICIT-NO-WEB PRECEDENCE CONTRACT OK"
)

print(
    "A3_4_WEB_INTENT_GATE=PASS"
)
