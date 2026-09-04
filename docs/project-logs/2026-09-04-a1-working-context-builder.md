# Stage A1 Checkpoint — Working Context Builder

## Context

Stage A1 needs to combine recent conversational continuity with A0 historical
Evidence Recall before calling the local 9B model.

## What We Did

Added `app/working_context.py`.

It now provides:

- token-budgeted Recent Conversation Context;
- newest-message priority with chronological model order;
- paged SQLite history loading;
- A0 `hybrid_search()` historical recall;
- deterministic message-ID deduplication;
- separate recent and historical token caps;
- final Working Context assembly;
- total input-budget enforcement.

Working Context order is:

system instructions
→ historical evidence
→ recent conversation
→ current user message

If total input exceeds budget:

historical evidence is trimmed first
→ oldest recent context is trimmed second
→ current user content is never silently truncated.

## Evidence / Results

Synthetic validation passed:

- pagination: PASS
- recent token cutoff: PASS
- newest messages preserved: PASS
- chronological recent order: PASS
- historical retrieval: PASS
- message-ID dedup: PASS
- A0 ranking preserved: PASS
- historical budget: PASS
- total input budget: PASS
- trim priority: PASS
- Working Context merge: PASS

Representative result:

`recent_ids=[7,8,9,10]`
`historical_ids=[3]`
`input_tokens=75`

`python -m py_compile app/working_context.py` also passed.

## Decision

ADOPT this builder as the Stage A1 Working Context integration layer.

It remains temporary runtime state and does not become another memory store.

## Architecture Impact

Corvus now has both A1 context paths:

Recent Conversation Context ─┐
                             ├→ Working Context → local 9B
A0 Historical Evidence ──────┘

The next step is to connect this builder to the persistent conversation loop.

## Next Step

Review and checkpoint the Working Context implementation, then replace the
prototype process-local chat flow with SQLite-first persistent orchestration.
