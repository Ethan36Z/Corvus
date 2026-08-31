# Phase 2D — Memory Record v0.1

**Status:** READY TO SEAL  
**Date:** 2026-08-31  
**Project:** Corvus — Persistent Personal AI on Consumer Hardware

## 1. Research Question

Phase 2D asked a concrete implementation question:

> Can the semantic and governance rules established in Phases 2A–2C be expressed as a small, runnable, auditable memory record and projection runtime without collapsing evidence, authority, support, time, and version state into one field or one opaque model judgment?

The phase intentionally avoided adding new relation families or retrieval features. Its purpose was to formalize and run the minimum durable memory substrate required by later Corvus phases.

---

## 2. Starting Constraints

Phase 2D inherited the following constraints:

- raw messages remain immutable evidence
- structured assertions are revisable interpretations, not replacements for raw evidence
- provenance and authority are separate axes
- support is a truth-maintenance concern, not a persisted universal truth bit
- historical validity is not rejection
- supersession is version history, not epistemic rejection
- accepted does not mean realized
- future time does not imply planning modality
- current-world projection must be derived from multiple independent conditions
- concrete assertion justification lineage must be non-circular
- mature mechanisms should be adopted where possible rather than reimplemented

---

## 3. Formal Memory Record v0.1

The formal SQLite schema introduced an `assertions` table with:

- `id`
- `subject`
- `predicate`
- `object`
- `provenance`
- `authority`
- `modality`
- `temporal_kind`
- `time_start`
- `time_end`
- `temporal_granularity`
- `recorded_at`
- `superseded_at`
- `superseded_by_assertion_id`

The schema intentionally does **not** persist:

- one universal confidence score
- one universal truth flag
- duplicated `SUPPORTED / UNSUPPORTED` state
- a permanent `ACTIVE / SUPERSEDED` lifecycle enum

`sqlite3` foreign-key enforcement is enabled for Corvus connections.

### 3.1 Typed lineage tables

Two typed junction tables represent machine-readable lineage:

- `assertion_message_basis`
- `assertion_assertion_basis`

A polymorphic `(basis_type, basis_id)` table was rejected because SQLite cannot enforce referential integrity cleanly across heterogeneous target tables.

The typed design preserves foreign-key enforcement while keeping evidence lineage and assertion-derivation lineage explicit.

---

## 4. Assertion Write Boundary

`memory/assertion_store.py` was introduced as the formal write boundary for Memory Record v0.1.

The minimum API now includes:

- `add_assertion(...)`
- `add_message_basis(...)`
- `add_assertion_basis(...)`
- `supersede_assertion(...)`
- `load_unsuperseded_assertions(...)`

The purpose of this layer is not to become a new reasoning engine. It centralizes write-time invariants so later runtime code does not scatter raw SQL writes across the project.

---

## 5. Justification DAG Safety

### 5.1 Discovered failure

The initial SQLite schema prevented direct self-dependency with:

- foreign keys
- uniqueness
- `CHECK (assertion_id != basis_assertion_id)`

but a smoke test showed that indirect cycles were still possible.

Example:

- assertion 2 depends on assertion 1
- assertion 1 depends on assertion 2
- SQLite accepted the cycle

### 5.2 Landscape conclusion

Concrete assertion justification lineage is a proof/justification graph, not recursive rule syntax. Circular self-support is therefore invalid even though recursive rule systems may legitimately contain cycles.

SQLite `CHECK` constraints cannot perform the transitive subquery required for general cycle detection, while a recursive trigger would hide a relatively important semantic invariant inside database machinery.

### 5.3 Adopted solution

Corvus adopted a standard DAG reachability preflight at the assertion write boundary.

Before inserting:

```text
assertion A depends on basis B
```

Corvus asks whether B already reaches A through existing basis edges.

The implementation uses SQLite's built-in recursive CTE rather than a hand-written graph framework.

`UNION` is used in the recursive traversal so the check terminates safely even if previously corrupted cyclic data were encountered.

### 5.4 Smoke tests

Validated:

- `A -> B` allowed
- `B -> A` rejected
- `B -> C` allowed
- `C -> A` rejected

Decision:

> Assertion justification lineage is a DAG. SQLite enforces local relational integrity; the assertion write layer enforces transitive cycle safety; Truth Maintenance handles support.

A recursive SQLite trigger and custom graph-cycle framework were rejected as unnecessary complexity.

---

## 6. End-to-End Evidence and Derivation Chain

The formal API was used to run the first full Memory Record v0.1 write path.

Evidence:

- message 1: `A happened before B.`
- message 2: `B happened before C.`

Assertions:

- assertion 1: `A BEFORE B`, `USER_EXPLICIT + ACCEPTED`
- assertion 2: `B BEFORE C`, `USER_EXPLICIT + ACCEPTED`
- assertion 3: `A BEFORE C`, `DERIVED_DETERMINISTIC + ACCEPTED`

Lineage:

```text
assertion 1 <- message 1
assertion 2 <- message 2
assertion 3 <- assertion 1
assertion 3 <- assertion 2
```

The derived assertion was written through the same formal API and retained a machine-readable basis.

Result:

> raw evidence -> structured assertion -> deterministic derivation -> traceable lineage is runnable end to end.

---

## 7. Supersession and Version Projection

A correction/version smoke test used:

- old assertion: `USER LIVES_IN Beijing`
- new assertion: `USER LIVES_IN Los Angeles`

After `supersede_assertion(old, new)`:

- the Beijing assertion remained in storage
- it received `superseded_at`
- it pointed to the Los Angeles assertion via `superseded_by_assertion_id`
- the Los Angeles assertion remained unsuperseded

A version projection API then returned only assertions where:

```sql
superseded_at IS NULL
```

The test returned only Los Angeles.

Important semantic boundary:

> unsuperseded means current **record version**, not current world truth.

This distinction is retained explicitly.

---

## 8. Temporal Policy v0.1

`memory/temporal_policy.py` introduced a thin deterministic temporal eligibility layer.

The first function answers only:

> Is this assertion temporally eligible for the CURRENT STATE projection?

It does **not** decide:

- authority
- support
- supersession
- provenance

### 8.1 Current policy

For the current-state projection:

- modality must be `ASSERTED`
- temporal kind must be `STATE_VALIDITY`
- current time must be within the assertion's validity interval

Intervals use half-open semantics:

```text
[start, end)
```

Timezone-aware timestamps are required.

### 8.2 Smoke test

Validated at a fixed UTC `now`:

- current state -> `True`
- historical state -> `False`
- future state -> `False`
- future plan -> `False`

This makes the Phase 2C rule executable:

> A future plan does not become realized merely because it has a timestamp, and a historical state does not remain part of the current state merely because it was once true.

---

## 9. World Projection v0.1

`memory/world_projection.py` composes independent layers rather than introducing a universal `is_true()` function.

Current-world eligibility requires:

1. assertion is unsuperseded
2. `authority = ACCEPTED`
3. external support checker reports valid support
4. Temporal Policy reports current-state temporal eligibility

Conceptually:

```text
Version Projection
+ Authority
+ Truth-Maintenance Support
+ Temporal Policy
= Current World Projection
```

The support checker is deliberately injected from outside the projection layer. The world projection does not compute support itself.

### 9.1 Combined smoke test

Six assertion cases were inserted together:

1. current state
2. historical state
3. future plan
4. superseded state
5. rejected assertion
6. unsupported assertion

Expected result:

- only the current, accepted, supported, unsuperseded state survives

Observed result:

```text
===== CURRENT WORLD =====
1 CURRENT
PASS: only CURRENT survived
```

This completed the Memory Record v0.1 runtime core loop.

---

## 10. Fresh Landscape Check — 2026-08-31

Phase 2D was compared again with current research and implementations before sealing.

### 10.1 APEX-MEM — ACL 2026

APEX-MEM combines:

- temporally grounded structured memory
- append-only history
- query-time resolution of conflicting and evolving information

Its ACL 2026 results further support preserving full temporal evolution rather than destructively consolidating old values.

Reference:

- https://aclanthology.org/2026.acl-long.749/

Impact on Corvus:

- **ADOPT / VALIDATE** append-only historical preservation
- **VALIDATE** query/projection-time resolution of evolving memory
- no architectural reversal required

### 10.2 Graphiti / Zep

Graphiti continues to use temporal knowledge graphs with separate world-validity and ingestion/history semantics, fact invalidation, provenance episodes, and hybrid retrieval.

References:

- https://help.getzep.com/graphiti/getting-started/overview
- https://www.getzep.com/ai-agents/temporal-knowledge-graph/

Impact on Corvus:

- **VALIDATE** bitemporal-style separation
- **VALIDATE** non-destructive invalidation/supersession
- do not adopt Graphiti wholesale yet because Corvus currently needs a smaller local substrate and already has Phase 1 retrieval infrastructure

### 10.3 MemIR — 2026

MemIR separates raw evidence, retrieval cues, and truth-bearing claims and restricts factual authorization to supported claim atoms.

Reference:

- https://arxiv.org/abs/2605.25869

Impact on Corvus:

- **STRONGLY VALIDATE** raw evidence vs. assertion separation
- **VALIDATE** structural factual authorization
- retain Corvus's explicit authority axis rather than treating every extracted/retrieved representation as fact

### 10.4 AuthMem-Bench — August 2026

`When Memory Becomes Authority: Benchmarking Authority Collapse at the Memory Consolidation Boundary` isolates a failure mode in which memory consolidation preserves a claim while erasing the source constraints controlling how that claim may be used.

Across the paper's evaluated configurations, authority collapse was widespread; persisting authority labels substantially reduced unauthorized downstream behavior.

Reference:

- https://arxiv.org/abs/2608.01679

Impact on Corvus:

- **STRONGLY VALIDATE** keeping `authority` independent from provenance, modality, support, and retrieval score
- do not collapse authority into confidence
- retain candidate assertions without granting them factual write authority

### 10.5 Supersede — June 2026

`Supersede: Diagnosing and Training the Memory-Update Gap in LLM Agents` treats use of the current value of changing facts as a distinct unresolved memory problem.

The reported gap persists even with stronger models and larger memory budgets, suggesting that current-vs-stale state maintenance should not be left to model strength alone.

Reference:

- https://arxiv.org/abs/2606.27472

Impact on Corvus:

- **STRONGLY VALIDATE** explicit supersession/version machinery
- **VALIDATE** separating stale/current-version selection from semantic retrieval
- **DEFER** learned supersession detection to the later relation/gating phase; once a correction is detected, the version substrate should remain deterministic and auditable

### 10.6 Truth Maintenance and current implementations

Recent agent-memory work continues to rediscover provenance, dependency support, and cascading invalidation concerns already addressed by classical Truth Maintenance Systems.

Corvus therefore retains the Phase 2C decision:

- support is computed from justification structure
- independent support paths matter
- support is not authority
- concrete lineage must not self-support circularly

Corvus does not introduce a new custom truth-maintenance theory in Phase 2D.

### 10.7 Emerging append-only implementations

Recent implementations such as Mneme and Weavatrix Memory independently emphasize:

- append-only claim history
- supersession rather than destructive overwrite
- bitemporal validity
- provenance and traceability
- deterministic or replayable derivation paths

References:

- https://github.com/BrettNye/Mneme
- https://github.com/Weavatrix/weavatrix-memory

These are not adopted as dependencies at this stage, but they are useful convergence evidence.

### 10.8 Proof-of-Execution Memory — August 2026

Recent work on Proof-of-Execution Memory shows that when an agent's memory is used to authorize real actions, a statement that an action occurred should not itself be sufficient proof that the action executed.

Reference:

- https://arxiv.org/abs/2608.16032

Impact on Corvus:

- **DEFER**, because Phase 2D models personal world memory rather than privileged action execution
- retain as a future design constraint if Corvus later gains autonomous tools: trusted execution evidence should remain distinct from ordinary remembered claims

---

## 11. Adopt / Improve / Defer / Abandon

### ADOPT / KEEP

- immutable raw evidence
- structured assertions separate from evidence
- typed message and assertion lineage
- append-only / non-destructive history
- explicit supersession links
- bitemporal-style world-validity and record-history separation
- independent provenance and authority
- Truth Maintenance support as a separate concern
- justification DAG invariant
- standard recursive reachability for cycle prevention
- half-open temporal validity intervals
- thin deterministic Temporal Policy
- compositional World Projection

### IMPROVE LATER, NOT IN 2D

- connect `support_checker` to a durable TMS adapter rather than a smoke-test callback
- add richer point-in-time and historical projections
- formalize modality/factuality taxonomy against mature linguistic schemes
- add entity normalization/canonicalization before large-scale assertion growth
- add explicit projection interfaces rather than relying on tuple positions once the record API stabilizes

### DEFER

- learned correction/supersession detection
- relation gate
- small relation model
- confidence calibration
- causal candidate generation
- temporal activation / decay / "time as memory currency"
- graph database migration
- cryptographic mutation authorization
- proof-of-execution ledger for autonomous actions

### ABANDON / DO NOT ADD

- universal scalar truth/confidence field
- destructive overwrite of corrected facts
- `REJECTED` as a synonym for historical or superseded
- persisted duplicated support bit
- monolithic `is_true()` logic
- recursive SQLite cycle trigger
- custom graph-cycle theory
- separate persistent table for every relation family
- treating future timestamp as automatic evidence of planning or realization

---

## 12. Corvus-Specific Working Hypotheses Retained

Phase 2D does not claim novelty for append-only memory, temporal graphs, Truth Maintenance, provenance, supersession, or DAG justification.

The Corvus-specific research direction remains in how these mature ideas are combined under severe consumer-hardware constraints and later connected to adaptive candidate generation and gated relation interpretation.

Working hypotheses retained for later phases:

- experience should replace repeated computation rather than justify more computation
- stable interpretations should be cheaply retrievable after they have been reasoned about once
- retrieval candidates should come from multiple neighborhoods: semantic, temporal, entity, and relation-path structure
- temporal proximity may affect candidate activation but must not become truth confidence
- authority gating may be more important than simply increasing relation-model capability
- archive size may grow while active context remains bounded

These remain hypotheses until later benchmarks test them.

---

## 13. Final State

Phase 2D has produced a runnable Memory Record v0.1 substrate with:

- formal assertion storage
- immutable evidence linkage
- machine-readable derivation lineage
- DAG-safe basis writes
- correction/supersession history
- current-version projection
- deterministic temporal eligibility
- compositional current-world projection
- explicit boundary for external Truth Maintenance support

The final combined smoke test confirms that current, historical, planned, superseded, rejected, and unsupported assertions are not collapsed into one lifecycle or truth state.

The Fresh Landscape Check found substantial convergence with current 2026 research rather than evidence that the design should be replaced.

**Phase conclusion:** retain the current Memory Record v0.1 architecture and stop adding Phase 2D features.

---

## 14. Open Questions for Later Phases

Not blocking Phase 2D closure:

- Which mature modality/factuality taxonomy should Corvus adopt?
- How should the relation gate determine when deterministic rules are sufficient vs. when a model is needed?
- Which small local model best performs relation interpretation under Corvus hardware constraints?
- How should entity canonicalization work without excessive model calls?
- How should the LTMS semantic-fit candidate be wrapped or replaced for durable runtime use?
- What projection types beyond current state are needed first: historical-at-time, planned future, hypothesis view, or explanation/provenance view?
- How should stable learned interpretations interact with Phase 1 hybrid retrieval?
- When should Corvus materialize a derived assertion versus recompute it cheaply?

---

## 15. Seal Decision

Phase 2D should be sealed after the local implementation changes are reviewed, committed, and pushed.

No additional Phase 2D feature work is justified by the current landscape check.
