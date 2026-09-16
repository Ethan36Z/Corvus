# A3.4c9d2a — Atomic Web Evidence Batch Store

Date: 2026-09-15

## Status

CHECKPOINT READY

This checkpoint adds atomic persistence for one complete Used Web
Evidence set.

It does not yet wire persistence into conversation_runtime.

---

## Baseline

Baseline commit:

    d3b51f7
    Carry Web evidence through conversation runtime

Before this checkpoint, `record_web_evidence()` persisted one evidence
row per connection and commit.

A runtime loop over multiple Used Web Evidence items could therefore
leave partial provenance if a later insert failed.

Example failure shape:

    web_1 committed
    web_2 failed
    web_3 never attempted

That state is not acceptable for auditable grounded answers.

---

## New Atomic Batch Store

New function:

    record_web_evidence_batch(
        assistant_message_id,
        evidence_items,
    )

The batch path:

    validate complete input set
        ->
    open one SQLite connection
        ->
    BEGIN
        ->
    verify target message is assistant
        ->
    insert every evidence row
        ->
    COMMIT

If any database write fails:

    ROLLBACK

The complete Used Web Evidence set therefore succeeds or fails as one
transaction.

---

## Prewrite Validation

Before database writes begin, the batch validates:

- evidence_items is iterable
- every item is a dict
- ordinal exists and is an integer
- ordinals are contiguous and zero-based
- source_url exists
- source_url passes the existing public-Web security validator
- excerpt exists and is non-empty
- evidence IDs are normalized
- duplicate evidence IDs inside the batch are rejected

This prevents known-invalid input from creating partial persistence.

---

## Assistant-Only Boundary

Web evidence may only attach to an existing assistant message.

User messages remain canonical User Evidence and cannot receive External
Web Evidence rows.

This preserves the provenance separation:

    User Evidence
    !=
    External Evidence
    !=
    Model Output

---

## Transaction Atomicity Contract

The test deliberately creates this sequence:

    insert web evidence row 1 successfully
        ->
    insert row 2 with a duplicate primary-key ID
        ->
    SQLite IntegrityError
        ->
    rollback transaction

After failure, the target assistant has:

    0 Web evidence rows

and the first inserted row does not leak into the database.

Passed:

    WEB EVIDENCE BATCH ROLLBACK CONTRACT OK

This proves transaction rollback rather than merely pre-validation.

---

## Compatibility

The existing single-row:

    record_web_evidence()

implementation remains unchanged.

The new batch API is additive.

Existing Web evidence persistence behavior therefore remains compatible.

---

## Contracts

Passed:

    WEB EVIDENCE BATCH SUCCESS CONTRACT OK
    WEB EVIDENCE BATCH ROLLBACK CONTRACT OK
    WEB EVIDENCE PREWRITE VALIDATION CONTRACT OK
    WEB EVIDENCE ASSISTANT-ONLY CONTRACT OK
    WEB EVIDENCE EMPTY-BATCH CONTRACT OK

    A3_4C9D2A_ATOMIC_WEB_EVIDENCE_BATCH_STORE=PASS

---

## Existing Regression

Passed:

    WEB USED-EVIDENCE PERSISTENCE CONTRACT OK
    WEB RETRIEVAL NON-PERSISTENCE CONTRACT OK
    WEB USER-EVIDENCE SEPARATION CONTRACT OK
    WEB SOURCE SAFETY CONTRACT OK

Runtime carrier regression also passed:

    WEB RUNTIME SQLITE-FIRST CARRIER CONTRACT OK
    WEB RUNTIME MODEL-INPUT CONTRACT OK
    WEB RUNTIME EVIDENCE-REF CONTRACT OK
    NON-WEB RUNTIME BACKWARD-COMPATIBILITY CONTRACT OK
    WEB PACK FAILURE PRESERVES USER EVIDENCE OK

    A3_4C9D1_RUNTIME_WEB_CARRIER=PASS

---

## Canonical Conversation Boundary

This checkpoint intentionally does not make the assistant message and
Web evidence one shared transaction.

The assistant reply is canonical conversation evidence and remains
committed even if derived External Web provenance persistence fails.

The intended runtime behavior is:

    assistant canonical commit succeeds
        ->
    atomic Web evidence batch persistence attempted
        ->
    success:
        full evidence set persisted

    failure:
        assistant retained
        Web evidence set = 0 rows
        runtime reports degraded provenance state

This follows the Corvus principle:

    canonical evidence must not be lost because a derived subsystem fails

---

## Not Yet Implemented

This checkpoint does not yet implement:

- conversation_runtime batch persistence wiring
- API Web orchestration
- automatic search
- Web mode request fields
- citation validation
- source metadata in chat responses
- production SearXNG deployment wiring

---

## Next

A3.4c9d2b should wire the same UsedWebEvidence tuple that was supplied
to the model into:

    record_web_evidence_batch()

after the assistant message has been successfully persisted.

The runtime must not re-search, re-rank, re-select, summarize, or
reconstruct the evidence before persistence.

The persisted evidence must be the same evidence set the model saw.

---

## Checkpoint

A3.4c9d2a Atomic Web Evidence Batch Store:

    PASS
