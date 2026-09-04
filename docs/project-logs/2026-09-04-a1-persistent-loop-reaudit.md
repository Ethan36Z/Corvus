# Stage A1 Checkpoint — Persistent Conversation Loop Re-Audit

## Context

Stage A0 sealed the Corvus Evidence Recall substrate as a
`PRODUCTION_CANDIDATE_FOUNDATION`.

Before Stage A1 integrates that substrate into a persistent conversational
runtime, the existing repository was re-audited rather than assuming that
components completed during earlier research phases were already suitable for
production-style integration.

The purpose of this checkpoint was not to redesign retrieval or memory.

The purpose was to determine:

- which existing components are mature enough to reuse;
- which conversation-layer components remain prototype glue;
- where canonical persistence boundaries actually exist;
- how retrieval, dense indexing, restart recovery, and the local model runtime
  currently behave;
- what the smallest justified Stage A1 integration must add.

Stage A1 continues the project rule:

> Research status and engineering maturity are separate judgments.

It also inherits the Stage A0 engineering principle:

> Canonical evidence must survive failure of derived intelligence.

## Research / Engineering Question

What is the real engineering state of the current Corvus conversation stack,
and what minimum production-minded integration is required to create a
persistent end-to-end conversation loop on top of the sealed Stage A0
Evidence Recall foundation?

The re-audit specifically examined:

1. current chat entrypoints and legacy dependencies;
2. user-message persistence;
3. assistant-message persistence;
4. process-local conversation state;
5. recent-context construction;
6. the formal A0 hybrid retrieval contract;
7. incremental dense synchronization;
8. restart recovery;
9. the local 9B API boundary;
10. retrieval, indexing, and model failure boundaries;
11. prototype glue that must not remain on the production path;
12. components mature enough for direct reuse.

## Starting Hypothesis

The starting hypothesis was that Stage A0 had already solved most retrieval
and dense-index engineering problems, while the existing chat programs were
still early experimental glue.

If correct, Stage A1 should not rebuild retrieval.

It should instead create the smallest production-minded conversation runtime
that:

- commits raw conversation evidence to SQLite first;
- reconstructs recent conversation context from persistent evidence;
- consumes A0 hybrid Evidence Recall;
- calls the established local 9B runtime;
- persists assistant responses;
- incrementally updates the derived dense index;
- survives process restart;
- preserves canonical conversation history when optional derived components
  fail.

## What We Did

The committed `main` repository at baseline `f9d083a` was re-audited.

Primary implementation reviewed:

- `app/chat.py`
- `app/chat_rag.py`
- `memory/store.py`
- `memory/hybrid_search.py`
- `memory/sparse_search.py`
- `memory/dense_index.py`
- `compose.corvus.yml`

Formal records cross-checked:

- `docs/phase-reports/phase-a0-retrieval-productionization.md`
- `docs/project-logs/2026-09-03-p3-hybrid-memory-architecture-and-plan.md`
- `docs/project-logs/2026-09-02-p3-existing-first-resource-aware-strategy.md`
- `docs/project-logs/2026-09-01-p3-corvus-main-model-runtime.md`
- `docs/roadmaps/corvus-capability-and-delivery-roadmap-v2.md`

No Stage A1 production code was modified during this checkpoint.

## Evidence / Results

### 1. Current chat entrypoints

`app/chat.py` remains a current-session-only experiment.

Conversation state is held in:

`messages = []`

and the program explicitly reports that nothing is saved when the process
ends.

`app/chat_rag.py` adds historical retrieval but still imports the legacy:

`from memory.semantic_search import semantic_search`

Therefore the existing chat RAG path does not consume the formal Stage A0
hybrid Evidence Recall interface.

### 2. User-message persistence

The current chat programs do not persist user messages to the Evidence Log.

However, `memory/store.py` already provides:

`add_message(session_id, role, content)`

which inserts into SQLite, commits, and returns the canonical message ID.

The storage capability therefore exists; the runtime wiring does not.

### 3. Assistant-message persistence

Assistant replies are currently appended only to the in-process Python
message list.

They are not inserted into the canonical SQLite Evidence Log.

### 4. Process-local state

The current session history is stored in a Python list.

A process exit therefore destroys the active conversation state even though
the underlying repository already contains persistent message-storage
infrastructure.

Stage A1 must make SQLite the conversation truth and treat request context as a
temporary rebuildable view.

### 5. Recent conversation context

`memory/store.py` provides:

`load_session(session_id)`

but it loads the complete session in ascending message order.

There is no bounded recent-context contract yet.

Stage A1 therefore needs a small persistent recent-context read path rather
than treating the complete process lifetime or complete session as the active
model context.

This is a Working Context concern, not a new short-term-memory research
system.

### 6. Formal hybrid Evidence Recall

The formal A0 entrypoint is:

`hybrid_search(query, limit=5, candidate_limit=20, rrf_k=60, session_id=None, role=None)`

It combines:

persistent dense retrieval
+
SQLite FTS5 / BM25
→ RRF

and returns canonical hydrated message data including message ID, session,
role, content, timestamp, RRF score, and dense/sparse ranking metadata.

The production hybrid path contains no dependency on
`memory.semantic_search`.

### 7. Incremental dense synchronization

`memory/dense_index.py` provides:

`sync_dense_message_ids(message_ids)`

Requested message IDs are classified as:

- `current`
- `missing`
- `stale`
- `source_missing`

Only `missing` and `stale` evidence is embedded.

LanceDB writes use message-ID merge semantics, allowing repeated recovery
attempts without creating duplicate canonical evidence.

### 8. Restart recovery

A0 already provides:

`sync_dense_tail_once()`

Recovery is driven from:

SQLite Evidence Log
→ durable progress cursor
→ newer canonical message IDs
→ targeted dense sync
→ progress advance only after success

This mechanism has already been validated across separate Python processes.

Stage A1 therefore needs to orchestrate this existing recovery mechanism rather
than invent another queue.

### 9. Local 9B runtime

The stable Corvus main-model boundary is:

127.0.0.1:8095
→ llama.cpp
→ Qwen3.5-9B-Q5_K_M

The Compose runtime pins the llama.cpp image and model execution parameters.

The model is intentionally on-demand and uses:

`parallel = 1`

Stage A1 must therefore treat model availability as an external runtime
condition and must not assume simultaneous foreground and background 9B
inference.

### 10. Failure boundaries

The re-audit identified several distinct failure classes.

#### SQLite write failure

Canonical persistence has failed.

The runtime must not pretend that the message exists.

#### Dense indexing failure

SQLite canonical message exists.
LanceDB derived representation is missing or stale.

This is a degraded derived state, not conversation loss.

Recovery can occur later from SQLite.

#### Retrieval failure

Historical Evidence Recall may be temporarily unavailable while canonical
conversation evidence remains intact.

#### Model failure

A user message may already exist canonically while no assistant reply was
successfully produced.

This is a valid historical state.

The user message must not be rolled back merely to preserve artificial
user/assistant pairing.

#### Assistant dense-sync failure

The assistant response remains canonical once committed to SQLite even when its
derived dense representation fails to update.

### 11. Prototype glue identified

The following must not define the Stage A1 production path:

- `memory.semantic_search`
- `search_messages()` LIKE-based lookup as Evidence Recall
- process-local `messages[]` as canonical conversation history
- model failure followed by rollback of already-committed user evidence
- unbounded whole-session context as the long-term runtime policy
- full-corpus re-embedding on each query
- NumPy brute-force runtime corpus search
- LanceDB as canonical truth

### 12. Mature reusable components

The following are suitable for direct reuse unless Stage A1 integration exposes
a concrete defect:

- SQLite `messages` Evidence Log
- `add_message()`
- canonical message IDs
- FTS5 synchronization triggers
- SQLite FTS5 / BM25
- pinned GTE multilingual embeddings
- LanceDB `evidence_dense_v1`
- exact persistent dense retrieval
- canonical SQLite hydration
- RRF `hybrid_search()`
- deterministic `session_id` / `role` filters
- dense message-ID classification
- targeted incremental dense synchronization
- durable dense progress cursor
- restart tail recovery
- full dense rebuild
- stable localhost llama.cpp API boundary
- Qwen3.5-9B main model runtime

## Interpretation

The re-audit found no evidence that Stage A1 needs to rebuild the Stage A0
retrieval foundation.

The primary integration gap is:

mature persistent storage / retrieval substrate
+
prototype conversational glue

Stage A1 should therefore be treated as a production-minded runtime integration
stage rather than another retrieval-research phase.

The key architectural transition is:

process-local conversation state
→ canonical SQLite conversation state

while preserving:

SQLite = truth
derived indexes = rebuildable
Working Context = temporary

The desired runtime is small in scope but explicit about ordering,
recoverability, inspection, and degraded behavior.

## Decision

### REUSE

- SQLite canonical Evidence Log
- `add_message()`
- FTS5 triggers
- SQLite FTS5 / BM25
- pinned GTE multilingual embeddings
- LanceDB exact dense retrieval
- canonical SQLite hydration
- RRF hybrid retrieval
- metadata filters
- targeted dense synchronization
- dense progress cursor
- restart recovery
- full rebuild
- stable llama.cpp / Qwen3.5-9B runtime boundary

### HARDEN

- conversational runtime
- model HTTP call
- request timeout behavior
- model-response validation
- runtime inspection and failure reporting

### ADD

- canonical conversation write ordering
- persistent end-to-end conversation orchestration
- bounded recent-context read
- startup dense-recovery orchestration
- explicit degraded-mode semantics
- retrieved-message-ID inspection contract

### DEFER

- durable job/outbox infrastructure
- advanced recent-context compression
- reranker
- ANN as default
- learned retrieval filtering
- automatic metadata-filter selection
- background 9B memory processing
- multi-model GPU scheduler
- advanced session-management features

### DO NOT USE

- legacy `semantic_search` in the production chat path
- LIKE search as formal Evidence Recall
- Python `messages[]` as canonical history
- full-corpus re-embedding
- NumPy runtime corpus brute force
- LanceDB as authoritative evidence
- rollback of canonical user evidence after model failure

## Architecture Impact

Stage A1 should now target the following runtime boundary:

user input
→ canonical SQLite commit
→ derived dense synchronization
→ bounded recent conversation
+
A0 hybrid Evidence Recall
→ Working Context
→ local 9B
→ validated assistant response
→ canonical SQLite commit
→ derived dense synchronization

Startup additionally needs to invoke the existing recoverable dense tail
synchronization path.

The system invariant is:

> Dense indexing, retrieval, or model failure must never erase successfully
> committed canonical conversation evidence.

A user message without an assistant response is valid historical evidence when
generation fails.

Corvus should preserve reality rather than force every canonical message into
an artificial successful request/response pair.

## Open Questions

The re-audit intentionally leaves several Stage A1 design choices unresolved
until a small fresh landscape check is completed:

1. What bounded recent-context read contract should be used?
2. Should targeted dense synchronization happen before retrieval, after the
   visible response, or use different treatment for user and assistant
   messages?
3. What degraded behavior should occur when dense indexing fails?
4. What degraded behavior should occur when hybrid retrieval fails?
5. What explicit connect/read timeout policy should protect the local model
   call?
6. How should malformed or incomplete model responses be represented?
7. At exactly which startup lifecycle point should dense tail recovery run?
8. What minimum inspection data should every turn expose for debugging and
   later UI integration?

These are concrete integration questions, not justification for reopening the
A0 retrieval architecture.

## Next Step

Perform a small, targeted fresh landscape check for the concrete Stage A1
integration gaps identified by the re-audit.

The check should focus on:

- persistent chat write ordering;
- bounded recent-context handling;
- local HTTP timeout/failure semantics;
- durable recovery without premature queue infrastructure;
- degraded retrieval/indexing behavior.

Then define and record the:

`A1 Minimal Integration Contract`

before modifying the conversation runtime.
