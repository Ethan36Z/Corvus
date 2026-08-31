# Phase 2C — Relationship and Authority

**Status:** SEALED  
**Date:** 2026-08-31  
**Project:** Corvus — Persistent Personal AI on Consumer Hardware

## 1. Research Question

Phase 2C asked a narrow but foundational question:

> When Corvus proposes, derives, stores, revises, or rejects a relationship, what gives that relationship the right to affect the system's working model of the user and the world?

The phase began after Phase 2B established a temporal layer with explicit time normalization, granularity preservation, interval representation, relative temporal constraints, and Allen-style deterministic temporal reasoning.

The focus of 2C was therefore not to invent more relation labels. It was to define the governance and lineage rules around any relation or structured assertion.

The phase specifically investigated:

- raw evidence vs. structured interpretation
- provenance vs. authorization
- correction vs. temporal evolution
- model inference vs. user-explicit evidence
- deterministic derivation and dependency lineage
- support maintenance after evidence changes
- multiple independent justifications for the same conclusion
- event occurrence vs. state validity
- modality and future plans
- temporal policy for world-state projection
- whether temporal, causal, correction, and other relations should share one storage model

---

## 2. Starting Hypotheses

The initial working model was intentionally small:

- Raw user messages should remain immutable evidence.
- Relationships should be allowed to exist as candidates before they are authorized.
- A relation should have a provenance describing where it came from.
- A relation should have an authority state describing whether Corvus may use it.
- A model-inferred relationship must not automatically become memory truth.
- Historical evidence should not be deleted when a newer interpretation appears.

The first authority vocabulary was:

- `CANDIDATE`
- `ACCEPTED`
- `REJECTED`

This vocabulary was treated as a hypothesis, not as a permanent ontology.

---

## 3. Experiments and Evidence

### 3.1 Correction lifecycle

Test case:

- "I moved to LA in 2025."
- "Actually, I moved to LA in 2024."

Observed requirement:

- The original message remains immutable evidence.
- The old world assertion is no longer used as the current interpretation.
- The corrected assertion becomes authoritative.

Initial state:

- `move_to_LA = 2025` → `REJECTED`
- `move_to_LA = 2024` → `ACCEPTED`

This confirmed that rejection applies to a structured assertion, not to the existence of the original evidence.

### 3.2 Temporal evolution is not correction

Test case:

- "I worked at Google in 2023."
- "I work at Apple now."

Both assertions must remain accepted because both may be true at different times.

Result:

- `WORKS_AT Google`, valid in 2023 → `ACCEPTED`
- `WORKS_AT Apple`, valid now → `ACCEPTED`

The current projection selects Apple without rejecting the historical Google assertion.

Conclusion:

> Authority and temporal validity are independent axes.

### 3.3 Model-inferred relations must remain candidates

Test case:

- "I moved to LA."
- "I became much happier afterward."

A model may propose:

- `MOVE_TO_LA POSSIBLE_CAUSE BECAME_HAPPIER`

but the system must not treat this as user-provided truth.

Result:

- provenance: `MODEL_INFERRED`
- authority: `CANDIDATE`
- no authorized world relation is produced

Conclusion:

> Corvus may have hypotheses without granting those hypotheses write authority over the world model.

### 3.4 User confirmation should not rewrite inference history

If the user later says:

- "Yes, moving to LA really was the reason I became happier."

then the model's earlier `POSSIBLE_CAUSE` candidate should not be rewritten in place as `USER_EXPLICIT`.

The smoke test exposed an important distinction:

- the old model candidate was not disproven
- it was replaced by stronger, more precise user-explicit evidence

This led to separating epistemic authority from record/version lifecycle.

### 3.5 True rejection

Test case:

- model proposes `POSSIBLE_CAUSE`
- user explicitly says the two events had nothing to do with one another

Result:

- the interpretation becomes `REJECTED`
- the rejection basis is retained
- it is excluded from the authorized world model

Conclusion:

> `REJECTED` should be reserved for cases with positive grounds not to adopt an assertion. Mere loss of support or replacement by a better assertion is not the same as rejection.

### 3.6 Deterministic derivation can be accepted

Test case:

- `A BEFORE B`
- `B BEFORE C`
- therefore `A BEFORE C`

Result:

- base relations: `USER_EXPLICIT + ACCEPTED`
- derived relation: `DERIVED_DETERMINISTIC + ACCEPTED`
- derivation basis retained

Conclusion:

> `ACCEPTED` does not mean "the user literally said this." A deterministic result may be authorized if its premises and derivation are traceable.

### 3.7 Derived authority must depend on its basis

If a premise used to derive `A BEFORE C` is later corrected, the derived assertion must not remain accepted automatically.

A first manual dependency test used machine-readable `basis_ids` and successfully downgraded the dependent derived assertion when a premise lost authorization.

This demonstrated the requirement but also showed that a hand-written recursive invalidation mechanism would quickly become a reinvention of a known problem.

### 3.8 Truth Maintenance System evaluation

Corvus evaluated the Python `ltms` implementation as a semantic-fit candidate for dependency support maintenance.

Three tests were run.

#### Test A — premise retraction

- `rain` supports `wet`
- retract `rain`
- both become unknown/unsupported as expected

#### Test B — recursive dependency invalidation

- `R1 + R2 -> R3`
- `R3 -> R4`
- retract `R2`
- `R3` and `R4` automatically lose support

#### Test C — multiple independent justifications

- basis #1 supports `R3`
- basis #2 independently supports `R3`
- retract basis #1 → `R3` remains supported
- retract basis #2 as well → `R3` becomes unsupported

This is a critical result because real long-term memory can contain multiple independent evidence chains for the same conclusion.

Conclusion:

> Dependency support is a Truth Maintenance problem and should not be reimplemented as ad hoc recursive `if` statements.

### 3.9 Unified Assertion Record smoke test

A provisional shared structure successfully represented:

- user-explicit facts
- model-inferred candidates
- deterministic temporal relations

using the same high-level fields:

- subject
- predicate
- object
- provenance
- authority
- temporal scope
- basis / lineage

This supported the hypothesis that Corvus should not create a separate persistent schema for every relation family.

### 3.10 Event occurrence vs. state validity

The following are not temporally equivalent even if both mention the same year:

- "I moved to LA in 2024."
- "I lived in LA in 2024."

The first is an event occurrence. The second is a state validity claim.

The phase therefore introduced a provisional `temporal_kind` distinction:

- `EVENT_OCCURRENCE`
- `STATE_VALIDITY`
- `RELATIVE_CONSTRAINT`
- `UNKNOWN`

The same computational interval can be used while preserving different temporal semantics.

### 3.11 Modality and future plans

Test case:

- "I plan to move to Japan next year."

The plan itself may be accepted as a user-explicit assertion, but it must not appear in the realized current-world projection.

Result:

- authority: `ACCEPTED`
- modality: `PLANNED`
- temporal kind: `EVENT_OCCURRENCE`
- future interval retained
- excluded from realized current world

Conclusion:

> Accepted does not mean realized.

### 3.12 Temporal Policy / Temporal Laws smoke test

A thin deterministic policy layer was tested with four cases:

- future plan → excluded from realized current world
- expired plan → still not automatically realized
- current valid state → included
- historical state → excluded from current projection without being rejected

This supported a useful separation:

- Assertion Record describes what is stored.
- Authority describes whether Corvus may adopt it.
- Modality describes what kind of claim it is.
- Temporal Policy describes what projection the claim is currently eligible to enter.

---

## 4. Technical Results

Phase 2C established the following technical principles.

### 4.1 Immutable evidence and revisable world assertions

Raw evidence is preserved independently from structured assertions.

A user can be wrong, change their mind, or later correct a statement. The immutable fact is that the evidence was observed or stated at a particular record time; the world assertion derived from it may later be revised, rejected, superseded, or reinterpreted.

### 4.2 Provenance is not authority

`provenance` answers:

> Where did this assertion come from?

Examples:

- `USER_EXPLICIT`
- `DERIVED_DETERMINISTIC`
- `MODEL_INFERRED`

`authority` answers:

> Is Corvus currently allowed to use this assertion in an authoritative world projection?

Working states:

- `CANDIDATE`
- `ACCEPTED`
- `REJECTED`

These must not be collapsed into one field.

### 4.3 Support is not authority

Truth-maintenance support answers:

> Does at least one valid justification currently support this assertion?

A supported model hypothesis may still be only a candidate. Conversely, loss of one justification does not necessarily invalidate a conclusion if another independent justification remains.

Therefore:

- support is maintained by a justification network / TMS
- authority remains a separate Corvus governance decision

### 4.4 Rejection is not supersession

A relation can be replaced by a better or more specific assertion without being proven false.

Therefore `REJECTED` should not be overloaded to mean "old version."

The phase initially introduced an `ACTIVE / SUPERSEDED` lifecycle enum, then revised that design during the final audit.

The preferred storage model is now system-time history:

- `recorded_at`
- `superseded_at`
- `superseded_by_assertion_id`

`ACTIVE` and `SUPERSEDED` should be derived projections rather than permanent enum truth.

### 4.5 Temporal validity is not authority

A historical assertion can remain accepted while no longer being current.

Currentness must be determined from temporal scope, not from authority state.

### 4.6 Deterministic reasoning should be reusable but retractable

Corvus may materialize deterministic conclusions to avoid repeated computation, but those conclusions must retain machine-readable justification lineage so their support can be updated when premises change.

### 4.7 Future time does not determine modality

A future time does not automatically mean `PLANNED`.

A future claim may be:

- planned
- scheduled
- predicted
- desired
- hypothetical
- otherwise modal

Temporal Policy may prevent a future occurrence from entering a realized projection, but it must not invent modality from clock position alone.

---

## 5. Provisional Assertion Record v0.1

Phase 2C converged on the following conceptual record for Phase 2D formalization.

```text
Assertion
├── id
├── subject
├── predicate
├── object
│
├── provenance
├── authority
│
├── modality                 # taxonomy remains provisional
│
├── temporal_kind
│     EVENT_OCCURRENCE
│     STATE_VALIDITY
│     RELATIVE_CONSTRAINT
│     UNKNOWN
│
├── time_start
├── time_end
├── granularity
│
├── recorded_at
├── superseded_at
├── superseded_by_assertion_id
│
└── basis / justification references
```

Notably absent as persisted single-value fields:

- a universal `confidence` score
- a duplicated `SUPPORTED / UNSUPPORTED` database field
- a permanent `ACTIVE / SUPERSEDED` lifecycle enum

Support should be computed from the justification network. Lifecycle/current-version state should be projected from system-time history.

---

## 6. Fresh Landscape Check

Phase 2C was compared against current and established work to avoid reinventing solved ideas.

### 6.1 APEX-MEM (ACL 2026)

APEX-MEM uses a temporally grounded property graph, append-only storage, and query-time resolution of conflicting or evolving information. This strongly supports Corvus's non-destructive history and temporalized-world-model direction.

Relevant overlap:

- append-only history
- temporally grounded structured memory
- query-time resolution of evolving facts
- bounded retrieval rather than naive full-history prompting

Reference: https://aclanthology.org/2026.acl-long.749/

### 6.2 Graphiti / Zep

Graphiti models facts as graph edges with temporal metadata such as `valid_at`, `invalid_at`, `expired_at`, and reference time. It also performs conflict/invalidation handling rather than simply overwriting older edges.

Relevant overlap:

- temporalized relations
- world-validity time separated from system/record history
- graph-compatible structured facts
- invalidation instead of destructive rewriting

References:

- https://github.com/getzep/graphiti
- https://github.com/getzep/graphiti/blob/main/graphiti_core/edges.py

### 6.3 MemIR (2026)

MemIR explicitly addresses provenance-role collapse in long-term agents by separating raw evidence, retrieval cues, and truth-bearing claims. It restricts factual authorization to supported claim atoms.

This is strong external support for Corvus's evidence/assertion separation and for treating factual authorization as a structural concern rather than assuming every retrieved or generated representation is truth.

Reference: https://arxiv.org/abs/2605.25869

### 6.4 TimeML / TimeBank

TimeML provides mature distinctions among event classes, state/event instances, tense, aspect, polarity, modality, and temporal links.

Corvus should therefore not invent a closed modality taxonomy prematurely.

Relevant lessons:

- event occurrence and state are distinct temporal semantics
- future tense is not equivalent to one modality
- polarity and modality are independent dimensions
- temporal signals and event instances should not be conflated

References:

- https://timeml.github.io/site/publications/timeMLdocs/timeml_1.1b.htm
- https://timeml.github.io/site/timebank/documentation-1.2.html

### 6.5 FactBank

FactBank and related factuality work reinforce the idea that factuality can depend on source and perspective rather than being a single intrinsic numeric truth value.

Corvus should therefore avoid prematurely compressing model certainty, evidence strength, source authority, temporal certainty, and world truth into one scalar confidence score.

Reference: https://catalog.ldc.upenn.edu/LDC2009T23

### 6.6 Truth Maintenance Systems

The dependency problem discovered during Phase 2C is a classic Truth Maintenance problem.

The evaluated Python `ltms` implementation correctly handled:

- premise retraction
- recursive downstream loss of support
- alternative independent justifications

Corvus should adopt Truth Maintenance concepts rather than build a bespoke recursive invalidation engine.

Implementation evaluated:

- https://github.com/pisanuw/ltms

The implementation is currently treated as a semantic-fit candidate, not yet as an irreversible production dependency.

### 6.7 W3C PROV-O

PROV-O already defines mature provenance concepts including derivation, revision, generation, and invalidation.

Corvus should use these concepts as reference semantics for lineage rather than inventing a new provenance theory.

Reference: https://www.w3.org/TR/prov-o/

---

## 7. Adopt / Improve / Defer / Abandon

### ADOPT

- append-only / non-destructive memory history
- raw evidence separated from structured assertions
- temporalized world relations
- bitemporal-style separation between world-validity time and system/record time
- Truth Maintenance concepts for dependency support
- multiple independent justifications
- deterministic derivation with machine-readable lineage
- mature temporal semantics as references rather than inventing a new temporal ontology
- standard provenance/derivation concepts as conceptual references

### IMPROVE

- replace the stored `lifecycle` enum with system-time history (`superseded_at`, `superseded_by`)
- rename provisional temporal semantics to the clearer `temporal_kind`
- keep Corvus-specific authority as a distinct governance axis
- use a thin Temporal Policy layer for hard projection invariants
- preserve machine-readable justification references rather than human-only explanation strings

### DEFER

- final modality / factuality taxonomy
- small relation model selection
- confidence calibration / conformal prediction
- relation-gate implementation
- temporal activation and decay
- the "time as memory currency" hypothesis
- long-range causal candidate generation
- final choice of Truth Maintenance implementation

### ABANDON

- one database schema per relation family
- one universal confidence score
- treating `support`, `authority`, lifecycle, and temporal validity as one status
- using `REJECTED` to mean merely old or superseded
- rewriting model inference history when stronger evidence arrives
- treating historical relations as rejected simply because they are no longer current
- future time automatically implying `PLAN`
- an expired plan automatically becoming realized
- custom recursive dependency invalidation when a Truth Maintenance system can solve it

---

## 8. Corvus-Specific / Original Hypotheses

The following are retained as Corvus-specific hypotheses, not claimed as established novel contributions.

### 8.1 Relation authorization should be separate from support

Truth Maintenance answers whether an assertion currently has valid justification.

Corvus additionally needs a governance question:

> Even if this assertion has support, is it authorized to affect the authoritative world model?

This motivates keeping `authority` separate from TMS support.

### 8.2 A relation gate may become the central reliability mechanism

The system may ultimately need a layered gate:

```text
hard deterministic evidence
        ↓
small relation intelligence
        ↓
abstain / escalate
        ↓
large-model interpretation
        ↓
authorization policy
```

The gate must distinguish candidate generation from relation authorization.

### 8.3 Temporal Policy as a thin projection layer

Corvus may benefit from a small set of hard temporal invariants that apply across all relation types, for example:

- future occurrence cannot enter realized-current projection
- time passing does not transform a plan into a realized event
- realization requires new evidence
- a historical state is not rejected merely because it ended
- a current state requires the current time to fall inside its validity interval

This policy should remain small and deterministic rather than becoming a separate temporal ontology.

### 8.4 Time as a common memory coordinate

A broader hypothesis remains open: time may serve as a common coordinate for retrieval, candidate generation, relation discovery, state projection, and activation.

This does **not** mean time proves relationships or causality.

Temporal proximity should be treated as a prior for what is worth checking, not as evidence that a relationship is true.

### 8.5 Reason once, retrieve cheaply thereafter

Stable facts should not require repeated model reasoning at every recall.

Where deterministic or strongly authorized structure exists, Corvus should reuse that structure and reserve expensive intelligence for unresolved cases.

---

## 9. Rejected Ideas and Why

### One scalar confidence value

Rejected because it collapses distinct quantities:

- classifier confidence
- evidence strength
- source authority
- temporal certainty
- support status
- factual authorization

### `REJECTED` as a generic inactive state

Rejected because an assertion may be unsupported, historical, or superseded without being false or explicitly rejected.

### Lifecycle as the same thing as authority

Rejected because "is this still the representative version?" and "may Corvus adopt this?" are independent questions.

### Currentness stored as truth

Rejected because current state should be a projection over temporal history, not a destructive update of that history.

### Plans becoming realized when their date passes

Rejected because clock time cannot supply missing realization evidence.

### Hand-written recursive dependency invalidation

Rejected after LTMS tests showed that Truth Maintenance already handles recursive dependency retraction and alternative justifications.

---

## 10. Final Architecture at Phase Exit

Conceptually, the memory path now looks like:

```text
IMMUTABLE RAW EVIDENCE
        │
        ▼
STRUCTURED ASSERTIONS
        │
        ├── provenance
        ├── authority
        ├── modality
        ├── temporal kind / scope
        ├── record/system time
        └── justification references
                │
                ▼
        TRUTH MAINTENANCE
        dynamic support state
                │
                ▼
        TEMPORAL POLICY
        hard projection constraints
                │
                ▼
     CURRENT / HISTORICAL /
     PLANNED / OTHER VIEWS
```

This model remains compatible with Phase 1 hybrid retrieval and Phase 2B temporal reasoning.

Retrieval answers which memories may matter. The semantic/governance layer decides what those memories mean, what supports them, and what they are currently allowed to influence.

---

## 11. Open Questions

The following are intentionally unresolved and should not be solved inside Phase 2C:

- exact SQLite schema for Assertion Record v0.1
- final entity/reference representation for subject and object
- whether assertions should reference messages, assertions, or a generalized evidence table through one junction structure
- final modality/factuality vocabulary
- how LTMS state should be synchronized or reconstructed from persistent storage
- relation-gate architecture and calibration
- specialized small model vs. NLI/cross-encoder vs. 9B escalation
- temporal activation / salience / decay
- relation candidate generation from temporal, semantic, entity, and graph neighborhoods
- how much deterministic derivation should be materialized vs. recomputed

---

## 12. Decision

**Phase 2C is formally complete.**

The phase answered its research question with working smoke tests, a Truth Maintenance semantic-fit evaluation, a Fresh Landscape Check, and a concrete set of Adopt / Improve / Defer / Abandon decisions.

No additional relationship types or policy rules should be added to Phase 2C unless later evidence reveals a missing requirement.

---

## 13. Next Phase — Phase 2D: Memory Record v0.1 / Core Formalization

Phase 2D will convert the validated semantics into an actual Corvus persistent data model.

Primary goals:

1. define the minimum durable Assertion Record schema
2. preserve raw evidence separately
3. implement machine-readable justification references
4. encode bitemporal-style world and system time without fake precision
5. represent authority without duplicating support state
6. integrate current temporal parsing and interval semantics into persisted assertions
7. provide a runnable inspector / projection checkpoint
8. perform another Fresh Landscape Check before sealing 2D

A successful Phase 2D should produce the first stable memory-core representation suitable for the planned **Corvus Memory Playground v0.1**.

---

## 14. Phase Report Discipline

Beginning with Phase 2C, a Corvus phase is not considered formally sealed until it has a version-controlled phase report covering:

- research question
- starting hypotheses
- experiments and evidence
- technical results
- architecture decisions
- Fresh Landscape Check
- Adopt / Improve / Defer / Abandon decisions
- Corvus-specific hypotheses
- rejected ideas
- final state
- open questions
- next phase

The purpose is to make Corvus's development history reusable evidence rather than disposable conversation context.
