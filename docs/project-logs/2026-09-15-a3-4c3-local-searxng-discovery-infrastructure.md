# A3.4c3 — Local SearXNG Discovery Infrastructure

Date: 2026-09-15

## Status

CHECKPOINT COMPLETE

This checkpoint establishes a local, zero-cost Web search discovery
infrastructure for Corvus and other local projects.

It does not yet connect SearXNG to the Corvus runtime.

The search service is deployed and validated independently first.

---

## Goal

Provide a local-first, free-by-default, replaceable search discovery layer.

Core principle:

> Local-first. Free-by-default. Provider-optional.

Corvus must not require a paid Web search API for its baseline Web capability.

The search engine is infrastructure, not part of Corvus identity or memory.

---

## Deployment

SearXNG is deployed as a standalone Docker service outside the Corvus
application repository.

Location:

    /home/ethan/srv/shared/searxng

Container:

    searxng-local

Image:

    docker.io/searxng/searxng:latest

Local endpoint:

    http://127.0.0.1:8110

The service is bound only to localhost:

    127.0.0.1:8110->8080/tcp

It is not exposed through Cloudflare, FoxGate, LAN, or the public Internet.

Restart policy:

    unless-stopped

JSON output is explicitly enabled for programmatic use.

---

## Shared Infrastructure Model

SearXNG is treated as server-level search infrastructure rather than
a Corvus-private component.

Potential consumers include:

- Corvus
- FoxWords
- future local AI services
- scripts and tools running on the same server

Conceptually:

    Applications
        |
        v
    Local Search Service
        |
        v
    SearXNG
        |
        +-- Google CSE
        +-- Brave
        +-- DuckDuckGo
        +-- Google News
        +-- Reuters
        +-- other replaceable engines

The application should depend on a narrow search abstraction rather than
a specific upstream provider.

---

## Baseline API Validation

Initial JSON API smoke test:

Query:

    linux kernel

Result count:

    30

Top results:

1. GitHub — torvalds/linux
2. The Linux Kernel Archives
3. Wikipedia — Linux kernel

Result:

    JSON API: PASS

---

## General Search Quality Validation

Queries tested:

- OpenAI latest news
- Qwen3.5 llama.cpp
- Python 3.14 release notes
- 洛杉矶 今日 新闻

Observed behavior:

### Technical Search

Technical and official-documentation retrieval was strong.

Examples:

- Qwen official llama.cpp documentation ranked first for
  `Qwen3.5 llama.cpp`.
- Python official documentation ranked first for
  `Python 3.14 release notes`.

### English General Search

Relevant first-party and established sources appeared near the top,
including OpenAI, Reuters, GitHub, kernel.org, and Python.org.

### Chinese General Search

Chinese queries successfully returned relevant sources including:

- 世界新闻网
- Los Angeles Times
- Los Angeles Daily News
- local Chinese-language pages

Result:

    GENERAL SEARCH BASELINE: PASS

---

## News / Freshness Validation

The `news` category with `time_range=day` was tested using:

- OpenAI
- artificial intelligence
- Los Angeles
- 洛杉矶

English news search returned same-day 2026-09-15 Reuters articles with
specific publication timestamps.

Examples included:

- OpenAI funding / IPO reporting
- OpenAI US Congress / biological threat legislation reporting
- OpenAI / Anthropic / Google AI safety reporting
- LA28 economic impact reporting

This demonstrates that SearXNG can provide genuinely current same-day
news discovery through compatible engines.

Result:

    ENGLISH NEWS FRESHNESS: PASS

---

## Chinese News Behavior

The direct Chinese news-category route was weaker.

Example:

    categories=news
    language=zh-CN
    query=洛杉矶

Observed:

    result_count = 0
    bing news = parsing error

This is not interpreted as a failure of Chinese Web search generally.

A general-category fallback using:

    洛杉矶 今日 新闻

returned more than 30 relevant results.

Therefore:

    Chinese general discovery: PASS
    Chinese news category: DEGRADED

---

## Engine Inventory

Relevant installed SearXNG engines:

### Baidu

    name = baidu
    enabled = False
    shortcut = bd
    categories = general
    time_range_support = True

### Google

    name = google
    enabled = False
    shortcut = go
    categories = general, web
    language_support = True
    time_range_support = True

### Google News

    name = google news
    enabled = True
    shortcut = gon
    categories = news
    language_support = True

### Google CSE

    name = google cse
    enabled = True
    shortcut = goc
    categories = general, web
    language_support = True
    time_range_support = True

---

## Chinese Route Validation

Direct Google CSE test:

    !goc 洛杉矶 今日 新闻

Observed:

    result_count = 20
    unresponsive_engines = []

Relevant Chinese-language results were returned.

Examples included:

- 世界新闻网
- Chinese-language Los Angeles coverage
- local Chinese-language sources

Direct Google News test:

    !gon 洛杉矶

Observed:

    result_count = 10
    unresponsive_engines = []

Google News successfully returned Chinese-language material, but relevance
was broader than local-current-news intent.

Therefore the current preferred routing policy is:

    Chinese general search
        -> Google CSE

    Chinese news discovery
        -> news route when healthy
        -> Google CSE / general-search fallback
        -> fetch page and verify freshness

    Google News
        -> auxiliary discovery source

---

## Baidu Validation

Direct Baidu engine test reached the engine but was blocked by CAPTCHA.

Observed:

    baidu = CAPTCHA

Therefore Baidu must not be a required baseline dependency.

It may remain an opportunistic future provider, but failure of Baidu must
never cause Chinese search failure.

---

## Resilience Principle

A search-engine failure is not equivalent to absence of information.

Examples observed during testing:

- DuckDuckGo CAPTCHA
- Bing News parsing error
- Wikidata timeout
- Baidu CAPTCHA

SearXNG continued producing useful results through other engines.

Corvus should preserve this property at the application layer.

Target behavior:

    primary route
        |
        +-- success -> use results
        |
        +-- degraded / empty
                |
                v
            fallback route
                |
                v
            alternate engines / categories

---

## Architecture Boundary

SearXNG performs discovery only.

It does not become the authority for:

- truth
- memory
- provenance
- evidence selection
- prompt construction
- user actions

Target Corvus flow remains:

    user query
        ->
    search discovery
        ->
    normalized SearchResult IDs
        ->
    Safe Public Fetch
        ->
    extraction / evidence selection
        ->
    persistent External Evidence
        ->
    Working Context
        ->
    local model
        ->
    cited answer

Existing Corvus Safe Fetch protections must not be weakened to accommodate
the local SearXNG service.

The future SearXNG adapter should use a fixed trusted internal endpoint.

Discovered external URLs must still pass through the existing Corvus
public-URL validation and Safe Fetch boundary.

---

## Persistence Policy

Search discovery remains ephemeral.

Do not persist by default:

- raw search queries
- full search result lists
- unused URLs
- engine ranking internals
- intermediate search-provider failures

Persist only the exact external evidence that actually contributes to the
assistant answer, using the existing Web Evidence model.

Principle:

> Web retrieval is ephemeral. Used evidence is persistent.

---

## Current Search Routing Baseline

Current validated baseline:

    English general
        -> SearXNG general aggregation

    English current news
        -> SearXNG news category

    Chinese general
        -> Google CSE preferred

    Chinese news
        -> news category when useful
        -> general / Google CSE fallback

    Baidu
        -> optional only; currently CAPTCHA-blocked

The routing policy should remain replaceable and should not be hard-coupled
to Corvus identity or memory architecture.

---

## Maturity

SearXNG local infrastructure:

    VALIDATED LOCAL BASELINE

Corvus integration:

    NOT YET IMPLEMENTED

A3.4c3 therefore establishes the discovery engine foundation only.

Next work should implement the narrow Corvus SearXNG provider adapter and
connect it to the existing ephemeral `search_web()` abstraction.

---

## Checkpoint

A3.4c3 Local SearXNG Discovery Infrastructure:

    PASS

Zero-cost search baseline:

    PASS

Localhost-only deployment:

    PASS

JSON API:

    PASS

English general search:

    PASS

English same-day news discovery:

    PASS

Chinese general search:

    PASS

Chinese Google CSE route:

    PASS

Chinese dedicated news route:

    DEGRADED WITH VALIDATED FALLBACK

Baidu:

    OPTIONAL / CAPTCHA-BLOCKED

No paid search API is required for the validated baseline.
