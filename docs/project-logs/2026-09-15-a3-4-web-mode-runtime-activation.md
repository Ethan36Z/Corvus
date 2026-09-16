# A3.4 — Web Mode Runtime Activation

Date: 2026-09-15

## Status

CHECKPOINT READY

This checkpoint activates explicit Web grounding inside the persistent
conversation runtime while preserving Corvus SQLite-first semantics.

It does not yet expose Web mode through `/api/chat`.

---

## Baseline

Baseline commit:

    372cc0a
    Add Web grounding orchestration foundation

Before this checkpoint, Corvus had:

    query
        ->
    Web orchestration
        ->
    UsedWebEvidence

and separately:

    UsedWebEvidence
        ->
    conversation runtime
        ->
    model
        ->
    assistant persistence
        ->
    exact Web provenance persistence

The missing connection was runtime-controlled Web activation.

---

## Runtime Web Mode

`process_turn()` now accepts:

    web_mode="off"

Supported values:

    off
    on

Default:

    off

This preserves existing text, vision, voice, and preselected-evidence
behavior unless Web mode is explicitly enabled.

---

## SQLite-First Ordering

Web discovery does not happen before canonical user persistence.

Successful Web-mode ordering is:

    canonical user SQLite commit
        ->
    optional attachment / voice perception
        ->
    Web grounding
        ->
    UsedWebEvidence
        ->
    Web evidence prompt packing
        ->
    Working Context
        ->
    model inference
        ->
    assistant SQLite commit
        ->
    exact Web evidence persistence
        ->
    dense synchronization

Contract:

    WEB MODE USER-COMMIT-BEFORE-GROUNDING CONTRACT OK

This preserves the Corvus rule:

    STORE ALL EXPERIENCE

A network failure must not erase what the user just said.

---

## Voice + Web Semantics

For voice turns:

    raw audio marker remains canonical user evidence

while:

    STT transcript is derived perception

When Web mode is enabled for a voice turn, the derived transcript is
used as the Web grounding query.

The transcript does not replace the canonical raw-audio evidence.

---

## Default Web Provider

The runtime has a default provider builder backed by:

    SearXNGProvider

Search route parameters come from the existing deterministic
SearchPlan attempt:

    category
    language
    engine_bang
    time_range

The provider remains discovery-only.

Safe Public Fetch continues to own public-page network access.

---

## Successful Grounding

When:

    web_mode = on

and orchestration returns:

    status = READY

the returned UsedWebEvidence tuple is passed directly into the existing
Web evidence runtime path.

No additional search, re-ranking, re-selection, or evidence rewriting
occurs after orchestration.

Contract:

    WEB MODE GROUNDING-TO-RUNTIME CONTRACT OK

The exact evidence subsequently persisted remains the same evidence
supplied to the model.

Contract:

    WEB MODE EXACT-EVIDENCE PERSISTENCE CONTRACT OK

---

## Fail-Closed Web Semantics

If Web grounding raises an exception:

    canonical user message remains persisted
    assistant message is not created
    model is not called
    ungrounded answer is not fabricated

Runtime reports:

    web_grounding_status =
        WEB_GROUNDING_FAILED

    web_evidence_status =
        NOT_AVAILABLE

Contract:

    WEB MODE FAILURE PRESERVES USER EVIDENCE OK
    WEB MODE FAILURE BLOCKS UNGROUNDED MODEL ANSWER OK

If orchestration completes but returns no usable evidence, for example:

    NO_RESULTS
    NO_USABLE_EVIDENCE

the runtime also fails closed before model inference.

Contract:

    WEB MODE NO-EVIDENCE FAIL-CLOSED CONTRACT OK

---

## Backward Compatibility

With:

    web_mode = off

Web orchestration is never invoked.

Existing non-Web behavior remains unchanged.

Contract:

    WEB MODE OFF BACKWARD-COMPATIBILITY CONTRACT OK

---

## Observability

Runtime results now expose:

    web_mode
    web_grounding_status
    web_grounding_error
    web_grounding_selected_result_id

Existing Web evidence observability remains:

    web_evidence_status
    web_evidence_error
    web_evidence_refs
    web_evidence_prompt_chars
    web_evidence_persisted_count

---

## Existing Regression

Passed:

    Web runtime carrier
    exact Web evidence persistence
    Web orchestration
    atomic Web evidence batch persistence
    unified Working Context
    Voice runtime
    Vision runtime
    Voice API
    Personality runtime
    SearXNG provider adapter

No existing runtime behavior regressed.

---

## Product Boundary

This checkpoint does not yet change the public chat API.

Current user-facing API behavior remains Web-off by default.

Still not implemented here:

- ChatRequest Web mode field
- `/api/chat` Web activation
- Web status in chat response
- source metadata in API response
- UI Web control
- live deployed Web E2E acceptance

---

## Next

Expose explicit Web activation through `/api/chat`.

Target flow:

    POST /api/chat
        web_mode = on
            ->
        process_turn(
            web_mode="on"
        )
            ->
        SQLite-first Web grounding
            ->
        grounded answer

The API should preserve:

    web_mode = off

as the default for backward compatibility.

---

## Checkpoint

A3.4 Web Mode Runtime Activation:

    PASS
