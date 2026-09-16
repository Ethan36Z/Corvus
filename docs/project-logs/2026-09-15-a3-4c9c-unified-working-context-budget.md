# A3.4c9c — Unified Working Context Budget

Date: 2026-09-15

## Status

CHECKPOINT READY

This checkpoint integrates optional current-turn Web evidence into the
existing Corvus Working Context input-token budget.

Web evidence is no longer treated as extra context outside the existing
model-input budget.

---

## Baseline

Existing Working Context defaults:

    recent_token_budget = 4096
    historical_token_budget = 2048
    input_token_budget = 7168

Existing final eviction order before this checkpoint:

    historical evidence
        ->
    oldest recent messages

The Web integration preserves the existing total input budget rather
than increasing it implicitly.

---

## New Input

`build_working_context()` now accepts:

    web_evidence_content

This value is expected to be the already-packed current-turn External
Web Evidence block produced by A3.4c9b.

The Working Context layer does not perform:

- Web search
- Web fetching
- extraction
- passage ranking
- evidence selection
- prompt packing

It only budgets the already-prepared Web evidence block.

---

## Unified Budget Rule

Web evidence participates inside the existing total input-token budget.

Conceptually:

    system/personality
    + historical memory
    + current Web evidence
    + recent conversation
    + current user message

must fit inside:

    input_token_budget

Web evidence is not appended after budgeting.

---

## Foreground Priority

Current checkpoint policy:

    system/personality + current user
        mandatory

    current-turn Web evidence
        foreground / retained

    recent conversation
        continuity context

    historical recalled memory
        opportunistic context

When the final context exceeds the total budget:

    historical memory yields first

then:

    recent conversation yields second

Current Web evidence is not silently truncated.

If:

    system/personality
    + current Web evidence
    + current user message

still exceeds the total budget after optional context is removed, context
construction fails explicitly.

---

## Exact-Evidence Invariant

This checkpoint does not truncate or rewrite Web evidence.

That preserves the existing provenance goal:

    evidence shown to the model
        ==
    exact selected evidence eligible for persistence

If the selected Web evidence cannot fit, the runtime must resolve that
before model inference rather than silently changing the evidence here.

---

## Recent Conversation Shape

The existing final recent-message eviction removed messages one at a
time.

This checkpoint strengthens the invariant so that after eviction the
remaining recent context cannot begin with an assistant message.

If removing the oldest message exposes a leading assistant message,
that assistant message is also removed.

The final recent context therefore retains a valid conversational shape.

---

## Observability

Working Context now reports:

    web_evidence_included

and:

    web_evidence_prompt_chars

The character count refers to the complete packed Web prompt block, not
only the raw External Evidence excerpt characters.

Token accounting remains based on the existing model-native
`count_tokens()` path.

---

## Structural Patch Safety

Initial text-patching attempts correctly failed before repository writes
because assumptions about indentation/counts did not match the actual
source structure.

The final patch enumerated the five real `_compose_working_messages()`
call sites structurally and inserted the Web argument according to each
call's own indentation.

Result:

    STRUCTURAL_COMPOSE_INSERTIONS=5
    WORKING_CONTEXT_WEB_BUDGET_PATCH=PASS

The failed attempts left the working tree clean.

---

## Focused Contracts

Passed:

    WEB CONTEXT HISTORICAL-FIRST EVICTION CONTRACT OK

    WEB CONTEXT RECENT-TURN EVICTION CONTRACT OK

    WEB CONTEXT MANDATORY-BUDGET FAILURE CONTRACT OK

    NON-WEB WORKING CONTEXT COMPATIBILITY CONTRACT OK

    A3_4C9C_UNIFIED_WORKING_CONTEXT_CONTRACT=PASS

---

## Runtime Regression

Existing behavior remained green:

    PERSONALITY RUNTIME CONTRACT OK

    VOICE SQLITE-FIRST ORDER OK
    VOICE TRANSCRIPT PERCEPTION OK
    VOICE CURRENT-TURN MODEL INPUT OK
    STT FAILURE PRESERVES RAW EVIDENCE OK
    A3.3 VOICE CONVERSATION RUNTIME: PASS

    RUNTIME BACKWARD SIGNATURE CONTRACT OK
    TEXT TURN REGRESSION CONTRACT OK
    VISION TURN ORDER CONTRACT OK
    LINK FAILURE PRESERVES USER EVIDENCE OK
    VISION FAILURE PRESERVES CANONICAL EVIDENCE OK
    A3 VISION CONVERSATION RUNTIME: PASS

---

## Web Regression

Existing Web contracts remained green:

    WEB EVIDENCE PROMPT EXACT-EXCERPT CONTRACT OK
    WEB EVIDENCE PROMPT CITATION-REF CONTRACT OK
    WEB EVIDENCE PROMPT UNTRUSTED-DATA CONTRACT OK
    WEB EVIDENCE PROMPT INJECTION-BOUNDARY CONTRACT OK
    WEB EVIDENCE PROMPT CPU-ONLY CONTRACT OK

    WEB USED-EVIDENCE EXACT-SLICE CONTRACT OK
    WEB USED-EVIDENCE BUDGET CONTRACT OK
    WEB USED-EVIDENCE OVERLAP CONTRACT OK
    WEB USED-EVIDENCE SOURCE-PROVENANCE CONTRACT OK
    WEB USED-EVIDENCE NO-MODEL BOUNDARY CONTRACT OK

---

## Compute Boundary

This checkpoint performs no model inference.

Web preparation remains:

    search
        ->
    Safe Fetch
        ->
    CPU extraction
        ->
    CPU passage construction
        ->
    CPU lexical ranking
        ->
    CPU evidence selection
        ->
    CPU prompt packing
        ->
    Working Context budgeting

GPU use still begins only when the final model-facing messages are
actually sent to the local model.

---

## Not Yet Implemented

This checkpoint does not yet provide:

- automatic Web decision/routing from normal chat
- conversation-runtime Web orchestration
- actual model generation using live Web evidence
- persistence of Used Web Evidence after assistant reply
- citation validation
- Web-aware generation-token policy

---

## Response-Budget Principle

The previously established principle remains:

    Web grounding raises the available response budget,
    not the required response length.

This checkpoint concerns input budgeting only.

Dynamic output-token allocation remains future runtime work.

---

## Next

Next work should connect the current Web pipeline to the conversation
runtime:

    user request
        ->
    Web discovery/fetch/extract/select/pack
        ->
    build_working_context(
        web_evidence_content=...
    )
        ->
    model

That runtime integration must preserve:

- SQLite-first user evidence
- exact Web evidence identity
- existing attachment / Voice / Vision behavior
- bounded model input
- failure isolation

Persistence of the exact Used Web Evidence should occur only after the
assistant message exists.

---

## Checkpoint

A3.4c9c Unified Working Context Budget:

    PASS
