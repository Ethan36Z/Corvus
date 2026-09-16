import ipaddress
import re
from urllib.parse import urlsplit, urlunsplit


ALLOWED_WEB_SCHEMES = {
    "http",
    "https",
}

DEFAULT_WEB_PORTS = {
    "http": 80,
    "https": 443,
}

MAX_URL_LENGTH = 2048

MAX_REDIRECTS = 3
MAX_RESPONSE_BYTES = 8 * 1024 * 1024
MAX_EXTRACTED_TEXT_CHARS = 60_000
MAX_FETCHES_PER_TURN = 4

CONNECT_TIMEOUT_SECONDS = 3
READ_TIMEOUT_SECONDS = 8


_HOST_LABEL_RE = re.compile(
    r"^[a-z0-9]"
    r"(?:[a-z0-9-]{0,61}[a-z0-9])?$"
)

_BLOCKED_HOST_SUFFIXES = (
    ".localhost",
    ".local",
    ".home.arpa",
)


class WebSecurityError(ValueError):
    def __init__(
        self,
        code,
        message,
    ):
        super().__init__(message)
        self.code = str(code)


def _raise(
    code,
    message,
):
    raise WebSecurityError(
        code,
        message,
    )


def _is_public_ip(address):
    mapped = getattr(
        address,
        "ipv4_mapped",
        None,
    )

    if mapped is not None:
        address = mapped

    return (
        address.is_global
        and not address.is_loopback
        and not address.is_private
        and not address.is_link_local
        and not address.is_multicast
        and not address.is_reserved
        and not address.is_unspecified
    )


def validate_public_ip(
    value,
):
    try:
        address = ipaddress.ip_address(
            str(value)
        )
    except ValueError as exc:
        raise WebSecurityError(
            "WEB_ADDRESS_INVALID",
            f"invalid IP address: {value}",
        ) from exc

    if not _is_public_ip(address):
        _raise(
            "WEB_ADDRESS_BLOCKED",
            (
                "non-public network address "
                f"is blocked: {address}"
            ),
        )

    return str(address)


def normalize_public_hostname(
    hostname,
):
    hostname = str(
        hostname
    ).strip().lower().rstrip(".")

    if not hostname:
        _raise(
            "WEB_HOST_INVALID",
            "hostname must not be empty",
        )

    if hostname == "localhost":
        _raise(
            "WEB_HOST_BLOCKED",
            "localhost is blocked",
        )

    if hostname.endswith(
        _BLOCKED_HOST_SUFFIXES
    ):
        _raise(
            "WEB_HOST_BLOCKED",
            (
                "local-only hostname "
                f"is blocked: {hostname}"
            ),
        )

    try:
        direct_ip = ipaddress.ip_address(
            hostname
        )
    except ValueError:
        direct_ip = None

    if direct_ip is not None:
        validate_public_ip(
            direct_ip
        )
        return str(direct_ip)

    try:
        ascii_hostname = (
            hostname
            .encode("idna")
            .decode("ascii")
            .lower()
        )
    except UnicodeError as exc:
        raise WebSecurityError(
            "WEB_HOST_INVALID",
            "hostname IDNA encoding failed",
        ) from exc

    if len(ascii_hostname) > 253:
        _raise(
            "WEB_HOST_INVALID",
            "hostname is too long",
        )

    labels = ascii_hostname.split(".")

    if any(
        not label
        or not _HOST_LABEL_RE.fullmatch(
            label
        )
        for label in labels
    ):
        _raise(
            "WEB_HOST_INVALID",
            (
                "hostname contains an "
                "invalid DNS label"
            ),
        )

    return ascii_hostname


def validate_public_url(
    url,
):
    if not isinstance(url, str):
        _raise(
            "WEB_URL_INVALID",
            "URL must be text",
        )

    url = url.strip()

    if not url:
        _raise(
            "WEB_URL_INVALID",
            "URL must not be empty",
        )

    if len(url) > MAX_URL_LENGTH:
        _raise(
            "WEB_URL_INVALID",
            "URL exceeds maximum length",
        )

    if any(
        ord(character) < 32
        for character in url
    ):
        _raise(
            "WEB_URL_INVALID",
            "URL contains control characters",
        )

    try:
        parsed = urlsplit(url)
    except ValueError as exc:
        raise WebSecurityError(
            "WEB_URL_INVALID",
            "URL could not be parsed",
        ) from exc

    scheme = parsed.scheme.lower()

    if scheme not in ALLOWED_WEB_SCHEMES:
        _raise(
            "WEB_SCHEME_BLOCKED",
            (
                "only public HTTP(S) "
                "URLs are allowed"
            ),
        )

    if (
        parsed.username is not None
        or parsed.password is not None
    ):
        _raise(
            "WEB_CREDENTIALS_BLOCKED",
            (
                "credentials in URLs "
                "are not allowed"
            ),
        )

    try:
        hostname = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise WebSecurityError(
            "WEB_URL_INVALID",
            "URL host or port is invalid",
        ) from exc

    if hostname is None:
        _raise(
            "WEB_HOST_INVALID",
            "URL has no hostname",
        )

    hostname = normalize_public_hostname(
        hostname
    )

    expected_port = DEFAULT_WEB_PORTS[
        scheme
    ]

    if (
        port is not None
        and port != expected_port
    ):
        _raise(
            "WEB_PORT_BLOCKED",
            (
                "non-default network ports "
                "are blocked in Web v1"
            ),
        )

    sanitized_url = urlunsplit(
        (
            scheme,
            parsed.netloc,
            parsed.path or "/",
            parsed.query,
            "",
        )
    )

    return {
        "url": sanitized_url,
        "scheme": scheme,
        "hostname": hostname,
        "port": (
            port
            if port is not None
            else expected_port
        ),
    }


def validate_resolved_addresses(
    hostname,
    addresses,
):
    hostname = normalize_public_hostname(
        hostname
    )

    addresses = tuple(
        addresses
    )

    if not addresses:
        _raise(
            "WEB_DNS_EMPTY",
            (
                "hostname resolved to "
                "no addresses"
            ),
        )

    validated = []

    for value in addresses:
        try:
            validated.append(
                validate_public_ip(value)
            )
        except WebSecurityError as exc:
            raise WebSecurityError(
                exc.code,
                (
                    f"{hostname} resolved to "
                    f"a blocked address: {value}"
                ),
            ) from exc

    return tuple(validated)


def validate_redirect_target(
    url,
):
    return validate_public_url(
        url
    )
