# W2 — Explicit evidence acceptance prototype

Date: **2026-10-18**

Verdict: **W2_PROTOTYPE_VALIDATED**

A local, opt-in prototype now distinguishes technical retrieval from coverage of explicitly supplied evidence requirements. It continues beyond an insufficient first page, collects at most two distinct sources within three candidate pages and 3,600 excerpt characters, preserves exact source slices, and exposes a read-only source map. Existing orchestration defaults and deployed behavior remain unchanged.

This validates the bounded prototype contracts, not universal semantic verification, real-site metadata extraction, browser citation delivery or production readiness.

## A. Baseline and isolated development

- Lab baseline: branch `lab/ow2e-console`, commit `975645963291ec992d64df0474a3ee9d0ba33dcd`, clean before and after. The running checkout was not edited.
- Dedicated local prototype branch: `prototype/w2-evidence-acceptance`, based directly on that verified commit, in a separate temporary worktree.
- **Code commit:** `01dd02e1aa826d49bd628891641892f3450b698f` — `Prototype explicit Web evidence acceptance and source mapping`.
- The code branch is **not pushed**. This SHA identifies a local code checkpoint; it is not promised to resolve on GitHub.
- Reporting branch baseline: `reports/web-validation`, commit `bc8ffdcf184df68cd41ebbbe892fd310594e082e`, clean before documentation changes.
- Complete [W1.3 report](2026-10-18-w1-3-retrieval-architecture-decision.md) and [W1.2b findings](2026-10-18-w1-2b-provider-comparison.md) reviewed. Historical reports and results are preserved.

No new live provider plan, candidate fetch or Qwen call occurred. The cumulative W1 ledger remains unchanged: nine plans/provider calls, six candidate fetches, fifteen DDGS HTTP dispatches, four SearXNG client searches, six page HTTP dispatches, two redirects and six historical Qwen attempts.

## B. Exact implementation scope and reused components

Six files comprise the local code checkpoint:

| File | Change |
| --- | --- |
| `app/web_acceptance.py` | Typed requirements, source-bound metadata witnesses, coverage collector, provider diagnostic classification, validated source-map and Open WebUI source-card data |
| `app/web_orchestration.py` | Twelve-line opt-in candidate-acceptor seam; default first-page behavior remains unchanged |
| `tests/test_web_acceptance.py` | Nineteen deterministic prototype tests with controlled positive fixtures |
| `tests/fixtures/web_acceptance_w1.json` | Four exact public extracted-page snapshots and historical Google News diagnostics, with original hashes |
| `tests/run_web_acceptance_offline.py` | Reusable guarded offline driver with isolated writable paths, denied network/subprocess operations and bounded test duration |
| `docs/prototypes/w2-evidence-acceptance.md` | API, trust boundaries, source/citation contract, reproduction and integration constraints |

The prototype reuses existing Corvus Safe Fetch, URL/public-IP rules, trafilatura extraction, passage construction, lexical ranking, exact-slice evidence selection, `UsedWebEvidence`, and the existing evidence packer. It introduces no dependency, engine, agent, framework, embedding/reranking service, API server or runtime service.

No deployed Pipe, persistence, memory, Hindsight, Arena, authentication, Compose or service file was modified. The additive module is not wired into the running request path. The existing search plan is restricted to its first attempt in this prototype; there is no new automatic provider fallback or retry.

## C. Requirements, coverage and technical compatibility

`EvidenceRequirements` accepts explicitly supplied:

- up to two required source versions;
- an optional authoritative domain set;
- one or two required distinct source pages, optionally with separate version sources;
- a publication-date requirement, exact date or inclusive date interval;
- exact required content strings, such as `Connection.autocommit`.

There is no universal natural-language requirements parser. Strings are narrow caller-supplied coverage conditions, not automatically discovered semantic facts.

The result separates three dimensions:

| Field | Meaning |
| --- | --- |
| `technical_status` | Legacy `READY` if the original positive-evidence condition was reached; otherwise the existing technical status |
| `retrieval_status` | `RETRIEVAL_SUCCESS`, `PROVIDER_FAILED`, `NO_RESULTS`, or insufficient evidence when hits fail to yield an extracted page; existing detailed fetch/extraction outcomes remain available |
| `evidence_status` | `EVIDENCE_SUFFICIENT` or `EVIDENCE_INSUFFICIENT` against the explicit requirements, with covered/missing fields and per-candidate decisions |

A readable page may therefore be `RETRIEVAL_SUCCESS` and technically `READY` while its evidence is insufficient. Missing publication metadata, the wrong version, missing literal content or insufficient source coverage cannot silently become sufficient. Existing normal callers do not opt into the hook and retain their existing behavior/statuses.

Raw SearXNG `unresponsive_engines` data can be converted before adapter normalization. The historical Google News access-denial fixture produces `PROVIDER_FAILED`, while a genuinely empty response without failure diagnostics produces `NO_RESULTS`. Existing provider exceptions are also preserved. Failure identities remain attached even if some evidence succeeds; arbitrary upstream error text is not placed in UI source data.

The adapter boundary matters: this module cannot reconstruct engine diagnostics that a caller has already discarded. The live SearXNG adapter was not changed.

## D. Bounded collection and provenance

The existing candidate loop is reused. A page that fails requirements can be skipped while the next candidate is considered. Collection stops when requirements are satisfied or the existing three-page budget is exhausted. There is no new search query or retry to fill missing evidence.

At most two source pages are accepted. For two-source requirements, the 3,600-character budget reserves 1,800 characters per source. Selected references/ordinals are assigned globally as `web_1`, `web_2`, and so on; independently numbered page-local sets are not concatenated. Exact excerpt bytes, original character ranges, passage IDs and source URLs remain intact and pass the existing packer.

Source identity hashes the normalized final public URL. Redirect aliases to the same final URL and identical extracted bodies cannot satisfy a two-source requirement. Distinct pages do not prove independent publishers, independent authorship or corroboration; the tested comparison is distinct version-source coverage.

`SourceFacts` binds a version/publication assertion to the final URL and SHA256 of the extracted text. A `TextFact` must match its exact source range and appear inside an actually selected excerpt. No coverage is awarded from a discovery title, snippet, missing witness or out-of-evidence fact.

**Explicit trust boundary:** a trusted source-specific adapter/operator must identify what a version/date means. A text witness proves provenance, not that an arbitrary mentioned date is a publication date or that a version in a change note identifies the document itself. No real-site metadata parser was implemented. Unknown or unprovided metadata remains insufficient.

## E. Offline validation and failure cases

Final results:

- **19 new prototype unittest cases passed.**
- **14 existing module-level contract scripts passed.** These are existing assertion-based scripts, not invented unittest counts.
- **24 existing Pipe unittest cases passed; one explicitly skipped.** The skipped case launches a fresh subprocess, which the offline driver forbids. It is not reported as passed.
- Across the two unittest suites: **43 passing methods, one skip**.
- Staged and unstaged whitespace checks passed; staged bytes and exact file scope were reviewed.

Required behavior demonstrated:

| Case | Offline result |
| --- | --- |
| Saved Python 3.8 sqlite3 page | Readable/technically ready but insufficient for explicit `Connection.autocommit` content |
| Saved Firefox release index | Insufficient without a verified publication-date witness |
| Saved unversioned concurrent.futures page | Cannot satisfy separately required 3.13/3.14 version sources |
| Saved Google News access denial | `PROVIDER_FAILED`, distinct from genuine empty discovery |
| Empty list versus provider exception | `NO_RESULTS` versus `PROVIDER_FAILED`; no candidate fetch/retry after failure |
| Two controlled official-domain version fixtures | Sufficient; separate identities, unique global refs, exact source slices |
| Controlled publication-date fixture | Sufficient inside inclusive bounds; outside/missing/wrong bindings rejected |
| Insufficient first page followed by valid page | Collector continues to candidate two and stops before candidate three |
| Five available candidate fixtures | At most three candidate fetches and two accepted sources |
| Redirect aliases and identical-body mirrors | Cannot masquerade as two distinct source pages |
| Large evidence, forged witness or map data | Character budget remains bounded; invalid provenance/ref mappings fail |
| Saved successful modern sqlite3 case | Remains sufficient for its explicit content requirement; legacy default orchestration still returns `READY` |

Controlled positive bodies are clearly labeled synthetic schema fixtures; their official-domain URLs are mock inputs, not newly fetched pages or claims that those exact bodies exist online. Historical negative results were not rewritten. Page fields in all four copied snapshots were compared against the original artifacts, and text/artifact SHA256 hashes were checked.

Existing regression coverage includes Safe Fetch public-network policy, DNS pinning/rebinding/redirect boundaries, extraction, passage ranking, evidence budgets/source slices, untrusted-evidence packing, search-result identity/fetch mapping, orchestration fallback/default behavior, canonical user/assistant/evidence ordering, batch provenance rollback and working-context compatibility. Pipe checks cover identity/authentication boundaries, ordinary-text guards, endpoint isolation, confirmed-result handling and uncertain-outcome/no-retry behavior. The real API boundary test used in-process ASGI with a stubbed runtime; it did not call a deployed API.

### Validation constraints encountered

The initial test fixture driver used a generic query for some historical pages, which correctly produced no lexical evidence. Tests were corrected to use the appropriate saved question terms; historical data was unchanged. The isolation driver also needed to allow a harmless `/dev/null` dependency probe and reset Python's cached tempfile directory after redirecting writable paths. A synthetic temporary SQLite path outside the selected test root was blocked before connection; no canonical database was accessed.

An existing ASGI Pipe test stalled in the sandbox; one process was stopped and a bounded run exited at its deadline. The same guarded Pipe suite then passed outside the sandbox, with network denial and isolated data still active. The stalled runs are not counted as passes. Final completed drivers reported no network/private-access violations. Embedding-model construction was stubbed to fail; no model weights or personal recall were loaded.

Reproduction uses the committed driver and existing Python environment, without installing tooling:

```sh
/path/to/existing/venv/bin/python -B tests/run_web_acceptance_offline.py
```

Additional existing contract filenames can be passed to the same driver. It redirects HOME/data/cache/temp paths before application imports, rejects external connections and subprocess creation, and permits SQLite only for isolated synthetic test data. Each module has a 30-second deadline. These are application-level guards, not full OS syscall containment.

## F. Open WebUI source/citation bridge contract

Pinned Open WebUI **0.6.5** source was inspected: backend middleware's `source`/`document`/`metadata` structures, `Citations.svelte` grouping by `metadata.source`, and `ResponseMessage.svelte` card presentation. The current deployed Corvus Pipe remains unchanged.

The read-only source map contains:

- evidence reference;
- validated final public URL;
- bounded heading from actual extracted source text;
- stable source identity;
- evidence status and coverage limitations;
- the exact excerpt used by the collector.

Unverified discovery titles are not promoted into verified UI titles. Model-generated citation text is never used to construct URLs. Mapping validates source slices, reference order, identity and the exact collected evidence set. Public URL checks at this layer are static; DNS/IP pinning and redirect checks remain Safe Fetch's responsibility.

The optional source-card formatter creates aligned `document` and `metadata` arrays plus `source.id/name/url`. The metadata carries the validated URL, `corvus_ref`, identity, status and coverage limits. Shape/provenance/forgery checks run offline. Native cards group same-URL excerpts.

**Not established:** `[web_n]` does not automatically become WebUI's numeric inline citation links. No event emission, Socket modification, frontend deployment or browser source-card acceptance was performed. A future adapter must explicitly map references and preserve authorization; a failed presentation event must never resubmit a canonical turn or invalidate an already committed assistant reply.

## G. Preserved boundaries and remaining limitations

- No Lab source checkout changes, Production/Demo changes, deployed Pipe changes, service restart/deployment, credential/network/Cloudflare changes or model-setting changes.
- No external requests, Qwen inference, deployed chat/API calls, canonical memory reads/writes or Hindsight access. Synthetic SQLite regression data existed only in temporary directories.
- Canonical Evidence Log ownership, user-first/assistant-before-provenance ordering and derived-write lifecycle were not changed. Existing runtime/provenance contracts passed; no new live persistence acceptance is claimed.
- Sufficiency means the supplied constraints pass, not universal relevance, correctness or truthful attribution of arbitrary claims. Literal coverage is deliberately narrow; request interpretation is not implemented.
- Metadata role identification is trusted input. Real-site version/date extraction and current-stable-channel proof still need a reviewed adapter. Missing metadata conservatively rejects pages.
- Fixed per-source quotas, lexical ranking and greedy source order can leave useful evidence unselected or reject otherwise useful pages. Unused budget is not redistributed. Different versions' content can be too large for the fixed budget.
- URL/content distinction is not a complete mirror/corroboration detector. No provider quality improvement, latency improvement, grounded answer quality, multi-source Qwen integration or everyday reliability rate was measured in W2.
- Native source payload formatting is not deployed inline-citation interoperability. One existing subprocess-only regression remains skipped.

## H. Recommended Lab integration step

Proceed to a **read-only semantic review of the local W2 code commit**, focusing on metadata-role trust, scope of sufficiency claims, conservative budgets and exact ref/provenance mapping. Do not deploy or cherry-pick automatically.

After review, the smallest implementation stage is a Lab-only adapter that supplies explicitly structured requirements, source-bound version/publication facts and raw engine diagnostics to this opt-in collector, plus a separate authorized read-only source-presentation bridge. Keep the single existing search pipeline and model interface, retain Safe Fetch, and preserve canonical persistence ownership/order. Use fixture acceptance before any separately authorized live trial. Do not remove existing Pipe search/media guards or enable native WebUI search as a shortcut.

No new framework, inference verifier, general benchmark or additional prompt-tuning loop is recommended.

## I. Privacy and publication

The code checkpoint remains local. Only this sanitized report and its relative-link index entry are published on `reports/web-validation`; no raw JSON, extracted-page fixture, terminal transcript, secret, private conversation, personal memory or database contents is part of the report commit. The code SHA is a reference only and does not push code objects or unpublished Lab commits. Historical report verdicts are preserved.
