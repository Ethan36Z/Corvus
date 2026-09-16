# A3.4c9d2b — Runtime Web Evidence Persistence

Date: 2026-09-15

## Status

CHECKPOINT READY

This checkpoint closes the runtime provenance loop between the exact
Used Web Evidence supplied to the model and the External Web Evidence
persisted against the resulting assistant message.

---

## Baseline

Baseline commit:

    aba50ca
    Add atomic Web evidence batch persistence

Before this checkpoint:

- UsedWebEvidence could enter the normal conversation runtime
- Web evidence could be packed into Working Context
- the local model could answer using that evidence
- atomic Web evidence batch persistence existed

but conversation_runtime did not yet connect the model-used evidence
to persistence.

---

## Runtime Provenance Flow

The successful Web-grounded turn now follows:

    canonical user SQLite commit
        ->
    UsedWebEvidence tuple
        ->
    Web prompt packing
        ->
    Working Context
        ->
    model inference
        ->
    assistant canonical SQLite commit
        ->
    same UsedWebEvidence tuple
        ->
    atomic Web evidence batch persistence
        ->
    dense synchronization

No Web re-search, re-fetch, re-ranking, re-selection, summarization, or
evidence reconstruction occurs between model inference and persistence.

---

## Exact Evidence Contract

The runtime converts the same UsedWebEvidence objects supplied to the
prompt packer into the batch persistence representation.

Persisted fields are taken directly from those objects:

    ordinal
    source_url
    source_title
    excerpt

Most importantly:

    persisted excerpt == model-used excerpt

Contract:

    WEB RUNTIME EXACT-EVIDENCE PERSISTENCE CONTRACT OK

---

## Assistant-First Canonical Boundary

The assistant reply is committed before Web provenance persistence is
attempted.

Ordering contract:

    model succeeds
        ->
    assistant message commits
        ->
    Web evidence persistence begins

Contract:

    WEB RUNTIME ASSISTANT-BEFORE-PROVENANCE ORDER CONTRACT OK

This preserves canonical conversation independently of a derived
provenance subsystem.

---

## Successful Web Persistence

After successful atomic Web evidence persistence:

    web_evidence_status = PERSISTED

and:

    web_evidence_persisted_count

records the number of persisted evidence rows.

The evidence references used in the prompt remain available through:

    web_evidence_refs

---

## Persistence Failure Semantics

If Web evidence persistence fails after the assistant message has
already committed:

    assistant message remains canonical
    complete Web evidence batch is rolled back
    Web evidence persisted count remains 0
    runtime reports degraded provenance
    dense synchronization still continues

Runtime state:

    web_evidence_status =
        USED_PERSISTENCE_FAILED

    persistence_status =
        WEB_EVIDENCE_PERSISTENCE_DEGRADED

The failure is surfaced through:

    web_evidence_error
    error

Contracts:

    WEB PERSISTENCE FAILURE PRESERVES ASSISTANT EVIDENCE OK
    WEB PERSISTENCE FAILURE CONTINUES DENSE SYNC OK

---

## Atomic Persistence Dependency

The runtime uses:

    record_web_evidence_batch()

from A3.4c9d2a.

Therefore multiple Used Web Evidence rows are persisted as one SQLite
transaction.

The runtime never loops over the old single-row persistence API.

---

## Canonical / Derived Failure Principle

This checkpoint preserves the Corvus rule:

    canonical evidence must not be lost because a derived subsystem fails

User and assistant conversation messages remain canonical.

External Web provenance is important and auditable, but persistence
failure does not delete an otherwise successful conversation turn.

---

## Contracts

Passed:

    WEB RUNTIME SQLITE-FIRST CARRIER CONTRACT OK
    WEB RUNTIME MODEL-INPUT CONTRACT OK
    WEB RUNTIME EVIDENCE-REF CONTRACT OK
    WEB RUNTIME EXACT-EVIDENCE PERSISTENCE CONTRACT OK
    WEB RUNTIME ASSISTANT-BEFORE-PROVENANCE ORDER CONTRACT OK
    NON-WEB RUNTIME BACKWARD-COMPATIBILITY CONTRACT OK
    WEB PACK FAILURE PRESERVES USER EVIDENCE OK
    WEB PERSISTENCE FAILURE PRESERVES ASSISTANT EVIDENCE OK
    WEB PERSISTENCE FAILURE CONTINUES DENSE SYNC OK

    A3_4C9D2B_RUNTIME_WEB_EVIDENCE_PERSISTENCE=PASS

---

## Atomic Store Regression

Passed:

    WEB EVIDENCE BATCH SUCCESS CONTRACT OK
    WEB EVIDENCE BATCH ROLLBACK CONTRACT OK
    WEB EVIDENCE PREWRITE VALIDATION CONTRACT OK
    WEB EVIDENCE ASSISTANT-ONLY CONTRACT OK
    WEB EVIDENCE EMPTY-BATCH CONTRACT OK

    A3_4C9D2A_ATOMIC_WEB_EVIDENCE_BATCH_STORE=PASS

Existing persistence contracts also remain green:

    WEB USED-EVIDENCE PERSISTENCE CONTRACT OK
    WEB RETRIEVAL NON-PERSISTENCE CONTRACT OK
    WEB USER-EVIDENCE SEPARATION CONTRACT OK
    WEB SOURCE SAFETY CONTRACT OK

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

## Not Yet Implemented

This checkpoint still does not perform Web discovery automatically.

Not yet wired:

- search routing from a chat request
- SearXNG discovery from `/api/chat`
- Safe Fetch orchestration
- extraction / passage / ranking orchestration
- Web mode request field
- source metadata in the chat API response
- citation validation
- deployed SearXNG runtime networking
- live end-to-end Web-grounded chat

---

## Next

The evidence path is now closed.

The next major task should move upward from persistence plumbing to Web
orchestration:

    user query
        ->
    search plan
        ->
    discovery
        ->
    Safe Fetch
        ->
    extraction
        ->
    passage construction
        ->
    ranking
        ->
    UsedWebEvidence
        ->
    process_turn()

At that point the existing Web components begin operating as one
product-level pipeline rather than isolated foundations.

---

## Checkpoint

A3.4c9d2b Runtime Web Evidence Persistence:

    PASS
