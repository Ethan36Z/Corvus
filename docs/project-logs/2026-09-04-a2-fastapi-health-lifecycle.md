# Stage A2 Checkpoint — FastAPI Health and Startup Lifecycle

## Context

Stage A2 needs a daily-use backend shell around the sealed A1 conversation
runtime.

The first requirement is a stable way to determine whether the API service,
local model runtime, and derived dense state are ready.

## Research / Engineering Question

Can the FastAPI service reuse the shared A2 runtime lifecycle and expose a
stable health contract without duplicating model or recovery logic?

## Starting Hypothesis

The API should reuse:

- `recover_dense_tail()` for bounded startup recovery;
- `check_model_health()` for local model status.

The API itself should remain reachable even when the model is offline.

## What We Did

Added a model health primitive to:

`app/model_client.py`

Added a configurable health timeout to:

`app/runtime_config.py`

Updated:

`app/playground_api.py`

to use a FastAPI lifespan handler.

On startup, the API now runs bounded dense recovery and stores the result in
application state.

Added:

`GET /api/health`

The response reports:

- overall status;
- API service status;
- model status;
- startup dense recovery status.

Model or recovery degradation does not make the API itself unavailable.

## Evidence / Results

Synthetic model health tests passed:

`model_health_success=PASS`

`model_health_unavailable=PASS`

Live local model health returned:

`True`

Synthetic API health contracts passed:

`health_contract_ok=PASS`

`health_degraded_contract=PASS`

Live FastAPI lifespan validation passed:

`fastapi_lifespan=PASS`

`live_health_contract=PASS`

A real Uvicorn HTTP test returned:

`GET /api/health HTTP/1.1 200 OK`

with:

- service `OK`;
- model `OK`;
- dense recovery `OK`;
- recovery cursor `28`.

Contract checks passed:

`real_http_health=PASS`

`health_response_contract=PASS`

The temporary validation server was then stopped successfully:

`temporary_server_stopped=PASS`

## Interpretation

The A2 backend now has a real daily-use service lifecycle and a stable health
surface.

The UI can later distinguish:

- backend unavailable;
- backend alive but model unavailable;
- backend alive with degraded dense recovery;
- fully healthy runtime.

## Decision

ADOPT the FastAPI lifespan-based startup lifecycle and structured health
contract.

Keep `/api/health` available as HTTP 200 when only model or derived recovery
state is degraded.

## Architecture Impact

FastAPI startup
→ shared dense recovery
→ application runtime state

`/api/health`
→ service status
→ shared model health
→ startup recovery status

No A1 memory semantics were changed.

## Open Questions

The next backend contract is the persistent chat turn API.

## Next Step

Checkpoint this health/lifecycle work, then expose A1 `process_turn()` through
a stable `POST /api/chat` contract.
