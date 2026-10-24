import json
import socket
import threading
import urllib.error
import urllib.request


from app.runtime_config import (
    MAX_GENERATION_TOKENS,
    MODEL_BASE_URL,
    MODEL_HEALTH_TIMEOUT_SECONDS,
    MODEL_TIMEOUT_SECONDS,
    TOKEN_TIMEOUT_SECONDS,
)


MODEL_NAME = "corvus"
MODEL_HEALTH_URL = f"{MODEL_BASE_URL}/health"
CHAT_COMPLETIONS_URL = f"{MODEL_BASE_URL}/v1/chat/completions"
INPUT_TOKENS_URL = f"{CHAT_COMPLETIONS_URL}/input_tokens"


# Server-side timings of the latest chat completion on this thread
# (llama.cpp "timings"); diagnostics only, never persisted.
_LAST_GENERATION = threading.local()


def take_last_generation_timings():
    """Return and clear this thread's latest llama.cpp timings, or None."""
    timings = getattr(_LAST_GENERATION, "timings", None)
    _LAST_GENERATION.timings = None
    return timings


class ModelClientError(RuntimeError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def _post_json(
    url,
    payload,
    timeout,
    opener=urllib.request.urlopen,
):
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with opener(
            request,
            timeout=timeout,
        ) as response:
            body = response.read()
    except (socket.timeout, TimeoutError) as exc:
        raise ModelClientError(
            "MODEL_TIMEOUT",
            "model request timed out",
        ) from exc
    except urllib.error.HTTPError as exc:
        raise ModelClientError(
            "MODEL_HTTP_ERROR",
            f"model server returned HTTP {exc.code}",
        ) from exc
    except urllib.error.URLError as exc:
        if isinstance(
            exc.reason,
            (socket.timeout, TimeoutError),
        ):
            code = "MODEL_TIMEOUT"
            message = "model request timed out"
        else:
            code = "MODEL_UNAVAILABLE"
            message = f"model server unavailable: {exc.reason}"

        raise ModelClientError(
            code,
            message,
        ) from exc

    try:
        return json.loads(
            body.decode("utf-8")
        )
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:
        raise ModelClientError(
            "MODEL_RESPONSE_INVALID",
            "model server returned invalid JSON",
        ) from exc


def check_model_health(
    timeout=MODEL_HEALTH_TIMEOUT_SECONDS,
    opener=urllib.request.urlopen,
):
    request = urllib.request.Request(
        MODEL_HEALTH_URL,
        method="GET",
    )

    try:
        with opener(
            request,
            timeout=timeout,
        ) as response:
            response.read()
    except (socket.timeout, TimeoutError) as exc:
        raise ModelClientError(
            "MODEL_TIMEOUT",
            "model health request timed out",
        ) from exc
    except urllib.error.HTTPError as exc:
        raise ModelClientError(
            "MODEL_HTTP_ERROR",
            f"model health returned HTTP {exc.code}",
        ) from exc
    except urllib.error.URLError as exc:
        raise ModelClientError(
            "MODEL_UNAVAILABLE",
            f"model server unavailable: {exc.reason}",
        ) from exc

    return True


def count_input_tokens(
    messages,
    timeout=TOKEN_TIMEOUT_SECONDS,
    opener=urllib.request.urlopen,
):
    data = _post_json(
        INPUT_TOKENS_URL,
        {
            "model": MODEL_NAME,
            "messages": messages,
        },
        timeout=timeout,
        opener=opener,
    )

    token_count = data.get(
        "input_tokens"
    )

    if (
        not isinstance(token_count, int)
        or isinstance(token_count, bool)
        or token_count < 0
    ):
        raise ModelClientError(
            "MODEL_RESPONSE_INVALID",
            "token endpoint returned invalid input_tokens",
        )

    return token_count


def generate_chat_completion(
    messages,
    timeout=MODEL_TIMEOUT_SECONDS,
    opener=urllib.request.urlopen,
):
    data = _post_json(
        CHAT_COMPLETIONS_URL,
        {
            "model": MODEL_NAME,
            "messages": messages,
            "temperature": 0,
            "top_p": 1.0,
            "seed": 42,
            "max_tokens": MAX_GENERATION_TOKENS,
            "chat_template_kwargs": {
                "enable_thinking": False,
            },
        },
        timeout=timeout,
        opener=opener,
    )

    timings = data.get("timings") if isinstance(data, dict) else None
    _LAST_GENERATION.timings = timings if isinstance(timings, dict) else None

    choices = data.get(
        "choices"
    )

    if (
        not isinstance(choices, list)
        or not choices
        or not isinstance(choices[0], dict)
    ):
        raise ModelClientError(
            "MODEL_RESPONSE_INVALID",
            "model response has no usable choices",
        )

    message = choices[0].get(
        "message"
    )

    if not isinstance(message, dict):
        raise ModelClientError(
            "MODEL_RESPONSE_INVALID",
            "model response has no usable message",
        )

    content = message.get(
        "content"
    )

    if (
        not isinstance(content, str)
        or not content.strip()
    ):
        raise ModelClientError(
            "MODEL_RESPONSE_INVALID",
            "model response has no usable content",
        )

    return content.strip()


# Additive stateless API transport. Existing callers above retain their contract.
class _NoModelRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def _bounded_model_opener(request, timeout):
    """Fixed loopback endpoint, no proxies/redirects; never read an error body."""
    from time import monotonic
    from urllib.parse import urlsplit
    parsed = urlsplit(MODEL_BASE_URL)
    if (parsed.scheme != 'http' or parsed.hostname != '127.0.0.1'
            or parsed.username or parsed.password or parsed.query or parsed.fragment
            or parsed.path or parsed.port is None
            or request.full_url not in (CHAT_COMPLETIONS_URL, INPUT_TOKENS_URL)
            or request.method != 'POST'):
        raise ModelClientError('MODEL_UNAVAILABLE', 'invalid inference endpoint')
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoModelRedirect())
    started = monotonic()
    try:
        response = opener.open(request, timeout=timeout)
    except urllib.error.HTTPError as exc:
        code = exc.code
        exc.close()
        raise ModelClientError('MODEL_UNAVAILABLE' if code in (429, 503) else
                               'MODEL_HTTP_ERROR', 'inference request failed') from None
    if (response.status != 200 or response.geturl() != request.full_url
            or response.headers.get_content_type() != 'application/json'
            or response.headers.get('Content-Encoding', 'identity').lower() != 'identity'):
        response.close()
        raise ModelClientError('MODEL_RESPONSE_INVALID', 'invalid inference response')

    class BoundedResponse:
        def __enter__(self):
            return self

        def __exit__(self, *unused):
            response.close()

        def read(self):
            chunks, size = [], 0
            while True:
                if monotonic() >= deadline:
                    raise TimeoutError()
                chunk = response.read1(min(4096, 262145 - size))
                if not chunk:
                    return b''.join(chunks)
                chunks.append(chunk)
                size += len(chunk)
                if size > 262144:
                    raise ModelClientError('MODEL_RESPONSE_INVALID', 'inference response too large')

    # Include response-header waiting in the supplied budget.
    deadline = started + timeout
    return BoundedResponse()


# Keep the budget start around opener.open as well as its bounded body reader.
# Defined separately for testing without any real model endpoint.
def stateless_chat_completion(payload, *, timeout=90, opener=None):
    """One count POST then at most one generation POST; no persistence or retries.

    The caller owns a wall-clock response deadline and retains its slot while this
    synchronous worker settles. Socket waits are finite but cannot prove remote
    inference was cancelled when a connection is closed.
    """
    from time import monotonic
    deadline = monotonic() + timeout
    if opener is None:
        opener = _bounded_model_opener
    request_body = dict(payload, stream=False, cache_prompt=False,
                        chat_template_kwargs={'enable_thinking': False})
    try:
        counts = _post_json(INPUT_TOKENS_URL, request_body,
                            max(0.001, deadline-monotonic()), opener=opener)
        tokens = counts.get('input_tokens') if isinstance(counts, dict) else None
        if type(tokens) is not int or tokens < 0:
            raise ModelClientError('MODEL_RESPONSE_INVALID', 'invalid token count')
        if tokens > 4096:
            raise ModelClientError('INPUT_TOO_LONG', 'input token limit exceeded')
        remaining = deadline-monotonic()
        if remaining <= 0:
            raise ModelClientError('MODEL_TIMEOUT', 'inference timed out')
        return _post_json(CHAT_COMPLETIONS_URL, request_body, remaining, opener=opener)
    except (ModelClientError, KeyboardInterrupt, SystemExit):
        raise
    except Exception:
        raise ModelClientError('MODEL_RESPONSE_INVALID', 'inference failed') from None
