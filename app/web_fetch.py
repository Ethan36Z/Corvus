import http.client
import ipaddress
import socket
import ssl
from urllib.parse import urljoin, urlsplit

from app.web_security import (
    CONNECT_TIMEOUT_SECONDS,
    MAX_REDIRECTS,
    MAX_RESPONSE_BYTES,
    READ_TIMEOUT_SECONDS,
    WebSecurityError,
    validate_public_url,
    validate_redirect_target,
    validate_resolved_addresses,
)


_FETCH_CHUNK_BYTES = 64 * 1024

_REDIRECT_STATUSES = {
    301,
    302,
    303,
    307,
    308,
}

_ALLOWED_APPLICATION_TYPES = {
    "application/json",
    "application/xhtml+xml",
    "application/xml",
    "application/rss+xml",
    "application/atom+xml",
}

_USER_AGENT = (
    "Corvus-Web/1.0 "
    "(read-only public information fetcher)"
)


class WebFetchError(RuntimeError):
    def __init__(
        self,
        code,
        message,
    ):
        super().__init__(message)
        self.code = str(code)


def _raise_fetch(
    code,
    message,
):
    raise WebFetchError(
        code,
        message,
    )


def _open_pinned_socket(
    connect_ip,
    port,
    timeout,
):
    """
    Open a TCP socket directly to an already-validated
    numeric IP address.

    No hostname is passed to the socket layer, so this
    function cannot perform a second DNS resolution.
    """
    address = ipaddress.ip_address(
        str(connect_ip)
    )

    family = (
        socket.AF_INET6
        if address.version == 6
        else socket.AF_INET
    )

    sock = socket.socket(
        family,
        socket.SOCK_STREAM,
    )

    try:
        sock.settimeout(timeout)

        if address.version == 6:
            destination = (
                str(address),
                int(port),
                0,
                0,
            )
        else:
            destination = (
                str(address),
                int(port),
            )

        sock.connect(destination)
        return sock

    except Exception:
        sock.close()
        raise


class _PinnedHTTPConnection(
    http.client.HTTPConnection
):
    def __init__(
        self,
        connect_ip,
        *,
        port,
        timeout,
    ):
        super().__init__(
            host=str(connect_ip),
            port=int(port),
            timeout=timeout,
        )

        self._connect_ip = str(
            connect_ip
        )

    def connect(self):
        self.sock = _open_pinned_socket(
            self._connect_ip,
            self.port,
            self.timeout,
        )


class _PinnedHTTPSConnection(
    http.client.HTTPSConnection
):
    def __init__(
        self,
        connect_ip,
        *,
        tls_hostname,
        port,
        timeout,
        context=None,
    ):
        if context is None:
            context = (
                ssl.create_default_context()
            )

        super().__init__(
            host=str(connect_ip),
            port=int(port),
            timeout=timeout,
            context=context,
        )

        self._connect_ip = str(
            connect_ip
        )
        self._tls_hostname = str(
            tls_hostname
        )

    def connect(self):
        raw_socket = _open_pinned_socket(
            self._connect_ip,
            self.port,
            self.timeout,
        )

        try:
            self.sock = (
                self._context.wrap_socket(
                    raw_socket,
                    server_hostname=(
                        self._tls_hostname
                    ),
                )
            )
        except Exception:
            raw_socket.close()
            raise


def _default_connection_factory(
    *,
    scheme,
    connect_ip,
    hostname,
    port,
    timeout,
):
    if scheme == "https":
        return _PinnedHTTPSConnection(
            connect_ip,
            tls_hostname=hostname,
            port=port,
            timeout=timeout,
        )

    if scheme == "http":
        return _PinnedHTTPConnection(
            connect_ip,
            port=port,
            timeout=timeout,
        )

    _raise_fetch(
        "WEB_SCHEME_INVALID",
        (
            "connection factory received "
            f"unsupported scheme: {scheme}"
        ),
    )


def resolve_public_addresses(
    hostname,
    port,
    *,
    resolver=socket.getaddrinfo,
):
    """
    Resolve a hostname exactly once for a fetch attempt
    and validate every returned address.

    The returned values are numeric IP strings only.
    """
    try:
        records = resolver(
            hostname,
            int(port),
            family=socket.AF_UNSPEC,
            type=socket.SOCK_STREAM,
            proto=socket.IPPROTO_TCP,
        )
    except socket.gaierror as exc:
        raise WebFetchError(
            "WEB_DNS_FAILED",
            (
                "DNS resolution failed "
                f"for {hostname}: {exc}"
            ),
        ) from exc

    addresses = []

    for record in records:
        try:
            sockaddr = record[4]
            address = sockaddr[0]
        except (
            IndexError,
            TypeError,
        ) as exc:
            raise WebFetchError(
                "WEB_DNS_INVALID",
                (
                    "DNS resolver returned "
                    "an invalid record"
                ),
            ) from exc

        if address not in addresses:
            addresses.append(
                address
            )

    return validate_resolved_addresses(
        hostname,
        addresses,
    )


def _format_host_header(
    hostname,
    scheme,
    port,
):
    try:
        address = ipaddress.ip_address(
            hostname
        )
    except ValueError:
        authority_host = hostname
    else:
        authority_host = (
            f"[{address}]"
            if address.version == 6
            else str(address)
        )

    default_port = (
        443
        if scheme == "https"
        else 80
    )

    if int(port) == default_port:
        return authority_host

    return (
        f"{authority_host}:{int(port)}"
    )


def _request_target(
    url,
):
    parsed = urlsplit(url)

    target = parsed.path or "/"

    if parsed.query:
        target = (
            f"{target}?{parsed.query}"
        )

    return target


def _response_media_type(
    content_type,
):
    if content_type is None:
        _raise_fetch(
            "WEB_CONTENT_TYPE_BLOCKED",
            (
                "response has no "
                "Content-Type header"
            ),
        )

    media_type = (
        content_type
        .split(";", 1)[0]
        .strip()
        .lower()
    )

    allowed = (
        media_type.startswith("text/")
        or media_type
        in _ALLOWED_APPLICATION_TYPES
    )

    if not allowed:
        _raise_fetch(
            "WEB_CONTENT_TYPE_BLOCKED",
            (
                "response content type "
                f"is not textual: {media_type}"
            ),
        )

    return media_type


def _response_charset(
    content_type,
):
    if not content_type:
        return "utf-8"

    parts = content_type.split(";")

    for part in parts[1:]:
        key, separator, value = (
            part.strip().partition("=")
        )

        if (
            separator
            and key.strip().lower()
            == "charset"
        ):
            charset = (
                value
                .strip()
                .strip("\"'")
            )

            if charset:
                return charset

    return "utf-8"


def _validate_content_encoding(
    response,
):
    encoding = response.getheader(
        "Content-Encoding"
    )

    if encoding is None:
        return

    normalized = encoding.strip().lower()

    if normalized in {
        "",
        "identity",
    }:
        return

    _raise_fetch(
        "WEB_CONTENT_ENCODING_BLOCKED",
        (
            "compressed or transformed "
            "responses are not accepted "
            "by the Web v1 fetch foundation"
        ),
    )


def _read_bounded_body(
    response,
):
    content_length = response.getheader(
        "Content-Length"
    )

    if content_length is not None:
        try:
            declared_size = int(
                content_length
            )
        except ValueError:
            declared_size = None

        if (
            declared_size is not None
            and declared_size
            > MAX_RESPONSE_BYTES
        ):
            _raise_fetch(
                "WEB_RESPONSE_TOO_LARGE",
                (
                    "declared response size "
                    "exceeds the Web v1 limit"
                ),
            )

    chunks = []
    total = 0

    while True:
        remaining = (
            MAX_RESPONSE_BYTES
            - total
        )

        read_size = min(
            _FETCH_CHUNK_BYTES,
            remaining + 1,
        )

        chunk = response.read(
            read_size
        )

        if not chunk:
            break

        total += len(chunk)

        if total > MAX_RESPONSE_BYTES:
            _raise_fetch(
                "WEB_RESPONSE_TOO_LARGE",
                (
                    "streamed response size "
                    "exceeds the Web v1 limit"
                ),
            )

        chunks.append(chunk)

    return b"".join(chunks)


def _decode_text(
    body,
    content_type,
):
    charset = _response_charset(
        content_type
    )

    try:
        return body.decode(
            charset,
            errors="replace",
        )
    except LookupError:
        return body.decode(
            "utf-8",
            errors="replace",
        )


def _fixed_request_headers(
    *,
    hostname,
    scheme,
    port,
):
    return {
        "Host": _format_host_header(
            hostname,
            scheme,
            port,
        ),
        "User-Agent": _USER_AGENT,
        "Accept": (
            "text/html,"
            "text/plain;q=0.9,"
            "application/xhtml+xml;q=0.8,"
            "application/json;q=0.6,"
            "application/xml;q=0.5"
        ),
        "Accept-Encoding": "identity",
        "Connection": "close",
    }


def fetch_public_page(
    url,
    *,
    resolver=socket.getaddrinfo,
    connection_factory=None,
):
    """
    Fetch one bounded public textual HTTP(S) resource.

    Security properties:

    - URL policy is validated before every request.
    - DNS answers are validated before connection.
    - the socket connects to a validated numeric IP.
    - HTTPS preserves original hostname for SNI and
      certificate verification.
    - Host header preserves the original hostname.
    - redirects are manually followed and revalidated.
    - response bytes and content types are bounded.
    - no cookies, authorization headers, credentials,
      proxy environment, POST body, or arbitrary headers
      are accepted from callers.
    """
    if connection_factory is None:
        connection_factory = (
            _default_connection_factory
        )

    current_url = str(url)
    redirect_chain = []

    while True:
        validated = validate_public_url(
            current_url
        )

        hostname = validated[
            "hostname"
        ]
        scheme = validated[
            "scheme"
        ]
        port = validated[
            "port"
        ]

        addresses = (
            resolve_public_addresses(
                hostname,
                port,
                resolver=resolver,
            )
        )

        connect_ip = addresses[0]

        connection = None

        try:
            connection = (
                connection_factory(
                    scheme=scheme,
                    connect_ip=connect_ip,
                    hostname=hostname,
                    port=port,
                    timeout=(
                        CONNECT_TIMEOUT_SECONDS
                    ),
                )
            )

            headers = (
                _fixed_request_headers(
                    hostname=hostname,
                    scheme=scheme,
                    port=port,
                )
            )

            connection.request(
                "GET",
                _request_target(
                    validated["url"]
                ),
                headers=headers,
            )

            sock = getattr(
                connection,
                "sock",
                None,
            )

            if sock is not None:
                sock.settimeout(
                    READ_TIMEOUT_SECONDS
                )

            response = (
                connection.getresponse()
            )

            status = int(
                response.status
            )

            if status in _REDIRECT_STATUSES:
                location = response.getheader(
                    "Location"
                )

                if not location:
                    _raise_fetch(
                        "WEB_REDIRECT_INVALID",
                        (
                            "redirect response "
                            "has no Location header"
                        ),
                    )

                if (
                    len(redirect_chain)
                    >= MAX_REDIRECTS
                ):
                    _raise_fetch(
                        "WEB_REDIRECT_LIMIT",
                        (
                            "redirect limit "
                            "exceeded"
                        ),
                    )

                next_url = urljoin(
                    validated["url"],
                    location,
                )

                next_validated = (
                    validate_redirect_target(
                        next_url
                    )
                )

                redirect_chain.append(
                    {
                        "status": status,
                        "from_url": (
                            validated["url"]
                        ),
                        "to_url": (
                            next_validated[
                                "url"
                            ]
                        ),
                    }
                )

                current_url = (
                    next_validated["url"]
                )

                continue

            if not (
                200
                <= status
                < 300
            ):
                _raise_fetch(
                    "WEB_HTTP_STATUS",
                    (
                        "public fetch returned "
                        f"HTTP {status}"
                    ),
                )

            content_type_header = (
                response.getheader(
                    "Content-Type"
                )
            )

            media_type = (
                _response_media_type(
                    content_type_header
                )
            )

            _validate_content_encoding(
                response
            )

            body = _read_bounded_body(
                response
            )

            text = _decode_text(
                body,
                content_type_header,
            )

            return {
                "url": validated["url"],
                "status": status,
                "media_type": media_type,
                "text": text,
                "bytes_read": len(body),
                "resolved_ip": connect_ip,
                "redirects": tuple(
                    redirect_chain
                ),
            }

        except (
            WebSecurityError,
            WebFetchError,
        ):
            raise

        except (
            socket.timeout,
            TimeoutError,
        ) as exc:
            raise WebFetchError(
                "WEB_FETCH_TIMEOUT",
                (
                    "public Web request "
                    "timed out"
                ),
            ) from exc

        except (
            ssl.SSLError,
            http.client.HTTPException,
            OSError,
        ) as exc:
            raise WebFetchError(
                "WEB_FETCH_FAILED",
                (
                    "public Web request "
                    f"failed: {exc}"
                ),
            ) from exc

        finally:
            if connection is not None:
                connection.close()
