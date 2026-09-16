import socket

import app.web_fetch as web_fetch
from app.web_fetch import (
    WebFetchError,
    fetch_public_page,
    resolve_public_addresses,
)
from app.web_security import (
    MAX_REDIRECTS,
    MAX_RESPONSE_BYTES,
    WebSecurityError,
)


class FakeResponse:
    def __init__(
        self,
        *,
        status=200,
        headers=None,
        body=b"",
    ):
        self.status = status
        self._headers = {
            str(key).lower(): str(value)
            for key, value
            in (headers or {}).items()
        }
        self._body = bytes(body)
        self._offset = 0

    def getheader(
        self,
        name,
    ):
        return self._headers.get(
            str(name).lower()
        )

    def read(
        self,
        amount=-1,
    ):
        if amount is None or amount < 0:
            amount = (
                len(self._body)
                - self._offset
            )

        start = self._offset
        end = min(
            len(self._body),
            start + amount,
        )

        self._offset = end

        return self._body[
            start:end
        ]


class FakeConnection:
    def __init__(
        self,
        response,
    ):
        self.response = response
        self.requests = []
        self.closed = False
        self.sock = None

    def request(
        self,
        method,
        target,
        body=None,
        headers=None,
    ):
        self.requests.append(
            {
                "method": method,
                "target": target,
                "body": body,
                "headers": dict(
                    headers or {}
                ),
            }
        )

    def getresponse(self):
        return self.response

    def close(self):
        self.closed = True


def fake_dns_record(
    address,
    port,
):
    family = (
        socket.AF_INET6
        if ":" in address
        else socket.AF_INET
    )

    sockaddr = (
        (
            address,
            port,
            0,
            0,
        )
        if family == socket.AF_INET6
        else (
            address,
            port,
        )
    )

    return (
        family,
        socket.SOCK_STREAM,
        socket.IPPROTO_TCP,
        "",
        sockaddr,
    )


def expect_fetch_error(
    code,
    fn,
):
    try:
        fn()
    except WebFetchError as exc:
        assert exc.code == code, (
            exc.code,
            code,
        )
    else:
        raise AssertionError(
            f"expected {code}"
        )


def expect_security_error(
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


def resolver_for(
    mapping,
):
    calls = []

    def resolver(
        hostname,
        port,
        *,
        family,
        type,
        proto,
    ):
        calls.append(
            {
                "hostname": hostname,
                "port": port,
                "family": family,
                "type": type,
                "proto": proto,
            }
        )

        addresses = mapping[
            hostname
        ]

        return [
            fake_dns_record(
                address,
                port,
            )
            for address in addresses
        ]

    resolver.calls = calls
    return resolver


def connection_factory_for(
    responses,
):
    queue = list(responses)
    calls = []
    connections = []

    def factory(
        **kwargs,
    ):
        calls.append(
            dict(kwargs)
        )

        if not queue:
            raise AssertionError(
                "unexpected connection"
            )

        connection = FakeConnection(
            queue.pop(0)
        )

        connections.append(
            connection
        )

        return connection

    factory.calls = calls
    factory.connections = connections
    return factory


# ==================================================
# Basic pinned fetch contract
# ==================================================

resolver = resolver_for(
    {
        "example.com": (
            "1.1.1.1",
        ),
    }
)

factory = connection_factory_for(
    [
        FakeResponse(
            status=200,
            headers={
                "Content-Type": (
                    "text/html; "
                    "charset=utf-8"
                ),
                "Content-Length": "5",
            },
            body=b"hello",
        ),
    ]
)

result = fetch_public_page(
    (
        "https://example.com/"
        "news?q=corvus#ignored"
    ),
    resolver=resolver,
    connection_factory=factory,
)

assert result["status"] == 200
assert result["text"] == "hello"
assert result["bytes_read"] == 5
assert result["resolved_ip"] == (
    "1.1.1.1"
)
assert result["url"] == (
    "https://example.com/news?q=corvus"
)

assert len(resolver.calls) == 1
assert (
    resolver.calls[0]["hostname"]
    == "example.com"
)

assert len(factory.calls) == 1

assert (
    factory.calls[0]["connect_ip"]
    == "1.1.1.1"
)

assert (
    factory.calls[0]["hostname"]
    == "example.com"
)

assert (
    factory.calls[0]["scheme"]
    == "https"
)

request = (
    factory.connections[0]
    .requests[0]
)

assert request["method"] == "GET"
assert request["target"] == (
    "/news?q=corvus"
)

assert (
    request["headers"]["Host"]
    == "example.com"
)

assert (
    request["headers"][
        "Accept-Encoding"
    ]
    == "identity"
)

assert (
    "Authorization"
    not in request["headers"]
)

assert (
    "Cookie"
    not in request["headers"]
)

assert (
    factory.connections[0].closed
    is True
)


# ==================================================
# DNS validation happens before connection
# ==================================================

mixed_resolver = resolver_for(
    {
        "example.com": (
            "1.1.1.1",
            "127.0.0.1",
        ),
    }
)

never_factory = (
    connection_factory_for([])
)

expect_security_error(
    "WEB_ADDRESS_BLOCKED",
    lambda: fetch_public_page(
        "https://example.com/",
        resolver=mixed_resolver,
        connection_factory=(
            never_factory
        ),
    ),
)

assert not never_factory.calls


# ==================================================
# Redirect revalidation
# ==================================================

redirect_resolver = resolver_for(
    {
        "example.com": (
            "1.1.1.1",
        ),
        "example.org": (
            "8.8.8.8",
        ),
    }
)

redirect_factory = (
    connection_factory_for(
        [
            FakeResponse(
                status=302,
                headers={
                    "Location": (
                        "https://"
                        "example.org/final"
                    ),
                },
            ),
            FakeResponse(
                status=200,
                headers={
                    "Content-Type": (
                        "text/plain"
                    ),
                },
                body=b"final",
            ),
        ]
    )
)

redirect_result = (
    fetch_public_page(
        "https://example.com/start",
        resolver=redirect_resolver,
        connection_factory=(
            redirect_factory
        ),
    )
)

assert redirect_result["text"] == (
    "final"
)

assert len(
    redirect_result["redirects"]
) == 1

assert [
    call["connect_ip"]
    for call in redirect_factory.calls
] == [
    "1.1.1.1",
    "8.8.8.8",
]


# ==================================================
# Redirect into localhost is blocked
# before another connection is created.
# ==================================================

blocked_redirect_resolver = (
    resolver_for(
        {
            "example.com": (
                "1.1.1.1",
            ),
        }
    )
)

blocked_redirect_factory = (
    connection_factory_for(
        [
            FakeResponse(
                status=302,
                headers={
                    "Location": (
                        "http://127.0.0.1/"
                        "admin"
                    ),
                },
            ),
        ]
    )
)

expect_security_error(
    "WEB_ADDRESS_BLOCKED",
    lambda: fetch_public_page(
        "https://example.com/",
        resolver=(
            blocked_redirect_resolver
        ),
        connection_factory=(
            blocked_redirect_factory
        ),
    ),
)

assert len(
    blocked_redirect_factory.calls
) == 1


# ==================================================
# Redirect limit
# ==================================================

limit_resolver = resolver_for(
    {
        "example.com": (
            "1.1.1.1",
        ),
    }
)

limit_responses = [
    FakeResponse(
        status=302,
        headers={
            "Location": (
                f"/hop-{index + 1}"
            ),
        },
    )
    for index in range(
        MAX_REDIRECTS + 1
    )
]

limit_factory = (
    connection_factory_for(
        limit_responses
    )
)

expect_fetch_error(
    "WEB_REDIRECT_LIMIT",
    lambda: fetch_public_page(
        "https://example.com/start",
        resolver=limit_resolver,
        connection_factory=(
            limit_factory
        ),
    ),
)


# ==================================================
# Content-type / encoding boundaries
# ==================================================

binary_factory = (
    connection_factory_for(
        [
            FakeResponse(
                status=200,
                headers={
                    "Content-Type": (
                        "image/png"
                    ),
                },
                body=b"\x89PNG",
            ),
        ]
    )
)

expect_fetch_error(
    "WEB_CONTENT_TYPE_BLOCKED",
    lambda: fetch_public_page(
        "https://example.com/image",
        resolver=resolver_for(
            {
                "example.com": (
                    "1.1.1.1",
                ),
            }
        ),
        connection_factory=(
            binary_factory
        ),
    ),
)

gzip_factory = (
    connection_factory_for(
        [
            FakeResponse(
                status=200,
                headers={
                    "Content-Type": (
                        "text/html"
                    ),
                    "Content-Encoding": (
                        "gzip"
                    ),
                },
                body=b"compressed",
            ),
        ]
    )
)

expect_fetch_error(
    "WEB_CONTENT_ENCODING_BLOCKED",
    lambda: fetch_public_page(
        "https://example.com/",
        resolver=resolver_for(
            {
                "example.com": (
                    "1.1.1.1",
                ),
            }
        ),
        connection_factory=(
            gzip_factory
        ),
    ),
)


# ==================================================
# Size boundaries
# ==================================================

declared_large_factory = (
    connection_factory_for(
        [
            FakeResponse(
                status=200,
                headers={
                    "Content-Type": (
                        "text/plain"
                    ),
                    "Content-Length": str(
                        MAX_RESPONSE_BYTES
                        + 1
                    ),
                },
                body=b"",
            ),
        ]
    )
)

expect_fetch_error(
    "WEB_RESPONSE_TOO_LARGE",
    lambda: fetch_public_page(
        "https://example.com/",
        resolver=resolver_for(
            {
                "example.com": (
                    "1.1.1.1",
                ),
            }
        ),
        connection_factory=(
            declared_large_factory
        ),
    ),
)

stream_large_factory = (
    connection_factory_for(
        [
            FakeResponse(
                status=200,
                headers={
                    "Content-Type": (
                        "text/plain"
                    ),
                },
                body=(
                    b"A"
                    * (
                        MAX_RESPONSE_BYTES
                        + 1
                    )
                ),
            ),
        ]
    )
)

expect_fetch_error(
    "WEB_RESPONSE_TOO_LARGE",
    lambda: fetch_public_page(
        "https://example.com/",
        resolver=resolver_for(
            {
                "example.com": (
                    "1.1.1.1",
                ),
            }
        ),
        connection_factory=(
            stream_large_factory
        ),
    ),
)


# ==================================================
# Non-success status is not silently accepted
# ==================================================

status_factory = (
    connection_factory_for(
        [
            FakeResponse(
                status=500,
                headers={
                    "Content-Type": (
                        "text/plain"
                    ),
                },
                body=b"error",
            ),
        ]
    )
)

expect_fetch_error(
    "WEB_HTTP_STATUS",
    lambda: fetch_public_page(
        "https://example.com/",
        resolver=resolver_for(
            {
                "example.com": (
                    "1.1.1.1",
                ),
            }
        ),
        connection_factory=(
            status_factory
        ),
    ),
)


# ==================================================
# Default connection factory preserves:
#
# numeric IP for transport
# original hostname for TLS verification / SNI.
# ==================================================

https_connection = (
    web_fetch
    ._default_connection_factory(
        scheme="https",
        connect_ip="1.1.1.1",
        hostname="example.com",
        port=443,
        timeout=3,
    )
)

assert (
    https_connection._connect_ip
    == "1.1.1.1"
)

assert (
    https_connection._tls_hostname
    == "example.com"
)

https_connection.close()


# ==================================================
# The pinned socket itself receives only
# the numeric address, never the hostname.
# ==================================================

original_socket = (
    web_fetch.socket.socket
)


class DummySocket:
    def __init__(
        self,
        family,
        sock_type,
    ):
        self.family = family
        self.sock_type = sock_type
        self.timeout = None
        self.destination = None
        self.closed = False

    def settimeout(
        self,
        timeout,
    ):
        self.timeout = timeout

    def connect(
        self,
        destination,
    ):
        self.destination = (
            destination
        )

    def close(self):
        self.closed = True


dummy_sockets = []


def fake_socket(
    family,
    sock_type,
):
    instance = DummySocket(
        family,
        sock_type,
    )

    dummy_sockets.append(
        instance
    )

    return instance


web_fetch.socket.socket = fake_socket

try:
    pinned = (
        web_fetch
        ._open_pinned_socket(
            "1.1.1.1",
            443,
            3,
        )
    )

    assert pinned.destination == (
        "1.1.1.1",
        443,
    )

    assert pinned.timeout == 3

finally:
    web_fetch.socket.socket = (
        original_socket
    )


# ==================================================
# Resolver contract itself rejects private answers.
# ==================================================

private_dns = resolver_for(
    {
        "example.com": (
            "192.168.1.5",
        ),
    }
)

expect_security_error(
    "WEB_ADDRESS_BLOCKED",
    lambda: resolve_public_addresses(
        "example.com",
        443,
        resolver=private_dns,
    ),
)



# ==================================================
# Large-but-bounded textual pages are accepted.
#
# Web v1 originally used a 2 MiB ceiling. That was
# too small for legitimate documentation pages such
# as the Python standard-library documentation.
#
# The fetch remains strictly bounded by the current
# MAX_RESPONSE_BYTES policy.
# ==================================================

previous_web_v1_limit = (
    2 * 1024 * 1024
)

large_but_allowed_size = (
    previous_web_v1_limit
    + 64 * 1024
)

assert (
    large_but_allowed_size
    < MAX_RESPONSE_BYTES
)

large_allowed_factory = (
    connection_factory_for(
        [
            FakeResponse(
                status=200,
                headers={
                    "Content-Type": (
                        "text/html; charset=utf-8"
                    ),
                    "Content-Length": str(
                        large_but_allowed_size
                    ),
                },
                body=(
                    b"A"
                    * large_but_allowed_size
                ),
            ),
        ]
    )
)

large_allowed_result = (
    fetch_public_page(
        "https://example.com/large-doc",
        resolver=resolver_for(
            {
                "example.com": (
                    "1.1.1.1",
                ),
            }
        ),
        connection_factory=(
            large_allowed_factory
        ),
    )
)

assert (
    large_allowed_result["bytes_read"]
    == large_but_allowed_size
)

assert (
    len(
        large_allowed_result["text"]
    )
    == large_but_allowed_size
)

print(
    "WEB LARGE-BUT-BOUNDED PAGE CONTRACT OK"
)


print(
    "WEB PINNED-IP FETCH CONTRACT OK"
)
print(
    "WEB DNS REBINDING BOUNDARY CONTRACT OK"
)
print(
    "WEB REDIRECT REVALIDATION CONTRACT OK"
)
print(
    "WEB CONTENT BOUNDARY CONTRACT OK"
)
print(
    "WEB RESPONSE SIZE CONTRACT OK"
)
print(
    "WEB READ-ONLY REQUEST CONTRACT OK"
)
