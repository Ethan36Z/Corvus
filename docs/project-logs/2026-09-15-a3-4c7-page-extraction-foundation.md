# A3.4c7 — Page Extraction Foundation

Date: 2026-09-15

## Status

CHECKPOINT READY

This checkpoint adds a bounded page-extraction layer between Safe Public
Fetch and future Web evidence selection.

Corvus can now convert already-fetched textual Web resources into cleaner,
bounded readable content without giving the extraction engine any network
authority.

---

## Goal

Transform:

    FetchedSearchResult
        ->
    readable extracted text
        ->
    bounded text

while preserving these boundaries:

- Safe Public Fetch owns networking
- extraction owns HTML -> readable text
- Corvus owns size limits and orchestration
- no persistence occurs during extraction
- no model access occurs during extraction
- no evidence selection occurs during extraction

---

## Dependency

Added:

    requirements-web.txt

Pinned extraction engine:

    trafilatura==2.2.0

Validated runtime:

    Python 3.12.3

Package metadata:

    license = Apache-2.0

Dependency check:

    pip check
        -> no broken requirements

---

## Added

    app/web_extract.py
    tests/test_web_extract.py
    requirements-web.txt

---

## Extraction Strategy

HTML resources:

    text/html
    application/xhtml+xml

are processed by:

    Trafilatura 2.2.0

with:

    output_format = txt
    include_comments = false
    include_tables = false

Already-textual resources use bounded passthrough.

Supported passthrough classes include:

- text/*
- application/json
- application/xml
- application/rss+xml
- application/atom+xml

---

## Size Boundary

The extraction layer reuses the existing Corvus Web security limit:

    MAX_EXTRACTED_TEXT_CHARS = 60000

It does not define a second competing size policy.

If readable extracted text exceeds the limit, it is truncated before it
can continue toward Working Context or model prompting.

---

## Contracts

Passed:

    WEB EXTRACTION HTML CONTRACT OK
    WEB EXTRACTION TEXT CONTRACT OK
    WEB EXTRACTION SIZE BOUNDARY CONTRACT OK
    WEB EXTRACTION EMPTY CONTRACT OK
    WEB EXTRACTION NO-NETWORK BOUNDARY CONTRACT OK

Dependency reproducibility:

    WEB_EXTRACTION_DEPENDENCY_PIN=PASS

Existing Web contracts also remained green, including:

- Web search
- Safe Public Fetch
- routing
- SearXNG provider
- route fallback
- SearchResult-ID Safe Fetch bridge

Result:

    A3_4C7_PAGE_EXTRACTION_FOUNDATION=PASS

---

## Live Acceptance

Live query:

    Python 3.14 release notes

Selected route:

    en-general

Fetched source:

    What's new in Python 3.14
    docs.python.org

Observed raw fetch:

    raw_bytes = 536817
    raw_chars = 536237
    media_type = text/html

Trafilatura extraction:

    extraction_engine = trafilatura-2.2.0
    original_extracted_chars = 119137

Corvus bounded output:

    bounded_chars = 59999
    truncated = true

The one-character difference from the nominal 60000-character maximum is
consistent with trailing-whitespace trimming after truncation.

The extracted preview contained useful Python documentation content and
did not resemble raw HTML/navigation boilerplate.

Results:

    LIVE_WEB_EXTRACTION=PASS
    A3_4C7_LIVE_EXTRACTION_ACCEPTANCE=PASS

---

## Compute Boundary

Current extraction is CPU work.

The path is approximately:

    network fetch
        -> CPU / I/O

    HTML parsing and main-content extraction
        -> CPU

    normalization and bounding
        -> CPU

No GPU or model inference is required by this checkpoint.

This supports the Corvus efficiency principle:

    Use inexpensive deterministic processing before
    spending model compute.

---

## Architecture Boundary

This checkpoint still does not:

- split readable text into passages
- rank passages against the user query
- select exact used External Evidence
- persist selected Web Evidence
- inject Web evidence into Working Context
- generate citations
- expose Web search through normal chat

---

## Maturity

Safe Fetch:

    LIVE VALIDATED

SearchResult -> Safe Fetch:

    LIVE VALIDATED

Page extraction:

    LIVE VALIDATED FOUNDATION

Evidence selection:

    NOT YET IMPLEMENTED

Search -> evidence -> answer:

    NOT YET IMPLEMENTED

---

## Next

Next work should add:

    readable extracted text
        ->
    bounded passages
        ->
    query-relevance ranking
        ->
    selected External Evidence

The first implementation should remain CPU-first and deterministic where
practical.

---

## Checkpoint

A3.4c7 Page Extraction Foundation:

    PASS
