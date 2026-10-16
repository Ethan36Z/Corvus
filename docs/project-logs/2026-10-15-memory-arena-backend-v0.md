# Memory Arena Backend v0 — Acceptance Checkpoint

Date: 2026-10-15 (local smoke completed 2026-10-16 UTC).

## Baseline and scope

Starting baseline: `87fa06a45298ecb30c62bc6eb4560f20553aa279`.
H1 remains sealed at `cee5a5e74216d9eaf393dcc290b4ad862a81657a`.

Memory Arena compares existing Corvus RAG with existing Hindsight recall on
real daily-use questions, with Ethan as human judge. It adds a comparison layer
only. It does not create a new memory backend, RAG, benchmark/gold set, judge,
scheduler, or standalone frontend, and does not redesign H1 or RAG.

## Backend design

`POST /api/arena/chat` is Lab-only and text-only, with web disabled. The
canonical RAG reply uses `process_turn()` and the normal persistence, dense
sync, and H1 lifecycle. Arena freezes one personality and recalls Hindsight
before the canonical turn can schedule retain. It captures the final RAG
recent context and composes a shadow candidate using the same personality,
recent messages, query, model, and generation function; historical evidence is
the intended variable. Hindsight recall is repeated in the existing H1
post-response lifecycle.

Fairness is `BEST_EFFORT_PRE_TURN`: no atomic shared historical snapshot or
server-side Hindsight as-of filter exists, so both providers use the closest
available pre-turn state. The shadow never calls `process_turn()`, writes
canonical messages, syncs dense evidence, or schedules retain. Only the
canonical result enters the existing H1 shadow-recall/comparison/retain path.

`POST /api/arena/vote` accepts `rag`, `hindsight`, `tie`, or `neither`. Trials
and votes are derived evaluation events in a separate Lab JSONL file; they are
not canonical memory. Personality is represented by a hash, and Hindsight
source IDs remain separate from canonical integer message IDs.

## Verification

Static and unit review passed; 46 mocked tests passed. The one controlled Lab
live smoke used session `memory-arena-smoke-v0-001` and exactly one Arena POST.
It created only canonical user/assistant IDs 17/18; dense rows grew 16 → 18.
Exactly one Arena trial was stored. The normal H1 background lifecycle ran
once, and its canonical-pair retain completed; Arena's preliminary recall
created no separate retain work. The trial was intentionally left unvoted.

Trial `25415702-8bac-4f1a-9dd8-5eba47de0ff4` passed engineering checks but
failed answer quality: both replies said “strict” despite the recorded
`BEST_EFFORT_PRE_TURN` metadata. RAG diagnosis: `FACT_NOT_STORED` in canonical
conversation evidence. Hindsight trial diagnosis: `RETRIEVAL_MISS`; its stored
recall evidence lacked the decision. This did not indicate an Arena assembly
defect.

Accepted v0 limits: no atomic cross-provider historical snapshot; duplicate
Hindsight recall; extra shadow latency; and JSONL lookup scans accumulated
history.

## Verdict

`MEMORY_ARENA_BACKEND_V0_ACCEPTED`. UI work is next. The whole Memory Arena is
**not sealed**.
