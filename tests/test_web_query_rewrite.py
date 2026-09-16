from app.web_query_rewrite import (
    WEB_QUERY_REWRITE_SYSTEM_PROMPT,
    WebQueryRewriteError,
    rewrite_web_query,
)


calls = []


def fake_generate(
    messages,
):
    calls.append(
        messages
    )

    return (
        "  Python 3.14 documentation "
        "compression.zstd module  "
    )


rewritten = rewrite_web_query(
    (
        "According to Python 3.14 docs, "
        "what is compression.zstd?"
    ),
    generate_fn=fake_generate,
)

assert rewritten == (
    "Python 3.14 documentation "
    "compression.zstd module"
)

assert len(calls) == 1

messages = calls[0]

assert messages[0]["role"] == "system"
assert messages[1]["role"] == "user"

assert (
    "Do not answer the question."
    in WEB_QUERY_REWRITE_SYSTEM_PROMPT
)

assert (
    "compression.zstd"
    in messages[1]["content"]
)

print(
    "WEB QUERY REWRITE PROMPT CONTRACT OK"
)

print(
    "WEB QUERY REWRITE NORMALIZATION CONTRACT OK"
)


def expect_error(
    code,
    fn,
):
    try:
        fn()
    except WebQueryRewriteError as exc:
        assert exc.code == code, (
            exc.code,
            code,
        )
    else:
        raise AssertionError(
            f"expected {code}"
        )


expect_error(
    "WEB_QUERY_REWRITE_INPUT_INVALID",
    lambda: rewrite_web_query(
        "   ",
        generate_fn=fake_generate,
    ),
)


expect_error(
    "WEB_QUERY_REWRITE_MODEL_FAILED",
    lambda: rewrite_web_query(
        "Python docs",
        generate_fn=lambda messages: (
            (_ for _ in ()).throw(
                RuntimeError(
                    "synthetic model failure"
                )
            )
        ),
    ),
)


expect_error(
    "WEB_QUERY_REWRITE_OUTPUT_INVALID",
    lambda: rewrite_web_query(
        "Python docs",
        generate_fn=lambda messages: "   ",
    ),
)


print(
    "WEB QUERY REWRITE FAILURE CONTRACT OK"
)

print(
    "WEB_QUERY_REWRITE_ADAPTER=PASS"
)
