# Phase 3 Checkpoint — Benchmark-96 First 32 Validated Cases

## 1. Context

Phase 3 is building Benchmark-96 before implementing Candidate Generation and Gate logic.

The benchmark is organized as six relation phenomena, each with sixteen cases across four decision modes:

- clear positive
- indirect positive
- hard negative
- ambiguous

This checkpoint records completion of the first two full families.

## 2. Completed Families

### Coreference Identity

Status: VALIDATED

Coverage includes:

- explicit identity and role reference
- aliases and nicknames
- pronoun resolution
- semantic-near hard negatives
- same-name collisions
- role ambiguity
- explicit abstention when identity cannot be uniquely resolved

Validation confirmed:

- 16 cases
- four cases per decision mode
- unique case IDs
- valid candidate references
- valid hard-negative references
- no candidate/hard-negative overlap

### Temporal Relation

Status: VALIDATED

Temporal-16 was revised after recovering the Phase 2 temporal contract.

Supporting representation follows Temporal Representation Contract v0.2.

The benchmark treats:

- temporal representation as supporting gold
- deterministic temporal relation as primary temporal gold
- persistence/materialization as out of scope

Temporal validation confirmed:

- 16 cases
- four cases per decision mode
- half-open interval contract
- deterministic clear-positive interval relations
- structured temporal signals in hard negatives
- abstention for insufficient temporal evidence
- no forced persistent Allen ontology

## 3. Current Benchmark State

Benchmark data:

- 32 authored cases
- 32 validated cases
- 64 remaining cases

Manifest state:

- status: IN_PROGRESS
- VALIDATED: 32
- UNWRITTEN: 64

The main benchmark remains DRAFT until the remaining families are completed and the full benchmark undergoes final review.

## 4. Decisions Reinforced

- Assertion remains the primary candidate unit.
- Retrieval relevance does not automatically imply a meaningful relation.
- Temporal proximity alone does not justify reasoning.
- Unknown or ambiguous evidence must permit abstention.
- Benchmark gold must not encode a preferred model size.
- Deterministic relations should be validated mechanically where possible.
- Benchmark requirements must not silently redesign earlier Corvus semantics.

## 5. Remaining Families

- State Evolution
- Correction / Contradiction
- Causal Relation
- Support / Evidence Relation

Each remaining family will contain sixteen cases using the same four decision modes.

## 6. Next Step

Design and validate State-Evolution-16, then continue the remaining Benchmark-96 families using batch authoring plus semantic review rather than manual one-case-at-a-time entry.
