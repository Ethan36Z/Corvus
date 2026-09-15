# A3.4c2 — Ephemeral Search Discovery Foundation

Date: 2026-09-15

Status:

**CHECKPOINT**

Project:

**Corvus — Persistent Personal AI on Consumer Hardware**

Stage:

**A3.4 — Web v1 / Read-Only Internet Grounding**

Substage:

**A3.4c2 — Ephemeral Search Discovery Foundation**

---

## 1. Purpose

A3.4c2 introduces the provider-neutral discovery layer used to find
public Web information.

Search itself remains ephemeral.

The search layer does not write search queries, raw search results, or
retrieval history into Corvus long-term memory.

This follows the A3.4c1 principle:

**Web retrieval is ephemeral. Used evidence is persistent.**

---

## 2. Architecture

The discovery flow is:

search query
→ search provider
→ raw provider results
→ Corvus normalization
→ public URL security validation
→ deduplication
→ turn-local SearchResult handles.

The output is an in-memory `SearchDiscovery`.

No database persistence is performed by this layer.

---

## 3. Provider Neutrality

The core search abstraction is provider-neutral.

A provider implements a narrow contract:

`search(query, limit=...)`

The Corvus search layer does not depend on provider-specific response
formats after normalization.

This allows future providers to be replaced without changing:

- Web security policy;
- safe fetch transport;
- External Evidence persistence;
- model-facing result handles.

Principle:

**Search providers are replaceable components.**

---

## 4. Turn-Local Result IDs

Normalized results receive handles such as:

`result_1`

`result_2`

These identifiers are temporary.

They are not database IDs and are not intended to survive across
search operations or sessions.

The purpose is to separate model-facing selection from raw URL
authority.

The intended future model interaction is:

`fetch result_2`

rather than:

`fetch arbitrary_url`

Corvus runtime remains responsible for resolving the handle to the
underlying URL.

---

## 5. Search Result Security

Every provider-supplied URL must pass the existing A3.4a public Web URL
policy before becoming a SearchResult.

Blocked results are discarded.

Examples include:

- localhost;
- private IP addresses;
- link-local destinations;
- unsupported schemes;
- credential-bearing URLs;
- forbidden ports.

Search providers therefore cannot bypass the Corvus Web security
boundary by returning unsafe destinations.

---

## 6. Result Normalization

Provider results are normalized into a Corvus-owned structure
containing:

- result ID;
- rank;
- title;
- normalized public URL;
- hostname;
- snippet;
- provider name.

Titles and snippets are bounded and whitespace-normalized.

Duplicate canonical URLs are removed.

Accepted results are reranked sequentially after filtering.

---

## 7. Query Boundaries

Search queries are normalized before provider execution.

Current limits include:

- non-empty query;
- normalized whitespace;
- maximum query length;
- bounded result count.

The current maximum normalized result count is:

`8`

---

## 8. Persistence Boundary

A3.4c2 performs no persistence.

Specifically, it does not create or write:

- search history;
- query history;
- search-result history;
- provider-response archives;
- fetch history.

Only evidence later selected for use in the model context may cross the
A3.4c1 persistence boundary.

---

## 9. Relationship to Safe Fetch

Search discovery does not itself fetch page content.

Its responsibility is only discovery and normalization.

The intended future path is:

SearchResult handle
→ Corvus runtime resolution
→ A3.4b Safe Public Fetch
→ bounded page content
→ extraction
→ evidence selection.

This preserves the A3.4b pinned-IP and SSRF-resistant transport
boundary.

---

## 10. Contract Validation

Validated contracts:

**WEB SEARCH EPHEMERAL CONTRACT OK**

Search discovery performs no long-term persistence.

**WEB SEARCH RESULT SAFETY CONTRACT OK**

Unsafe URLs are rejected before they become Corvus SearchResults.

**WEB SEARCH RESULT-ID CONTRACT OK**

Accepted results receive deterministic turn-local handles.

**WEB SEARCH DEDUP CONTRACT OK**

Duplicate canonical URLs do not produce duplicate accepted results.

**WEB SEARCH BOUNDARY CONTRACT OK**

Query limits, provider failures, and malformed responses are handled
inside the search boundary.

Regression validation confirms:

- A3.4a Web Security remains passing;
- A3.4b Safe Public Fetch remains passing;
- A3.4c1 Used Web Evidence remains passing.

---

## 11. Architecture Principle

The durable model is:

**Discovery is temporary.**

**URLs remain backend-controlled.**

**Only adopted evidence becomes durable.**

This prevents Corvus from accumulating permanent browser history while
still allowing the model to reason over current Web information.

---

## 12. Next Step

The next step is to implement one real search provider adapter behind
the provider-neutral interface.

That adapter should produce raw results only.

Corvus remains responsible for:

- normalization;
- URL validation;
- result IDs;
- safe fetching;
- evidence selection;
- persistence.

Status:

**A3.4c2 Ephemeral Search Discovery Foundation — CHECKPOINT**
