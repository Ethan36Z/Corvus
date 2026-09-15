# A3.4c3 — Local SearXNG Provider Adapter

Date: 2026-09-15

## Status

CHECKPOINT READY

This checkpoint connects the existing Corvus ephemeral Web discovery
abstraction to the validated local SearXNG service.

Local search infrastructure:

    http://127.0.0.1:8110

Provider:

    SearXNGProvider

Provider name:

    searxng-local

---

## Scope

Added:

    app/searxng_provider.py
    tests/test_searxng_provider.py

No changes were required to:

    app/web_search.py
    app/web_fetch.py
    memory/*
    Web Evidence persistence
    prompt construction
    UI

---

## Architecture

The integration preserves the existing provider abstraction:

    Corvus search_web()
        ->
    SearchProvider protocol
        ->
    SearXNGProvider
        ->
    Local SearXNG
        ->
    upstream discovery engines

SearXNG remains a replaceable discovery engine.

Corvus does not become coupled to a paid search API.

---

## Security Boundary

The adapter performs discovery only.

Search provider output remains untrusted external data.

The existing search_web() layer continues to:

- normalize provider results
- validate public URLs
- reject unsafe URLs
- deduplicate results
- assign turn-local result IDs

The adapter does not weaken or bypass Safe Public Fetch.

Discovered URLs must still pass through the existing Corvus Web security
boundary before page content is fetched.

---

## Persistence Boundary

Search remains ephemeral.

The adapter does not persist:

- queries
- raw result lists
- engine internals
- unused URLs
- provider failures

Existing principle remains:

> Web retrieval is ephemeral. Used evidence is persistent.

---

## Validation

Existing Web search contracts:

    WEB SEARCH EPHEMERAL CONTRACT OK
    WEB SEARCH RESULT SAFETY CONTRACT OK
    WEB SEARCH RESULT-ID CONTRACT OK
    WEB SEARCH DEDUP CONTRACT OK
    WEB SEARCH BOUNDARY CONTRACT OK

Provider contracts:

    SEARXNG PROVIDER CONTRACT OK
    SEARXNG SEARCH_WEB INTEGRATION OK
    SEARXNG EPHEMERAL BOUNDARY OK

Live local integration:

Query:

    Qwen3.5 llama.cpp

Provider:

    searxng-local

Returned:

    3 results

Observed results included:

- Qwen official llama.cpp documentation
- llama-cpp-python GitHub issue
- relevant community discussion

Result:

    SEARXNG_LIVE_ADAPTER=PASS

---

## Maturity

Local SearXNG infrastructure:

    VALIDATED LOCAL BASELINE

Corvus SearXNG provider adapter:

    VALIDATED INTEGRATION FOUNDATION

Search routing for language / news intent:

    NOT YET IMPLEMENTED

Search -> fetch -> evidence -> answer orchestration:

    NOT YET IMPLEMENTED

---

## Next

Next work should add routing policy without hard-coupling it to Corvus identity:

    English general
        -> default general discovery

    English news
        -> news route

    Chinese general
        -> Google CSE preferred route

    Chinese news
        -> news route with general / Google CSE fallback

Then connect selected SearchResult IDs to the existing Safe Public Fetch
boundary.

---

## Checkpoint

A3.4c3 SearXNG Provider Adapter:

    PASS
