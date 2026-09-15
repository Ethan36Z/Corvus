# A3.4c4 — Web Search Routing Policy

Date: 2026-09-15

## Status

CHECKPOINT READY

This checkpoint adds a pure, deterministic routing policy for Web search.

It performs no network access and no persistence.

---

## Goal

Separate search intent routing from provider execution.

Corvus should decide which discovery route to attempt before any provider
request is made.

Current validated routing policy:

    English general
        -> general

    English news / current
        -> news
        -> general fallback

    Chinese general
        -> Google CSE route

    Chinese news / current
        -> news
        -> Google CSE fallback

---

## Added

    app/web_search_routing.py
    tests/test_web_search_routing.py

---

## Search Plan Model

Routing produces:

    SearchPlan

containing ordered:

    SearchAttempt

records.

A SearchAttempt may specify:

- category
- language
- engine bang
- time range

The routing layer does not execute these attempts.

---

## Language Routing

Queries containing Han characters are routed through the Chinese path.

Current Chinese locale target:

    zh-CN

Chinese general discovery prefers:

    Google CSE
    shortcut: goc

This choice is based on live SearXNG validation performed during A3.4c3.

---

## News Intent

The current narrow heuristic recognizes explicit current-news terms.

English examples:

- news
- latest
- today
- breaking
- current news
- recent news

Chinese examples:

- 新闻
- 最新
- 今天
- 今日
- 刚刚
- 刚才
- 近期

This is intentionally a simple deterministic baseline.

It can later be replaced or expanded without changing provider or memory
boundaries.

---

## Fallback Policy

Fallback is represented as ordered attempts.

Example:

    洛杉矶 今日 新闻

produces:

    1. zh-news
    2. zh-general-goc

This encodes the principle:

> Search-engine failure is not equivalent to absence of information.

The router only defines the fallback sequence.

Actual fallback execution remains future work.

---

## Validation

Contracts passed:

    WEB SEARCH ROUTING LANGUAGE CONTRACT OK
    WEB SEARCH ROUTING NEWS INTENT CONTRACT OK
    WEB SEARCH ROUTING FALLBACK CONTRACT OK
    WEB SEARCH ROUTING PURE POLICY CONTRACT OK

Existing search contracts also remained green:

    WEB SEARCH EPHEMERAL CONTRACT OK
    WEB SEARCH RESULT SAFETY CONTRACT OK
    WEB SEARCH RESULT-ID CONTRACT OK
    WEB SEARCH DEDUP CONTRACT OK
    WEB SEARCH BOUNDARY CONTRACT OK

Existing SearXNG adapter contracts also remained green:

    SEARXNG PROVIDER CONTRACT OK
    SEARXNG SEARCH_WEB INTEGRATION OK
    SEARXNG EPHEMERAL BOUNDARY OK

---

## Preview Validation

Validated plans:

    Qwen3.5 llama.cpp
        -> en-general

    OpenAI latest news
        -> en-news
        -> en-general-fallback

    洛杉矶餐馆
        -> zh-general-goc

    洛杉矶 今日 新闻
        -> zh-news
        -> zh-general-goc

---

## Architecture Boundary

Routing remains separate from:

- SearXNG transport
- Safe Public Fetch
- External Evidence persistence
- Working Context
- model prompting
- UI
- memory

This preserves replaceability of both routing policy and discovery provider.

---

## Maturity

Search routing policy:

    VALIDATED PURE POLICY FOUNDATION

Route execution:

    NOT YET IMPLEMENTED

Search -> fetch -> evidence -> answer orchestration:

    NOT YET IMPLEMENTED

---

## Next

Next work should execute SearchPlan attempts through the local SearXNG
provider while preserving:

- ordered fallback
- ephemeral search
- SearchResult URL validation
- provider replaceability
- existing Safe Fetch boundary

---

## Checkpoint

A3.4c4 Web Search Routing Policy:

    PASS
