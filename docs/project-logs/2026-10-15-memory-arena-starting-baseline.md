# Corvus Memory Arena — RAG vs Hindsight Human Evaluation

Date: 2026-10-15. Canonical handoff into the dedicated Memory Arena workstream.
This is a documentation-only starting baseline; no Arena implementation or live
memory experiment is part of this task.

## Verified repository and H1 seal evidence

Lab repository: `/home/ethan/srv/apps/corvus-lab`, branch `lab/ow2e-console`.
Before this log, HEAD was `cee5a5e74216d9eaf393dcc290b4ad862a81657a`
(`Seal H1 Hindsight integration`), and the worktree and index were clean.
That commit contains both canonical H1 records, inspected for this handoff:

- [H1 phase report](../phase-reports/h1-hindsight-integration.md).
- [Final daily-use acceptance and seal](2026-10-11-h1-final-daily-use-acceptance.md).

These are recorded H1 acceptance evidence, not a fresh runtime health audit.
Production was not inspected for this task.

## H1 status

**H1 — Hindsight Integration is SEALED.** Do not reopen H1 unless real daily-use
evidence exposes a concrete blocker.

The accepted architecture includes:

- Corvus SQLite Evidence Log as canonical truth; recent conversation context
  remains Corvus-owned; Hindsight is derived long-term memory intelligence.
- Durable async retain, a retain intent/outcome ledger, stable operation UUIDs
  and bounded reconciliation. Reconciliation remains explicit/manual.
- A host-wide foreground registry with Lab + Production foreground publishers
  and Hindsight read-only foreground admission.
- BUSY → `DeferOperation`, durable resume after idle/grace, and deliberate defer
  without retry-count consumption.
- Bounded consolidation: model context **8192**, consolidation completion cap
  **1024**, safety margin **256**, consolidation reasoning disabled.
- Reflect deferred.

H1 is a provisional local daily-use candidate with accepted constraints. Async
retain is enabled in Lab; Production's H1 participation is foreground publishing,
not adoption of the Lab Hindsight memory-writing lifecycle.

Accepted limitations:

- No preemption if foreground arrives after memory inference has started.
- Oversized indivisible consolidation inputs may remain deferred.
- Retained documents may yield zero semantic facts.
- Reflect remains deferred.
- H1 does not claim Hindsight is universally semantically superior to Corvus RAG.

## Existing memory paths

**Path A — original Corvus RAG** is already built and deployed:

```text
SQLite canonical Evidence Log
→ SQLite FTS5 / BM25
→ GTE multilingual dense embeddings
→ LanceDB derived dense index
→ RRF fusion
→ canonical SQLite hydration
```

FTS5/BM25 and dense retrieval provide the sparse/dense rankings combined by RRF.
Do **not** rebuild this path for Memory Arena.

**Path B — Hindsight** is already integrated and daily-use capable through H1.
It includes recall plus the durable retain/consolidation lifecycle above. In the
sealed lifecycle, Hindsight recall is shadow-only and active historical retrieval
remains Corvus RAG. Do **not** rebuild this path for Memory Arena.

## Goal and Arena v0 architecture principle

Memory Arena is not a new memory architecture or a formal benchmark system.
Use real daily-use questions and Ethan's human judgment to compare original
Corvus RAG vs Hindsight. The primary question is:

> Given the same historical state and the same user query, which historical-memory
> provider produces the more useful/correct Corvus response?

**REUSE EXISTING SYSTEMS. ADD ONLY THE COMPARISON LAYER.** Reuse:

- The existing Open WebUI-based Corvus UI.
- Existing Corvus RAG and Hindsight recall.
- Existing Qwen3.5-9B.
- Existing Corvus conversation/runtime infrastructure.

Do not create another frontend project unless a fresh audit proves the existing
Open WebUI cannot reasonably support the feature.

Hold constant where practical: user query, historical cutoff, recent context,
Qwen model, system/personality prompt and generation profile. The intended
experimental variable is **historical-memory provider**.

## Arena v0 main/shadow rule

Original Corvus RAG remains the **MAIN / CANONICAL** conversation path. The normal
RAG-based Corvus reply is the real assistant reply, persists normally in canonical
conversation and follows the normal memory lifecycle.

The Hindsight-based candidate is a **SHADOW experimental reply**. It may be shown
side-by-side for comparison, but **MUST NOT** become canonical assistant history
and **MUST NOT** itself be retained into long-term memory. Evaluation/voting
records may be stored separately as derived evaluation data.

## Leakage and fairness

The Hindsight candidate must not receive the current turn as newly retained memory
before answering the same query. Both providers should evaluate the same historical
cutoff/state as closely as the current architecture permits. The Arena must not
contaminate the memory being evaluated.

The next audit must establish how this is enforced before implementation; the
existing post-response shadow lifecycle alone is not a fairness guarantee for a
new comparison flow.

## UI direction

Build on the existing Open WebUI source already used by Corvus. Likely UX:

- Normal Corvus interaction remains available.
- A Memory Arena view or Compare Memory action.
- Main response vs shadow candidate, displayed side-by-side.
- Expandable retrieved memory/evidence and retrieval/generation latency.
- Human choices: **RAG better**, **Hindsight better**, **Tie**, **Neither**.

Blind/randomized presentation may be considered if simple.

## Explicit non-goals

Do not build:

- A new RAG, another Hindsight integration, or a new memory backend/database.
- Synthetic benchmark/gold-set infrastructure or LLM-as-a-judge.
- A new scheduler/queue/framework.
- Reflect.
- A new standalone frontend.
- Changes to the sealed H1 memory lifecycle merely for Arena.

## Evaluation philosophy

Use real daily-use questions; Ethan is the primary judge. Arena exists to accumulate
practical evidence over time, not to manufacture a formal benchmark score before
use. Later evidence may support Hindsight becoming primary historical memory,
original RAG remaining primary, dual/fallback recall remaining, or query-dependent
provider selection. Do not decide this before evidence exists.

## Next dedicated workstream step

The next Memory Arena thread must begin with a fresh **READ-ONLY audit before
coding**, establishing:

1. Exact current Open WebUI source/version/deployment location.
2. Current Open WebUI → Corvus call path.
3. Exact Corvus RAG historical recall entry point.
4. Exact Hindsight recall entry point.
5. Both current input/output contracts.
6. Existing historical-memory provider seam.
7. Smallest Arena comparison API seam.
8. Smallest Open WebUI extension point.
9. How shadow generation avoids canonical/retain pollution.
10. How same-turn historical cutoff fairness is enforced.

No Arena coding occurs in this task. This handoff changes no runtime behavior,
Hindsight, Open WebUI, services, memory data, deployment configuration or Production.
