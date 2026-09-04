# Stage A1 Checkpoint — Targeted Fresh Landscape Check

## Context

Stage A1 is integrating the sealed Stage A0 Evidence Recall foundation into
a production-minded persistent conversation runtime.

The preceding Stage A1 re-audit found no evidence that retrieval, embedding,
dense storage, or the main-model runtime needed to be redesigned.

Instead, the remaining gaps were narrow integration questions:

- canonical write ordering;
- bounded recent conversation context;
- model-call timeout and failure behavior;
- dense-index recovery orchestration;
- degraded retrieval/indexing behavior;
- whether additional queue/outbox infrastructure was justified.

Corvus project discipline requires a fresh check of current mature practices
before adopting a technical design, while avoiding unnecessary broad research
when the engineering gap is already well defined.

This checkpoint therefore performs a targeted landscape check only for those
remaining Stage A1 integration questions.

## Research / Engineering Question

What current mature practices should Stage A1 adopt for:

1. canonical conversation persistence;
2. bounded recent-context construction;
3. model-native token budgeting;
4. local HTTP timeout and retry behavior;
5. dense-index recovery;
6. graceful degradation;
7. queue/outbox infrastructure?

The goal is to avoid both:

- reinventing solved reliability patterns;
- introducing infrastructure that Corvus does not yet need.

## Starting Hypothesis

The starting hypothesis was:

- SQLite should remain the canonical commit boundary;
- recent conversation context should be bounded independently from permanent
  history;
- token budgeting should prefer the model runtime's own tokenizer when
  available;
- derived dense state should remain recoverable from canonical evidence;
- local model calls should use explicit timeout behavior;
- automatic retries should be conservative because generation is not safely
  idempotent from the client's perspective;
- a transactional outbox or durable queue should remain deferred unless the
  actual failure model requires distributed dual-write guarantees.

## What We Did

Performed a small landscape check against current mature documentation and
patterns relevant to the identified Stage A1 gaps.

Areas checked included:

- SQLite atomic commit behavior;
- bounded conversation history and context trimming;
- llama.cpp server token-counting support;
- Python HTTP timeout behavior;
- retry semantics for non-idempotent operations;
- graceful degradation;
- transactional outbox use cases.

We then validated the most important implementation-specific finding against
the actual pinned Corvus runtime rather than relying only on current upstream
documentation.

Pinned Corvus runtime:

- llama.cpp image:
  `ghcr.io/ggml-org/llama.cpp:server-cuda12-b10630`
- API:
  `127.0.0.1:8095`
- model:
  `Qwen3.5-9B-Q5_K_M`
- context:
  `8192`
- parallel slots:
  `1`

The pinned runtime was started and reached healthy state.

The endpoint:

`POST /v1/chat/completions/input_tokens`

was tested with a minimal chat request containing:

`Hello Corvus`

Observed response:

`{"input_tokens":13,"object":"response.input_tokens"}`

The endpoint returned HTTP 200.

## Evidence / Results

### 1. Canonical persistence

SQLite continues to provide the appropriate canonical transaction boundary.

Stage A1 should preserve the ordering:

user input
→ SQLite INSERT
→ COMMIT
→ derived / optional work

Dense indexing must not be part of the canonical transaction.

A derived-index failure after SQLite commit represents degraded derived state,
not conversation loss.

Decision:

`ADOPT`

### 2. Permanent history versus Working Context

Current mature chat systems generally separate durable conversation history
from the bounded set of messages sent to the model.

Corvus already makes the same conceptual distinction:

Evidence Log
!=
Working Context

Therefore the complete session must not be continuously injected into the
model as it grows.

Decision:

`ADOPT bounded recent conversation context`

This is an active-context policy, not a new short-term-memory architecture.

### 3. Token-budgeted recent context

Fixed message counts are a weak context bound because message sizes vary
substantially.

A token budget is more directly aligned with the actual model context window.

The pinned Corvus llama.cpp build was verified to expose:

`POST /v1/chat/completions/input_tokens`

Therefore Stage A1 can use the model runtime's own tokenizer instead of:

- maintaining a duplicate tokenizer dependency;
- estimating tokens from characters;
- relying only on a fixed number of messages.

Decision:

`ADOPT model-native token counting`

Architecture:

persistent current-session history
→ select recent tail
→ measure with pinned llama.cpp tokenizer
→ trim to configured recent-context budget
→ Working Context

### 4. Context window ownership

The current model runtime uses:

`context = 8192`

The entire 8192-token context must not be assigned to recent conversation.

Working Context also needs room for:

- system instructions;
- retrieved historical evidence;
- current user input;
- generation headroom;
- future structured-memory additions.

Therefore Stage A1 should define explicit separate context budgets rather than
allow recent history to consume the full model context.

Exact budget values should be defined in the Minimal Integration Contract and
validated locally.

Decision:

`ADOPT explicit context budgeting`

### 5. HTTP timeout behavior

The current prototype model caller has no explicit timeout.

The Python HTTP client supports explicit timeout behavior, and a persistent
interactive runtime should not be able to hang indefinitely on an unavailable
or stalled model service.

Decision:

`ADOPT explicit bounded model-call timeout`

The precise value should be selected during implementation validation against
the local 9B runtime rather than copied blindly from a remote-service default.

### 6. Automatic retry behavior

A timed-out generation request is not necessarily known to have failed before
execution.

The model server may have received and processed the request while the client
failed to receive the response.

Blindly retrying can therefore:

- duplicate expensive inference;
- create ambiguity about which response is canonical;
- unnecessarily occupy the single available model slot.

This is particularly relevant because the pinned Corvus runtime uses:

`parallel = 1`

Decision for Stage A1:

`REJECT blind automatic generation retry`

Prefer:

bounded timeout
→ explicit generation failure
→ preserve committed user evidence
→ allow later/manual continuation

More sophisticated retry behavior may be reconsidered only if real use
demonstrates a need.

### 7. Graceful degradation

The remaining Corvus subsystems do not have equal authority.

Failure should respect this hierarchy:

SQLite canonical Evidence Log
>
derived dense index
>
retrieval result
>
temporary Working Context

Examples:

SQLite commit succeeds
dense sync fails
→ canonical evidence remains
→ derived state degraded
→ recover later

historical retrieval fails
→ current conversation may still continue
→ recall capability degraded

model call fails
→ committed user evidence remains
→ no assistant evidence is created

Decision:

`ADOPT explicit graceful-degradation states`

### 8. Dense recovery

Stage A0 already provides:

- targeted message-ID synchronization;
- current / missing / stale / source_missing classification;
- idempotent message-ID merge behavior;
- durable progress cursor;
- `sync_dense_tail_once()`;
- full rebuild from SQLite.

No new recovery mechanism was found necessary for Stage A1.

Decision:

`KEEP existing A0 recovery architecture`

Stage A1 only needs to define where recovery is orchestrated in the runtime
lifecycle.

### 9. Transactional outbox / durable queue

Transactional outbox patterns primarily address reliable coordination between
a database transaction and an external message broker or distributed service.

Corvus currently has:

SQLite canonical Evidence Log
→ rebuildable local LanceDB derived index

and already has durable progress plus idempotent recovery from canonical
evidence.

Introducing:

- Kafka;
- Redis queues;
- Celery;
- a transactional outbox;
- another durable job database;

would add infrastructure without evidence that Stage A1 requires distributed
dual-write guarantees.

Decision:

`DEFER`

Reopen only if later runtime requirements introduce a real durable asynchronous
work-dispatch problem that cannot be recovered from the Evidence Log.

## Interpretation

The fresh landscape check did not reveal a stronger architecture that
justifies replacing the Stage A0 foundation.

Instead, it reinforces the current Corvus design:

canonical evidence first
derived intelligence second
bounded active context
explicit failure boundaries
recovery from truth

The major new implementation-specific finding is that the pinned Corvus
llama.cpp build itself exposes exact chat input token counting.

This allows Stage A1 to implement bounded recent conversation context without
inventing tokenizer heuristics or introducing another tokenizer dependency.

The appropriate Stage A1 architecture remains deliberately small:

SQLite permanent history
        |
        +→ bounded token-budgeted recent tail
        |
        +→ A0 hybrid historical Evidence Recall
                    |
                    v
              Working Context
                    |
                    v
                 local 9B

No evidence currently justifies a summarization layer, queue system, new
retrieval engine, or new memory algorithm.

## Decision

### ADOPT

- SQLite canonical commit before derived work
- bounded recent conversation context
- model-native token counting
- explicit context budgets
- explicit model-call timeout
- graceful degradation
- recovery from canonical evidence
- existing A0 targeted dense synchronization
- existing A0 durable tail recovery

### KEEP

- complete permanent raw conversation history
- A0 hybrid Evidence Recall
- exact dense retrieval
- current pinned local 9B runtime
- `parallel = 1` foreground-priority assumption

### DEFER

- transactional outbox
- durable task queue
- Redis / Kafka / Celery infrastructure
- background 9B processing
- advanced conversation summarization
- context compression
- automatic retry framework
- circuit breaker framework

### REJECT FOR STAGE A1

- unbounded full-session model context
- fixed message count as the sole context-safety mechanism
- heuristic character-based token estimation when model-native counting exists
- blind automatic model-generation retry
- coupling LanceDB success to canonical SQLite commit
- treating derived-index failure as conversation failure

## Architecture Impact

Stage A1 Minimal Integration Contract should now define:

1. SQLite-first canonical write ordering.
2. Separate recent-context and historical-retrieval budgets.
3. Model-native `/v1/chat/completions/input_tokens` counting.
4. A bounded recent-session tail built from persistent SQLite history.
5. Historical cross-session recall through A0 `hybrid_search()`.
6. Explicit generation headroom within the 8192-token context.
7. Explicit timeout behavior for the local 9B call.
8. No blind automatic generation retry.
9. Explicit degraded states for:
   - dense sync failure;
   - retrieval failure;
   - model unavailability / generation failure.
10. Startup orchestration of existing dense tail recovery.
11. Preservation of inspectable canonical message IDs.
12. No queue/outbox infrastructure unless a later measured gap requires it.

## Open Questions

The landscape check narrows the remaining questions but does not set arbitrary
values prematurely.

The Minimal Integration Contract still needs to decide:

- exact recent-context token budget;
- exact historical-evidence token budget;
- generation reserve;
- system-prompt reserve;
- how to avoid duplicate evidence appearing both in recent context and
  historical retrieval;
- exact local model-call timeout;
- startup recovery batch behavior;
- user-visible / diagnostic degraded-state representation;
- exact per-turn inspection fields.

These should be selected against the real pinned 8192-token runtime and then
validated locally.

## References

SQLite atomic commit:
https://www.sqlite.org/atomiccommit.html

Python urllib request behavior:
https://docs.python.org/3/library/urllib.request.html

llama.cpp server documentation:
https://github.com/ggml-org/llama.cpp/tree/master/tools/server

Microsoft Azure retry pattern:
https://learn.microsoft.com/en-us/azure/architecture/patterns/retry

Microsoft Azure reliability / self-preservation guidance:
https://learn.microsoft.com/en-us/azure/well-architected/reliability/self-preservation

Transactional Outbox pattern:
https://microservices.io/patterns/data/transactional-outbox.html

## Next Step

Define the formal:

`A1 Minimal Integration Contract`

before modifying production conversation code.

The contract should convert the verified architecture and fresh landscape
findings into explicit runtime invariants, interfaces, budgets, failure
semantics, and inspection requirements.
