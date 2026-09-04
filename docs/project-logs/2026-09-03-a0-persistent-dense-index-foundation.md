# Stage A0 — Persistent Dense Index Foundation v1

## Context

Corvus Phase 1 validated dense retrieval conceptually, but the original
`memory/semantic_search.py` implementation was not production-mature.

For every query it:

1. loaded all SQLite messages,
2. instantiated the embedding model,
3. re-embedded the entire message corpus,
4. performed an in-memory NumPy similarity scan.

Stage A0 — Retrieval Productionization was introduced to replace that research
prototype with a persistent, rebuildable retrieval foundation while preserving
SQLite as the canonical Evidence Log.

## Research / Engineering Question

Can Corvus maintain a persistent dense retrieval index that:

- derives entirely from the SQLite Evidence Log,
- uses a fixed and reproducible embedding artifact,
- survives process restart,
- supports idempotent keyed synchronization,
- can be safely deleted and deterministically rebuilt,
- never becomes an independent factual source of truth?

## Starting Hypothesis

Use:

- SQLite `messages` as canonical evidence,
- LanceDB as a derived local vector index,
- `message_id` as the synchronization identity,
- a pinned GTE multilingual embedding revision,
- explicit schema/version metadata,
- content hashes to verify source/index correspondence.

The derived index should contain retrieval representation and provenance
metadata, but not become the authoritative store for message content.

## What We Did

### Existing retrieval audit

The current retrieval files were inspected:

- `memory/store.py`
- `memory/semantic_search.py`
- `memory/sparse_search.py`
- `memory/hybrid_search.py`

Findings:

- SQLite `data/corvus.db` is the current persistent source.
- `messages_fts` is maintained through SQLite FTS5 triggers.
- `semantic_search.py` re-embeds the full corpus for every query.
- `sparse_search.py` uses SQLite FTS5/BM25.
- `hybrid_search.py` already performs RRF-style rank fusion.

This confirmed that the dense leg required productionization while the
SQLite/FTS foundation could remain in place.

### LanceDB API verification

Installed version:

`lancedb==0.37.1`

The actual local API was inspected and verified to provide:

- `add`
- `merge_insert`
- `update`
- `delete`
- `create_index`
- `create_fts_index`
- `optimize`
- `search`

A disposable persistence test confirmed that a local LanceDB table survives
reopen.

### Idempotent merge proof

A disposable explicit-schema test used:

`merge_insert("message_id")`

with:

- `when_matched_update_all()`
- `when_not_matched_insert_all()`

Results:

- initial sync: 2 rows
- identical resync: 2 rows
- incremental sync: 3 rows
- message IDs: `[1, 2, 3]`
- IDs remained unique
- reopen preserved all 3 rows

This supports `message_id` as the controlled synchronization key.

LanceDB is not assumed to enforce SQL-style primary-key uniqueness. Corvus
should use one controlled indexing path.

## Embedding Contract

Production dense embedding candidate:

`Alibaba-NLP/gte-multilingual-base`

Pinned revision:

`ca1791e0bcc104f6db161f27de1340241b13c5a4`

Embedding dimension:

`768`

Index schema version:

`1`

The pinned revision was confirmed through MTEB model metadata and exists as a
local Hugging Face snapshot.

A final CPU profile of the exact pinned revision on the Ryzen 7 3700X produced:

- load: 2.238 s
- dimensions: 768
- median query embedding: 47.1 ms
- mean query embedding: 47.5 ms
- 6-document batch: 63.5 ms
- short-batch throughput: 94.49 docs/s
- max RSS: approximately 2270 MB

Result:

`PINNED GTE PROFILE PASS`

## Implementation

Created:

`memory/dense_index.py`

The production foundation defines:

- LanceDB path:
  `data/corvus-retrieval.lancedb`
- table:
  `evidence_dense_v1`
- pinned embedding model and revision
- explicit 768-dimensional vector schema
- content SHA-256
- embedding metadata
- schema version
- deterministic full rebuild from SQLite
- status inspection

The derived-index schema contains:

- `message_id`
- `session_id`
- `role`
- `created_at`
- `content_sha256`
- `embedding_model`
- `embedding_revision`
- `embedding_dim`
- `schema_version`
- `vector[768]`

Raw `content` is intentionally not authoritative in LanceDB. Search results can
use `message_id` to hydrate canonical content from SQLite.

## Evidence / Results

### Real Corvus Evidence Log rebuild

SQLite source count:

`25`

First real rebuild result:

- source_messages: 25
- indexed_messages: 25
- table_rows: 25

Persistent index status:

- exists: true
- rows: 25
- table: `evidence_dense_v1`
- embedding model: `Alibaba-NLP/gte-multilingual-base`
- revision:
  `ca1791e0bcc104f6db161f27de1340241b13c5a4`
- embedding dimension: 768
- schema version: 1

Index disk usage at this scale:

approximately `124K`

The derived database is covered by the existing `data/` Git ignore rule and
does not appear in repository status.

### Deterministic rebuild validation

Before rebuild:

- rows: 25
- message IDs: 1 through 25

After a complete second rebuild:

- source_messages: 25
- indexed_messages: 25
- table_rows: 25
- message IDs: 1 through 25

Every indexed row was validated against SQLite for:

- `session_id`
- `role`
- `created_at`
- SHA-256 of canonical message content
- embedding model
- embedding revision
- embedding dimension
- schema version
- vector length

Result:

`SOURCE + HASH + METADATA: PASS`

Vector comparison between the first and second complete rebuild:

`MAX_ABS_VECTOR_DELTA: 0.0`

Result:

`VECTOR STABILITY: PASS`

Final identity checks:

- `MESSAGE IDS STABLE: PASS`
- `ROW COUNT STABLE: PASS`

Overall:

`RESULT: DETERMINISTIC REBUILD CONTRACT PASS`

## Interpretation

The dense retrieval representation now has a clean ownership boundary.

SQLite remains the canonical Evidence Log.

LanceDB is a derived retrieval structure that can be:

- deleted,
- recreated,
- independently optimized,
- replaced in the future,

without losing factual memory.

Pinning the embedding revision prevents future rebuilds from silently changing
representation because an upstream model repository moved its `main` branch.

The explicit schema and content hashes provide enough information to detect
stale or incompatible derived rows.

## Decision

### ADOPT

Use LanceDB as the persistent dense retrieval index for Stage A0.

### KEEP

Use SQLite as the sole authoritative Evidence Log.

### ADOPT

Use:

`merge_insert("message_id")`

for controlled idempotent synchronization.

### ADOPT

Freeze dense index v1 to:

- GTE multilingual base
- revision `ca1791e0bcc104f6db161f27de1340241b13c5a4`
- dimension 768
- schema version 1

### KEEP

Retain SQLite FTS5 as the current sparse/BM25 path rather than migrating sparse
retrieval into LanceDB without demonstrated need.

### DEFER

Do not choose an ANN index configuration yet.

Exact dense retrieval should first establish the correctness baseline. ANN
indexing should be introduced only when scale measurements demonstrate a need.

## Architecture Impact

The Stage A0 retrieval foundation is now:

SQLite Evidence Log
        |
        +--------------------+
        |                    |
        v                    v
SQLite FTS5             LanceDB
BM25 / sparse           GTE dense
                             |
                             v
                    evidence_dense_v1

The next layer will combine sparse and dense candidate rankings through RRF.

Materialized Memory remains a separate future recall path and is not moved into
this dense evidence index.

## Open Questions

- incremental indexing semantics after each new Evidence Log insertion
- stale-index detection
- controlled synchronization after source updates
- dense search result hydration from SQLite
- metadata filtering
- production RRF integration
- exact-search performance at larger scales
- when ANN indexing becomes worthwhile
- 1k / 10k / 100k behavior
- restart and recovery behavior

## Next Step

Implement incremental dense indexing and persistent dense search on top of the
validated `evidence_dense_v1` foundation.

Then replace the old brute-force dense leg of `hybrid_search.py` while retaining
SQLite FTS5/BM25 as the sparse leg and RRF as the fusion baseline.
