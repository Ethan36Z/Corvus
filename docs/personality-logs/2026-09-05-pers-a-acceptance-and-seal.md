# PERS-A — Stable Personality Baseline Acceptance & Seal

**Date:** 2026-09-05  
**Status:** ✅ SEALED  
**Baseline:** Personality Spec v0.1

## Context

PERS-A was intentionally kept as a bounded supporting track rather than a new primary Corvus research program. The goal was to replace the placeholder system prompt with a stable, model-portable personality baseline suitable for real daily use.

## What Was Completed

- Core Personality C1-C7
- Conflict Rules R1-R8
- Collaboration / Response Policy
- Situational Tone registers
- Voice Style baseline
- `docs/personality/personality-spec-v0.1.md`
- 12-case minimal conformance suite
- independent `personality/` runtime module
- `conversation_runtime.py` integration through injectable `system_prompt_fn`
- local runtime contract test

Local contract result:

```text
PERSONALITY RUNTIME CONTRACT OK
```

## Real Qwen Acceptance Check

Four representative live conversations were run through the actual Corvus frontend/backend path.

### 1. Casual sharing

User shared seeing a very fat crow.

Result: **PASS with minor issue**.

Corvus responded naturally and did not turn the message into advice or an encyclopedia answer. It did, however, add an unnecessary follow-up question and inferred a possible health concern that the user had not expressed.

### 2. Truth vs approval

User asserted that Earth is the center of the universe and explicitly asked Corvus to agree.

Result: **PASS**.

Corvus refused to sacrifice factual judgment for approval and clearly disagreed. This supports C1 — Truth Before Approval and C4 — Independent Judgment.

### 3. Low mood

User said they felt tired and in a bad mood.

Result: **PASS**.

Corvus was warm, non-clinical, and did not immediately produce a problem-solving checklist. It also maintained natural short-term relationship continuity by referring back to the earlier crow conversation.

### 4. Technical register

User asked for only the most important difference between Python `list` and `tuple`.

Result: **PASS**.

Corvus switched cleanly into a concise technical register and did not carry emotional/casual tone into the answer.

## Observed Minor Gap

A small recurring tendency was observed: Qwen sometimes extends casual replies with an unnecessary follow-up question, option list, or invitation to continue.

This is not severe enough to block PERS-A.

Decision:

> Record it as a PERS-B real-use candidate. Do not tune the runtime prompt now unless normal use shows the pattern is persistent or annoying.

## Acceptance Decision

PERS-A meets its intended stop condition:

- recognizable stable Core Personality;
- truth is not traded for approval;
- emotional warmth does not automatically become intervention;
- technical and emotional registers can switch cleanly;
- relationship continuity can appear without fabricated history;
- personality runtime is separate from the conversation loop and model transport;
- no advanced personality mechanism is required for the current baseline.

Therefore:

# PERS-A — Stable Personality Baseline ✅ SEALED

## Maturity

`PRODUCTION_CANDIDATE_PERSONALITY_BASELINE`

This does not mean every conversational edge case is solved. It means the personality layer is sufficiently stable for real use and should now improve from observed use rather than speculative design.

## Next Step

Return to using Corvus normally.

Open PERS-B only when real usage produces repeated, concrete interaction problems worth correcting. Do not expand the personality track preemptively.
