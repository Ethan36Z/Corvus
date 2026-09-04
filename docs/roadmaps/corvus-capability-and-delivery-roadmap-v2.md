# Corvus Capability & Delivery Roadmap v2

**Project:** Corvus — Persistent Personal AI on Consumer Hardware  
**Baseline commit reviewed:** `b2b2f19 Complete Stage A0 retrieval productionization`  
**Status of this roadmap:** Working architecture and delivery plan

---

## 1. Why This Roadmap Exists

Corvus originally used a Phase-oriented research roadmap (`P0` through later `P` stages) to describe the capabilities the system should eventually acquire.

That roadmap remains useful.

What changed is the development philosophy.

The project should **not** require every research phase to be fully designed and implemented before a usable Corvus exists. Doing so creates a high-cost research waterfall:

```text
research question
→ custom mechanism
→ benchmark
→ reviewer
→ meta-validation
→ more mechanisms
→ eventual integration
```

For an individual project on fixed consumer hardware, that path can produce a sophisticated research architecture while postponing the existence of a usable product.

The revised principle is:

> **Always maintain a working Corvus. Research should upgrade the product, not postpone its existence.**

Or:

```text
Working Corvus
→ use it
→ measure failures
→ check current mature technology
→ add the smallest justified capability
→ validate
→ Working Corvus+
→ repeat
```

The original `P` roadmap therefore becomes a **long-term capability map**.

The `Stage` roadmap becomes the **delivery/evolution plan**.

---

## 2. Evidence Reviewed

This rebaseline was checked against the current committed repository and project records at `b2b2f19`.

Reviewed records include:

- `docs/project-logs/2026-09-03-p3-hybrid-memory-architecture-and-plan.md`
- `docs/project-logs/2026-09-02-p3-existing-first-resource-aware-strategy.md`
- `docs/project-logs/2026-09-02-p3-benchmark-v0.1-freeze.md`
- `docs/phase-reports/phase-2d-memory-record-v0.1.md`
- `docs/phase-reports/phase-a0-retrieval-productionization.md`
- `app/chat_rag.py`
- `memory/hybrid_search.py`

### Evidence scope

This review covers the committed `main` repository.

Local-only untracked files such as the current Playground and reviewer artifacts are **not** treated as audited evidence by this roadmap until they are separately inspected.

---

## 3. What the Existing Records Already Say

The revised Phase 3 architecture record already established three delivery stages:

```text
Stage A — Mature Persistent-Memory Baseline
Stage B — Phase 2 Structured-Memory Integration
Stage C — Measure Before Adding Phase 3 Complexity
```

It also explicitly states:

- mature baseline first;
- Phase 2 Materialized Memory second;
- Relation Gate is not automatically mandatory;
- a small background model is not automatically mandatory;
- expensive intelligence should be delayed when possible;
- Evidence Recall must remain usable independently from advanced structured memory.

The Phase 3 resource-aware research record independently established:

```text
Reuse components.
Innovate composition.
Validate the gap.
```

and rejected recursive benchmark / reviewer / meta-reviewer growth as the default research workflow.

Stage A0 then demonstrated that this development philosophy works in practice.

Instead of discarding P1 research, A0:

- re-audited engineering maturity;
- kept mature BM25 / FTS5 and RRF;
- selected a mature persistent dense backend;
- selected and pinned a validated embedding model;
- added incremental indexing and recovery;
- measured exact retrieval at 1k / 10k / 100k scale;
- tested ANN only after exact latency showed a real gap;
- deferred ANN when recall evidence was insufficient.

This is exactly the rolling-development pattern this roadmap adopts.

---

## 4. Current Architectural Baseline

Corvus has three top-level memory concepts:

```text
Evidence Log
→ Working Context
→ Materialized Memory
```

### Evidence Log

Canonical source of truth.

Current canonical implementation:

```text
SQLite messages
```

Raw user / assistant / tool / world evidence is preserved first.

### Working Context

Small, fast, rebuildable active context composed from:

- recent conversation;
- current task;
- retrieved historical evidence;
- useful structured memory.

### Materialized Memory

Derived and rebuildable interpretation:

- assertions;
- entities;
- relations;
- temporal validity;
- provenance;
- authority;
- state;
- Current World Projection.

Materialized Memory must never silently replace canonical evidence.

---

## 5. Two Recall Paths

### Evidence Recall

Answers:

> What did the user actually say or what was directly observed?

Current A0 substrate:

```text
SQLite Evidence Log
        |
   +----+----+
   |         |
 FTS5      GTE
 BM25     LanceDB
   |       exact
   +----+----+
        |
       RRF
        |
SQLite canonical hydration
        |
Working Context
```

### Knowledge Recall

Answers:

> What does Corvus currently understand from the evidence?

Existing Phase 2 substrate includes:

- Assertion Record;
- provenance;
- authority;
- modality;
- temporal validity;
- typed lineage;
- supersession;
- Temporal Policy;
- Current World Projection.

Knowledge Recall is derived, revisable, and rebuildable.

---

## 6. Capability Roadmap — Long-Term Goals

The original `P` series remains the long-term capability map.

It does **not** prescribe a rigid implementation order.

```text
P0 — Hardware / Model Runtime
P1 — Retrieval Infrastructure
P2 — Memory Semantics
     P2A What Is Memory?
     P2B Temporal Memory
     P2C Relationship & Authority
     P2D Memory Record
P3 — Relation Intelligence
P4 — Hierarchical / Structured Long-Term Memory
P5 — Background Consolidation
P6 — Adaptive Recall / Memory Economy
P7 — Personal Model / Personalization
P8 — Multi-Agent
```

These describe desired capability territory.

They may be:

- implemented in a different order;
- combined;
- skipped temporarily;
- reinterpreted using newer technology;
- satisfied partly by mature external components.

### Rule

> **Freeze the goal, not the implementation.**

When Corvus reaches a later capability, perform a fresh landscape check instead of blindly implementing an architecture chosen months earlier.

---

# 7. Delivery / Evolution Roadmap

This is the actual implementation plan.

Every Stage must leave Corvus in a usable state.

A later Stage upgrades the previous working system rather than delaying its existence.

---

## Stage A — Usable Persistent Companion

### Goal

Produce the first Corvus that is worth using as a real persistent conversational companion.

### A0 — Retrieval Productionization

**Status:** ✅ SEALED

Evidence Recall maturity:

```text
VALIDATED_PROTOTYPE
→ PRODUCTION_CANDIDATE_FOUNDATION
```

Delivered:

- SQLite canonical Evidence Log;
- SQLite FTS5 / BM25;
- pinned GTE multilingual embeddings;
- LanceDB persistent dense index;
- exact vector retrieval;
- RRF hybrid fusion;
- SQLite canonical hydration;
- targeted incremental indexing;
- restart recovery;
- explicit metadata filtering;
- bounded scale validation.

### A1 — Persistent Conversation Loop

**Status:** 🟡 NEXT

Current repo evidence shows why this is necessary:

`memory/hybrid_search.py` already uses the A0 persistent dense path.

But `app/chat_rag.py` still:

- imports the old `memory.semantic_search`;
- keeps current-session messages in an in-memory Python list;
- does not persist the conversational loop;
- ends with `Session ended. Nothing was saved.`

Therefore A0 completed the retrieval substrate but did not yet complete the user-facing persistent companion.

### A1 minimum runtime contract

```text
user message
→ SQLite commit first
→ recent-context update
→ targeted dense indexing / recovery path
→ A0 hybrid Evidence Recall
→ Working Context
→ local 9B
→ assistant reply
→ SQLite commit
→ targeted index update
```

Rules:

- canonical SQLite persistence must succeed before optional dense intelligence;
- failure of dense indexing must not lose the conversation;
- no full-corpus re-embedding;
- no active production dependency on the old `semantic_search.py`;
- recent context stays bounded;
- historical retrieval remains traceable to message IDs.

### A1 exit test

At minimum:

1. Start session A.
2. Tell Corvus a fact not present elsewhere.
3. Persist both sides of the conversation.
4. Exit the process.
5. Restart in a fresh process/session.
6. Ask a paraphrased question requiring the old fact.
7. A0 hybrid retrieval finds the canonical historical evidence.
8. The 9B answers using it.
9. Retrieved evidence IDs are inspectable.
10. Simulated dense-index failure does not remove the canonical SQLite record.

### A2 — Daily-Use Baseline

After A1 works:

- connect the existing Playground / minimal UI only after auditing its local state;
- add simple operational visibility;
- make restart/startup behavior predictable;
- run several real conversational sessions;
- record real failures instead of inventing hypothetical architecture.

### Stage A exit condition

Corvus is a usable local persistent conversational AI even with Materialized Memory disabled.

---

## Stage B — Dual Recall / Structured-Memory Integration

### Goal

Attach existing Phase 2 Materialized Memory as a second recall path without making it a single point of failure.

### B0 — Phase 2 Engineering Re-Audit

Before integration, inspect actual runtime code and classify each P2 component:

```text
EXPERIMENTAL
VALIDATED_PROTOTYPE
PRODUCTION_CANDIDATE
PRODUCTION_READY
```

Do not assume `SEALED` research means production maturity.

Audit at least:

- `assertion_store.py`
- temporal policy
- world projection
- support / TMS boundary
- lineage
- supersession
- inspector / retrieval interfaces

### B1 — Knowledge Recall Read Path

Implement the smallest read path for:

```text
assertions
temporal state
Current World Projection
```

The first goal is read-only retrieval into Working Context.

Do not begin with a large automatic extraction pipeline.

### B2 — Evidence + Knowledge Context Assembly

Runtime:

```text
                    QUERY
                     |
            +--------+--------+
            |                 |
            v                 v
     Evidence Recall    Knowledge Recall
            |                 |
            +--------+--------+
                     |
               Working Context
                     |
                    9B
```

Required properties:

- Evidence Recall always remains available;
- structured memory carries provenance;
- authority is preserved;
- temporal state is preserved;
- the user can trace structured claims back toward evidence;
- incorrect structured memory can be bypassed or rebuilt.

### B3 — Minimal Background Materialization

Only after the read path works:

```text
persist evidence first
→ foreground response
→ idle/background extraction when useful
→ update Materialized Memory
```

Use deterministic logic where sufficient.

Reuse the 9B while idle before introducing a second model.

### Stage B exit condition

Corvus can both:

> find what was said

and:

> retrieve its current structured understanding

while raw evidence remains the fallback truth source.

---

## Stage C — Real-Use Measurement and Architecture Decision

### Goal

Measure the working A+B system before adding major P3 complexity.

### Measure

- retrieval misses;
- irrelevant candidate volume;
- latency;
- structured-memory errors;
- stale-current-state failures;
- temporal conflicts;
- unnecessary model calls;
- background queue pressure;
- foreground interference;
- provenance / authority mistakes.

### Benchmark policy

Use mature external benchmarks first.

Use Corvus-specific benchmark surfaces only for uncovered behavior.

`Benchmark-96` remains frozen and diagnostic.

It does **not** dictate that a Relation Gate must exist.

### Stage C outputs

Produce an explicit decision matrix:

```text
Observed gap
→ frequency
→ user impact
→ existing mature solution
→ local reproduction evidence
→ ADOPT / ADAPT / DEFER / REJECT
```

### Stage C exit condition

Corvus has evidence for which advanced capability should be built next.

If no relation bottleneck exists, do not build a Relation Gate merely because P3 originally contained one.

---

## Stage D — Targeted Relation Intelligence

**Conditional Stage**

Enter only if Stage C demonstrates a real need.

Possible problems:

- too many relation candidates;
- stale/current fact conflicts;
- support contradictions;
- temporal relation ambiguity;
- unnecessary 9B relation reasoning.

Possible mechanisms:

- deterministic candidate pruning;
- relation-worthiness filtering;
- `supersedes`;
- `contradicts`;
- `supports`;
- `before`;
- `after`;
- abstention;
- 9B semantic fallback.

`Benchmark-96` may be used here.

### Small-model rule

Do not add a small model by default.

Add one only if:

- the background queue cannot keep up;
- foreground latency is harmed;
- a defined task can be performed reliably enough by the smaller model;
- local evidence shows meaningful resource savings.

---

## Stage E — Memory Lifecycle and Hierarchy

Draws from original P4 and P5 goals.

Possible capabilities:

- entity normalization;
- episodes;
- hierarchical memory views;
- semantic abstraction;
- relationship memory;
- historical snapshots;
- background consolidation;
- replay / rebuild;
- promotion between derived memory views.

Important rule:

Hierarchy is a derived organization of evidence.

It must not become destructive compression of canonical history.

---

## Stage F — Adaptive Recall / Memory Economy

Draws from original P6.

Research questions:

- When should retrieval activate?
- Evidence Recall, Knowledge Recall, or both?
- How many candidates are enough?
- When should retrieval stop?
- When is deterministic reasoning sufficient?
- When is 9B worth calling?
- When can a previously materialized interpretation replace repeated reasoning?

Core principle:

```text
SPEND INTELLIGENCE SELECTIVELY
```

This Stage should be driven by real operational traces from earlier working versions.

---

## Stage G — Personalization

Draws from original P7.

Goal:

Move from:

> a good persistent assistant

toward:

> a model/system increasingly specific to one person.

Possible future techniques may include:

- adapters;
- LoRA;
- preference models;
- activation / external parameter memory;
- continual adaptation;
- techniques that do not exist yet.

Do not freeze today's technique.

Perform a fresh landscape check when Stage G actually begins.

---

## Stage H — Multi-Agent

Draws from original P8.

Only after memory identity and authority boundaries are mature.

Potential problems:

- multiple agent identities;
- private vs shared memory;
- authority across agents;
- conflicting interpretations;
- agent-to-agent provenance;
- social / collaborative behavior involving the user and multiple AIs.

Multi-Agent remains a valid long-term goal.

It is deliberately late because memory boundaries must be trustworthy first.

---

# 8. Delivery Rules

## Rule 1 — Always Maintain a Working Corvus

Every major Stage starts from a working version and must end with a working version.

Research must not require destroying the previous usable baseline.

## Rule 2 — Capability Map != Construction Order

`P0–P8` describe long-term capabilities.

`Stage A–H` describe current delivery strategy.

The Stage plan may change as evidence and technology change.

## Rule 3 — Mature Baseline First

Prefer mature external:

- components;
- algorithms;
- libraries;
- benchmarks.

Original work is concentrated on:

- architecture;
- orchestration;
- memory semantics;
- policies;
- consumer-hardware integration;
- demonstrated Corvus-specific gaps.

## Rule 4 — Measure Before Adding Complexity

Do not add:

- gates;
- rerankers;
- ANN;
- small models;
- queues;
- extra indexes;
- learned policies

because a diagram contains a box for them.

Add them when a measured problem justifies them.

## Rule 5 — Engineering Maturity Is Separate From Research Status

For important components record both:

```text
Research Status
Engineering Maturity
```

Suggested engineering labels:

```text
EXPERIMENTAL
VALIDATED_PROTOTYPE
PRODUCTION_CANDIDATE
PRODUCTION_READY
```

## Rule 6 — Fresh Landscape Check

At meaningful Stage boundaries:

- inspect current literature;
- inspect mature open source;
- inspect benchmarks;
- inspect relevant new model/runtime capabilities.

Do not bind later Corvus to technology selected months earlier.

## Rule 7 — External Benchmark First

Before creating a custom benchmark:

- search established benchmarks;
- reproduce/adapt them when possible;
- add small Corvus-specific tests only for uncovered behavior.

Stop once sufficient evidence exists for an engineering decision.

## Rule 8 — Version-Control Discipline

Before a Stage is SEALED:

- actual repo audit;
- checkpoint logs;
- Fresh Landscape Check;
- phase/stage report;
- explicit staging;
- staged diff review;
- commit;
- push;
- `main == origin/main`.

Never use:

```text
git add .
```

---

# 9. Current Position

```text
Capability map:

P0 Runtime                  ✅
P1 Retrieval research       ✅
P2 Memory semantics         ✅
P3 Relation intelligence    🟡 partial research / conditional
P4+                         ⬜ future capability territory

Delivery roadmap:

Stage A
  A0 Retrieval Foundation   ✅ SEALED
  A1 Persistent Chat Loop   🟡 NEXT
  A2 Daily-Use Baseline     ⬜

Stage B Dual Recall         ⬜
Stage C Measure / Decide    ⬜
Stage D Relation Intel      ⬜ conditional
Stage E Lifecycle/Hierarchy ⬜
Stage F Memory Economy      ⬜
Stage G Personalization     ⬜
Stage H Multi-Agent         ⬜
```

---

# 10. Immediate Next Step

Do **not** resume the old P3 Gate implementation yet.

Begin:

# Stage A1 — Persistent Conversation Loop

First re-audit the current chat entrypoints and define the smallest production conversation contract connecting:

```text
SQLite persistence
+
recent context
+
A0 hybrid Evidence Recall
+
local 9B
```

The first product milestone is:

> **Corvus can be stopped, restarted, and still remember a previous conversation through the production A0 retrieval path.**

Only after that milestone is usable should Stage B attach Materialized Memory.

---

# 11. Standing Principle

The Corvus roadmap is now governed by:

> **Always maintain a working Corvus. Research should upgrade the product, not postpone its existence.**

Supporting principles:

```text
STORE ALL EXPERIENCE.
SPEND INTELLIGENCE SELECTIVELY.

FOREGROUND FIRST.
BACKGROUND WHEN POSSIBLE.

REUSE COMPONENTS.
INNOVATE COMPOSITION.
VALIDATE THE GAP.

FREEZE THE GOAL,
NOT THE IMPLEMENTATION.
```
