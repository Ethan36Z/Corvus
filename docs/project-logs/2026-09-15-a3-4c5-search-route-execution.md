# A3.4c5 — Web Search Route Execution

Date: 2026-09-15

## Status

CHECKPOINT READY

This checkpoint turns the previously validated Web search routing policy
into executable ordered search attempts.

Corvus can now automatically fall back to another discovery route when
the preferred route is empty or its provider fails.

---

## Goal

Execute SearchPlan attempts in order while preserving:

- ephemeral discovery
- provider replaceability
- existing SearchResult validation
- Safe Public Fetch boundary
- no Web persistence at the search stage

---

## Changes

Modified:

    app/searxng_provider.py
    tests/test_searxng_provider.py

Added:

    app/web_search_execution.py
    tests/test_web_search_execution.py

---

## SearXNG Route Support

SearXNGProvider now supports route-specific configuration:

- category
- language
- engine bang
- time range

It can derive a routed provider using:

    with_route(...)

Examples:

    category=news
    language=zh-CN

or:

    category=general
    language=zh-CN
    engine_bang=goc
    time_range=day

The existing provider abstraction remains intact.

---

## Route Execution

The new execution layer:

    execute_search_plan(...)

runs SearchPlan attempts in order.

Behavior:

    success
        -> stop and return discovery

    empty result
        -> try next route

    WEB_SEARCH_PROVIDER_FAILED
        -> try next route

    all routes exhausted
        -> return no selected discovery

Other SearchDiscovery errors are not silently swallowed.

---

## Contracts

Existing Web search contracts remained green:

    WEB SEARCH EPHEMERAL CONTRACT OK
    WEB SEARCH RESULT SAFETY CONTRACT OK
    WEB SEARCH RESULT-ID CONTRACT OK
    WEB SEARCH DEDUP CONTRACT OK
    WEB SEARCH BOUNDARY CONTRACT OK

Routing contracts remained green:

    WEB SEARCH ROUTING LANGUAGE CONTRACT OK
    WEB SEARCH ROUTING NEWS INTENT CONTRACT OK
    WEB SEARCH ROUTING FALLBACK CONTRACT OK
    WEB SEARCH ROUTING PURE POLICY CONTRACT OK

SearXNG route contract:

    SEARXNG ROUTE PARAMETER CONTRACT OK

Execution contracts:

    WEB SEARCH ROUTE EXECUTION CONTRACT OK
    WEB SEARCH EMPTY FALLBACK CONTRACT OK
    WEB SEARCH PROVIDER FAILURE FALLBACK CONTRACT OK
    WEB SEARCH ALL-ROUTES-EXHAUSTED CONTRACT OK

---

## Live Validation

Live query:

    洛杉矶 今日 新闻

Generated plan:

    1. zh-news
    2. zh-general-goc

Observed outcomes:

    zh-news
        -> empty

    zh-general-goc
        -> success

Selected route:

    zh-general-goc

Returned:

    5 results

Observed sources included:

- 世界新闻网
- 大洛杉矶新闻
- 联合早报
- 洛城焦点

Result:

    LIVE_ROUTED_SEARCH=PASS

This is the first live validation that Corvus can automatically change
search routes when the preferred discovery route produces no usable
results.

---

## Architecture Boundary

This checkpoint still performs discovery only.

It does not yet:

- fetch selected result pages
- extract page content
- select External Evidence
- persist Web Evidence
- construct Web-grounded Working Context
- generate cited answers
- expose Web search through the chat runtime

The existing Safe Public Fetch boundary remains unchanged.

---

## Maturity

Search routing policy:

    VALIDATED

SearXNG route execution:

    VALIDATED INTEGRATION FOUNDATION

Automatic fallback:

    LIVE VALIDATED

Search -> fetch -> evidence -> answer:

    NOT YET IMPLEMENTED

---

## Next

Next work should connect selected SearchResult IDs to the existing
Safe Public Fetch layer.

The model must not receive arbitrary URL fetch authority.

Target flow:

    SearchPlan
        ->
    routed discovery
        ->
    selected SearchResult ID
        ->
    Safe Public Fetch
        ->
    extraction / evidence selection
        ->
    External Evidence
        ->
    cited answer

---

## Checkpoint

A3.4c5 Web Search Route Execution:

    PASS
