import json
import socket
import urllib.error
import urllib.request


MODEL_NAME = "corvus"
MODEL_BASE_URL = "http://127.0.0.1:8095"
CHAT_COMPLETIONS_URL = f"{MODEL_BASE_URL}/v1/chat/completions"
INPUT_TOKENS_URL = f"{CHAT_COMPLETIONS_URL}/input_tokens"

MODEL_TIMEOUT_SECONDS = 60
TOKEN_TIMEOUT_SECONDS = 30
MAX_GENERATION_TOKENS = 512


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
