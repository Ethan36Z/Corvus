from app.web_security import (
    CONNECT_TIMEOUT_SECONDS,
    MAX_FETCHES_PER_TURN,
    MAX_REDIRECTS,
    MAX_RESPONSE_BYTES,
    READ_TIMEOUT_SECONDS,
    WebSecurityError,
    validate_public_url,
    validate_resolved_addresses,
)


def expect_error(
    code,
    fn,
):
    try:
        fn()
    except WebSecurityError as exc:
        assert exc.code == code, (
            exc.code,
            code,
        )
    else:
        raise AssertionError(
            f"expected {code}"
        )


public_https = validate_public_url(
    "https://example.com/news?q=corvus#section"
)

assert public_https["scheme"] == "https"
assert public_https["hostname"] == (
    "example.com"
)
assert public_https["port"] == 443

assert (
    public_https["url"]
    == "https://example.com/news?q=corvus"
)

public_http = validate_public_url(
    "http://example.com/"
)

assert public_http["port"] == 80

public_ip = validate_public_url(
    "https://1.1.1.1/"
)

assert public_ip["hostname"] == (
    "1.1.1.1"
)

expect_error(
    "WEB_SCHEME_BLOCKED",
    lambda: validate_public_url(
        "file:///etc/passwd"
    ),
)

expect_error(
    "WEB_SCHEME_BLOCKED",
    lambda: validate_public_url(
        "ftp://example.com/file"
    ),
)

expect_error(
    "WEB_HOST_BLOCKED",
    lambda: validate_public_url(
        "http://localhost/"
    ),
)

expect_error(
    "WEB_HOST_BLOCKED",
    lambda: validate_public_url(
        "http://printer.local/"
    ),
)

for blocked_url in (
    "http://127.0.0.1/",
    "http://10.0.0.1/",
    "http://172.16.0.1/",
    "http://192.168.1.1/",
    "http://169.254.169.254/",
    "http://100.64.0.1/",
    "http://[::1]/",
    "http://[fe80::1]/",
):
    expect_error(
        "WEB_ADDRESS_BLOCKED",
        lambda url=blocked_url:
            validate_public_url(url),
    )

expect_error(
    "WEB_CREDENTIALS_BLOCKED",
    lambda: validate_public_url(
        "https://user:password@example.com/"
    ),
)

expect_error(
    "WEB_PORT_BLOCKED",
    lambda: validate_public_url(
        "https://example.com:8443/"
    ),
)

resolved = validate_resolved_addresses(
    "example.com",
    (
        "1.1.1.1",
        "2606:4700:4700::1111",
    ),
)

assert len(resolved) == 2

expect_error(
    "WEB_ADDRESS_BLOCKED",
    lambda: validate_resolved_addresses(
        "example.com",
        (
            "1.1.1.1",
            "127.0.0.1",
        ),
    ),
)

assert MAX_REDIRECTS == 3
assert MAX_RESPONSE_BYTES == (
    2 * 1024 * 1024
)
assert MAX_FETCHES_PER_TURN == 4
assert CONNECT_TIMEOUT_SECONDS == 3
assert READ_TIMEOUT_SECONDS == 8

print(
    "WEB URL POLICY CONTRACT OK"
)
print(
    "WEB PRIVATE NETWORK BLOCK CONTRACT OK"
)
print(
    "WEB DNS ADDRESS POLICY CONTRACT OK"
)
print(
    "WEB RESOURCE LIMIT POLICY CONTRACT OK"
)
