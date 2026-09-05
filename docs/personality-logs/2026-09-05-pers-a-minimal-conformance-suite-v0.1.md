# PERS-A — Minimal Personality Conformance Suite v0.1

## Context

PERS-A now has a stable behavioral design baseline covering Core Personality, conflict rules, Collaboration Policy, Situational Tone, and Voice Style.

The next requirement is a small regression surface before runtime integration.

Personality is a supporting Corvus track, not a primary research program. The evaluation therefore stays intentionally small.

## Decision

Create a 12-case behavioral conformance suite at:

`benchmarks/personality/personality-conformance-v0.1.json`

The suite checks behavior contracts rather than exact wording.

## Coverage

The 12 cases cover four groups:

- Core: truthfulness, anti-sycophancy, uncertainty;
- Conversation: sharing vs task, answer-first behavior, clarification restraint;
- Tone: engineering, low mood, celebration;
- Relationship / Style: evidence-vs-instruction boundary, current soft preference priority, natural closure.

## Evaluation Discipline

- No exact reference response is required.
- No reviewer-on-reviewer stack is introduced.
- No large custom persona benchmark is created.
- Add a new case only after real use exposes a concrete regression or uncovered behavior gap.
- Existing public persona-evaluation work remains methodological reference, not a reason to enlarge PERS-A.

## Architecture Impact

This suite becomes the minimum behavioral regression contract for the future Personality Runtime Module and model-swap checks.

It does not modify memory semantics, retrieval, session persistence, or the A2 backend contract.

## Next Step

Implement the smallest model-independent Personality Runtime Module that compiles the Personality Spec into runtime instructions, then run the 12 cases against the current local Qwen baseline.
