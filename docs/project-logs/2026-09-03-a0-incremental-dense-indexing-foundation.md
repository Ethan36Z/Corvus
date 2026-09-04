# Stage A0 — Incremental Dense Indexing Foundation

## Context

Stage A0 is productionizing Corvus Evidence Recall.

The previous dense retrieval prototype rebuilt embeddings from the
entire SQLite message corpus during query-time retrieval. The persistent
LanceDB foundation established SQLite as the canonical Evidence Log and
LanceDB as a rebuildable derived dense index.

This checkpoint extends that foundation toward incremental indexing.

## Research / Engineering Question

When one new Evidence Log message arrives, how can it enter the
persistent dense index without rescanning or re-embedding historical
evidence?

## Starting Hypothesis

Incremental indexing should operate on explicit SQLite message IDs.

For each requested message ID, Corvus should compare canonical SQLite
evidence against the existing LanceDB metadata and classify the derived
row as current, missing, stale, or source-missing.

Only missing or stale evidence should require embedding.

Current evidence should perform no embedding work.

## What We Did

Added targeted dense-index metadata lookup by message ID.

Added targeted SQLite Evidence Log lookup by message ID.

Added classification states:

- current
- missing
- stale
- source_missing

Added `sync_dense_message_ids()` as the controlled incremental writer.

Validated the current fast path using messages 1 and 25.

Validated a real missing-row recovery by deleting only message 25 from
the derived LanceDB table while leaving canonical SQLite evidence
untouched.

The incremental sync was then asked to repair only message 25.

## Evidence / Results

Targeted LanceDB lookup on LanceDB 0.37.1 successfully returned metadata
for explicit message IDs.

Current-path validation:

- messages tested: 1, 25
- indexed: 0
- embedding model cache before: empty
- embedding model cache after: empty
- LanceDB rows remained: 25

This demonstrated that already-current evidence does not load the
embedding model and does not perform unnecessary index writes.

Missing-row recovery validation:

- SQLite message 25 remained present
- LanceDB rows before deletion: 25
- LanceDB rows after deletion: 24
- classification after deletion: missing=[25]
- embedding model cache before sync: empty
- incremental sync indexed: 1
- embedding model cache after sync: one loaded model
- classification after sync: current=[25]
- LanceDB rows after recovery: 25

No historical messages were re-embedded during the repair.

Stale-row repair validation:

- test message: 25
- canonical SQLite evidence remained unchanged
- LanceDB `content_sha256` was intentionally replaced with a stale test value
- rows updated during stale injection: 1
- classification before repair: stale=[25]
- incremental sync indexed: 1
- classification after repair: current=[25]
- final LanceDB row count: 25

This demonstrated that stale derived metadata triggers targeted
re-embedding of only the affected message and returns the row to the
current state without rebuilding historical evidence.

Crash-window recovery validation:

- canonical SQLite message 25 remained present
- derived LanceDB message 25 was deleted
- dense progress was moved back from 25 to 24
- pre-recovery classification: missing=[25]
- recovery worker discovered message_ids=[25]
- recovery worker indexed exactly 1 message
- progress advanced only after successful synchronization
- post-recovery classification: current=[25]
- final LanceDB row count: 25
- final dense progress: 25

This demonstrated the at-least-once recovery contract: if canonical
Evidence Log persistence succeeds but dense indexing does not complete,
the durable progress point allows the worker to rediscover and repair
the missing derived row without rescanning or re-embedding historical
evidence.

The progress cursor had also already been observed from a subsequent
Python process, confirming that the worker completion point persists
across process boundaries.

Cross-process restart recovery validation:

- process 1 deleted only the derived LanceDB row for message 25
- process 1 moved dense progress back to 24
- process 1 confirmed message 25 classified as missing
- process 1 then exited
- process 2 started as a fresh Python process
- process 2 read durable progress=24
- process 2 confirmed message 25 still classified as missing
- embedding model cache began empty in process 2
- recovery worker discovered message_ids=[25]
- recovery worker indexed exactly 1 message
- progress advanced to 25 only after successful synchronization
- post-recovery classification: current=[25]
- final LanceDB row count: 25
- final durable progress: 25

This confirmed restart recovery across independent process lifetimes,
not merely recovery within a single process.

## Interpretation

The minimum incremental indexing contract is viable.

Corvus can identify whether explicitly requested evidence requires dense
index work without scanning or re-embedding the historical corpus.

The current fast path avoids embedding model initialization entirely.

A missing derived row can be reconstructed from canonical SQLite evidence
by embedding only the affected message and applying LanceDB
`merge_insert(message_id)`.

## Decision

ADOPT the explicit message-ID incremental indexing contract.

Maintain:

- SQLite as canonical Evidence Log
- LanceDB as deletable/rebuildable derived dense index
- one controlled dense-index writer
- pinned GTE model/revision/schema metadata
- content SHA256 stale detection
- full rebuild as the authoritative recovery path

Do not couple SQLite Evidence Log persistence directly to synchronous
embedding work.

## Architecture Impact

The dense indexing path now has two distinct modes:

Full recovery:

SQLite Evidence Log
→ deterministic full rebuild
→ LanceDB

Incremental maintenance:

SQLite commit
→ message ID
→ targeted source/index comparison
→ current: skip
→ missing/stale: targeted embedding
→ merge_insert
→ LanceDB

This preserves FOREGROUND FIRST / BACKGROUND WHEN POSSIBLE.

## Open Questions

- Validate targeted repair for stale content/config metadata.
- Define the eventual background handoff after SQLite commit.
- Determine whether a durable indexing queue/outbox is necessary.
- Validate restart and interrupted-indexing recovery.
- Measure when message-ID filtering or merge lookup benefits from a
  scalar index at larger corpus sizes.

## Next Step

Validate the STALE path:

- create a controlled stale derived row
- confirm classification as stale
- confirm only that message is re-embedded
- confirm the repaired row returns to current
