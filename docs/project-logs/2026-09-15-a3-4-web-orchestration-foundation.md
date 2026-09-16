# A3.4 — Web Orchestration Foundation

Date: 2026-09-15

## Status

CHECKPOINT READY

This checkpoint composes the existing Corvus Web v1 components into
one current-turn Web grounding preparation pipeline.

It does not yet connect Web orchestration to `/api/chat`.

---

## Baseline

Baseline commit:

    6e55179
    Persist runtime Web evidence provenance

Before this checkpoint, Corvus already had production-candidate
foundations for:

    search routing
    search execution
    SearXNG discovery
    SearchResult validation
    Safe Public Fetch
    extraction
    passage construction
    lexical ranking
    Used Web Evidence selection
    prompt packing
    Working Context budgeting
    runtime evidence transport
    atomic evidence persistence

Those components were individually tested but did not yet have one
product-level orchestration entry point.

---

## New Orchestration Entry Point

New module:

    app/web_orchestration.py

New function:

    prepare_web_grounding()

The pipeline is:

    query
        ->
    build_search_plan()
        ->
    execute_search_plan()
        ->
    SearchDiscovery
        ->
    bounded candidate iteration
        ->
    fetch_search_result()
        ->
    Safe Public Fetch
        ->
    extract_web_page()
        ->
    build_web_passages()
        ->
    rank_web_passages()
        ->
    select_used_web_evidence()
        ->
    UsedWebEvidence

The orchestration layer performs no model inference and no persistence.

---

## Candidate Fallback

Search discovery may return multiple SearchResults.

The orchestration layer attempts a bounded number of candidates in rank
order.

A candidate may fail because of:

    fetch failure
    extraction failure
    passage failure
    evidence-selection failure
    no relevant evidence

When a candidate fails, the next candidate may be tried.

Contract:

    WEB ORCHESTRATION RESULT FALLBACK CONTRACT OK

---

## Current Web v1 Source Policy

This checkpoint intentionally uses evidence from the first usable
source page only.

It does not yet merge evidence from multiple pages.

Reason:

    select_used_web_evidence()

currently assigns local evidence references and ordinals beginning at:

    web_1
    ordinal = 0

for one ExtractedWebPage.

Naively concatenating evidence from multiple pages would create
duplicate evidence references and ordinals.

Therefore this checkpoint chooses correctness over premature
multi-source composition.

Future multi-source grounding should add an explicit global evidence
merge / resequencing contract.

---

## Grounding Status

Successful preparation:

    status = READY

and returns:

    selected_result_id
    used_web_evidence
    candidate_outcomes

No search results:

    status = NO_RESULTS

Search results exist but no candidate produces usable relevant evidence:

    status = NO_USABLE_EVIDENCE

---

## Security Boundary

This orchestration layer preserves the existing Web security design.

The model does not receive arbitrary URL authority.

Fetch still flows through:

    SearchResult ID
        ->
    discovery lookup
        ->
    Safe Public Fetch

The orchestration layer does not weaken:

    SSRF protection
    DNS validation
    redirect validation
    localhost / LAN blocking
    response size limits
    read-only Web semantics

Principle remains:

    READ THE WEB, NEVER ACT ON THE WEB

---

## Persistence Boundary

Search execution remains ephemeral.

Fetch and intermediate extraction state remain ephemeral.

Only Used Web Evidence that later matters to a successful model answer
is eligible for persistence through the existing runtime provenance
path.

Principle:

    Web retrieval is ephemeral.
    Used evidence is persistent.

---

## Contracts

Passed:

    WEB ORCHESTRATION SEARCH-TO-EVIDENCE CONTRACT OK
    WEB ORCHESTRATION RESULT FALLBACK CONTRACT OK
    WEB ORCHESTRATION NO-RESULT CONTRACT OK
    WEB ORCHESTRATION NO-USABLE-EVIDENCE CONTRACT OK

    A3_4_WEB_ORCHESTRATION_FOUNDATION=PASS

---

## Pipeline Regression

Passed:

    Web search routing
    Web search execution
    SearchResult-ID Safe Fetch bridge
    extraction
    passage construction
    multilingual lexical ranking
    Used Web Evidence exact-slice selection
    evidence provenance boundaries

---

## Runtime Regression

Passed:

    runtime Web evidence carrier
    exact model-used evidence persistence
    assistant-before-provenance ordering
    atomic Web evidence batch persistence
    Web persistence failure degradation
    unified Working Context budgeting

Existing non-Web runtime contracts remain green.

---

## Not Yet Implemented

This checkpoint does not yet provide:

- `/api/chat` Web request mode
- automatic Web invocation from chat
- UI Web toggle
- API source metadata
- citation validation
- multi-source evidence merging
- live deployed SearXNG runtime wiring
- end-to-end user-visible Web chat

---

## Next

The next product-level integration should connect:

    /api/chat
        ->
    explicit Web request
        ->
    prepare_web_grounding()
        ->
    UsedWebEvidence
        ->
    process_turn()

The first version should use explicit Web activation rather than giving
the model autonomous network-request authority.

---

## Checkpoint

A3.4 Web Orchestration Foundation:

    PASS
