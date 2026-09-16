# A3.4c9d1 — Runtime Web Evidence Carrier

Date: 2026-09-15

## Status

CHECKPOINT READY

This checkpoint connects already-selected Used Web Evidence to the
normal Corvus conversation runtime.

It does not yet perform Web discovery or persist Web evidence.

---

## Baseline

Baseline commit:

    20c2f7d
    Integrate Web evidence into working context budget

Before this checkpoint, Corvus had:

    search
      ->
    Safe Fetch
      ->
    extraction
      ->
    passage construction
      ->
    lexical ranking
      ->
    Used Web Evidence selection
      ->
    Web evidence prompt packing
      ->
    unified Working Context budgeting

but `conversation_runtime.process_turn()` had no path for carrying
Used Web Evidence into the normal model call.

---

## Runtime Input

`process_turn()` now accepts optional:

    used_web_evidence

and an injectable:

    pack_web_evidence_fn

The default packer is the existing A3.4c9b Web evidence prompt packer.

No Web search or fetching occurs inside `process_turn()` in this
checkpoint.

---

## SQLite-First Invariant

Canonical user evidence is still persisted before Web preparation.

The ordering is:

    canonical user SQLite commit
        ->
    optional Web evidence packing
        ->
    Working Context
        ->
    local model
        ->
    assistant SQLite commit
        ->
    dense synchronization

Therefore a Web prompt packing failure cannot erase or prevent the
already-committed canonical user evidence.

Contract:

    WEB PACK FAILURE PRESERVES USER EVIDENCE OK

---

## Exact Evidence Carrier

The runtime receives the selected UsedWebEvidence objects and passes
those same objects to the existing prompt packer.

The resulting packed Web evidence is passed into:

    build_working_context(
        web_evidence_content=...
    )

The model-facing Working Context therefore consumes the evidence
selected by the previous Web pipeline rather than independently
re-selecting or reconstructing evidence.

---

## Backward Compatibility

When no Used Web Evidence is supplied:

    web_evidence_content

is not passed to the injected Working Context function at all.

This preserves compatibility with existing adapters and tests using the
old Working Context callable signature.

Contract:

    NON-WEB RUNTIME BACKWARD-COMPATIBILITY CONTRACT OK

---

## Runtime Observability

The conversation result now exposes:

    web_evidence_status
    web_evidence_error
    web_evidence_refs
    web_evidence_prompt_chars

Initial state:

    web_evidence_status = NOT_REQUESTED

Prepared Web evidence:

    web_evidence_status = PREPARED

After successful model generation using Web evidence:

    web_evidence_status = USED

`web_evidence_refs` contains the stable prompt references such as:

    web_1

---

## Failure Isolation

Invalid or failed Web evidence packing stops the turn before:

- Working Context construction
- model inference
- assistant persistence
- dense synchronization

but after canonical user persistence.

This preserves the existing Evidence Log safety principle:

    canonical evidence first
    derived processing second

---

## Contracts

Passed:

    WEB RUNTIME SQLITE-FIRST CARRIER CONTRACT OK
    WEB RUNTIME MODEL-INPUT CONTRACT OK
    WEB RUNTIME EVIDENCE-REF CONTRACT OK
    NON-WEB RUNTIME BACKWARD-COMPATIBILITY CONTRACT OK
    WEB PACK FAILURE PRESERVES USER EVIDENCE OK

    A3_4C9D1_RUNTIME_WEB_CARRIER=PASS

---

## Existing Runtime Regression

Passed:

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

## Working Context Regression

Passed:

    WEB CONTEXT HISTORICAL-FIRST EVICTION CONTRACT OK
    WEB CONTEXT RECENT-TURN EVICTION CONTRACT OK
    WEB CONTEXT MANDATORY-BUDGET FAILURE CONTRACT OK
    NON-WEB WORKING CONTEXT COMPATIBILITY CONTRACT OK

    A3_4C9C_UNIFIED_WORKING_CONTEXT_CONTRACT=PASS

---

## Web Evidence Regression

Passed:

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

## Important Limitation

`web_evidence_status = USED` currently means:

    the packed evidence was supplied to the successful model call

It does not yet mean:

    the evidence was persisted in the web_evidence table

This distinction is intentional.

---

## Not Yet Implemented

This checkpoint does not yet implement:

- persistence of exact Used Web Evidence
- automatic Web search from `/api/chat`
- search routing from user intent
- live search/fetch orchestration
- citation validation
- API response Web provenance
- dynamic Web-aware output token allocation

---

## Next

A3.4c9d2 should close the provenance loop:

    same UsedWebEvidence
        ->
    model input
        ->
    successful assistant SQLite commit
        ->
    record exact UsedWebEvidence against
    assistant_message_id

The evidence persisted after generation must be the same evidence set
that was supplied to the model.

Do not re-search, re-rank, re-select, summarize, or reconstruct evidence
between model generation and persistence.

---

## Checkpoint

A3.4c9d1 Runtime Web Evidence Carrier:

    PASS
