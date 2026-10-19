# W2 explicit evidence acceptance prototype

Local prototype only. Nothing imports this module in the deployed request path.
No services, installed Pipe, authentication, search configuration or persistence
code is changed. There are no new dependencies.

## Entry point and status contract

`app.web_acceptance.accept_web_evidence` takes an explicit `EvidenceRequirements`,
the existing provider builder, an optional trusted `source_facts(page)` adapter,
and a callback returning preserved provider diagnostics. Requirements cover up to
two source versions, an authoritative domain set (exact host or subdomain), one
or two distinct source pages, a publication date/inclusive date window, and exact
required content strings. There is no natural-language parser or general claim
verifier. Exact strings such as `Connection.autocommit` are explicit caller
requirements, not automatically extracted user intent.

The result separates:

- `technical_status`: legacy `READY` when the original positive-evidence loop
  would accept a page; otherwise the existing technical status.
- `retrieval_status`: `RETRIEVAL_SUCCESS` for successful extraction,
  `PROVIDER_FAILED` for preserved discovery errors, `NO_RESULTS` for genuine
  empty discovery, or `EVIDENCE_INSUFFICIENT` when hits cannot yield an extracted
  page. Detailed existing fetch/extraction outcomes remain in `grounding`.
- `evidence_status`: `EVIDENCE_SUFFICIENT` or `EVIDENCE_INSUFFICIENT` for the
  explicit requirements only; `covered`, `missing` and candidate decisions make
  partial coverage visible. It says nothing about arbitrary factual truth.

Provider failures remain attached even when another result provides usable
content. Pass raw SearXNG payloads to `searxng_failures` before normalization;
Google News access denial is not a genuine empty result. The prototype does not
change the installed SearXNG adapter or automatically capture diagnostics that a
caller has discarded. Malformed failure diagnostics fail closed.

## Reuse and limits

The existing orchestrator has one optional `candidate_acceptor` hook. With its
normal default `None`, all existing behavior and statuses are unchanged. The
prototype uses that hook to continue after an insufficient page and reuses Safe
Fetch, trafilatura extraction, passage construction/ranking, exact-slice evidence
selection and `UsedWebEvidence`. It restricts the existing search plan to its
first attempt: no provider fallback/retry is introduced.

There are at most three candidate pages, two accepted sources and 3,600 excerpt
characters. For two-source requirements, 1,800 characters are reserved per source;
unused quota is not redistributed. Large passages may therefore be rejected or
omit useful facts. Source order and lexical ranking can still cause conservative
false negatives. This prototype is not an optimizer for the best evidence set.

Identity is a hash of the normalized final public URL. Identical final URLs and
identical extracted bodies cannot count as two sources. Different URLs/content
are distinct pages, not proof of independent publishers or corroboration. A
version-comparison request can additionally require distinct version assertions.
Evidence refs/ordinals are reassigned globally without changing excerpt bytes,
source URLs, passage IDs or character ranges. The collected set can be passed to
the existing evidence packer; no inference or persistence is performed here.

## Trusted metadata boundary

`SourceFacts` binds a version/publication assertion to the final URL and SHA256
of the exact extracted text. `TextFact` supplies the source value and character
range. The value must match that source slice and be included in an actually
selected excerpt. Publication values use ISO dates. Unverified search titles,
snippets, unrelated page dates, missing adapter metadata and facts outside the
selected evidence cannot supply coverage automatically.

The adapter/operator must correctly identify the *role* of the version/date.
The module cannot prove that a supplied date is a publication date rather than
an event date, or that a quoted version identifies the document itself rather
than a version mentioned in a change note. This is an explicit trust boundary;
no real-site metadata extraction adapter is implemented. Unknown metadata stays
insufficient. Successful positive fixtures are controlled schema tests, not live
claims about those pages. No general semantic verification is established.

## Read-only source presentation contract

`source_map(result)` returns immutable entries containing evidence reference,
validated final public URL, bounded source-text heading, source identity,
evidence status, coverage limitations and exact excerpt. Discovery titles are
not presented as verified titles. The map checks exact source slices, global
ref order, identity and the exact collected-evidence set. It never accepts model
citation strings as URLs. URL validation here is static; DNS/IP pinning and
redirect validation remain the unchanged Safe Fetch responsibility.

`open_webui_sources(result)` creates source-card data matching inspected Open
WebUI **0.6.5** contracts:

- `source`: `id`, `name`, `url`;
- aligned `document` and `metadata` arrays;
- `metadata.source` is the validated public URL used by the frontend to group
  excerpts; `corvus_ref` preserves `[web_n]` identity alongside status/limitations.

Relevant pinned sources: `backend/open_webui/utils/middleware.py` source payloads;
`src/lib/components/chat/Messages/Citations.svelte` grouping by metadata URL;
`ResponseMessage.svelte` source/citation card display. Existing native cards use
numeric inline citation positions, so `[web_n]` does **not** gain working inline
links automatically. No events are emitted, no Socket or deployed Pipe is
modified, and source-card/browser acceptance is not claimed. A future bridge
must map refs explicitly, retain session authorization and never resubmit a turn
when a presentation event fails.

## Offline verification

Use the existing Python environment; do not install anything:

```sh
/path/to/existing/venv/bin/python -B tests/run_web_acceptance_offline.py
```

The committed driver redirects home/data/cache/temp paths before imports,
forbids network and subprocess dispatch, restricts SQLite to temporary test data,
and rejects personal-home reads outside the checkout and dependencies. It stubs
embedding model construction to fail if requested. It has a 30-second module
wall deadline. This is an application-level guard, not an OS-level security
boundary. Existing tests may create synthetic SQLite data only inside that
temporary root; no canonical deployed data is used.

Four saved W1.2b/W1.3 public extracted pages and original hashes are copied to
`tests/fixtures/web_acceptance_w1.json`; original artifacts are unchanged.
The controlled positive bodies in `test_web_acceptance.py` are clearly marked
synthetic and are never fetched. Tests exercise negative evidence, positive
version/date coverage, continuation, caps, duplicate-source rejection, exact
provenance, single-page compatibility, provider-error visibility and source maps.

Legacy scripts passed to the driver may use module-level `assert` contracts
rather than unittest methods; report those as script passes, not invented test
counts. One existing Pipe fresh-subprocess test is explicitly skipped because
the driver forbids subprocesses. It is not reported as passed.

## Integration boundary

Do not call this directly from the deployed Lab. First review the opt-in hook,
metadata trust boundary, conservative quotas and ref mapping. Then design a
small Lab-only adapter supplying explicit requirements, trustworthy source facts
and raw diagnostics, plus an authorized read-only source bridge. Preserve user-
first canonical writes, assistant commit before evidence/derived writes,
exact-used-evidence provenance, Hindsight/Memory Arena isolation, authentication,
and uncertain-outcome/no-retry semantics. No persistence or memory ownership
change is part of W2.
