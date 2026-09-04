# Stage A2 — Daily-Use Baseline

## Status

Stage A2 backend implementation is complete.

Proposed maturity:

`PRODUCTION_CANDIDATE_DAILY_USE_BACKEND`

This maturity applies only to the local single-user backend baseline.

It does not claim whole-system production readiness.

The explicit Stage A2 stop condition is:

`A2 backend ready for UI integration — PAUSED.`

UI integration itself is outside this stage and must happen in the dedicated UI
workflow.

## Context

Corvus uses two complementary roadmaps.

The Capability Roadmap describes long-term goals such as retrieval, structured
memory, relation intelligence, lifecycle, adaptive recall, personalization,
and multi-agent behavior.

The Delivery / Evolution Roadmap describes the order in which a continuously
usable Corvus should be built.

Stage A0 productionized Evidence Recall.

Stage A1 created a persistent conversation loop over that retrieval foundation.

Stage A2 was intentionally narrower:

turn the A1 runtime into a backend that could plausibly be used every day by
the already-built Corvus Memory Playground UI.

The goal was not to introduce another memory algorithm.

The goal was to make the existing architecture operational as a service.

## Stage Question

Can the sealed A1 persistent conversation runtime be turned into a stable,
restartable, inspectable local backend suitable for daily UI use without
changing Corvus memory semantics or prematurely introducing later-stage
research?

## Starting Principles

Stage A2 followed these constraints:

- preserve SQLite as canonical Evidence Log;
- preserve A1 `process_turn()` as conversation authority;
- preserve A0 Evidence Recall;
- reuse mature infrastructure instead of inventing replacements;
- centralize runtime configuration;
- expose health and failure state explicitly;
- recover derived dense state on service startup;
- expose a stable HTTP chat contract;
- expose only the minimum session state required for reload and resume;
- do not redesign the already-completed UI;
- do not introduce P3 relation intelligence;
- do not introduce structured-memory integration;
- do not introduce summarization or compression;
- do not build a complex session manager;
- stop when the backend is ready for UI integration.

## Baseline Entering A2

Stage A1 was sealed at:

`e3bd42f Seal Stage A1 persistent conversation loop`

A1 maturity was:

`PRODUCTION_CANDIDATE_RUNTIME`

The existing UI baseline had already been committed at:

`0f68a1f Add Corvus Memory Playground v0.1 baseline`

A2 therefore treated the UI as frozen.

The backend had to meet the UI rather than cause the UI to be redesigned.

## A2.1 — Shared Runtime Configuration

A2 first audited the A1 runtime for daily-use hardcoded configuration.

The repository did not contain an existing application configuration framework
that justified adding another dependency.

A small standard-library configuration module was created:

`app/runtime_config.py`

It centralizes:

- model base URL;
- model request timeout;
- token-count timeout;
- model health timeout;
- maximum generation tokens;
- startup recovery batch size;
- startup recovery maximum batches.

Environment overrides are supported while preserving the sealed A1 defaults.

Validation covered:

`default_config_preserved=PASS`

`env_override=PASS`

`invalid_config_guard=PASS`

`shared_config_import=PASS`

`model_urls_valid=PASS`

`a1_defaults_preserved=PASS`

`model_client_env_override=PASS`

## A2.1 — Shared Runtime Lifecycle

A1 previously owned its startup dense-recovery behavior inside the persistent
CLI entry point.

A2 extracted that behavior into:

`app/runtime_lifecycle.py`

The shared function:

`recover_dense_tail()`

preserves the A1 semantics.

Possible startup recovery states include:

- `OK`;
- `DEGRADED`;
- `BOUNDED`.

Recovery remains derived-state maintenance.

Failure of dense recovery does not rewrite or invalidate canonical SQLite
conversation history.

Validation covered:

`shared_recovery_behavior=PASS`

`recovery_degradation=PASS`

The persistent CLI was updated to reuse the same lifecycle function.

A2.1 was committed as:

`6dbe1d0 Add Stage A2 shared runtime lifecycle`

## A2.2 — Model and Service Health

A2 added:

`check_model_health()`

to the existing model client.

The health check uses the configured local model server rather than creating a
second model integration path.

A configurable short health timeout was added.

The FastAPI service adopted a lifespan handler.

At application startup:

FastAPI
→ bounded dense recovery
→ recovery result stored in application state.

The API exposes:

`GET /api/health`

The health response separates:

- API service state;
- local model state;
- startup dense-recovery state;
- overall state.

A model outage or degraded derived recovery does not make the FastAPI process
itself disappear.

This allows a UI to distinguish:

- backend unavailable;
- backend alive but model unavailable;
- backend alive with degraded derived state;
- fully healthy runtime.

Synthetic and live validation included:

`model_health_success=PASS`

`model_health_unavailable=PASS`

`health_contract_ok=PASS`

`health_degraded_contract=PASS`

`fastapi_lifespan=PASS`

`live_health_contract=PASS`

`real_http_health=PASS`

`health_response_contract=PASS`

`temporary_server_stopped=PASS`

This checkpoint was committed as:

`8ba741b Add Stage A2 backend health lifecycle`

## A2.3 — Persistent Chat HTTP Contract

The core design decision was:

do not recreate conversation logic inside FastAPI.

The HTTP service delegates directly to:

`app.conversation_runtime.process_turn()`

The backend exposes:

`POST /api/chat`

The request contains:

- `session_id`;
- `message`.

The response exposes:

- reply;
- session ID;
- canonical user message ID;
- canonical assistant message ID;
- Recent Context message IDs;
- Historical Evidence message IDs;
- hydrated retrieved memories;
- model input token count;
- retrieval status;
- model status;
- persistence status;
- dense status;
- inspection status;
- structured error information.

Historical evidence IDs returned by A1 are hydrated from canonical SQLite for
UI inspection.

The API does not invent a retrieval score that the A1 runtime does not expose.

Instead, hydrated memories contain deterministic retrieval rank.

## Chat Failure Semantics

A2 made failure state explicit.

If the user message cannot become canonical:

the request receives a structured hard failure.

If the user message is canonical but no assistant message becomes canonical:

overall chat status is `FAILED`.

If the canonical conversation succeeds but a secondary subsystem degrades:

overall status is `DEGRADED`.

Examples include:

- retrieval degradation;
- dense synchronization degradation;
- retrieved-memory inspection degradation.

If the canonical user and assistant messages persist successfully and all
required components succeed:

overall status is `OK`.

This preserves the architectural rule:

canonical conversation state is more important than derived inspection state.

## Retrieved-Memory Inspection Boundary

A2 explicitly tested what happens if the canonical conversation succeeds but
the API cannot hydrate the retrieved-memory inspector rows.

The canonical reply must survive.

Validation passed:

`canonical_turn_survives_inspection_failure=PASS`

`inspection_degradation_exposed=PASS`

`stable_chat_contract_preserved=PASS`

Normal-path regression also passed:

`normal_chat_contract_after_inspection_change=PASS`

`normal_inspection_status=PASS`

`retrieved_memory_order_preserved=PASS`

`hard_failure_contract=PASS`

## Live HTTP Cross-Session Recall

A real Uvicorn process was started.

The backend received:

`POST /api/chat`

using a new session:

`a2-http-live`

The request asked Corvus for a verification token supplied in an earlier
session.

Corvus answered:

`cedar-lantern-5842`

The request created canonical messages:

- user `#29`;
- assistant `#30`.

Historical Evidence Recall returned:

`[27, 28, 26, 2, 4]`

Original evidence `#26` contained the verification token.

The HTTP response hydrated the retrieved evidence for inspection.

All reported runtime states were healthy.

Validation passed:

`real_http_chat=PASS`

`cross_session_recall_over_http=PASS`

`canonical_message_ids_returned=PASS`

`retrieved_memories_hydrated=PASS`

`full_chat_status_ok=PASS`

`temporary_server_stopped=PASS`

The chat service checkpoint was committed as:

`948de85 Add Stage A2 persistent chat API`

## A2.4 — Minimal Session Resume

A daily-use browser client must be able to reload after refresh or backend
restart.

A2 deliberately did not introduce a separate session database.

Session state remains derived directly from canonical messages.

The API exposes:

`GET /api/sessions`

This returns basic SQLite-derived metadata:

- session ID;
- message count;
- first canonical message ID;
- last canonical message ID;
- created timestamp;
- updated timestamp.

The API also exposes:

`GET /api/sessions/{session_id}`

This returns canonical messages in chronological order.

The response reports:

- total message count;
- returned count;
- whether older messages remain outside the requested limit.

Missing sessions return HTTP 404.

Validation passed:

`session_list_route=PASS`

`session_detail_route=PASS`

`session_list_contains_live_session=PASS`

`canonical_session_resume=PASS`

`canonical_message_ids_preserved=PASS`

`chronological_session_messages=PASS`

`missing_session_404=PASS`

No additional session abstraction was introduced.

## Final Daily-Use Acceptance

The final A2 acceptance was designed to test actual product lifecycle rather
than another isolated function.

The acceptance covered:

1. backend startup;
2. health check;
3. first HTTP chat turn;
4. second HTTP turn in the same session;
5. Recent Conversation Context reuse;
6. canonical persistence;
7. backend shutdown;
8. backend restart;
9. startup dense recovery;
10. canonical session resume;
11. continued conversation after restart.

## Real Bug Discovered During Acceptance

The first final acceptance attempt did not pass.

Turn one succeeded.

The first session contained:

- user `#31`;
- assistant `#32`.

Turn two persisted its user message as:

`#33`

but returned before Working Context construction completed.

This was useful evidence for the SQLite-first architecture:

the user message remained canonical despite downstream failure.

The failure was traced to:

`build_recent_context()`

Recent messages were scanned backward to preserve newest-history preference.

During that scan, the runtime temporarily constructed:

assistant-only recent context.

That temporary candidate was passed into the model-native token counter.

The Qwen chat template rejected the assistant-only shape with HTTP 500.

A minimal reproduction confirmed:

`assistant_only_rejected=PASS`

The corresponding valid user-plus-assistant sequence succeeded:

`valid_conversation_counted=PASS`

## Recent Context Fix

The fix was deliberately narrow.

`build_recent_context()` now maintains a valid chat-shape invariant during
token budgeting.

When backward scanning temporarily encounters a leading assistant message, that
partial suffix is held until the preceding user message is available.

The model-native token endpoint is therefore called only with a recent context
beginning with a user message.

The fix preserves:

- SQLite-first persistence;
- newest-history preference;
- chronological final ordering;
- model-native token counting;
- existing recent token budget;
- existing historical token budget;
- existing total input budget;
- existing A1 retrieval behavior.

Regression validation passed:

`assistant_partial_shape_not_counted=PASS`

`complete_recent_turn_preserved=PASS`

`live_recent_context_31_32=PASS`

`recent_context_starts_with_user=PASS`

`qwen_token_count_regression=PASS`

## Final Acceptance — Successful Run

A fresh session was used:

`a2-daily-use-final`

The temporary marker was:

`silver-fox-8427`

The first persistent turn succeeded:

`first_persistent_turn=PASS`

The second turn recalled the marker correctly.

Its Recent Context contained:

`[34, 35]`

Validation passed:

`same_session_recent_context=PASS`

`second_persistent_turn=PASS`

The first backend process shut down cleanly:

`first_server_stopped=PASS`

A second backend process then started.

Startup dense recovery returned:

`OK`

with recovery progress through canonical message:

`#37`

Validation passed:

`backend_restart=PASS`

`restart_dense_recovery=PASS`

The session endpoint then restored the canonical transcript:

`[34, 35, 36, 37]`

Validation passed:

`session_resume_after_restart=PASS`

`canonical_transcript_preserved=PASS`

A third conversation turn was sent after the restart.

Corvus again recalled:

`silver-fox-8427`

Its Recent Context included the pre-restart conversation.

Validation passed:

`continued_chat_after_restart=PASS`

`persistent_recent_context_after_restart=PASS`

The second backend process also shut down cleanly.

The complete acceptance ended with:

`daily_use_http_loop=PASS`

`restart_resume_continue=PASS`

`recent_context_bug_fixed=PASS`

`a2_backend_acceptance=PASS`

## Final A2 Runtime Architecture

The resulting daily-use backend path is:

Browser / future UI
→ FastAPI
→ stable HTTP service contract
→ A1 `process_turn()`
→ canonical user SQLite commit
→ Recent Conversation Context
→ A0 Historical Evidence Recall
→ bounded Working Context
→ local Qwen
→ canonical assistant SQLite commit
→ targeted dense synchronization
→ retrieved-memory hydration
→ structured API response.

On restart:

FastAPI lifespan
→ bounded dense recovery
→ canonical SQLite session state
→ session resume
→ continued conversation.

## Canonical and Derived State

Canonical:

SQLite Evidence Log.

Canonical conversation messages survive downstream failures whenever their
individual SQLite commit has completed.

Derived:

- sparse retrieval state;
- dense retrieval state;
- Working Context;
- retrieved-memory inspection response;
- service health aggregation.

Derived failures must not silently rewrite canonical evidence.

## Fresh Landscape Check

A targeted fresh landscape check was performed before sealing Stage A2.

### FastAPI Lifecycle

Current FastAPI documentation continues to recommend application `lifespan`
for startup and shutdown behavior.

A2 already uses that mechanism.

Decision:

`ADOPT / KEEP`

### Local Model Service Boundary

Current llama.cpp server usage continues to support an HTTP health surface and
OpenAI-compatible chat-completion service behavior.

A2 already builds on those mature boundaries rather than inventing a custom
model transport.

Decision:

`ADOPT / KEEP`

### Liveness vs Readiness

Modern orchestrated deployment systems distinguish process liveness from
traffic readiness.

Corvus currently runs as a local single-user service.

Its structured `/api/health` response already distinguishes service, model,
and recovery state sufficiently for the A2 UI boundary.

Separate deployment-oriented liveness and readiness endpoints would be useful
only if Corvus moves into an orchestrated service environment.

Decision:

`DEFER`

### Larger Stateful-Agent Frameworks

Stage A2 does not require replacing Corvus with an external agent framework.

Doing so would increase architectural surface area without solving a proven A2
gap.

Decision:

`ABANDON for A2`

Re-evaluate external components only when a concrete future-stage requirement
justifies them.

## Adopt / Improve / Defer / Abandon

### Adopt / Keep

- SQLite as canonical Evidence Log;
- A0 persistent Evidence Recall;
- A1 `process_turn()` as conversation authority;
- model-native token counting;
- FastAPI lifespan lifecycle;
- llama.cpp HTTP model boundary;
- structured health reporting;
- HTTP chat adapter;
- SQLite-derived session resume;
- explicit degraded/failure states.

### Improve

Improvement during A2 was limited to product-hardening gaps that were proven by
daily-use validation.

The important example was the Recent Context valid-chat-shape invariant.

### Defer

Deferred beyond A2:

- structured Knowledge Recall integration;
- assertion/world projection in the chat path;
- relation intelligence;
- background consolidation;
- memory lifecycle and hierarchy;
- adaptive recall economy;
- personalization;
- multi-agent behavior;
- automatic conversation titles;
- session rename/delete workflows;
- generated session summaries;
- conversation folders;
- authentication and multi-user isolation;
- deployment-specific liveness/readiness endpoints;
- distributed service orchestration;
- advanced observability.

### Abandon for This Stage

A2 explicitly avoided:

- a second conversation runtime;
- a second canonical session store;
- fabricated retrieval scores;
- mandatory summarization;
- UI redesign;
- speculative infrastructure not justified by daily-use evidence.

## What A2 Proves

A2 proves that Corvus now has a local backend capable of:

- starting as a service;
- reporting health;
- recovering derived dense state;
- accepting persistent HTTP chat turns;
- committing user evidence before downstream processing;
- using same-session Recent Context;
- using cross-session Historical Evidence Recall;
- calling the local Qwen model;
- committing assistant replies canonically;
- synchronizing derived dense state;
- returning retrieved-memory inspection information;
- listing canonical sessions;
- restoring a canonical transcript;
- surviving backend restart;
- continuing a conversation after restart.

## What A2 Does Not Prove

A2 does not prove:

- whole-system production readiness;
- multi-user correctness;
- internet-facing security;
- high concurrency;
- distributed deployment;
- indefinite-scale session history;
- complete observability;
- zero-downtime deployment;
- semantic current-state memory;
- contradiction resolution;
- relation intelligence;
- memory consolidation;
- memory hierarchy;
- adaptive forgetting;
- personalization;
- autonomous agent behavior.

Those are outside the Stage A2 claim.

## Maturity Judgment

Stage A2 maturity:

`PRODUCTION_CANDIDATE_DAILY_USE_BACKEND`

Rationale:

The backend has passed real local HTTP validation across:

- multiple turns;
- canonical persistence;
- Recent Context;
- Historical Evidence Recall;
- model inference;
- dense synchronization;
- service restart;
- startup recovery;
- session resume;
- continued conversation.

A real acceptance failure was found, diagnosed from canonical evidence,
reproduced independently, fixed narrowly, and validated again in a fresh
end-to-end run.

The remaining work before actual user interaction is UI integration rather than
missing A2 backend architecture.

## Architecture Decision

Stage A2 is accepted.

No additional backend feature should be added before UI integration.

The existing UI is the next consumer of these service contracts.

## Final State

Stage A2 backend:

`READY FOR UI INTEGRATION`

Stage A2 execution state:

`PAUSED AT UI INTEGRATION BOUNDARY`

Formal seal remains pending only:

- final diff review;
- explicit staging;
- commit;
- push;
- verification that `HEAD == origin/main`.

## Next Step

Perform the final Stage A2 diff and repository review.

If clean:

commit and push the A2 session baseline, Recent Context fix, final acceptance
records, and this report.

Then mark:

`Stage A2 — Daily-Use Baseline ✅ SEALED`

and return to the dedicated UI integration conversation.
