# Stage A0 Phase Report — Retrieval Productionization

## Status

Stage A0 is implementation-complete and ready for final version-control
validation.

This report does not mark the stage SEALED until the intended files have
been explicitly staged, reviewed, committed, pushed, and the repository
is confirmed synchronized with origin/main.

## Context

Corvus previously had a validated retrieval research prototype, but its
dense retrieval path was not production-ready.

The old dense implementation loaded all messages from SQLite, instantiated
a SentenceTransformer, re-embedded the complete corpus, and performed a
NumPy brute-force similarity search on every query.

That architecture was useful for research validation but unsuitable as a
durable foundation for a persistent personal AI.

Stage A0 therefore re-opened retrieval engineering maturity without
discarding the earlier research conclusions.

The architectural boundary for this stage is:

Evidence Log
→ Working Context
→ Materialized Memory

SQLite remains the canonical Evidence Log and source of truth.

Derived retrieval indexes may be deleted and rebuilt without losing
canonical user evidence.

## Research / Engineering Question

How should Corvus productionize evidence retrieval on consumer hardware
while preserving:

- complete canonical evidence
- durable dense retrieval
- incremental indexing
- crash/restart recovery
- hybrid lexical and semantic recall
- rebuildability
- deterministic metadata constraints
- acceptable latency at long-lived memory scales

without introducing unnecessary infrastructure or premature
approximate-search complexity?

## Starting Hypotheses

1. SQLite should remain the canonical Evidence Log.
2. Dense embeddings should live in a persistent but rebuildable derived
   index.
3. Mature BM25/FTS retrieval should be retained rather than reinvented.
4. Hybrid fusion should use rank fusion rather than attempt to directly
   calibrate incompatible lexical and vector scores.
5. Dense indexing should become incremental rather than rebuild the whole
   corpus after every new message.
6. Background recovery should be idempotent and driven from durable
   evidence rather than require a second canonical queue.
7. Exact vector search should remain the default until real scale
   measurements demonstrate a need for ANN.
8. ANN should not be adopted unless latency improvement is accompanied by
   sufficiently high recall.

## Landscape and Component Selection

### Embedding Model

A fresh comparison considered current multilingual embedding candidates,
including:

- Alibaba-NLP/gte-multilingual-base
- Qwen3-Embedding-0.6B
- newer frontier candidates retained as watch items

Corvus selected:

- model: Alibaba-NLP/gte-multilingual-base
- revision: ca1791e0bcc104f6db161f27de1340241b13c5a4
- dimension: 768

Representative MTEB MLQARetrieval results showed GTE competitive with or
better than Qwen3-Embedding-0.6B on the tested English and Chinese
retrieval tasks while being substantially cheaper on the Corvus CPU.

Local reference measurements for GTE included approximately:

- query embedding median: 47.1 ms
- six-document batch: 63.5 ms
- throughput: 94.49 documents/s
- process RSS: approximately 2.27 GB

This was substantially lighter than the tested Qwen alternative.

Decision: ADOPT pinned GTE as the Stage A0 embedding model.

### Dense Storage

Fresh landscape review considered:

- LanceDB
- Qdrant Server
- Qdrant Edge
- Milvus
- Vespa

Decision:

- LanceDB: ADOPT as primary local persistent dense backend
- Qdrant Server: retain as an alternative/control
- Qdrant Edge: WATCH while immature/beta
- Milvus: DEFER for single-user consumer deployment
- Vespa: DEFER for single-user consumer deployment

The architectural boundary is explicit:

SQLite = canonical Evidence Log
LanceDB = derived dense index

No unique canonical fact is allowed to exist only in LanceDB.

### Sparse and Hybrid Retrieval

The existing SQLite FTS5/BM25 path was retained.

The existing Reciprocal Rank Fusion strategy was also retained.

Current production candidate:

SQLite FTS5 / BM25
+
Pinned GTE dense embeddings
+
Persistent LanceDB exact vector retrieval
+
RRF hybrid fusion

Fresh landscape checks continued to support lexical + dense hybrid
retrieval and rank fusion as mature production patterns.

No Corvus-specific replacement for BM25 or RRF was justified.

## What We Built

### Persistent Dense Index

Implemented a LanceDB-backed persistent dense index using:

- table: evidence_dense_v1
- embedding dimension: 768
- schema version: 1

Stored derived metadata includes:

- message_id
- session_id
- role
- created_at
- content_sha256
- embedding_model
- embedding_revision
- embedding_dim
- schema_version
- vector

Raw message content remains authoritative only in SQLite.

### Rebuild

A full rebuild path remains the authoritative recovery mechanism.

A real 25-message rebuild validated:

- source rows: 25
- index rows: 25
- message ID coverage: 1 through 25
- metadata compatibility
- content hashes
- deterministic vectors
- maximum vector delta: 0

### Incremental Indexing

Implemented targeted source and index lookup by explicit message IDs.

Each requested ID is classified as:

- current
- missing
- stale
- source_missing

Only missing and stale rows are embedded.

Current rows are not re-embedded.

This removes the previous full-corpus embedding behavior from the
production candidate.

### Idempotent Recovery

Implemented a small SQLite operational progress cursor for dense indexing.

Recovery flow:

SQLite Evidence Log
→ durable message IDs
→ progress cursor
→ targeted dense synchronization
→ advance cursor only after successful sync

Because dense writes are idempotent by message_id, a crash after index
write but before cursor advancement is safe: the row may be processed
again without duplicating canonical evidence.

A separate durable job/outbox table was therefore not introduced at this
stage.

### Restart Validation

Recovery was tested across separate Python processes.

Fault state:

- SQLite message 25 remained canonical
- derived LanceDB row 25 was deleted
- progress cursor was set to 24

A fresh process then:

- read progress 24
- discovered message 25
- classified it missing
- loaded the embedding model only when required
- rebuilt row 25
- advanced progress to 25

Final state:

- row 25 current
- LanceDB row count restored to 25
- progress cursor = 25

### Persistent Dense Search

Implemented persistent vector search against LanceDB.

Search returns message IDs and distances.

Results are then hydrated from canonical SQLite rows.

Derived LanceDB content is never treated as canonical evidence.

### Hybrid Integration

The previous hybrid retrieval module imported the old prototype
semantic_search path.

Stage A0 replaced only the dense leg while retaining mature sparse and RRF
logic.

The resulting path is:

query
→ sparse BM25 candidates
+
persistent dense candidates
→ RRF
→ canonical hydrated results

The old semantic_search dependency is no longer present in the production
hybrid path.

### Metadata Filtering

Added explicit deterministic filters for:

- session_id
- role

The same constraints are forwarded to both sparse and dense retrieval
before hybrid fusion.

These filters define which evidence may compete in retrieval.

They are not learned memory-importance or admission decisions.

Intelligent automatic filter selection is outside Stage A0.

## Integration Evidence

Representative hybrid smoke tests included:

Query:

Where do I live now?

Top result:

I live in Los Angeles now.

The top result was rank 1 in both dense and sparse retrieval.

Query:

What port does Project Magpie use?

Top result:

Corvus trigger test: Project Magpie uses port 8842.

Again, the expected evidence ranked first in both retrieval paths.

A mixed-role session validated metadata filtering:

- user filter returned only the user evidence
- assistant filter returned only the assistant evidence
- hybrid fusion preserved the constraints

## Scale Validation

Disposable synthetic normalized 768-dimensional vectors were used to
measure LanceDB mechanics without modifying production Corvus data.

This was an engineering scale test, not a semantic benchmark.

### Exact Search

1,000 vectors:

- p50: 2.755 ms
- p95: 3.840 ms
- mean: 2.841 ms
- Top-1 self retrieval: 30/30

10,000 vectors:

- p50: 13.033 ms
- p95: 28.770 ms
- mean: 16.909 ms
- Top-1 self retrieval: 30/30

100,000 vectors:

- p50: 112.643 ms
- p95: 146.248 ms
- mean: 115.011 ms
- Top-1 self retrieval: 30/30

This demonstrated a real scale-dependent latency cost and justified a
bounded ANN investigation.

## ANN Evaluation

Exact exhaustive Top-5 retrieval was used as ground truth.

### IVF-HNSW-FLAT

Configuration:

- 100,000 vectors
- 64 partitions
- m=20
- ef_construction=300
- ef=100

Results:

- index build: 7,372.05 ms
- ANN p50: 9.113 ms
- ANN p95: 23.036 ms
- mean Recall@5: 0.55
- minimum Recall@5: 0.20

Latency improved substantially, but recall was insufficient.

### HNSW-FLAT Unified API

Local LanceDB 0.37.1 confirmed the unified HnswFlat API.

Configuration:

- 100,000 vectors
- num_partitions=1
- m=20
- ef_construction=300
- ef=100
- no vector quantization

Results:

- exact comparison p50: 128.466 ms
- exact comparison p95: 204.506 ms
- HNSW build: 124,659.35 ms
- HNSW p50: 4.195 ms
- HNSW p95: 26.299 ms
- mean Recall@5: 0.48
- minimum Recall@5: 0.20

Reducing partitions did not resolve the recall deficit.

The synthetic random-vector workload does not prove that real GTE memory
embeddings will exhibit identical ANN recall behavior.

It does prove that the tested ANN configurations are not sufficiently
validated to replace exact retrieval in Stage A0.

Decision: DEFER ANN.

No broad ANN parameter sweep was performed.

## Final Architecture Decision

Stage A0 production candidate:

Canonical Evidence Log:
SQLite messages

Sparse retrieval:
SQLite FTS5 / BM25

Dense representation:
Pinned GTE multilingual embeddings

Persistent dense storage:
LanceDB

Dense retrieval:
Exact persistent vector search

Hybrid fusion:
Reciprocal Rank Fusion

Hydration:
Canonical SQLite rows

Incremental indexing:
Explicit message-ID synchronization

Recovery:
Durable Evidence Log + progress cursor + idempotent dense writes

Filtering:
Explicit deterministic session_id / role constraints

## Adopt / Improve / Defer / Abandon

### ADOPT

- SQLite as canonical Evidence Log
- LanceDB as rebuildable persistent dense index
- pinned GTE multilingual embedding model
- SQLite FTS5/BM25
- reciprocal rank fusion
- persistent exact dense retrieval
- canonical SQLite hydration
- targeted incremental indexing
- idempotent restart recovery
- explicit metadata filters

### IMPROVE LATER

- operational observability
- automated background scheduling
- hardware-aware retrieval strategy
- real large-corpus latency profiling

### DEFER

- ANN as default retrieval
- broad HNSW parameter tuning
- PQ/SQ vector quantization
- reranking
- learned memory-importance filtering
- automatic metadata-filter selection
- dedicated job/outbox infrastructure
- scalar LanceDB indexes until workload demonstrates need
- million-scale stress testing until the 100k trend or real corpus makes
  it necessary

### ABANDON

For the production retrieval path:

- full-corpus re-embedding on every query
- model instantiation on every query
- NumPy brute-force corpus search as the runtime dense backend
- duplicating canonical evidence into a second authoritative store
- premature ANN adoption solely because long-term memory may eventually
  become large

## Corvus-Specific Architectural Contribution

Stage A0 does not claim novelty for its individual retrieval components.

GTE, BM25, LanceDB, exact vector search, HNSW, and RRF are established
external techniques or components.

The Corvus-specific work is the system boundary and integration discipline:

- immutable/canonical Evidence Log
- rebuildable derived semantic representation
- selective incremental intelligence expenditure
- hybrid Evidence Recall
- exact-first scaling policy
- foreground correctness before premature optimization
- recovery from canonical evidence rather than treating derived indexes as
  truth

The intended contribution remains architectural integration for persistent
personal AI on constrained consumer hardware rather than reinvention of
mature retrieval components.

## Rejected Ideas

Rejected or deferred during Stage A0:

- replacing SQLite FTS5 with a new sparse engine without evidence of need
- using LanceDB as the canonical memory store
- re-embedding the entire evidence corpus during retrieval
- synchronous embedding tightly coupled to the canonical SQLite commit
- introducing a durable queue before recovery requirements justify one
- inventing a new retrieval benchmark when mature retrieval evaluations
  already cover semantic quality
- forcing ANN into the production path merely because exact search scales
  linearly
- repeated ANN meta-tuning after tested configurations failed the recall
  requirement

## Engineering Maturity

Stage A0 moves Corvus Evidence Recall from:

VALIDATED_PROTOTYPE

to:

PRODUCTION_CANDIDATE_FOUNDATION

This does not mean the entire Corvus memory system is production-complete.

It means the retrieval substrate is now suitable to serve as the reusable
foundation for later memory-intelligence stages, subject to normal future
integration and real-world operational validation.

## Open Questions

- Exact-search behavior on a truly large real GTE personal-memory corpus
- Future threshold for ANN or another vector index strategy
- Background scheduling and prioritization with foreground model workloads
- Whether future retrieval precision demonstrates a need for a reranker
- Whether future workload justifies additional metadata/scalar indexes
- How higher memory-intelligence stages should choose between Evidence
  Recall and Knowledge Recall

None of these block Stage A0 completion.

## Final State

Stage A0 implementation and validation are complete.

The retrieval architecture now supports:

Evidence Log
→ persistent sparse + dense retrieval
→ hybrid fusion
→ canonical hydration
→ Working Context

with incremental persistence and restart recovery.

The remaining sealing actions are:

1. explicitly stage only the intended Stage A0 files
2. inspect the staged diff
3. commit
4. push to origin/main
5. confirm repository synchronization

Only after those steps should Stage A0 be marked SEALED.
