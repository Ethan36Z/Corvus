# Phase 3 — Reviewer Methodology Boundary

## 1. Context

Phase 3 Benchmark-96 requires an independent quality-control process before the benchmark can be frozen.

Several blind-review protocols were tested with the Corvus 9B model.

The experiments exposed repeated protocol sensitivity:
- routing labels collapsed toward model judgment;
- evidence-status labels were not sufficiently informative;
- structured output guaranteed syntax but not semantic consistency;
- unconstrained critic output could hit the token ceiling;
- bounded output fixed verbosity but not semantic reliability;
- candidate selection and relation classification became entangled;
- small prompt changes could materially alter reviewer behavior.

## 2. Research / Engineering Question

What role can an LLM reviewer safely play in validating Benchmark-96 without becoming an unreliable substitute for human gold adjudication?

## 3. Starting Hypothesis

Working hypothesis:

An independent LLM reviewer may be useful for detecting overlooked interpretations, candidate links, relation families, and adversarial objections.

It should not be treated as a gold-answer oracle.

## 4. What We Did

Tested several reviewer formulations:

- routing-oriented reviewer;
- evidence-status reviewer;
- semantic critic;
- bounded semantic critic;
- grounded candidate critic;
- candidate-only grounding experiments.

Important failure cases and partial runs were preserved rather than erased.

## 5. Evidence / Results

Observed failures included:

- routing-label collapse;
- semantic cross-field inconsistency despite JSON Schema;
- prompt-only JSON instability;
- token truncation from unbounded critic prose;
- semantic behavior changing after seemingly small prompt edits;
- false relation construction;
- candidate competition / omission.

A schema-level output budget successfully reduced one 400-token truncation case to a normal completion below the ceiling.

However, improving individual benchmark cases by repeatedly changing the prompt created a growing risk of reviewer overfitting.

## 6. Interpretation

There is no evidence that a single carefully tuned LLM prompt can serve as a trustworthy semantic oracle for Benchmark-96.

Per-case prompt correction would contaminate the validation process.

Reviewer disagreement is useful as evidence for inspection, but disagreement alone does not establish that the benchmark gold is wrong.

Likewise, reviewer agreement does not prove that the benchmark gold is correct.

## 7. Decision

KEEP:
- blind independent review as adversarial quality control;
- bounded structured output;
- preservation of failed reviewer protocols;
- human adjudication as final authority.

REJECT:
- Reviewer as gold oracle;
- Reviewer as Gate-routing oracle;
- continued prompt tuning in response to individual Benchmark-96 cases;
- changing benchmark gold automatically because the Reviewer disagrees.

FREEZE METHODOLOGY RULE:

After the generic critic protocol is frozen, individual benchmark-case outcomes MUST NOT be used to modify the reviewer prompt.

Protocol changes are allowed only for protocol-level failures such as:
- invalid/unparseable output;
- internally impossible schema requirements;
- implementation bugs;
- clearly defective task definitions independent of a particular desired answer.

Any such change must be documented and requires a new reviewer protocol version.

## 8. Architecture Impact

The Reviewer is not part of the Corvus runtime architecture.

It is a temporary benchmark-development QC instrument.

Runtime questions remain separate:

Candidate Generation
→ relation-worthy Gate
→ resolution/routing
→ deterministic / model / abstain paths

The Reviewer must not determine these runtime architecture decisions.

## 9. Open Questions

- What minimal generic critic output is most useful for human adjudication?
- Should more than one independent reviewer be used?
- How should reviewer disagreements be ranked for manual inspection?
- Which benchmark cases should later be reserved from Gate-development tuning?
- How should final benchmark confidence and limitations be reported?

## 10. Next Step

Define one small, generic, case-independent adversarial critic protocol.

Freeze that protocol before running it across Benchmark-96.

Do not optimize it against individual benchmark cases after freezing.
