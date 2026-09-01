# Phase 3 Checkpoint — Temporal Representation Contract v0.2

## 1. Context

While designing the Phase 3 Temporal-16 benchmark, we reviewed the temporal semantics established in Phase 2B, Phase 2C, and Phase 2D.

The review exposed an important distinction between two previously unfrozen areas:

1. Corvus had not frozen a complete Allen-style persistent temporal relation ontology.
2. The experimental temporal adapter had not completed canonical boundary encoding for YEAR, MONTH, DAY, and INSTANT.

These two gaps were not treated equivalently.

The first remains intentionally deferred because deterministic reasoning vocabulary does not need to define Corvus's persistent relation ontology.

The second became relevant because Phase 3 benchmark gold depends on stable temporal representation semantics.

---

## 2. Research / Engineering Question

What minimum temporal representation contract must be frozen before Phase 3 can benchmark deterministic temporal relations without silently changing Phase 2 semantics?

---

## 3. Starting Hypothesis

### Established Phase 2 facts

- Temporal semantics distinguish:
  - `EVENT_OCCURRENCE`
  - `STATE_VALIDITY`
  - `RELATIVE_CONSTRAINT`
  - `UNKNOWN`
- Granularity must be preserved independently from computational interval representation.
- Current-state validity uses half-open interval semantics: `[start, end)`.
- Recorded/system time is separate from event/world-validity time.
- Deterministic temporal conclusions may be materialized with lineage.
- Materialization policy is not itself temporal semantic truth.

### Working hypothesis entering this checkpoint

The full Allen relation vocabulary should remain unfrozen, but coarse calendar boundary encoding should be canonicalized before Temporal-16 is frozen.

---

## 4. What We Did

Reviewed:

- `memory/temporal_adapter.py`
- `memory/temporal_policy.py`
- Phase 2C and Phase 2D phase reports
- existing temporal runtime call sites

Confirmed that `memory/temporal_adapter.py` had no external Corvus runtime callers outside its own experimental path.

The adapter was then tightened without changing the Assertion schema or current-world projection.

Implemented:

- canonical half-open YEAR bounds
- canonical half-open MONTH bounds
- canonical half-open DAY bounds
- explicit INSTANT point encoding
- UTC normalization for timezone-aware instants

Added:

- `tests/test_temporal_adapter.py`

---

## 5. Evidence / Results

Canonical examples now produce:

```text
YEAR 2026
→ [2026-01-01T00:00:00Z, 2027-01-01T00:00:00Z)

MONTH 2026-12
→ [2026-12-01T00:00:00Z, 2027-01-01T00:00:00Z)

DAY 2026-09-01
→ [2026-09-01T00:00:00Z, 2026-09-02T00:00:00Z)
```

INSTANT is represented as:

```text
start == end == t
```

This equality is explicitly treated as a temporal POINT sentinel when `granularity=INSTANT`, not as an ordinary empty half-open duration interval.

Timezone-aware instants are normalized to UTC.

Regression test result:

```text
TEMPORAL ADAPTER CONTRACT OK
```

---

## 6. Interpretation

The Phase 2 architecture itself did not require redesign.

The unresolved Allen ontology was a valid scope boundary, not a defect.

The incomplete coarse-granularity boundary encoding was an implementation gap that became relevant only once Phase 3 required stable temporal benchmark gold.

The benchmark therefore exposed a representation contract that was now worth freezing.

---

## 7. Decision

### ADOPT

- half-open calendar interval encoding for YEAR / MONTH / DAY
- preservation of temporal granularity independently from interval bounds
- UTC-normalized point representation for INSTANT
- explicit distinction between point semantics and interval semantics

### KEEP

- existing `temporal_kind` architecture
- existing Assertion Record schema
- existing Temporal Policy
- existing world projection behavior
- separation of temporal reasoning from authority, support, supersession, and provenance

### DEFER

- complete Allen-style Corvus relation ontology
- persistent storage policy for every deterministic temporal relation
- generic late-binding relative-anchor resolver
- full temporal uncertainty taxonomy

### REJECT

- encoding coarse periods with inclusive `23:59:59` endpoints
- inventing artificial duration such as `t + 1 second` for INSTANT
- treating `[t,t)` point encoding as an ordinary duration interval
- allowing benchmark needs to silently redesign Phase 2 semantics

---

## 8. Architecture Impact

No database migration was introduced.

No existing assertions were rewritten.

No changes were made to:

- authority
- support
- supersession
- provenance
- current-world projection

The change is limited to the temporal normalization contract used by the experimental adapter and future Phase 3 temporal benchmark work.

---

## 9. Open Questions

- Which subset of Allen-style relations, if any, should become a formal Corvus reasoning vocabulary?
- Which deterministic temporal conclusions should be materialized versus recomputed?
- How should unresolved relative temporal constraints be represented before their anchors are uniquely resolved?
- Should future point/interval reasoning expose an explicit operand type instead of relying on granularity metadata?

These remain outside the scope of this checkpoint.

---

## 10. Next Step

Use Temporal Representation Contract v0.2 to revise and freeze the Phase 3 Temporal-16 benchmark.

Temporal-16 should treat:

- temporal representation as supporting gold
- deterministic temporal relation as primary temporal gold
- persistence/materialization as out of scope
