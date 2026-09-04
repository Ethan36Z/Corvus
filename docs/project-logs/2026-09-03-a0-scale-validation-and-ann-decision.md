# Stage A0 — Scale Validation and ANN Decision

## Context

Stage A0 productionized Corvus Evidence Recall around SQLite as the
canonical Evidence Log and LanceDB as a persistent, rebuildable dense
retrieval index.

The persistent exact dense search path was functional, but Corvus is
intended to support long-lived personal memory. A bounded scale check was
therefore required before deciding whether approximate nearest-neighbor
indexing should enter the Stage A0 production candidate.

## Research / Engineering Question

At what point does persistent exact dense search become materially
expensive on the Corvus reference consumer machine, and does ANN provide
a sufficiently safe latency/recall tradeoff to justify adoption now?

Reference machine:

- Ryzen 7 3700X
- 32 GB RAM
- Linux Mint
- Corvus embedding dimension: 768

## Starting Hypothesis

Exact search should remain the default until measured scale creates a
demonstrable latency gap.

If such a gap appears, ANN should only be adopted if it provides a large
latency improvement while preserving sufficiently high retrieval recall.

Exact exhaustive search should serve as the ground truth for ANN
Recall@5 evaluation.

## What We Did

Created disposable LanceDB datasets using deterministic normalized
768-dimensional vectors.

The production Corvus SQLite database and production LanceDB index were
not modified.

Measured exact persistent vector search at:

- 1,000 rows
- 10,000 rows
- 100,000 rows

Then compared exhaustive exact Top-5 results against two HNSW-family ANN
configurations at 100,000 rows.

ANN configuration 1 used the legacy IVF-HNSW-FLAT API with:

- 64 partitions
- m=20
- ef_construction=300
- ef=100

After a fresh API/documentation check and local LanceDB 0.37.1
inspection, configuration 2 used the unified HnswFlat API with:

- num_partitions=1
- m=20
- ef_construction=300
- ef=100
- no vector quantization

No additional ANN families or repeated parameter sweeps were performed.

## Evidence / Results

Exact search scale results:

1,000 rows:

- p50: 2.755 ms
- p95: 3.840 ms
- mean: 2.841 ms
- Top-1 self retrieval: 30/30

10,000 rows:

- p50: 13.033 ms
- p95: 28.770 ms
- mean: 16.909 ms
- Top-1 self retrieval: 30/30

100,000 rows:

- p50: 112.643 ms
- p95: 146.248 ms
- mean: 115.011 ms
- Top-1 self retrieval: 30/30

A subsequent 100k ANN comparison run observed exact latency of:

- p50: 128.466 ms
- p95: 204.506 ms

This confirms normal run-to-run variance while preserving the same
hundred-millisecond scale.

ANN configuration 1, IVF-HNSW-FLAT with 64 partitions:

- index build: 7,372.05 ms
- ANN p50: 9.113 ms
- ANN p95: 23.036 ms
- mean Recall@5: 0.55
- minimum Recall@5: 0.20
- query count: 20

ANN configuration 2, HNSW-FLAT with one partition:

- index build: 124,659.35 ms
- ANN p50: 4.195 ms
- ANN p95: 26.299 ms
- mean Recall@5: 0.48
- minimum Recall@5: 0.20
- query count: 20

Both ANN configurations demonstrated substantial search-latency
improvement but unacceptable recall loss relative to exact Top-5 ground
truth.

## Interpretation

The scale validation demonstrated a real exact-search latency growth
curve.

At 100k 768-dimensional vectors, exact search reaches approximately the
hundred-millisecond range on the Corvus reference CPU. This establishes
a genuine future optimization opportunity rather than a hypothetical
one.

However, the tested ANN configurations traded too much recall for that
latency improvement.

Changing from 64 IVF/HNSW partitions to one HNSW-FLAT partition did not
resolve the recall deficit.

The synthetic deterministic-vector workload is not a substitute for
future evaluation on a large real Corvus GTE embedding distribution.
Therefore these results do not establish that HNSW itself is unsuitable
for Corvus.

They do establish that no tested ANN configuration is sufficiently
validated to replace exact retrieval in Stage A0.

## Decision

ADOPT persistent exact dense search as the Stage A0 production candidate.

DEFER ANN from the default Stage A0 retrieval path.

Do not continue broad ANN parameter sweeps, index-family comparisons, or
meta-evaluation in this stage.

Revisit ANN only when one of the following creates a concrete need:

- real Corvus evidence approaches a scale where exact latency materially
  harms user-facing retrieval
- a representative large real-GTE workload is available
- multi-year or million-scale evidence requires another scale tier

When revisited:

- exact exhaustive retrieval remains the recall ground truth
- latency and Recall@k must both be measured
- hardware-specific thresholds must not be hard-coded as universal
  Corvus behavior

## Architecture Impact

The Stage A0 dense path remains:

query
→ pinned GTE query embedding
→ persistent LanceDB exact search
→ message IDs
→ SQLite canonical hydration

No ANN index is required for correctness.

The architecture remains compatible with adding ANN later because
LanceDB is a derived index backend and SQLite remains the canonical
source of truth.

This supports the standing principle:

Architecture for large persistent memory.
Optimize only when measured.

## Open Questions

- How does exact retrieval scale on real GTE vectors rather than
  deterministic synthetic vectors?
- At what real Corvus corpus size does exact user-facing latency become
  unacceptable?
- Would a later HNSW configuration achieve near-exact recall on real
  personal-memory embeddings?
- Should future hardware-adaptive retrieval choose exact versus ANN
  dynamically rather than use a fixed row-count threshold?

These are deferred and do not block Stage A0.

## Next Step

Perform the Stage A0 final landscape/repository validation, write the
Stage A0 final report, then explicitly stage the intended retrieval code
and documentation before commit and push.
