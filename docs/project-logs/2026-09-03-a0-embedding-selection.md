# Stage A0 — Production Embedding Selection

## Context

Corvus Phase 1 established dense retrieval as a research prototype, but the
existing implementation reloaded the embedding model and re-embedded the full
message corpus on every query. During the architecture rebaseline, retrieval
was therefore reclassified as VALIDATED_PROTOTYPE rather than production-ready.

Stage A0 — Retrieval Productionization was introduced to establish a mature
persistent retrieval foundation before further memory-system integration.

The embedding decision was deliberately reopened rather than preserving the
existing model only because it had already been used.

## Research / Engineering Question

Which multilingual embedding model provides the best engineering tradeoff for
Corvus on the fixed consumer-hardware target?

Primary candidates:

- Alibaba-NLP/gte-multilingual-base
- Qwen/Qwen3-Embedding-0.6B

The decision must consider retrieval quality together with foreground latency,
background indexing throughput, RAM usage, embedding dimension, license, and
ecosystem maturity.

## Starting Hypothesis

Qwen3-Embedding-0.6B might provide enough multilingual retrieval-quality gain
to justify its larger model and higher CPU cost.

GTE multilingual remained the efficiency-oriented incumbent.

The precommitted decision rule was:

- If Qwen3 showed a clear and stable retrieval-quality advantage, accept its
  additional resource cost.
- If quality was close or mixed, prefer GTE because Corvus targets constrained
  consumer hardware.

## What We Did

### Fresh landscape check

Reviewed current multilingual embedding candidates and mature retrieval
practice before implementation.

Candidates considered included:

- GTE multilingual base
- Qwen3-Embedding-0.6B
- BGE-M3
- Bekko embedding family
- Jina multilingual embedding models

The shortlist was reduced to GTE and Qwen3 for immediate evaluation.

Bekko was classified as FRONTIER WATCH because of its compelling efficiency
but very recent release and limited production history.

### Hardware profiling

Both models were tested on the fixed Corvus CPU target:

- AMD Ryzen 7 3700X
- CPU-only embedding execution

Observed results:

#### GTE multilingual base

- query median: 42.2 ms
- document throughput: 72.00 docs/s
- peak RSS: 2242.9 MB
- embedding dimension: 768

#### Qwen3-Embedding-0.6B

- query median: 182.0 ms
- document throughput: 18.97 docs/s
- peak RSS: 3871.4 MB
- embedding dimension: 1024

Both passed the precommitted foreground-latency acceptance threshold, but GTE
was approximately 4.3x faster for query embedding and 3.8x faster for document
embedding while using approximately 1.63 GB less RAM.

### Established retrieval benchmark

Before creating any Corvus-specific benchmark, the current established
benchmark ecosystem was reviewed.

MTEB 2.18.6 was installed and used directly rather than creating a custom
retrieval evaluator.

The benchmark family selected was MLQARetrieval validation with three subsets:

- eng-eng — English query / English corpus
- zho-zho — Simplified Chinese query / Simplified Chinese corpus
- zho-eng — Chinese query / English corpus

Both models were loaded through MTEB's model registry so model-specific
retrieval semantics and prompt handling were not replaced with a custom wrapper.

## Evidence / Results

### MTEB MLQARetrieval validation

| Subset | Model | NDCG@10 | MAP@10 | Recall@10 |
|---|---|---:|---:|---:|
| eng-eng | GTE | 0.83858 | 0.81233 | 0.91986 |
| eng-eng | Qwen3 | 0.83101 | 0.79976 | 0.92683 |
| zho-zho | GTE | 0.82368 | 0.79256 | 0.91865 |
| zho-zho | Qwen3 | 0.81373 | 0.77926 | 0.92063 |
| zho-eng | GTE | 0.81554 | 0.77749 | 0.93452 |
| zho-eng | Qwen3 | 0.82007 | 0.78217 | 0.93651 |

NDCG@10 delta, Qwen3 minus GTE:

- eng-eng: -0.00757
- zho-zho: -0.00995
- zho-eng: +0.00453

Three-subset mean:

| Metric | GTE | Qwen3 |
|---|---:|---:|
| NDCG@10 | 0.82593 | 0.82160 |
| MAP@10 | 0.79413 | 0.78706 |
| Recall@10 | 0.92434 | 0.92799 |

Qwen3 achieved a very small average Recall@10 advantage, but did not show a
clear or stable ranking-quality advantage.

GTE achieved the better average NDCG@10 and MAP@10 while being substantially
more efficient on the target hardware.

## Interpretation

The quality comparison does not justify Qwen3's additional foreground and
background compute cost.

Qwen3 is a capable model and remained competitive, particularly on the
Chinese-to-English subset, but the difference is too small and inconsistent to
justify:

- approximately 4.3x slower query embedding
- approximately 3.8x slower document embedding
- approximately 1.63 GB additional RAM
- larger 1024-dimensional vectors

For Corvus, retrieval quality must be considered as a system-level
quality/resource tradeoff rather than as a leaderboard-only choice.

## Decision

### ADOPT

`Alibaba-NLP/gte-multilingual-base`

Status:

`PRODUCTION_CANDIDATE`

Use GTE multilingual base as the default dense embedding model for Stage A0
retrieval productionization.

### RETAIN AS CHALLENGER

`Qwen/Qwen3-Embedding-0.6B`

Do not use it as the default production embedding under current evidence.

Reconsider only if future real Corvus workloads demonstrate a concrete
multilingual or cross-lingual retrieval gap.

### WATCH

Bekko embedding family remains a frontier efficiency candidate, but its novelty
does not justify replacing the mature baseline without demonstrated need.

## Architecture Impact

The production retrieval path can now be designed around a fixed 768-dimensional
dense embedding contract.

Canonical ownership remains:

SQLite Evidence Log
= authoritative raw evidence

LanceDB
= deletable and deterministically rebuildable derived retrieval index

The next retrieval baseline remains:

BM25
+
GTE dense retrieval
+
RRF fusion

No reranker is added unless a measured precision problem demonstrates the need.

## Open Questions

- Exact LanceDB schema and versioning contract
- Content-hash strategy for deterministic idempotent indexing
- Incremental ingestion semantics
- Index rebuild behavior after deletion or corruption
- Metadata filtering behavior
- Scale behavior at 1k, 10k, and 100k evidence records
- Whether hybrid retrieval exposes a real reranking gap

## Next Step

Define the LanceDB production schema and deterministic rebuild contract from the
SQLite Evidence Log using the frozen GTE 768-dimensional embedding model.
