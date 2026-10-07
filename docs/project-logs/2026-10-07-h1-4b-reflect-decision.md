# H1.4b — Hindsight Reflect architecture decision

Date: 2026-10-07

Baseline: `lab/ow2e-console` at `a1d6d47532b879b366d080ba372802c01aba98d5`

Contract audit: PASS WITH CONSTRAINTS

## Original hypothesis

Explicit Reflect might be required after retain as memory maintenance. The real
local API/source/config audit established a different role: Reflect is
memory-grounded reasoning and synthesis.

## Evidence

The running Hindsight instance at `http://127.0.0.1:8888` reports API version
`0.10.1`. The audit used live `/openapi.json`, installed source under
`/app/api/hindsight_api` in `hindsight-lab`, non-secret runtime configuration,
local benchmark scripts, and read-only bank APIs.

- `POST /v1/default/banks/{bank_id}/reflect` accepts a question and synchronously
  returns a synthesized answer, with optional evidence, usage, and execution
  trace. It uses an agent/model path with retrieval tools; it is not routine
  memory maintenance and does not persist its answer or consolidate memories.
- Retain ingests content, extracts facts, and performs embeddings/entity/link
  processing. This bank enables observations and automatic consolidation, so
  retain schedules built-in consolidation without an explicit Reflect call.
  Consolidation can continue after synchronous retain completes.
- Reflect may perform multiple model calls, including additional synthesis,
  length rewriting, and optional structured extraction. Its agent execution has
  a configured 300-second timeout; preparatory reads occur outside that limit.
  The provider HTTP timeout is 180 seconds. General provider retry configuration
  permits three retries, potentially four attempts per eligible call.
- Background execution does not itself guarantee foreground-chat priority;
  inference can contend with Corvus's shared local model.
- No live Reflect probe was needed to establish the contract, and no Reflect
  operation was executed. Bank `corvus-hindsight-lab-v1` remained unchanged:
  6 documents, 6 memories (3 world facts, 3 observations), and 13 links.
- Caveat: the Reflect entry path can create a missing bank through profile
  assurance. The existing bank's memory-answering loop is read-only. Actual
  Reflect latency, model tool-calling compatibility, and answer quality remain
  unevaluated.

Key implementation evidence: `api/http.py:6091–6257`,
`engine/memory_engine.py:14998–15585` and `6080–6107`,
`engine/reflect/tools_schema.py:338–398`, and `config.py:1860–1875`.

## Corrected mental model and decision

- **Retain:** ingest/extract/consolidate; consolidation is built-in and can be
  asynchronous.
- **Recall:** retrieve memory evidence.
- **Reflect:** reason and synthesize an answer grounded in stored memory.

**REFLECT IS NOT PART OF THE NORMAL CORVUS MEMORY LIFECYCLE.** It is deferred as
an optional future memory-reasoning path, with potential value for difficult
cross-memory synthesis questions.

- **ADOPT:** retain-time extraction and built-in consolidation.
- **ADOPT:** Recall as the normal memory read operation.
- **DEFER:** Reflect as an optional reasoning experiment.
- **REJECT:** per-turn, periodic, or idle Reflect as a memory-maintenance hook.

Corvus already has its own foreground reasoning model. The default architecture
for reasoning over Hindsight evidence is:

`Hindsight Recall → Corvus model reasoning → final response`

This preserves separation between memory backend, reasoning model, personality,
and UI/tooling. The sealed runtime still uses Corvus active historical recall
and hybrid RAG; Hindsight Recall remains shadow-only. This decision introduces
no active-provider switch.

## Future evaluation — deferred

A later authorized experiment may compare:

1. Single Hindsight Recall → Corvus Qwen.
2. Corvus Qwen agent with repeated Hindsight Recall.
3. Hindsight Reflect.

Evaluate synthesis quality, latency, model-call cost, and foreground contention.
No experiment, scheduler, worker, queue, or integration is implemented here.

## Final H1.4 lifecycle

```text
canonical Corvus persistence
→ Corvus active historical recall / model reply
→ Hindsight shadow recall
→ durable comparison record
→ Hindsight retain
→ Hindsight built-in extraction/consolidation
```

The completed canonical user/assistant rows must exist before the shadow flow.
Same-turn shadow recall and its durable comparison record must precede retain;
failed comparison append prevents retain. SQLite remains canonical, and all
Hindsight state remains derived. Foreground Corvus chat must remain higher
priority than any future Reflect evaluation.

H1.4 final verdict: **PASS WITH CONSTRAINTS** — shadow recall/retain are sealed,
built-in consolidation supplies memory maintenance, and explicit Reflect is
deferred as an optional memory-reasoning path.
