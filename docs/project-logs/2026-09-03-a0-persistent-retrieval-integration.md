# Stage A0 — Persistent Retrieval Integration

## Context

Stage A0 is productionizing Corvus Evidence Recall.

The preceding checkpoint established persistent incremental dense
indexing, targeted missing/stale repair, durable progress tracking,
and cross-process restart recovery.

This checkpoint integrates the persistent dense index into the actual
Evidence Recall search path while retaining SQLite FTS5/BM25 as the
sparse retrieval leg.

## Research / Engineering Question

Can Corvus replace the old corpus-wide dense retrieval prototype with
persistent LanceDB retrieval while preserving canonical SQLite
hydration, hybrid BM25+dense fusion, and deterministic metadata
constraints?

## Starting Hypothesis

The existing sparse retrieval and RRF fusion are already suitable for
reuse.

Only the old dense leg should be replaced.

Persistent dense search should:

- embed only the query
- search previously persisted LanceDB vectors
- return derived message IDs and distances
- hydrate canonical message content from SQLite
- never treat LanceDB as authoritative raw-content storage

Hybrid retrieval should continue using rank-based RRF, allowing the
persistent dense leg to replace the old semantic-search implementation
without requiring score calibration.

Metadata filtering should remain deterministic and caller-explicit,
initially supporting only session_id and role.

## What We Did

Added persistent dense query search using the pinned GTE embedding model
and LanceDB.

Explicitly selected `_distance` in LanceDB search output to avoid
relying on deprecated scoring autoprojection behavior.

Added SQLite hydration for ranked dense message IDs.

Replaced the old `memory.semantic_search.semantic_search` dense leg in
`memory.hybrid_search` with the persistent dense search path.

Kept `memory.sparse_search` on SQLite FTS5/BM25.

Kept reciprocal rank fusion as the hybrid combination method.

Added explicit `session_id` and `role` metadata filters to:

- persistent dense retrieval
- SQLite FTS5/BM25 retrieval
- hybrid retrieval

## Evidence / Results

Persistent dense self-retrieval:

- query: exact content of message 25
- top-1 message ID: 25
- top-1 vector distance: 0.0
- SQLite hydrated content matched canonical message 25

Hybrid production smoke:

Query:
`Where do I live now?`

Top result:
`I live in Los Angeles now.`

- dense rank: 1
- sparse rank: 1

Query:
`What port does Project Magpie use?`

Top result:
`Corvus trigger test: Project Magpie uses port 8842.`

- dense rank: 1
- sparse rank: 1

Metadata filtering used the real mixed-role session
`p1-roundtrip-test`:

- message 3: role=user
- message 4: role=assistant

Dense filtering:

- role=user returned message 3 only
- role=assistant returned message 4 only
- both session and role checks passed

Sparse filtering:

- role=user returned message 3 only
- role=assistant returned message 4 only
- both session and role checks passed

Hybrid filtering:

- user-filtered hybrid result returned message 3 with dense rank 1 and
  sparse rank 1
- assistant-filtered hybrid result returned message 4 with dense rank 1
  and sparse rank 1
- both filter-consistency checks passed

## Interpretation

The persistent Evidence Recall search path is now operational.

Dense retrieval no longer requires corpus-wide message loading or
historical re-embedding at query time.

SQLite remains the canonical Evidence Log and canonical raw-content
source.

LanceDB remains a deletable and rebuildable derived vector index.

SQLite FTS5/BM25 continues to provide the sparse lexical retrieval leg.

RRF combines independent dense and sparse rankings without requiring
score normalization between vector distance and BM25 scores.

Explicit metadata filtering can constrain both retrieval legs
consistently without introducing a learned or heuristic memory-admission
policy.

## Decision

ADOPT the production-candidate retrieval composition:

SQLite Evidence Log
→ SQLite FTS5/BM25 sparse retrieval

SQLite Evidence Log
→ pinned GTE embeddings
→ persistent LanceDB dense retrieval

Sparse ranking + dense ranking
→ RRF
→ SQLite canonical hydration
→ Working Context

KEEP metadata filtering deterministic and caller-explicit.

For Stage A0, support only:

- session_id
- role

DEFER intelligent filter selection, temporal reasoning filters,
authority filters, and other higher-level memory policies to the layers
that actually require them.

## Architecture Impact

The old `memory/semantic_search.py` corpus-wide re-embedding path is no
longer required by hybrid retrieval.

Production-candidate Evidence Recall now follows:

query
→ GTE query embedding
→ persistent LanceDB dense search
→ ranked message IDs
→ SQLite canonical hydration

in parallel with:

query
→ SQLite FTS5/BM25

then:

dense rank + sparse rank
→ RRF
→ Working Context

Both retrieval legs can be constrained by the same explicit session_id
and role filters.

## Open Questions

- At what corpus scale does exact dense search cease to be sufficient?
- When, if ever, does message-ID filtering or merge lookup warrant a
  scalar index?
- At what scale would ANN provide a meaningful latency/resource benefit?
- Does real future Corvus workload reveal a precision gap that warrants
  a reranker?
- Should the legacy semantic_search module eventually be removed or kept
  temporarily as a research/control implementation?

## Next Step

Perform bounded scale validation at 1k, 10k, and 100k derived evidence
rows to measure persistent exact dense retrieval and incremental
maintenance behavior before deciding whether ANN or additional indexing
is necessary.
