# Phase 3 — Existing-First and Resource-Aware Research Strategy

## 1. Context

During Phase 3, Corvus spent substantial effort designing, validating, blind-reviewing, and auditing Benchmark-96 before beginning the actual Gate experiments.

This work produced useful methodology lessons, but also exposed a risk:

A research workflow can recursively expand from:

mechanism
→ benchmark
→ benchmark reviewer
→ reviewer validation
→ meta-evaluation

without a natural stopping point.

Corvus is an individual research/engineering project operating under fixed consumer-hardware and limited experimental-resource constraints.

The project therefore needs a research strategy that preserves rigor without attempting to reproduce the experimental scale of a large academic or industrial lab.

At the same time, the goal is not to eliminate original work.

The goal is to concentrate original work where it has the highest leverage: system architecture, orchestration, policies, and genuinely uncovered gaps.

## 2. Research / Engineering Question

How should Corvus balance reuse and original research so that limited compute, time, and human attention are spent on the parts of the system that actually require new work?

## 3. Starting Hypothesis

The updated working hypothesis is:

Corvus should prefer mature external components, algorithms, baselines, and benchmarks for component-level problems.

Original effort should be concentrated on:

- system architecture;
- integration between independently developed components;
- memory lifecycle and orchestration policies;
- cost-aware routing between deterministic and learned mechanisms;
- Corvus-specific gaps that remain after existing approaches are reproduced or adapted.

A component does not need to be original for the overall Corvus architecture to be original or valuable.

## 4. What We Did

Phase 3 reviewed existing work relevant to memory gating, retrieval, and model routing.

Relevant existing directions include:

- lightweight memory admission / routing;
- utility-, novelty-, confidence-, and recency-based memory admission;
- query-time memory intent gates;
- memory write and retrieval gates;
- adaptive halting;
- hybrid semantic / lexical / graph retrieval;
- weak-model versus strong-model routing;
- uncertainty-aware escalation.

This revealed that several mechanisms Corvus had considered designing independently already exist in partial or mature forms.

We also reviewed the experience of constructing Benchmark-96.

That process demonstrated that custom evaluation can become disproportionately expensive when every layer of validation creates another object that itself appears to require validation.

## 5. Evidence / Results

Several concrete lessons emerged.

### Component reuse

Different existing systems already implement substantial portions of the functionality needed by Corvus.

Some existing gates overlap with one another.

Therefore, Corvus should not assume that every conceptual Gate in the architecture requires a separately invented implementation.

### Storage-policy distinction

Some existing memory-admission systems use a KEEP / DROP decision.

Corvus follows a different storage philosophy:

ARCHIVE CAN GROW.
ACTIVE CONTEXT SHOULD NOT.

Therefore, an existing admission mechanism can often be reused while changing the consequence of the decision:

existing system:

KEEP / DROP

Corvus:

PROMOTE / ARCHIVE_ONLY

Raw evidence remains available even when it is not promoted into structured or active memory.

The filtering mechanism itself may still be reusable.

### Benchmark cost

Benchmark-96 required significantly more validation work than initially expected.

The resulting benchmark is useful, but the process showed that repeatedly creating custom benchmarks and meta-evaluators is not sustainable as the default workflow for an individual project.

### Resource constraints

Corvus cannot economically reproduce every large-scale experiment across many models, seeds, datasets, ablations, and hardware configurations.

External published evidence and validated benchmarks should therefore carry part of the evidentiary burden.

Local experiments should focus on whether an external result still holds under Corvus-specific conditions.

## 6. Interpretation

Corvus should distinguish three layers of innovation.

### Layer 1 — Components

Examples:

- embeddings;
- rerankers;
- classifiers;
- memory-admission models;
- retrieval mechanisms;
- weak/strong model routers;
- evaluation benchmarks.

Default policy:

REUSE OR ADAPT FIRST.

### Layer 2 — Policies

Examples:

- when raw evidence should be promoted;
- when retrieval should be activated;
- when deterministic logic is sufficient;
- when evidence is insufficient;
- when more retrieval is justified;
- when a small model is sufficient;
- when escalation to the 9B model is justified.

Policy-level design may be Corvus-specific.

### Layer 3 — Architecture

Examples:

- immutable raw evidence;
- structured assertions;
- provenance and authority;
- temporal validity;
- historical versus current-world projection;
- relation intelligence;
- archive versus active memory;
- memory promotion;
- deterministic / abstain / semantic routing;
- integration of multiple mature components under a persistent personal-memory system.

This is the primary area in which Corvus should seek architectural originality.

The project should not confuse "using existing components" with "having no original architecture."

## 7. Decision

### ADOPT — Existing-First Rule

Before designing a new component:

1. Search current literature and open-source implementations.
2. Identify mature existing approaches.
3. Prefer reproduction or adaptation before invention.
4. Compare overlapping approaches before integrating multiple redundant components.
5. Create a new mechanism only when a concrete Corvus-specific gap survives.

### ADOPT — External-Benchmark-First Rule

Before creating a new benchmark:

1. Search for established benchmarks that already measure the capability.
2. Prefer official evaluation harnesses and validated datasets.
3. Use external benchmarks as the primary evidence when they adequately cover the problem.
4. Create Corvus-specific tests only for requirements not covered externally.

A custom Corvus benchmark MUST NOT become the sole evidence when appropriate established external benchmarks exist.

### ADOPT — Verification Budget

Default validation depth:

Level 1:
External literature, mature baselines, and established benchmarks.

Level 2:
Reproduce or adapt the relevant mechanism under Corvus hardware and architecture.

Level 3:
Create a small targeted Corvus-specific evaluation only for uncovered behavior.

STOP after sufficient evidence exists to make the engineering decision.

Additional meta-validation requires a concrete reason such as:

- implementation error;
- dataset leakage;
- contradictory benchmark definitions;
- severe result instability;
- a demonstrated protocol-level defect.

General uncertainty alone is not sufficient reason to create another evaluator.

### ADOPT — Resource-Aware Research

Corvus should not attempt experimental scale that is unrealistic for an individual project.

Limited compute and human attention should be concentrated on:

- integration failures;
- architecture-level hypotheses;
- Corvus-specific behavior;
- consumer-hardware constraints;
- gaps not already well tested by existing research.

### REJECT

- Reinventing mature components solely for originality.
- Creating custom benchmarks before checking existing ones.
- Recursive benchmark → reviewer → reviewer-validator loops without a demonstrated need.
- Optimizing evaluators against individual benchmark cases.
- Treating architectural originality as requiring every underlying component to be original.

## 8. Architecture Impact

The updated Phase 3 strategy becomes:

Existing components and research
        ↓
Capability / overlap matrix
        ↓
Select the smallest non-redundant set
        ↓
Adapt to Corvus semantics
        ↓
Assemble Corvus architecture
        ↓
Validate with established external benchmarks
        ↓
Identify remaining Corvus-specific gaps
        ↓
Design original mechanism only where necessary

The current conceptual pipeline remains approximately:

Raw Evidence
    ↓
Archive
    ↓
Promotion / Admission Policy
    ├── ARCHIVE_ONLY
    └── PROMOTE
           ↓
Candidate Retrieval
           ↓
Relation / Resolution Layer
    ├── deterministic
    ├── insufficient evidence / abstain
    └── semantic reasoning
             ↓
        Model Routing
        ├── smaller model
        └── 9B escalation

However, none of these boxes is assumed to require a newly invented Corvus component.

The architecture may be original even when most boxes contain mature external mechanisms.

## 9. Open Questions

- Which existing memory-admission mechanisms best map from KEEP/DROP to PROMOTE/ARCHIVE_ONLY?
- Which retrieval mechanisms overlap enough that only one should be retained?
- Is a separate query-time memory intent gate useful for Corvus?
- Which existing routing method is most appropriate for small-model versus 9B escalation?
- Can deterministic Phase 2 temporal and lineage logic eliminate additional model calls?
- After existing components are assembled, does a distinct relation-worthiness gap actually remain?
- Which external benchmarks best cover each P3 capability?
- Which aspects of Corvus still require a small project-specific regression suite?

## 10. Next Step

Complete the already-started final adjudication pass for Benchmark-96 under the existing stop rule.

Fix only demonstrated defects.

Freeze Benchmark v0.1.

Then stop benchmark development and begin the next P3 checkpoint:

Gate Capability and Overlap Matrix.

For every required Corvus capability:

- identify existing implementations;
- identify established benchmarks;
- identify licensing and deployment constraints;
- identify overlap with other components;
- decide ADOPT / ADAPT / DEFER / REJECT.

Only after that matrix is complete should Corvus decide what, if anything, still needs to be invented.

Core strategy:

Reuse components.
Innovate composition.
Validate the gap.
