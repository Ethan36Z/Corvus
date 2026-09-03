# Phase 3 — Benchmark v0.1 Final Adjudication and Freeze

## 1. Context

Phase 3 created Benchmark-96 to evaluate whether cheap structural and retrieval signals can reduce the archive to a small relation-worthy candidate set while preserving important memory relations.

The benchmark contains 96 cases:

- 6 relation phenomena;
- 4 decision modes per phenomenon;
- 4 scenarios per mode.

After the benchmark was authored and individually validated, Corvus performed a fixed blind adversarial critic run and a disagreement audit.

The final acceptance pass focused on the 19 hard-negative cases challenged by the critic.

## 2. Research / Engineering Question

Is Benchmark-96 sufficiently internally consistent and well-bounded to be frozen as Corvus Phase 3 benchmark v0.1, without continuing into recursive benchmark and evaluator validation?

## 3. Starting Hypothesis

The benchmark should be frozen if:

- all 96 cases remain structurally valid;
- the frozen case ordering and family balance remain intact;
- reviewer disagreements do not reveal a systematic benchmark failure;
- demonstrated defects are repaired;
- no unexplained semantic edits remain;
- existing contracts remain internally consistent.

The reviewer is an adversarial critic, not an oracle.

Reviewer disagreement alone is therefore not sufficient reason to modify benchmark gold.

## 4. What We Did

Corvus completed the following final acceptance steps:

1. Ran the frozen blind critic protocol across all 96 cases.
2. Generated a disagreement audit.
3. Identified 19 hard-negative candidate challenges.
4. Manually adjudicated all 19 challenged hard negatives.
5. Accepted 14 original hard negatives unchanged.
6. Identified 5 demonstrated benchmark defects:
   - CAU-N4
   - SUP-N1
   - SUP-N2
   - SUP-N3
   - SUP-N4
7. Applied targeted repairs only to those 5 cases.
8. Compared the repaired benchmark against pre-repair blind and audit artifacts.
9. Confirmed that exactly those 5 intended cases changed.
10. Ran a deterministic structural integrity check across the full 96-case benchmark.
11. Synchronized the manifest.
12. Changed benchmark and manifest status to FROZEN.

No new reviewer, meta-reviewer, or additional benchmark layer was introduced.

## 5. Evidence / Results

Final deterministic structural check:

- JSON parse: PASS
- duplicate JSON keys: PASS
- cases: 96 / 96
- unique case IDs: 96 / 96
- frozen case order: PASS
- families: 6 × 16 PASS
- decision modes: 4 × 24 PASS
- per-family mode balance: 4 × 4 PASS
- assertion reference integrity: PASS
- hard-negative structure: PASS
- cross-family contract: PASS
- support contract: PASS
- causal contract: PASS
- unexpected semantic edits: 0
- intentional repaired cases: 5 / 5

Hard-negative adjudication:

- challenged cases reviewed: 19 / 19
- original gold retained: 14
- demonstrated defects repaired: 5

The principal defect patterns were:

### CAU-N4

The original wording contained an explicit relative temporal relation:

"later that afternoon"

This violated the v0.1 hard-negative requirement that no non-trivial relation-worthy link exist across any family.

The case was rewritten to remove the temporal relation while preserving the causal hard-negative role.

### SUP-N1 through SUP-N4

The original support hard negatives incorrectly blurred two different concepts:

- the archived assertion is not valid support for the new claim;
- the archived assertion is not relation-worthy enough to inspect.

Under the global candidate contract, an assertion may still deserve inspection even when the final relation judgment is "not valid support."

The four cases were rewritten as strong lexical or semantic retrieval distractors whose scopes or entities do not form a non-trivial relation-worthy link.

Final frozen SHA256 values:

Benchmark:

c8ad651b200d90d97c74d79d6dc306f0c6bfb41aa6d0e5e96ac16cea8df98c57

Manifest:

9acdb43e75276a3f9ab04160158da933de4d8b996f5d82a2ea81b9a574787033

## 6. Interpretation

The final audit did not reveal a benchmark-wide failure.

The adversarial critic tended to use a broader notion of semantic relatedness than the benchmark's GLOBAL_RELATION_WORTHY candidate contract.

Examples included:

- same date;
- nearby dates;
- same person but unrelated attributes;
- lexical overlap;
- incidental temporal ordering.

These signals can make an assertion retrievable without making it relation-worthy.

This distinction is central to the Phase 3 Gate question.

The final audit also demonstrated the usefulness of adversarial review when bounded by an explicit stop rule: it identified a localized systematic defect in support hard negatives and one cross-family leakage case without requiring recursive evaluator construction.

## 7. Decision

### ADOPT

Freeze `p3-benchmark-v0.1` as the Phase 3 Corvus-specific benchmark.

### KEEP

Keep the existing global candidate contract:

`INCLUDE_OLD_ASSERTION_IF_IGNORING_IT_COULD_MISS_A_NONTRIVIAL_RELATION_OR_REQUIRED_ABSTENTION`

Keep the distinction:

retrievable similarity != relation-worthy memory relation.

Keep:

timeline != semantic relation graph.

### REJECT

Do not:

- tune the reviewer against individual cases;
- create another reviewer;
- recursively validate the reviewer;
- reopen benchmark v0.1 because of general uncertainty;
- silently modify frozen v0.1 during Gate development.

A future benchmark revision requires a demonstrated failure discovered during real Phase 3 experimentation.

Such changes belong in a later benchmark version, not in frozen v0.1.

## 8. Architecture Impact

Benchmark v0.1 now provides a frozen Corvus-specific test surface for:

Archive Assertions
        ↓
Candidate Generation
        ↓
Relation-Worthy Gate
        ↓
Deterministic / Abstain / Semantic Resolution

It is not intended to replace established external benchmarks.

Under the updated resource-aware research strategy, external benchmarks and mature implementations remain the primary evidence for capabilities they already cover.

Benchmark v0.1 is retained for Corvus-specific integration behavior and candidate-worthiness semantics.

## 9. Open Questions

The benchmark does not determine:

- which candidate-generation algorithm should be adopted;
- whether one Gate or several specialized gates are required;
- whether existing memory admission mechanisms can be adapted directly;
- which deterministic features provide the best recall/economy tradeoff;
- when a small learned model is useful;
- when escalation to the 9B model is justified.

These are Phase 3 implementation questions, not benchmark-design questions.

## 10. Next Step

Stop benchmark construction.

Build a Gate Capability / Overlap Matrix from current literature and open-source systems.

Identify the smallest non-redundant set of mature components that can cover:

- memory admission / promotion;
- candidate retrieval;
- relation-worthiness gating;
- deterministic resolution;
- uncertainty / abstention;
- weak-to-strong model routing.

Then reproduce or adapt existing approaches before inventing new Corvus components.

Reuse components.
Innovate composition.
Validate the gap.
