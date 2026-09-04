# Stage A1 — Persistent Conversation Loop

## Status

`PRODUCTION_CANDIDATE_RUNTIME`

Stage A1 implements and validates the first persistent end-to-end Corvus
conversation runtime.

It is not yet whole-product production readiness.

Daily-use hardening belongs to Stage A2.

## Goal

Stage A1 asked:

Can Corvus maintain a persistent conversational loop on top of the sealed A0
Evidence Recall foundation without losing canonical conversation history when
derived systems or the model fail?

Target flow:

user
→ SQLite canonical commit
→ bounded Recent Conversation Context
→ A0 Historical Evidence Recall
→ Working Context
→ local Qwen3.5-9B
→ SQLite assistant commit
→ derived dense synchronization

## Starting Point

Stage A0 already provided:

- SQLite canonical Evidence Log;
- FTS5/BM25 sparse retrieval;
- GTE multilingual embeddings;
- LanceDB persistent dense retrieval;
- RRF hybrid retrieval;
- canonical SQLite hydration;
- targeted dense synchronization;
- durable dense recovery cursor;
- restart recovery.

The pre-A1 chat programs were still prototypes:

- process-local `messages[]`;
- no canonical user/assistant persistence;
- obsolete retrieval wiring;
- unbounded session context;
- weak model failure handling.

## Implemented Architecture

### Canonical History

SQLite remains the authoritative Evidence Log.

User messages are committed before retrieval or generation.

Assistant messages become canonical only after successful model generation and
successful SQLite persistence.

Derived failures never roll back canonical evidence.

### Recent Conversation Context

Added persistent bounded recent-message loading.

Recent Conversation Context is:

- reconstructed from SQLite;
- scoped to the current session;
- bounded by model-native token count;
- newest-message prioritized;
- returned in chronological order.

It is not a separate short-term-memory store.

### Historical Evidence Recall

A1 uses the formal A0:

`hybrid_search()`

Historical retrieval is cross-session by default.

Message IDs already present in Recent Context are deterministically excluded.

A1 does not introduce a new retrieval ranking algorithm.

### Working Context

Added:

`app/working_context.py`

Working Context combines:

- one system message;
- Historical Evidence;
- Recent Conversation Context;
- current user input.

Default context policy:

- model context: 8192
- maximum input: 7168
- generation reserve: 512
- safety margin: 512
- Recent Context cap: 4096
- Historical Evidence cap: 2048

The pinned llama.cpp runtime's own:

`/v1/chat/completions/input_tokens`

endpoint is used as token authority.

### Model Client

Added:

`app/model_client.py`

Responsibilities:

- input token counting;
- chat completion request;
- explicit timeout;
- response validation;
- structured failure reporting.

Validated states include:

- `MODEL_UNAVAILABLE`
- `MODEL_TIMEOUT`
- `MODEL_HTTP_ERROR`
- `MODEL_RESPONSE_INVALID`

Blind automatic generation retry is not used.

### Persistent Turn Runtime

Added:

`app/conversation_runtime.py`

Normal turn:

user SQLite commit
→ Working Context
→ model generation
→ assistant SQLite commit
→ targeted dense sync

Per-turn inspection exposes:

- canonical message IDs;
- recent-context IDs;
- historical-evidence IDs;
- input tokens;
- retrieval status;
- model status;
- persistence status;
- dense status;
- errors.

### Interactive Runtime

Added:

`app/chat_persistent.py`

The CLI provides:

- explicit session IDs;
- bounded startup dense recovery;
- persistent conversation turns;
- runtime inspection output;
- graceful degraded-state reporting;
- clean process exit.

## Failure Semantics

The following behaviors were validated.

### Model Failure

If the user SQLite commit succeeds but generation fails:

user evidence remains canonical
→ no assistant evidence is created
→ no rollback occurs.

### Retrieval Failure

If Historical Evidence Recall fails:

Recent/Current Context remains usable
→ model generation may continue
→ retrieval status becomes degraded.

### Dense Failure

If dense synchronization fails:

both canonical messages remain intact
→ dense state becomes degraded
→ later recovery can repair it.

### Assistant Persistence Failure

If model generation succeeds but SQLite assistant persistence fails:

generated text is not treated as canonical assistant evidence
→ dense synchronization does not run.

### Context Failure

If the user is already canonical and Working Context construction unexpectedly
fails:

user evidence remains canonical
→ no assistant evidence is fabricated
→ failure is explicitly exposed.

## Live End-to-End Validation

A unique verification fact was entered in Session A:

`cedar-lantern-5842`

It became canonical message:

`#26`

The first live model request failed with HTTP 500.

The runtime correctly preserved `#26`, created no assistant message, and exited.

A new process was then started with a different session.

Startup recovery reported:

`Dense recovery: OK (batches=1, indexed=1, progress=26)`

Session B asked:

`What verification token did I give you in an earlier conversation?`

Inspection showed:

`recent=[]`

`history=[26, 2, 15, 16, 14]`

Corvus answered:

`Your verification token is **cedar-lantern-5842**.`

This demonstrates that the answer did not come from current-session recent
context.

It came from cross-session Historical Evidence Recall after process restart.

Canonical Session B records:

- `#27` — user recall question
- `#28` — assistant correct answer

Dense classification confirmed:

`current=[26, 27, 28]`

with no missing, stale, or source-missing rows.

## Live Bug Found and Fixed

The live test exposed a pinned Qwen3.5 chat-template constraint.

This message shape failed:

system
→ system Historical Evidence
→ user

with HTTP 500:

`No user query found in messages.`

Runtime experiments confirmed:

- system → user: PASS
- system → system → user: FAIL
- merged system → user: PASS
- system → recent conversation → user: PASS

Historical Evidence is therefore merged into the single system message.

Token budgeting was also changed to measure Historical Evidence incrementally
inside a valid complete chat-template shape.

The corrected live Working Context passed with exactly one system message.

## Restart Recovery Validation

After foreground targeted synchronization:

`#27/#28`

were already classified as current while the durable recovery cursor remained:

`26`

A subsequent tail recovery returned:

- message IDs: `[27, 28]`
- indexed: `0`
- progress: `26 → 28`

This validates the intended A0/A1 interaction:

foreground targeted sync
+
idempotent restart cursor recovery

Already-current messages are not unnecessarily re-embedded.

## Fresh Landscape Check

The targeted A1 landscape check supported:

ADOPT:

- SQLite canonical commit first;
- bounded active context;
- model-native token counting;
- explicit HTTP timeout;
- graceful degradation;
- recovery from canonical evidence.

KEEP:

- A0 hybrid Evidence Recall;
- targeted dense synchronization;
- durable recovery cursor.

DEFER:

- transactional outbox;
- Redis/Kafka/Celery;
- advanced summarization;
- context compression;
- blind retry frameworks;
- background 9B processing.

No evidence justified replacing the A0 retrieval foundation for Stage A1.

## Final Architecture

Evidence Log
    |
    +→ Recent Conversation Context
    |
    +→ A0 Historical Evidence Recall
                |
                v
          Working Context
                |
                v
         local Qwen3.5-9B
                |
                v
         SQLite assistant evidence
                |
                v
        targeted dense synchronization

On restart:

SQLite Evidence Log
→ bounded dense tail recovery
→ persistent conversation ready

## Maturity Judgment

Stage A1:

`PRODUCTION_CANDIDATE_RUNTIME`

Why it is beyond prototype:

- canonical persistence is real;
- process restart is real;
- cross-session recall is real;
- live pinned-model integration is real;
- major failure boundaries are explicit and tested;
- derived-state recovery is validated;
- runtime inspection is available.

Why it is not `PRODUCTION_READY`:

- daily-use workload has not yet been accumulated;
- UX/session management remains minimal;
- long-running operational behavior needs real-use measurement;
- context and retrieval budgets have not yet been tuned from sustained use;
- broader product hardening belongs to Stage A2.

## Adopt / Improve / Defer / Abandon

### Adopt

- SQLite-first persistent conversation
- token-budgeted Recent Context
- A0 Historical Evidence Recall
- deterministic ID deduplication
- single-system Working Context serialization
- model-native token counting
- explicit degraded states
- startup recovery
- foreground targeted dense synchronization

### Improve in A2

- daily-use UX
- runtime observability
- session ergonomics
- real-world latency measurements
- context-budget tuning
- long-running reliability

### Defer

- structured Knowledge Recall
- summarization/compression
- relation intelligence
- memory hierarchy/lifecycle
- personalization
- background intelligence
- multi-agent behavior

### Abandon for Production Path

- process-local `messages[]` as history
- legacy `semantic_search` chat wiring
- unbounded whole-session context
- rollback of canonical user evidence after model failure
- blind automatic generation retry

## Final Decision

Stage A1 exit criteria are satisfied.

Corvus now has an evidence-grounded persistent conversation loop that survives
process restart and can recall relevant canonical evidence across sessions.

This is the first usable persistent Corvus runtime foundation.

Next Delivery Stage:

`Stage A2 — Daily-Use Baseline`
