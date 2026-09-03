# Phase 3 — Hybrid Memory Architecture and Revised Action Plan

## 1. Context

During Phase 3, Corvus gradually expanded toward a multi-stage architecture involving candidate generation, promotion, relation-worthiness gating, deterministic resolution, model routing, and background consolidation.

Although these mechanisms may eventually be useful, treating all of them as required architecture before running the complete memory system created two problems:

1. the architecture became increasingly difficult to understand and remember;
2. several components were being assumed necessary before runtime evidence demonstrated that they solved a real bottleneck.

A review of mature persistent-memory systems suggested a safer development strategy.

Corvus should first assemble a mature retrieval-based persistent-memory system using already proven techniques.

The structured memory capabilities built during Phase 2 should then be attached as an additional, more advanced memory path.

Phase 3 mechanisms should only be added when measurements demonstrate a concrete need.

This is an architecture simplification and reorganization, not a restart.

Most work from Phase 0 through Phase 2 maps directly into the revised architecture.

## 2. Research / Engineering Question

What is the smallest, mature, understandable architecture that can provide Corvus with useful persistent personal memory while preserving a path toward advanced structured and relational intelligence?

A second question is:

Which memory operations must happen during the user-visible response path, and which expensive operations can safely be delayed until the foreground model is idle?

## 3. Starting Hypothesis

Corvus should be organized around three core concepts:

1. Evidence Log
2. Working Context
3. Materialized Memory

Raw user evidence should be persisted immediately.

There should be no KEEP / DROP gate before the Evidence Log.

The current conversation should use a small Working Context composed primarily of:

- recent turns;
- the current task;
- historically retrieved evidence;
- structured memories when useful.

Structured assertions, entities, relations, temporal state, and Current World Projection should be treated as derived Materialized Memory.

Materialized Memory is not the source of truth.

Raw evidence remains the source of truth and can be reinterpreted later.

The mature retrieval path must remain usable independently from the advanced structured-memory path.

## 4. Revised Core Architecture

The simplified Corvus architecture is:

                         USER INPUT
                             |
                             v
                    +----------------+
                    |  EVIDENCE LOG  |
                    |                |
                    | all raw input  |
                    | persistent     |
                    | source of truth|
                    +-------+--------+
                            |
                 +----------+----------+
                 |                     |
                 v                     v
        +----------------+    +----------------------+
        | WORKING CONTEXT|    | MATERIALIZED MEMORY  |
        |                |    |                      |
        | recent turns   |    | assertions           |
        | current task   |    | entities             |
        | retrieved raw  |    | relations            |
        | useful memory  |    | temporal state       |
        |                |    | world projection     |
        +--------+-------+    +----------+-----------+
                 |                       |
                 +-----------+-----------+
                             |
                             v
                            LLM

The architecture therefore contains two complementary recall paths.

### Evidence Recall

Evidence Recall answers:

"What did the user actually say or what did the system directly observe?"

Primary mechanisms include:

- recent conversation context;
- persistent message history;
- SQLite;
- FTS5;
- semantic retrieval;
- raw evidence provenance.

Evidence Recall is the mature and reliable baseline path.

### Knowledge Recall

Knowledge Recall answers:

"What does Corvus currently understand from the historical evidence?"

Primary mechanisms include:

- assertions;
- entities;
- relations;
- temporal validity;
- provenance;
- authority;
- historical state;
- Current World Projection.

Knowledge Recall is the advanced structured-memory path primarily developed during Phase 2 and later phases.

Knowledge Recall does not replace Evidence Recall.

Both recall paths can contribute to the Working Context.

## 5. Mapping Existing Corvus Work

The revised architecture preserves most existing work.

### Phase 0 — Local Model and Hardware Runtime

Phase 0 provides:

- Qwen 9B;
- llama.cpp;
- RTX 2080 Ti 11 GB runtime;
- generation measurements;
- prefill measurements;
- GPU residency behavior;
- consumer-hardware constraints.

This remains the execution foundation for both foreground conversation and background memory processing.

### Phase 1 — Evidence Recall

Phase 1 already provides much of the mature persistent-memory baseline:

- persistent messages;
- FTS5;
- semantic search;
- retrieval infrastructure;
- RAG experiments.

Phase 1 therefore becomes the main foundation of Evidence Recall.

### Phase 2 — Materialized Memory

Phase 2 already provides much of the advanced structured-memory system:

- immutable raw evidence separation;
- Assertion Record;
- provenance;
- authority;
- modality;
- temporal validity;
- assertion lineage;
- supersession;
- Temporal Policy;
- truth-maintenance concepts;
- Current World Projection.

The Phase 2 principle:

RAW EVIDENCE != STRUCTURED ASSERTION

becomes a foundational architectural rule.

### Phase 3 Benchmark

Benchmark-96 remains useful, but its role changes.

Benchmark-96 no longer implies that a Relation-Worthy Gate must exist.

Instead, it becomes a diagnostic benchmark.

If runtime experiments later demonstrate that candidate relation filtering is a meaningful accuracy or compute bottleneck, Benchmark-96 can evaluate proposed solutions.

The benchmark does not dictate the architecture.

## 6. Runtime Principle

The revised system separates storage from expensive intelligence.

The basic principle is:

STORE NOW.
USE NOW.
UNDERSTAND LATER WHEN POSSIBLE.

More precisely:

- persist raw evidence immediately;
- make recent conversation immediately available;
- retrieve older evidence when the current answer requires it;
- perform only necessary foreground reasoning;
- defer non-urgent enrichment and consolidation until after the response or during idle periods.

Corvus does not need a small model to decide whether an utterance deserves long-term existence.

Raw evidence is long-lived by default.

The temporary component is the Working Context, not the underlying historical record.

Materialized Memory behaves more like indexes or materialized views built over the permanent Evidence Log.

Materialized Memory can therefore be:

- updated;
- corrected;
- rebuilt;
- reinterpreted;
- improved when better models become available.

## 7. Foreground and Background Execution

Corvus should prioritize user-visible latency.

### Foreground Path

The foreground path is:

    user input
        |
        v
    persist raw evidence
        |
        v
    update recent Working Context
        |
        v
    retrieve only memory needed now
        |
        v
    local 9B
        |
        v
    reply to user

The foreground path should remain as small and predictable as possible.

Cheap operations may happen immediately:

- SQLite writes;
- timestamps;
- FTS indexing;
- recent-context maintenance;
- cheap retrieval;
- deterministic bookkeeping.

### Background Path

After the response, optional work may continue:

    queued raw evidence
        |
        v
    indexing / extraction
        |
        v
    temporal normalization
        |
        v
    assertion extraction
        |
        v
    relation processing
        |
        v
    Materialized Memory update

Expensive model work should preferably happen while:

- the user is reading;
- the user is thinking;
- the user is typing;
- the system is otherwise idle.

Human interaction latency is therefore usable background compute budget.

A new foreground request always takes priority over optional background work.

## 8. Model Strategy

The revised architecture does not assume that Corvus requires a second small model.

The initial strategy is:

Foreground:
- use the local 9B model for conversation.

Background:
- use deterministic and cheap processing whenever possible;
- reuse the 9B model when the foreground is idle.

A smaller background model should only be introduced if measurements demonstrate a real problem such as:

- the background queue grows continuously;
- memory processing cannot keep up;
- foreground latency is harmed by background work;
- a smaller model can perform a specific task accurately enough at substantially lower cost.

A model should enter the architecture because evidence demonstrates its value, not because a diagram has an empty box for it.

## 9. Decision

### ADOPT — Three-Part Core Architecture

The system-level memory architecture is:

Evidence Log
Working Context
Materialized Memory

These three concepts define Corvus memory at the highest level.

Mechanisms such as gates, rerankers, classifiers, temporal resolvers, and model routers remain implementation details unless experiments demonstrate that they deserve separate architectural status.

### ADOPT — Hybrid Recall

Corvus will use:

Evidence Recall
+
Knowledge Recall

Evidence Recall retrieves original historical evidence.

Knowledge Recall retrieves derived structured understanding.

Both can contribute to the Working Context.

### ADOPT — Mature Baseline First

Before adding further Phase 3 complexity, Corvus will assemble a mature retrieval-based memory baseline using existing Phase 0 and Phase 1 components.

The first target is:

Recent Context
+
FTS5
+
Semantic Retrieval
+
Local 9B

The goal is to make Corvus a usable persistent conversational AI before adding additional research complexity.

### ADOPT — Phase 2 as the Second Memory Engine

After the mature baseline works reliably, Phase 2 Materialized Memory will be attached as a second recall path.

The runtime can then use:

Raw Evidence Retrieval
+
Structured Assertion / World-State Retrieval

This allows advanced memory to improve the baseline without becoming a single point of failure.

### DEFER — Relation-Worthy Gate

A Relation-Worthy Gate is no longer assumed to be mandatory.

First measure whether mature retrieval plus existing deterministic mechanisms already provide acceptable candidate quality, latency, and compute cost.

If candidate overload or unnecessary semantic reasoning becomes a demonstrated bottleneck, Benchmark-96 can evaluate relation-filtering mechanisms.

### DEFER — Small Background Model

Do not introduce a second model until runtime measurements demonstrate that the 9B model plus idle-time background scheduling cannot keep up.

### REJECT

Do not:

- place KEEP / DROP filtering before the Evidence Log;
- divide raw user experience into temporary versus permanent storage;
- make advanced structured memory the only source of recall;
- add a small model merely because background work exists;
- add multiple gates before evidence demonstrates their value;
- let experimental mechanisms block delivery of a mature persistent-memory baseline.

## 10. Revised Engineering Plan

The project will proceed in three major stages.

### Stage A — Mature Persistent-Memory Baseline

Assemble:

P0 local 9B runtime
+
P1 persistent messages
+
recent conversation context
+
FTS5
+
semantic retrieval

Runtime shape:

                 USER QUERY
                     |
            +--------+--------+
            |                 |
            v                 v
       Recent Turns      Evidence Search
                         FTS + Semantic
            |                 |
            +--------+--------+
                     |
                     v
               Working Context
                     |
                     v
                    9B
                     |
                     v
                  Response

Goal:

Corvus should become a usable persistent conversational AI that:

- remembers the immediate conversation;
- can retrieve information from previous sessions;
- can cite or trace retrieved memory back to original evidence;
- remains responsive on the existing consumer hardware.

This stage intentionally uses mature techniques first.

### Stage B — Phase 2 Structured-Memory Integration

Attach Materialized Memory as the second recall path.

The architecture becomes:

                     QUERY
                       |
              +--------+--------+
              |                 |
              v                 v
       Evidence Recall     Knowledge Recall
              |                 |
       raw messages          assertions
       FTS / semantic        temporal state
                            world projection
              |                 |
              +--------+--------+
                       |
                       v
                 Working Context
                       |
                       v
                      9B

Goal:

Move from:

"I can find what you said."

toward:

"I understand how your state changed over time."

Evidence Recall remains available even if structured memory is incomplete or incorrect.

### Stage C — Measure Before Adding Phase 3 Complexity

After Stage A and Stage B are running, measure:

- retrieval recall;
- candidate pool size;
- response latency;
- foreground responsiveness;
- background queue behavior;
- structured-memory accuracy;
- temporal update behavior;
- conflict resolution;
- unnecessary model computation.

Only after observing real bottlenecks should Corvus decide whether it needs:

- Relation-Worthy Gate;
- learned classifier;
- small background model;
- weak-to-strong routing;
- adaptive consolidation;
- additional memory policies.

Benchmark-96 remains frozen and available for demonstrated relation-filtering gaps.

## 11. Simplified Mental Model

The whole Corvus memory architecture should be understandable using one sentence:

All experience is permanently stored in the Evidence Log; the current conversation uses a small Working Context; background processing gradually turns history into searchable structured Materialized Memory.

Or more simply:

原话库
  ↓
当前工作区
  ↓
整理后的记忆

The implementation may contain many algorithms internally, but the system architecture should remain understandable through these three concepts.

## 12. Project Principles

ARCHIVE CAN GROW.
ACTIVE CONTEXT SHOULD NOT.

RAW EVIDENCE != STRUCTURED ASSERTION.

STORE ALL EXPERIENCE.
SPEND INTELLIGENCE SELECTIVELY.

FOREGROUND FIRST.
BACKGROUND WHEN POSSIBLE.

MATURE BASELINE FIRST.
ADVANCED MEMORY SECOND.

REUSE COMPONENTS.
INNOVATE COMPOSITION.
VALIDATE THE GAP.

## 13. Next Step

Stop expanding the architecture.

Begin Stage A.

Connect the existing Phase 0 local 9B runtime and Phase 1 retrieval infrastructure into the smallest usable persistent conversational loop.

The next engineering question is:

Can Corvus, using only mature recent-context and retrieval techniques, already provide a useful long-term conversational memory experience on the existing hardware?

Only after this baseline is working should Phase 2 Materialized Memory be attached as the second memory path.
