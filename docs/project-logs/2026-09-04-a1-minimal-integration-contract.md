# Stage A1 Checkpoint — Minimal Integration Contract

## Context

Stage A1 converts the existing Corvus storage, retrieval, dense-index, and
local-model components into a persistent end-to-end conversation runtime.

The preceding Stage A1 checkpoints established that:

- Stage A0 Evidence Recall is a reusable `PRODUCTION_CANDIDATE_FOUNDATION`;
- SQLite already provides canonical persistent conversation storage;
- A0 already provides incremental dense synchronization and restart recovery;
- the existing chat programs remain prototype glue;
- the pinned llama.cpp runtime exposes model-native chat input token counting;
- no evidence currently justifies rebuilding retrieval, adding a queue/outbox,
  or introducing a summarization memory layer.

This contract defines the minimum runtime invariants that must hold before
Stage A1 can be considered complete.

It is intentionally small in scope.

The goal is not to design the final Corvus memory system.

The goal is to establish a production-minded persistent conversation loop on
top of the existing A0 foundation.

## Research / Engineering Question

What exact interfaces, ordering rules, context budgets, failure semantics,
recovery behavior, and inspection requirements must Stage A1 implement so that
Corvus can converse persistently across process restarts without sacrificing
canonical evidence integrity?

## Starting Hypothesis

The smallest sufficient architecture is:

user input
→ canonical SQLite commit
→ reconstruct bounded Working Context
→ A0 historical Evidence Recall
→ local 9B generation
→ canonical assistant commit
→ targeted derived dense synchronization

with restart recovery driven from the canonical SQLite Evidence Log.

SQLite must remain authoritative.

Recent conversation context, historical retrieval results, dense vectors, and
model request payloads are all derived or temporary views.

## Contract

### 1. Canonical Evidence Contract

The SQLite `messages` table is the canonical conversation Evidence Log.

Every successfully accepted user message must be committed to SQLite before:

- dense indexing;
- historical retrieval;
- model generation;
- any other derived intelligence operation.

Canonical ordering:

user input
→ `add_message(session_id, "user", content)`
→ SQLite commit
→ canonical `user_message_id`

The runtime must not report the user message as accepted if the canonical
SQLite write fails.

No derived subsystem may roll back an already committed canonical message.

Invariant:

`CANONICAL_WRITE_BEFORE_DERIVED_WORK`

### 2. Assistant Evidence Contract

An assistant reply becomes canonical only after:

- the model request succeeds;
- the response structure is validated;
- usable assistant text is extracted;
- `add_message(session_id, "assistant", content)` commits successfully.

Ordering:

validated model response
→ SQLite assistant insert
→ commit
→ canonical `assistant_message_id`

If generation succeeds but assistant persistence fails, the runtime must report
a persistence failure rather than silently pretending the response is safely
recorded.

Invariant:

`ASSISTANT_IS_CANONICAL_ONLY_AFTER_SQLITE_COMMIT`

### 3. Session Contract

Stage A1 uses the existing `session_id` field.

Stage A1 does not require:

- a dedicated sessions table;
- session titles;
- automatic session summarization;
- advanced session metadata;
- device synchronization.

A session identifier must be explicit and stable for the lifetime of one
conversation session.

Advanced session lifecycle management is deferred to later delivery stages.

### 4. Recent Conversation Context Contract

Recent Conversation Context is not a separate memory store.

It is a temporary bounded view reconstructed from canonical SQLite messages.

Definition:

Recent Conversation Context
=
prior messages from the current `session_id`
selected from newest to oldest
until the configured recent-context token budget is reached.

The current user message is handled separately as mandatory input and must not
be duplicated inside the prior-message recent tail.

The current implementation must not use an unbounded whole-session history as
the long-term runtime policy.

Stage A1 should add a persistent bounded recent-message read path.

The complete historical session remains permanently stored in SQLite even when
only a bounded subset is sent to the model.

Invariant:

`PERMANENT_HISTORY_BOUNDED_ACTIVE_VIEW`

### 5. Model-Native Token Counting Contract

The pinned Corvus llama.cpp runtime has been verified to support:

`POST /v1/chat/completions/input_tokens`

Stage A1 must use model-native token counting for final Working Context budget
validation.

Do not introduce:

- a duplicate tokenizer dependency;
- character-count token estimation;
- fixed message count as the sole context-safety mechanism.

The runtime may use incremental candidate construction internally, but the
final request budget must be verified using the pinned model runtime.

Invariant:

`MODEL_TOKENIZER_IS_CONTEXT_AUTHORITY`

### 6. Context Budget Contract

Pinned model context:

`8192 tokens`

Stage A1 default budget:

- maximum total input: `7168`
- generation reserve: `512`
- safety margin: `512`

Within the input budget:

- Recent Conversation Context maximum: `4096`
- Historical Evidence maximum: `2048`
- system instructions: mandatory
- current user message: mandatory

The `4096` and `2048` values are caps, not quotas.

The runtime must not force-fill either section.

Budget priority:

1. system instructions;
2. current user message;
3. recent current-session context;
4. relevant historical evidence.

If the total request exceeds the input budget:

1. trim Historical Evidence first;
2. then trim the oldest Recent Conversation Context;
3. never silently truncate the current user message;
4. never exceed the configured model input cap.

If a single current user message plus required system instructions already
exceeds the input budget, Stage A1 must report an explicit context-size failure.

Invariant:

`WORKING_CONTEXT_MUST_FIT_BEFORE_GENERATION`

### 7. Historical Evidence Recall Contract

Historical Evidence Recall must use the formal A0 entrypoint:

`memory.hybrid_search.hybrid_search`

Stage A1 must not use:

- `memory.semantic_search`;
- `search_messages()` LIKE lookup;
- direct LanceDB content as canonical evidence.

Default historical retrieval is cross-session unless an explicit deterministic
filter is intentionally applied.

Historical Evidence Recall answers:

"What relevant canonical evidence exists outside the active recent context?"

### 8. Evidence Deduplication Contract

Historical Evidence must not duplicate evidence already present in the active
Working Context.

At minimum, Historical Evidence Recall must exclude:

- the current `user_message_id`;
- message IDs already selected into Recent Conversation Context.

This is a deterministic exclusion rule, not an importance or memory-admission
model.

Stage A1 may implement this by extending the retrieval interface or by a thin
integration-layer exclusion mechanism, but the resulting behavior must be
deterministic and inspectable.

Invariant:

`NO_DUPLICATE_MESSAGE_ID_IN_WORKING_CONTEXT`

### 9. Working Context Contract

The Stage A1 model request is composed from three logical sources:

1. system instructions;
2. bounded Recent Conversation Context;
3. relevant Historical Evidence;
4. current user message.

Historical evidence must remain visibly distinguishable from ordinary recent
conversation in the model request.

The existing memory annotation style may be adapted, for example using
canonical message IDs and roles.

Working Context is temporary.

It must never become a second authoritative memory store.

### 10. Foreground Dense-Synchronization Contract

Dense synchronization must not block canonical persistence.

For the normal successful conversational path, Stage A1 should prioritize the
visible response before non-essential dense synchronization.

Preferred ordering:

user SQLite commit
→ construct Working Context
→ model generation
→ assistant SQLite commit
→ targeted dense sync for newly committed user and assistant IDs

Rationale:

- the current user message does not need to retrieve itself;
- sparse FTS synchronization already occurs through SQLite triggers;
- delaying dense embedding reduces foreground latency;
- A0 restart recovery can repair derived dense gaps after a crash.

A targeted sync should normally use:

`sync_dense_message_ids([user_message_id, assistant_message_id])`

If no assistant message exists because generation failed, the committed user
message remains valid canonical evidence and may be synchronized later by
recovery.

Invariant:

`DENSE_SYNC_IS_DERIVED_NOT_TRANSACTIONAL`

### 11. Dense Failure Contract

If targeted dense synchronization fails after canonical commits:

- do not delete canonical messages;
- do not roll back the turn;
- mark dense state as degraded;
- preserve the affected canonical message IDs;
- allow A0 restart/tail recovery to repair the derived index later.

Dense indexing failure is not conversation persistence failure.

Invariant:

`DENSE_FAILURE_NEVER_ERASES_EVIDENCE`

### 12. Historical Retrieval Failure Contract

If A0 historical Evidence Recall fails:

- canonical user evidence remains committed;
- Recent Conversation Context may still be used;
- the model request may continue without historical evidence if the remaining
  context is valid;
- the turn must expose a degraded retrieval state for inspection.

Stage A1 must not silently claim that historical recall succeeded.

Invariant:

`RETRIEVAL_FAILURE_DEGRADES_RECALL_NOT_HISTORY`

### 13. Model Runtime Contract

Stable model endpoint:

`http://127.0.0.1:8095/v1/chat/completions`

Current main model:

`Qwen3.5-9B-Q5_K_M`

Current runtime assumption:

`parallel = 1`

Stage A1 treats the model service as an external on-demand runtime dependency.

The conversation runtime must not assume the model is always online.

Model unavailability must be handled explicitly.

### 14. Model Timeout Contract

Stage A1 default model-call timeout:

`60 seconds`

The value must live in a named configuration constant rather than being
scattered through request code.

The timeout exists to prevent indefinite blocking.

The value may be adjusted later using real-use latency measurements.

Stage A1 must not implement blind automatic generation retry.

Reason:

a client timeout does not prove that the server failed to execute the request.

A retry could duplicate expensive inference or create ambiguous response
semantics.

Invariant:

`BOUNDED_WAIT_NO_BLIND_RETRY`

### 15. Model Response Validation Contract

A successful HTTP response is not sufficient by itself.

Before assistant persistence, Stage A1 must validate that the response contains
a usable structure equivalent to:

`choices[0].message.content`

The runtime must explicitly handle:

- connection failure;
- timeout;
- non-success HTTP behavior;
- invalid JSON;
- missing `choices`;
- empty `choices`;
- missing `message`;
- missing or unusable `content`.

Malformed model output must not create a canonical assistant message.

Invariant:

`INVALID_MODEL_RESPONSE_IS_NOT_ASSISTANT_EVIDENCE`

### 16. Model Failure Contract

If the model is unavailable, times out, or produces an invalid response after
the user message was committed:

state becomes:

user evidence: canonical
assistant evidence: absent

This is valid history.

The runtime must not delete or roll back the user message merely to preserve a
synthetic one-user-one-assistant pairing.

Invariant:

`PRESERVE_REAL_HISTORY`

### 17. Startup Recovery Contract

Stage A1 must run existing A0 dense tail recovery during runtime startup.

Recovery uses:

`sync_dense_tail_once(limit=...)`

Startup recovery must be bounded and observable.

The runtime should process recoverable batches until either:

- no newer canonical message IDs remain;
- a recovery failure occurs;
- a configured startup recovery bound is reached.

A recovery failure must not corrupt or delete the SQLite Evidence Log.

Full dense rebuild remains a separate explicit maintenance operation and is not
the normal Stage A1 startup path.

### 18. Inspection Contract

Every completed or degraded turn must expose enough information for debugging,
validation, and later UI integration.

Minimum per-turn inspection data:

- `session_id`
- canonical `user_message_id`
- canonical `assistant_message_id` or `None`
- Recent Conversation Context message IDs
- Historical Evidence message IDs
- historical retrieval status
- dense synchronization status
- model status
- total input token count when model call is attempted
- degraded-mode indicators
- error summary when applicable

Inspection data is operational metadata.

It is not itself canonical conversation evidence.

### 19. Degraded-State Contract

Stage A1 should distinguish at least:

`NORMAL`

All required canonical and derived operations for the turn succeeded.

`DENSE_DEGRADED`

Canonical conversation succeeded but dense synchronization failed.

`RETRIEVAL_DEGRADED`

Historical recall failed but the current conversation remained usable.

`MODEL_UNAVAILABLE`

The user message was committed but no assistant response was generated because
the model service could not be reached.

`MODEL_TIMEOUT`

The user message was committed but generation exceeded the configured timeout.

`MODEL_RESPONSE_INVALID`

The user message was committed but the returned model response could not be
validated.

`ASSISTANT_PERSISTENCE_FAILED`

Generation produced usable text but the assistant response could not be made
canonical in SQLite.

SQLite user-write failure is not a degraded state.

It is a hard failure because the canonical user evidence does not exist.

### 20. Prototype Exclusion Contract

The Stage A1 production path must not depend on:

- `memory.semantic_search`;
- `search_messages()` as formal Evidence Recall;
- process-local `messages[]` as canonical history;
- unbounded whole-session model input;
- full-corpus embedding per turn;
- direct NumPy corpus search;
- LanceDB as canonical truth;
- rollback of committed user evidence on model failure;
- blind automatic generation retries.

### 21. Deferred Infrastructure Contract

Stage A1 does not add:

- Redis;
- Kafka;
- Celery;
- transactional outbox;
- dedicated durable job queue;
- advanced summarization;
- context compression;
- reranking;
- ANN default retrieval;
- background 9B memory processing;
- automatic GPU scheduling;
- advanced session-management infrastructure.

These remain reopenable only when a measured later-stage requirement
demonstrates a concrete gap.

## Target Runtime Flow

Normal successful turn:

USER INPUT
↓
SQLite user commit
↓
canonical user_message_id
↓
load bounded prior current-session context
↓
A0 hybrid historical Evidence Recall
↓
exclude current/recent duplicate message IDs
↓
construct Working Context
↓
model-native input-token validation
↓
local 9B generation
↓
validate assistant response
↓
SQLite assistant commit
↓
canonical assistant_message_id
↓
targeted dense sync for new canonical IDs
↓
inspection result

Startup:

Corvus runtime start
↓
initialize canonical store
↓
bounded A0 dense tail recovery
↓
conversation loop ready

## Evidence Supporting the Contract

The contract is grounded in:

- the Stage A1 repository re-audit;
- the sealed Stage A0 retrieval productionization report;
- the existing Evidence Log / Working Context / Materialized Memory
  architecture;
- the Stage A1 targeted fresh landscape check;
- the actual pinned llama.cpp runtime;
- successful live validation of:
  `POST /v1/chat/completions/input_tokens`;
- local context-budget calibration against Qwen3.5-9B-Q5_K_M.

Observed token-calibration examples:

- current user only: 13 tokens
- system + current user: 36 tokens
- representative recent conversation: 101 tokens
- recent conversation plus retrieved evidence: 169 tokens
- long repeated English message: 890 tokens
- long repeated Chinese message: 770 tokens

These measurements support a simple explicit budget without introducing
premature summarization or context compression.

## Interpretation

Stage A1 does not require another memory algorithm.

It requires a reliable orchestration layer.

The design intentionally preserves one canonical history while allowing
different temporary read views over that history:

SQLite Evidence Log
→ Recent Conversation Context

SQLite Evidence Log
→ A0 Historical Evidence Recall

Both feed:

Working Context
→ local 9B

This produces short-term conversational continuity and long-term historical
recall behavior without creating separate authoritative short-term and
long-term memory stores.

## Decision

ADOPT:

- SQLite-first conversation persistence;
- bounded token-budgeted Recent Conversation Context;
- A0 cross-session Historical Evidence Recall;
- deterministic message-ID deduplication;
- model-native token counting;
- explicit context budgets;
- foreground-first response path;
- post-response targeted dense sync;
- bounded model timeout;
- no blind generation retry;
- explicit degraded states;
- startup dense tail recovery;
- inspectable canonical message IDs.

KEEP:

- Stage A0 retrieval architecture;
- exact dense search;
- canonical SQLite hydration;
- existing dense progress/recovery mechanism;
- pinned local 9B runtime.

DEFER:

- summarization;
- outbox / task queue;
- complex retry framework;
- reranker;
- ANN default;
- background 9B memory intelligence;
- advanced session management.

## Architecture Impact

After Stage A1 implementation, Corvus should possess its first persistent
conversation runtime:

conversation
→ canonical Evidence Log
→ bounded current-session continuity
+
cross-session historical Evidence Recall
→ local 9B
→ canonical assistant history
→ restart-safe continuation

This is the minimum architecture required for the first usable persistent
Corvus Alpha.

## Open Questions

The contract intentionally leaves later product questions outside Stage A1:

- richer UI session management;
- advanced context compression;
- Materialized Memory integration;
- structured Knowledge Recall;
- relation intelligence;
- background consolidation;
- personalization;
- multi-agent behavior.

Real-use measurements after A1/A2 should determine which of these becomes the
next highest-value gap.

## Next Step

Implement the smallest production-minded runtime changes required by this
contract.

Implementation should begin with persistent bounded recent-context support and
the canonical SQLite-first conversation loop.

Each meaningful implementation checkpoint must be documented under:

`docs/project-logs/`

before Stage A1 can be sealed.
