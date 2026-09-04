# Stage A1 Checkpoint — Model Client

## Context

Stage A1 needs a reliable boundary between Working Context construction and
the pinned local llama.cpp / Qwen3.5-9B runtime.

## What We Did

Added `app/model_client.py`.

It provides:

- model-native input token counting;
- chat completion requests;
- explicit request timeouts;
- model response validation;
- structured failure codes.

Current failure states include:

- `MODEL_UNAVAILABLE`
- `MODEL_TIMEOUT`
- `MODEL_RESPONSE_INVALID`
- `MODEL_HTTP_ERROR`

The client does not handle persistence or memory policy.

## Evidence / Results

Synthetic validation passed for:

- token response parsing;
- successful generation;
- invalid model response;
- unavailable model server;
- model timeout.

The client was then tested against the actual pinned Corvus runtime.

Observed:

`/health` → `{"status":"ok"}`

Live token count:

`33`

Live generation:

`CORVUS_A1_OK`

Results:

- live token count: PASS
- live generation: PASS
- `python -m py_compile app/model_client.py`: PASS
- whitespace check: PASS

## Decision

ADOPT `app/model_client.py` as the Stage A1 model-runtime boundary.

Working Context decides what the model sees.

Model Client decides how the model is called and whether its response is valid.

SQLite persistence remains outside this module.

## Architecture Impact

The major A1 components now exist independently:

SQLite Evidence Log
→ Working Context Builder
→ Model Client
→ local Qwen3.5-9B

The remaining integration step is the persistent conversation orchestrator.

## Next Step

Review and checkpoint the Model Client, then implement the SQLite-first
Persistent Conversation Loop.
