# A3.4 — Web API Entry

Date: 2026-09-15

## Status

CHECKPOINT READY

This checkpoint exposes explicit Web mode through the Corvus chat API.

The API now forwards an explicit Web activation request into the
already validated SQLite-first conversation runtime.

---

## Baseline

Baseline commit:

    f4f32b4
    Activate SQLite-first Web mode runtime

Before this checkpoint, Web mode existed only inside process_turn().

The public chat request schema did not yet expose a Web activation
field.

---

## Chat Request

ChatRequest now accepts:

    web_mode: str = "off"

Supported values:

    off
    on

Default:

    off

This preserves backward compatibility for existing clients.

---

## API Runtime Flow

With:

    web_mode = on

the API forwards:

    process_turn(
        ...
        web_mode="on"
    )

The runtime remains responsible for the security-critical ordering:

    canonical user SQLite commit
        ->
    Web grounding
        ->
    UsedWebEvidence
        ->
    Working Context
        ->
    model
        ->
    assistant SQLite commit
        ->
    exact Web evidence persistence

The API does not perform discovery or fetching directly.

---

## Invalid Mode

Any Web mode other than:

    off
    on

fails with HTTP 400 before the conversation runtime is called.

Contract:

    WEB API INVALID-MODE FAIL-CLOSED CONTRACT OK

---

## API Observability

Chat responses now expose:

    web_mode
    web_grounding_status
    web_grounding_selected_result_id
    web_evidence_status
    web_evidence_refs
    web_evidence_persisted_count
    web_grounding_error
    web_evidence_error

The nested status object also exposes:

    status.web_grounding
    status.web_evidence

This makes Web grounding behavior inspectable without exposing
intermediate search or fetch internals.

---

## Backward Compatibility

Requests that omit web_mode continue to behave as:

    web_mode = off

Contract:

    WEB API DEFAULT-OFF BACKWARD-COMPATIBILITY CONTRACT OK

Existing Voice API behavior remains unchanged.

Existing text behavior remains unchanged.

---

## Contracts

Passed:

    WEB API MODE FORWARDING CONTRACT OK
    WEB API OBSERVABILITY CONTRACT OK
    WEB API DEFAULT-OFF BACKWARD-COMPATIBILITY CONTRACT OK
    WEB API INVALID-MODE FAIL-CLOSED CONTRACT OK

    A3_4_WEB_API_ENTRY=PASS

---

## Regression

Passed:

    Voice API contract
    Web mode runtime activation
    SQLite-first Web evidence carrier
    exact Web evidence persistence
    Web orchestration foundation
    Voice conversation runtime
    Vision conversation runtime

---

## Product Boundary

This checkpoint creates the product API entry but does not yet perform
a deployed live acceptance.

Still pending:

- localhost live Web-grounded chat acceptance
- source/citation response audit
- UI Web control
- deployed Private/Demo wiring verification
- Web v1 seal

---

## Next

Run a localhost live acceptance against the Private Corvus API and
local SearXNG.

Target:

    POST /api/chat
        web_mode = on
            ->
        real SearXNG discovery
            ->
        Safe Public Fetch
            ->
        extraction / ranking
            ->
        UsedWebEvidence
            ->
        Qwen grounded answer
            ->
        persisted External Web Evidence

No public exposure changes are required for that acceptance.

---

## Checkpoint

A3.4 Web API Entry:

    PASS
