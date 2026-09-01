# Phase 3 Benchmark Pilot v0.1 Frozen

**Date:** 2026-09-01
**Phase:** Phase 3 — Relation Intelligence & Gate
**Status:** CHECKPOINT
**Project:** Corvus — Persistent Personal AI on Consumer Hardware

## 1. Context

Phase 3 requires a benchmark before choosing Gate, routing, or small-model architecture.

## 2. Research / Engineering Question

Can a small evaluation set distinguish candidate generation, deterministic resolution, semantic relation judgment, unnecessary reasoning, and abstention?

## 3. Starting Hypothesis

A small manually reviewed pilot should expose benchmark-design problems before expanding to a larger dataset.

## 4. What We Did

- Defined the P3 benchmark schema.
- Chose assertions as the primary candidate unit.
- Separated relation phenomena from epistemic requirements.
- Designed and manually sanity-checked 12 pilot cases.
- Covered coreference, temporal relation, state evolution, correction, causality, and support/evidence.
- Included hard negatives and insufficient-evidence cases.
- Validated case count, unique IDs, and epistemic requirements.
- Frozen the dataset as `p3-pilot-v0.1`.

## 5. Evidence / Results

- 12/12 cases passed structural validation.
- Duplicate case IDs: none.
- Invalid epistemic requirements: none.
- Final status: `FROZEN_PILOT`.

## 6. Interpretation

The pilot is sufficient to serve as the first stable evaluation contract for Phase 3, while remaining small enough to revise the broader benchmark design before scaling.

## 7. Decision

**ADOPT:** Freeze `p3-pilot-v0.1` as the initial P3 evaluation contract.

**DEFER:** Do not choose a small relation model or final Gate architecture yet.

## 8. Architecture Impact

No runtime architecture change yet.

The benchmark now provides the evaluation boundary that future Candidate Generation and Gate implementations must satisfy.

## 9. Open Questions

- How should the pilot expand toward the full benchmark?
- Which candidate-generation signals provide the best recall/cost tradeoff?
- Is a small model actually necessary?
- How should escalation and abstention be calibrated?

## 10. Next Step

Expand the benchmark beyond the pilot and prepare the first Candidate Generation baseline.
