# A3.4c6 — SearchResult Safe Fetch Bridge

Date: 2026-09-15

## Status

CHECKPOINT READY

This checkpoint connects ephemeral Web search results to the existing
Safe Public Fetch boundary.

Corvus can now fetch a discovered page by turn-local SearchResult ID
without exposing arbitrary URL fetch authority to callers.

---

## Goal

Bridge:

    SearchDiscovery
        ->
    result_id
        ->
    server-side SearchResult resolution
        ->
    existing Safe Public Fetch

while preserving:

- result-ID authority boundary
- public URL validation
- SSRF protection
- DNS rebinding protection
- redirect revalidation
- response size limits
- content-type limits
- read-only GET behavior
- ephemeral search semantics

---

## Added

    app/web_search_fetch.py
    tests/test_web_search_fetch.py

---

## Result-ID Fetch Boundary

The new function:

    fetch_search_result(...)

accepts:

    SearchDiscovery
    result_id

It does not accept an arbitrary caller-supplied URL.

The result ID is resolved against the current SearchDiscovery object.

Only the URL already attached to that validated SearchResult is passed
to:

    fetch_public_page(...)

This preserves the Web v1 authority boundary:

> Search results may identify fetch targets.
> Callers may not grant arbitrary fetch targets.

---

## Returned Record

The bridge returns a FetchedSearchResult containing:

- result_id
- provider
- title
- original source URL
- final fetched URL
- HTTP status
- media type
- fetched text
- bytes read
- redirect chain

No persistence occurs at this stage.

---

## New Contracts

Passed:

    WEB SEARCH RESULT-ID FETCH CONTRACT OK
    WEB SEARCH NO-ARBITRARY-URL CONTRACT OK
    WEB SEARCH SAFE-FETCH BRIDGE CONTRACT OK
    WEB SEARCH FETCH RESPONSE CONTRACT OK

---

## Regression Contracts

Existing Web discovery contracts remained green:

    WEB SEARCH EPHEMERAL CONTRACT OK
    WEB SEARCH RESULT SAFETY CONTRACT OK
    WEB SEARCH RESULT-ID CONTRACT OK
    WEB SEARCH DEDUP CONTRACT OK
    WEB SEARCH BOUNDARY CONTRACT OK

Existing Safe Public Fetch contracts remained green:

    WEB PINNED-IP FETCH CONTRACT OK
    WEB DNS REBINDING BOUNDARY CONTRACT OK
    WEB REDIRECT REVALIDATION CONTRACT OK
    WEB CONTENT BOUNDARY CONTRACT OK
    WEB RESPONSE SIZE CONTRACT OK
    WEB READ-ONLY REQUEST CONTRACT OK

Routing and SearXNG contracts also remained green.

---

## Live Acceptance

Live query:

    Python 3.14 release notes

Selected route:

    en-general

Search results included:

    result_1
    What's new in Python 3.14 — Python 3.14.7 documentation

Source:

    https://docs.python.org/3/whatsnew/3.14.html

The page was then fetched using:

    result_1

Observed:

    status = 200
    media_type = text/html
    bytes_read = 536817
    text_chars = 536237
    redirect_count = 0

Result:

    LIVE_SEARCH_RESULT_SAFE_FETCH=PASS

    A3_4C6_LIVE_ACCEPTANCE=PASS

This validates the complete live path:

    search
        ->
    SearchResult
        ->
    result_id
        ->
    Safe Public Fetch
        ->
    real public page

---

## Important Observation

The live Python documentation page produced more than 500,000 characters
of raw fetched text.

This confirms that raw fetched page content must not be injected directly
into Working Context.

The next layer must perform bounded extraction and evidence selection.

---

## Architecture Boundary

This checkpoint still does not:

- extract readable article content
- remove HTML/navigation boilerplate
- rank page passages
- select exact used evidence
- persist External Evidence
- build Web-grounded Working Context
- generate cited model answers
- expose Web search through normal chat

Those remain later steps.

---

## Maturity

Search discovery:

    LIVE VALIDATED

Search routing and fallback:

    LIVE VALIDATED

SearchResult -> Safe Public Fetch:

    LIVE VALIDATED

Search -> extraction -> evidence -> answer:

    NOT YET IMPLEMENTED

---

## Next

Next work should introduce a bounded page extraction layer.

Target:

    FetchedSearchResult.text
        ->
    readable text extraction
        ->
    bounded candidate passages
        ->
    evidence selection

The extraction layer must remain separate from:

- Web transport
- search routing
- memory persistence
- model prompting

---

## Checkpoint

A3.4c6 SearchResult Safe Fetch Bridge:

    PASS
