# Stage A2 Checkpoint — Persistent Chat API

## Context

Stage A2 needs a stable HTTP boundary between the sealed A1 persistent
conversation runtime and the existing Corvus Memory Playground UI.

## Research / Engineering Question

Can the A1 persistent turn runtime be exposed through FastAPI without changing
its persistence or memory semantics, while also providing useful recall
inspection data to the UI?

## Starting Hypothesis

`process_turn()` should remain the conversation authority.

The API should adapt its existing result into a stable product-facing response
rather than introduce another conversation implementation.

Historical message IDs can be hydrated from canonical SQLite evidence for UI
inspection.

## What We Did

Added:

`POST /api/chat`

Request contract:

- `session_id`
- `message`

Response contract includes:

- reply;
- session ID;
- canonical user message ID;
- canonical assistant message ID;
- recent-context message IDs;
- historical-evidence message IDs;
- hydrated retrieved memories;
- input token count;
- retrieval, model, persistence, dense, and inspection states;
- structured errors.

Retrieved memories preserve retrieval order and expose a deterministic rank.

No synthetic retrieval score is invented.

## Failure Semantics

If no assistant message becomes canonical, overall status is `FAILED`.

If the canonical turn succeeds but retrieval, dense sync, or inspection is
degraded, overall status is `DEGRADED`.

A failure while hydrating inspection data does not invalidate an already
canonical conversation turn.

Input validation and hard user-persistence failures return structured failure
responses.

## Evidence / Results

Synthetic contracts passed:

`chat_response_contract=PASS`

`retrieved_memory_hydration_contract=PASS`

`retrieval_rank_preserved=PASS`

`chat_degraded_contract=PASS`

`chat_failed_contract=PASS`

`canonical_user_failure_state=PASS`

`post_chat_route=PASS`

Inspection failure validation passed:

`canonical_turn_survives_inspection_failure=PASS`

`inspection_degradation_exposed=PASS`

`stable_chat_contract_preserved=PASS`

Normal-path regression passed:

`normal_chat_contract_after_inspection_change=PASS`

`normal_inspection_status=PASS`

`retrieved_memory_order_preserved=PASS`

`hard_failure_contract=PASS`

## Live HTTP Validation

A real Uvicorn service received:

`POST /api/chat`

using session:

`a2-http-live`

The request asked for the verification token from an earlier conversation.

The API returned:

`cedar-lantern-5842`

Canonical messages were created:

- user `#29`
- assistant `#30`

Historical recall returned:

`[27, 28, 26, 2, 4]`

and hydrated the same evidence into `retrieved_memories`.

The original verification fact `#26` was present in Historical Evidence.

All runtime states were healthy:

- overall `OK`
- retrieval `OK`
- model `OK`
- persistence `NORMAL`
- dense `OK`
- inspection `OK`

Live checks passed:

`real_http_chat=PASS`

`cross_session_recall_over_http=PASS`

`canonical_message_ids_returned=PASS`

`retrieved_memories_hydrated=PASS`

`full_chat_status_ok=PASS`

The temporary validation server was stopped successfully.

## Interpretation

The backend path required by the existing UI is now operational end to end.

The HTTP layer is an adapter over the A1 runtime rather than a second memory or
conversation architecture.

## Decision

ADOPT the current `/api/chat` contract as the A2 persistent-chat service
baseline.

Keep canonical SQLite evidence and A1 `process_turn()` authoritative.

## Architecture Impact

Browser / UI
→ FastAPI `/api/chat`
→ A1 persistent turn runtime
→ A0 Evidence Recall
→ local Qwen
→ canonical SQLite
→ dense synchronization
→ hydrated recall inspection
→ JSON response

## Open Questions

A minimal session API is still needed so a daily-use client can resume
canonical conversation history after reload or restart.

## Next Step

Checkpoint the chat API, then implement the smallest session baseline required
before declaring the backend ready for UI integration.
