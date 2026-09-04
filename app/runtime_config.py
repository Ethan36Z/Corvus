import os


def _positive_int_env(name, default):
    raw = os.getenv(name)

    if raw is None:
        return default

    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(
            f"{name} must be an integer"
        ) from exc

    if value <= 0:
        raise ValueError(
            f"{name} must be positive"
        )

    return value


MODEL_BASE_URL = os.getenv(
    "CORVUS_MODEL_BASE_URL",
    "http:" + chr(47) + chr(47) + "127.0.0.1:8095",
).rstrip("/")

MODEL_TIMEOUT_SECONDS = _positive_int_env(
    "CORVUS_MODEL_TIMEOUT_SECONDS",
    60,
)

TOKEN_TIMEOUT_SECONDS = _positive_int_env(
    "CORVUS_TOKEN_TIMEOUT_SECONDS",
    30,
)

MODEL_HEALTH_TIMEOUT_SECONDS = _positive_int_env(
    "CORVUS_MODEL_HEALTH_TIMEOUT_SECONDS",
    5,
)

MAX_GENERATION_TOKENS = _positive_int_env(
    "CORVUS_MAX_GENERATION_TOKENS",
    512,
)

RECOVERY_BATCH_SIZE = _positive_int_env(
    "CORVUS_RECOVERY_BATCH_SIZE",
    64,
)

RECOVERY_MAX_BATCHES = _positive_int_env(
    "CORVUS_RECOVERY_MAX_BATCHES",
    8,
)
