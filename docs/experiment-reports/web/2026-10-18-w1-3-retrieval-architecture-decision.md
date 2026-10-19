# W1.3 — Retrieval quality and architecture decision

Date: **2026-10-18** (operator timezone; execution metadata UTC 2026-10-19).

Verdict: **W1_3_VALIDATED_WITH_CONSTRAINTS**

The final authorized small comparison completed: six provider plans/calls, three candidate-page fetches and zero Qwen calls. Three plans yielded readable selected evidence, but none satisfied the full question requirements. Three other plans failed at provider level, including Google News access denial hidden behind an empty normalized result. No mandatory safety stop, uncertain request, retry or budget expansion occurred.

**Decision:** keep existing Corvus Safe Fetch, extraction, model interface and canonical persistence. Prototype constraint-aware evidence acceptance and bounded source coverage using those components, with truthful provider diagnostics and a source metadata bridge to Open WebUI. Do not enable a second search pipeline, deploy a provider switch or introduce a framework. This report recommends a concrete integration prototype, not another general benchmark.

## A. Experiment results

### Baseline, resumption and isolation

Lab branch `lab/ow2e-console`, HEAD `975645963291ec992d64df0474a3ee9d0ba33dcd`, and clean worktree verified. Reporting worktree was clean on `reports/web-validation` at `42dec4ec262335481bc6964d04afa62d18a4e74c`.

The capacity interruption occurred during preparation, before any W1.3 live dispatch. Resume inspection found the prepared runner and original W1.3 ledger snapshot, no W1.3 result, no pending plan and no unresolved stop. Counters exactly matched the preserved snapshot. No completed plan was repeated. The original W1 Grokipedia stop remains recorded; it was not cleared. Six later historical Qwen attempts also remain counted.

Reused the W1.1 controls and W1.2b measurement/admission runner in a temporary W1.3 derivative. Only temporary experiment scripts/fixtures were edited. A fixed W1.3 baseline snapshot enforces new budgets across counters; existing cumulative caps still apply. An exclusive process lock, persist-before-dispatch counters, pending-plan refusal, completed-plan suppression and sticky stop were retained. Per-plan results were saved before completion was recorded.

Twenty-one offline checks passed before execution: the previous eighteen W1.1/W1.2b controls plus three W1.3 checks covering exact cases/engine routing, new budget and zero-inference blocks in the retrieval runner, and query/repeat/history preservation. Mocked socket operations prevented live requests in the tests. No tests wrote to deployed storage.

Writable home/cache/temp/data locations were redirected under the isolated W1 directory before importing retrieval modules. Hindsight was disabled; credential/proxy environment variables were stripped. Audit guards prohibited deployed-data/credential reads, writes outside the isolated root, SQLite connections and subprocesses. Retrieval imported no canonical storage or recall lifecycle. No deployed Corvus API/chat call, personal memory access, database write, service restart, Production/Demo change, auth/network/Cloudflare change or model-setting mutation occurred. These are application-level guards, not a complete OS/network-namespace audit or an audit of unrelated concurrent service activity.

Preflight at `2026-10-19T02:07:26.017025+00:00` confirmed both selected SearXNG engines enabled and local Qwen health HTTP 200. The health request was not inference. No other model engine was used.

### Frozen questions and execution policy

| Case | Question | Identical discovery query for both providers |
| --- | --- | --- |
| A / W0 4 | Firefox 当前稳定版是什么？发布日期是哪天？ | Firefox 当前 稳定版 发布日期 官方 |
| B / W0 5 | Search NASA's official releases from the past seven days. Summarize one with its publication date. | NASA official news releases past seven days |
| C / W0 8 | 查阅 Python 3.13 和 3.14 官方文档，比较 concurrent.futures 的变化，分别提供来源。 | Python 3.13 3.14 concurrent.futures changes official documentation |

These are the existing W0 frozen queries. No Qwen intent call or query rewrite ran. Stored historical question wording differs slightly for B/C but asks the same task; the full requirements above governed evaluation.

DDGS 9.16.0 used explicit `duckduckgo` only, one worker, 8-second client timeout. SearXNG used exactly `google cse` for A/C and `google news` for B, with no categories/bangs sent. Each plan admitted one provider call and no fallback attempt. The existing deterministic first route was reused; its time range was set to None in the temporary runner, because the default news day filter would not represent seven days. No engine expansion or service configuration change occurred. General language settings followed the frozen query: Chinese A and English B/C; the Chinese C question had an English frozen query for both providers.

The NASA rolling-seven-day evaluation anchor was the preflight UTC timestamp, approximately 2026-10-12 02:07:26 through 2026-10-19 02:07:26 UTC. No candidate publication date was obtained, so boundary-day ambiguity did not affect a sufficiency decision. The query's relative date words alone would not verify freshness.

Pipeline `READY` is reported unchanged. `RETRIEVAL_SUCCESS` below means a page was fetched, extracted and selected; `EVIDENCE_SUFFICIENT` additionally requires the actual requested facts, date/version fidelity and source coverage. Discovery hits and titles alone do not qualify. `PROVIDER_FAILED` includes a selected engine explicitly reporting failure even if the adapter returns an empty list.

| Case | Provider | Pipeline | Retrieval/provider classification | Question evidence | Official hit rank | Normalized hits |
| --- | --- | --- | --- | --- | ---: | ---: |
| A — Firefox | DDGS | `READY` | `RETRIEVAL_SUCCESS` | `EVIDENCE_INSUFFICIENT` | 1 | 5 |
| A — Firefox | SearXNG | `READY` | `RETRIEVAL_SUCCESS` | `EVIDENCE_INSUFFICIENT` | 3 | 5 |
| B — NASA | DDGS | `NO_RESULTS` | `PROVIDER_FAILED` | `EVIDENCE_INSUFFICIENT` | Not observed | 0 |
| B — NASA | SearXNG | `NO_RESULTS` | `PROVIDER_FAILED` | `EVIDENCE_INSUFFICIENT` | Not observed | 0 |
| C — Python versions | DDGS | `NO_RESULTS` | `PROVIDER_FAILED` | `EVIDENCE_INSUFFICIENT` | Not observed | 0 |
| C — Python versions | SearXNG | `READY` | `RETRIEVAL_SUCCESS` | `EVIDENCE_INSUFFICIENT` | 1 | 5 |

Official-host evaluation recognizes Firefox's `firefox.com` brand site and `mozilla.org` subdomains, NASA's domain and `docs.python.org`. The original W0 Firefox preferred-host list contained only `mozilla.org`; on that narrower match DDGS's first hit is rank 5, versus rank 1 for the release index on `firefox.com`. This evaluator distinction did not change provider ranking or routing. An official host is not proof of the correct product channel, version or publication date.

### Per-plan evidence and diagnostics

### A — Firefox / DDGS

Query: **Firefox 当前 稳定版 发布日期 官方**

Pipeline `READY`; evaluation `RETRIEVAL_SUCCESS` / `EVIDENCE_INSUFFICIENT`. Release index has versions, no release date/current-stable proof.

Official-domain hit rank: 1. Selected URL: https://www.firefox.com/en-US/releases/.

| Rank | Returned title | URL |
| --- | --- | --- |
| 1 | Firefox Release Notes — Firefox.com | https://www.firefox.com/en-US/releases/ |
| 2 | 火狐 Firefox 143 浏览器稳定版发布：Win10 / Win11 版支持网站变 Web 应用 - IT之家 | https://www.ithome.com/0/883/262.htm |
| 3 | Firefox 158.0, See All New Features, Updates and Fixes | https://www.firefox.com/firefox/releasenotes |
| 4 | Firefox 火狐浏览器发布说明 (Release Notes) - ypingcn's blog / 相信万物逢时而美 | https://blog.ypingcn.com/special/firefox/releasenotes/ |
| 5 | Firefox 140.0, See All New Features, Updates and Fixes - Mozilla | https://www.mozilla.org/firefox/140.0/releasenotes/ |

Safe Fetch: HTTP 200, text/html, 160,469 bytes, 0 redirects.

Extraction: trafilatura-2.2.0, 1,352 characters; truncated=false.

Captured diagnostics before normalization: DDGS host `html.duckduckgo.com`, HTTP 200.

Search execution outcome(s): success.


### A — Firefox / SearXNG

Query: **Firefox 当前 稳定版 发布日期 官方**

Pipeline `READY`; evaluation `RETRIEVAL_SUCCESS` / `EVIDENCE_INSUFFICIENT`. Wikipedia references/novelty text selected instead of current release/date.

Official-domain hit rank: 3. Selected URL: https://zh.wikipedia.org/wiki/Firefox.

| Rank | Returned title | URL |
| --- | --- | --- |
| 1 | Firefox - 維基百科，自由的百科全書 | https://zh.wikipedia.org/wiki/Firefox |
| 2 | 火狐Firefox 浏览器152 稳定版发布：改版设置页面、增强媒体控制 | https://www.ithome.com/0/964/746.htm |
| 3 | Firefox ESR 的发布周期 | https://support.mozilla.org/zh-CN/kb/Firefox%20ESR%20%E7%9A%84%E5%8F%91%E5%B8%83%E5%91%A8%E6%9C%9F |
| 4 | Firefox版本列表- 維基百科，自由的百科全書 | https://zh.wikipedia.org/wiki/Firefox%E7%89%88%E6%9C%AC%E5%88%97%E8%A1%A8 |
| 5 | Firefox版本列表- 维基百科，自由的百科全书 | https://zh.wikipedia.org/zh-hans/Firefox%E7%89%88%E6%9C%AC%E5%88%97%E8%A1%A8 |

Safe Fetch: HTTP 200, text/html, 668,056 bytes, 0 redirects.

Extraction: trafilatura-2.2.0, 30,747 characters; truncated=false.

Captured diagnostics before normalization: SearXNG HTTP 200, selected `google cse`, responding `['google cse']`, raw results 20, unresponsive engines `[]`.

Search execution outcome(s): success.


### B — NASA / DDGS

Query: **NASA official news releases past seven days**

Pipeline `NO_RESULTS`; evaluation `PROVIDER_FAILED` / `EVIDENCE_INSUFFICIENT`. DDGSException: No results found; exact upstream cause unestablished.

Official-domain hit rank: Not observed. Selected URL: None.

No normalized result list was retained for this plan; no candidate fetch or extraction ran. This does not establish that no relevant public page exists.

Observed provider exception: `DDGSException`, `No results found.`. No retry.

Captured diagnostics before normalization: DDGS host `duckduckgo.com`, HTTP 200; DDGS host `duckduckgo.com`, HTTP 200.

Search execution outcome(s): provider_failed / WEB_SEARCH_PROVIDER_FAILED.


### B — NASA / SearXNG

Query: **NASA official news releases past seven days**

Pipeline `NO_RESULTS`; evaluation `PROVIDER_FAILED` / `EVIDENCE_INSUFFICIENT`. Google News access denied; adapter returned empty results.

Official-domain hit rank: Not observed. Selected URL: None.

No normalized result list was retained for this plan; no candidate fetch or extraction ran. This does not establish that no relevant public page exists.

Captured diagnostics before normalization: SearXNG HTTP 200, selected `google news`, responding `[]`, raw results 0, unresponsive engines `[['google news', 'access denied']]`.

Search execution outcome(s): empty.


### C — Python versions / DDGS

Query: **Python 3.13 3.14 concurrent.futures changes official documentation**

Pipeline `NO_RESULTS`; evaluation `PROVIDER_FAILED` / `EVIDENCE_INSUFFICIENT`. HTTP 202 followed by DDGSException; cause unestablished.

Official-domain hit rank: Not observed. Selected URL: None.

No normalized result list was retained for this plan; no candidate fetch or extraction ran. This does not establish that no relevant public page exists.

Observed provider exception: `DDGSException`, `No results found.`. No retry.

Captured diagnostics before normalization: DDGS host `html.duckduckgo.com`, HTTP 202.

Search execution outcome(s): provider_failed / WEB_SEARCH_PROVIDER_FAILED.


### C — Python versions / SearXNG

Query: **Python 3.13 3.14 concurrent.futures changes official documentation**

Pipeline `READY`; evaluation `RETRIEVAL_SUCCESS` / `EVIDENCE_INSUFFICIENT`. Useful change notes, but one unversioned page instead of both requested version sources.

Official-domain hit rank: 1. Selected URL: https://docs.python.org/3/library/concurrent.futures.html.

| Rank | Returned title | URL |
| --- | --- | --- |
| 1 | concurrent.futures — Launching parallel tasks — Python 3.15.0 ... | https://docs.python.org/3/library/concurrent.futures.html |
| 2 | What's New In Python 3.13 — Python 3.15.0 documentation | https://docs.python.org/3/whatsnew/3.13.html |
| 3 | What's new in Python 3.14 — Python 3.15.0 documentation | https://docs.python.org/3/whatsnew/3.14.html |
| 4 | What's new for Python in 2025? - Jumping Rivers | https://www.jumpingrivers.com/blog/whats-new-py314/ |
| 5 | Summary of Major Changes Between Python Versions | https://www.nicholashairs.com/posts/major-changes-between-python-versions/ |

Safe Fetch: HTTP 200, text/html, 108,627 bytes, 0 redirects.

Extraction: trafilatura-2.2.0, 24,417 characters; truncated=false.

Captured diagnostics before normalization: SearXNG HTTP 200, selected `google cse`, responding `['google cse']`, raw results 20, unresponsive engines `[]`.

Search execution outcome(s): success.


Only the first result was fetched in each of the three nonempty plans. Later result contents were not fetched or validated; no inferred answer was credited from their snippets. All three fetched pages were readable, untruncated, HTTP 200, with no redirects or fetch/extraction exceptions.

### Latency and cumulative accounting

Observed seconds, rounded to three decimals; no medians, percentiles or broad performance estimates. Total includes routing, URL normalization, ranking, selection and admission-accounting overhead.

| Case | Provider | Discovery | Fetch | Extraction | Total retrieval |
| --- | --- | ---: | ---: | ---: | ---: |
| A — Firefox | DDGS | 0.810 | 0.447 | 0.331 | 1.589 |
| A — Firefox | SearXNG | 0.433 | 1.228 | 0.280 | 1.951 |
| B — NASA | DDGS | 0.525 | Not run | Not run | 0.526 |
| B — NASA | SearXNG | 0.482 | Not run | Not run | 0.482 |
| C — Python versions | DDGS | 0.264 | Not run | Not run | 0.264 |
| C — Python versions | SearXNG | 0.298 | 0.347 | 0.080 | 0.729 |

| Counter | Before W1.3 | New usage | Cumulative after |
| --- | ---: | ---: | ---: |
| plans | 3 | 6 | 9 |
| provider_calls | 3 | 6 | 9 |
| candidate_fetches | 3 | 3 | 6 |
| ddgs_http | 11 | 4 | 15 |
| searxng_http | 1 | 3 | 4 |
| fetch_http | 3 | 3 | 6 |
| redirects | 2 | 0 | 2 |
| qwen_turns | 6 | 0 | 6 |

The six cumulative Qwen attempts are historical; this run used zero of its optional maximum two. New candidate fetches were three of eighteen, not eighteen. All six plans counted, including failed plans. Historical completed plans and source-artifact hash were preserved. Elapsed admission-clock accounting rose from 25.458 to 31.598 seconds; this excludes operator/tool waiting and is not project wall time.

Original caps remain: 16 total plans, 32 provider calls, 48 candidate fetches, 128 DDGS transport dispatches, 32 SearXNG client search dispatches, 96 page HTTP dispatches, 64 redirects and eight cumulative Qwen attempts. Per-plan deadline 45 seconds; cumulative admission-clock deadline 900 seconds; ten DDGS HTTP dispatches per plan; two DDGS redirect hops per chain; normal Safe Fetch public-IP pinning/TLS and up to three page redirects. Additional W1.3 retrieval admission caps were 6/6/18 logical operations, 30 DDGS transports, three SearXNG client requests, 72 page transports and 60 redirects, always subject to the remaining cumulative caps. The retrieval runner had zero inference allowance.

**SearXNG upstream limitation:** one selected engine and one client search call do not cap or measure every internal preparation request, redirect or retry. Server-internal HTTP counts remain unknown. No strict internal cap is claimed, and a client stop could not cancel work already dispatched by the service.

## B. Provider comparison

- **A / Firefox:** DDGS found a first-party release index; Google CSE selected Wikipedia, with an official Mozilla ESR-support page only at rank 3. Neither supplied selected evidence for current stable release plus date. This case does not favor a provider switch.
- **B / NASA:** DDGS raised “No results found” after two allowed HTTP 200 responses. That exception does not establish whether the engine truly had no results or failed to parse a usable response. Google News returned `access denied`, zero results, no responding engine. The SearXNG adapter classified the response as empty; evaluator classification is provider failure. Neither found a usable release in the requested date window.
- **C / version comparison:** DDGS returned HTTP 202 then raised “No results found”; challenge/rate-limit explanations remain unverified. Google CSE found useful official change notes but selected an unversioned /3/ page rather than independently providing the requested version sources. Discovery was better; full-task sufficiency was not achieved.

W1's original auto-backend zstd sample remains separate because its backend settings differ and the experiment stopped on a destination-policy violation. W1.2b showed Google CSE finding modern `autocommit` evidence where DDGS selected a Python 3.8 page. Across the four paired questions in W1.2b/W1.3, Google CSE/SearXNG produced three technically selected pages and DDGS two; only the SearXNG sqlite3 selection was judged sufficient for its requested task. These are descriptive counts under deliberately strict requirements, not everyday reliability rates, statistical superiority or evidence that all provider configurations would behave identically.

There is evidence to retain SearXNG/Google CSE as a strong discovery candidate, but no basis to make it an unconditional live replacement. Google News currently fails this sample. No automatic general-engine fallback or extra provider call was attempted. Preserve configured engine identity and diagnostics; do not turn access denial into “nothing exists.”

## C. Evidence sufficiency findings

**A — Page relevance and dates:** DDGS's extracted release index lists versions, including 158.0, but no release dates or explicit current-stable status. It is a navigational page, not an answer. The SearXNG search snippet mentioned a version/date; extracted Wikipedia text also contains a bibliography reference to that release, but the selected excerpts instead contain external links, novelty features and older references. A search snippet or an unselected bibliography entry is not the evidence given to the model. No independently fetched first-party release/date was established, and the report makes no claim about the true current Firefox version.

**B — Failure transparency:** no release page, publication date, extracted body or selected evidence exists. No summary can responsibly be generated from these plans. The raw Google News diagnostic demonstrates a real provider failure misreported by normalized empty discovery. DDGS's exception was already recorded as `provider_failed` internally but collapsed to top-level `NO_RESULTS`.

**C — Versions and independent sources:** the selected Python source has a search title identifying 3.15.0 and an unversioned URL. Its exact excerpts do contain version-tagged changes: 3.13 worker-count defaults, 3.14 process start-method behavior and `terminate_workers`. They also include a 3.15 fix and general API background. This is useful partial evidence, but not separately fetched 3.13 and 3.14 documentation. Search hits for both What's New pages existed at ranks 2/3 and were never fetched. One page cannot demonstrate the requested independent source coverage or multi-source integration. The full extraction additionally includes buffersize and InterpreterPoolExecutor changes; those relevant sections were not selected. No inferred completeness is awarded.

**Selection weakness:** the current first-positive-evidence stopping rule and lexical ranking accept topical overlap. They do not establish publication freshness, target-version fidelity or full requested coverage. Firefox gives a particularly clear ranking failure; Python gives a clear source-coverage failure; W1.2b gives a clear old-version acceptance failure. None of the three readable W1.3 selections satisfies its full question.

Traceable selected-excerpt hashes are recorded below; references are local to each plan, not a combined multi-source prompt. No full fetched pages or raw metrics are included in the public report.

| Case/provider | Reference | Characters | Excerpt SHA256 |
| --- | --- | ---: | --- |
| 4/DDGS | web_1 | 1195 | `1b7fcc50cff073b1e460c357fdda05969db7e531f731642a7f0f0675732f78dc` |
| 4/SearXNG | web_1 | 757 | `f6b421b67e63ba5c2ab8f4b30199d170228b487d0758b1febd410f114dee61de` |
| 4/SearXNG | web_2 | 1125 | `ffe6aaea51e039d14fd7947cad5424ade9ef4d1fe587430508fd361783991fd4` |
| 4/SearXNG | web_3 | 1130 | `7eff3f2ad06b66ac6d2200766cb2b9140f09c6d1a288c8af6cf8febc74fdfb84` |
| 8/SearXNG | web_1 | 1113 | `29150566af3e8eb4a2700dcc928261d07ac183a670d5e5793b66b67d96b589c0` |
| 8/SearXNG | web_2 | 1113 | `6738c3dea1dd6313625b4deacb274483ed07469832e466817d0c88f611f0741f` |
| 8/SearXNG | web_3 | 1179 | `4350ae5e4023c866b06d0e7aa18b0c57e5ef064006bf09cc260a0626b461786b` |

## D. Model-answer observations

**Not run: zero new Qwen calls.** No plan supplied evidence sufficient for its full authorized question, so neither optional inference call was used. No answers, token counts, new grounding scores, unsupported-claim counts or generation latencies are fabricated. Model health HTTP 200 is availability evidence only.

Historical W1.2a-R1/R2 show natural Chinese/English explanation from a single reliable document, with inconsistent factual restraint. R2 removed some Chinese overclaims but English performance/dependency claims remained. Those are historical findings, not new W1.3 results or proof of multi-source ability. Better prompting alone cannot supply missing dates, correct page versions or independent sources. No further zstd tuning, new model, agent or framework is justified here.

## E. Remaining limitations

- Three W1.3 paired questions, sequential provider order, one call per plan, five normalized-result budget. No repeat trials, cache controls, inference trials or statistical reliability claim.
- NASA provider responses supplied no release evidence; the actual release inventory and whether a general engine would succeed remain unknown. This does not prevent implementing truthful failure handling.
- No later candidate was fetched after the first accepted page. A bounded continuation policy is justified, but its recovery success is unmeasured. No new request was made to fill that gap.
- No independent version-source pair was selected. Multi-source answer quality and real Qwen attribution across pages remain unverified.
- The extracted pages and search snippets are snapshots. Unversioned URLs and current-release claims can change. Dates mentioned in snippets were not promoted into verified publication metadata.
- No automatic-intent/query-rewrite accuracy or UI/browser live acceptance was tested; frozen queries intentionally removed that variable.
- Existing canonical user-first/assistant-after-generation/provenance/derived-state ordering was inspected in source but not executed. No database inspection, chat call, canonical write or Hindsight access occurred.
- Cached Open WebUI 0.6.5 source was reviewed for integration options; no native-search runtime comparison was performed. Prior reports retain their original verdicts.

## F. Architecture recommendation

### A. Search-provider quality

Reuse existing provider adapters and SearXNG. Keep explicit engine selection, bounded work and raw engine diagnostics. Google CSE is suitable for the first prototype's general discovery configuration, with DDGS retained as a supported explicit alternative; this is a prototype choice, not an authorized production default change. Expose Google News access denial as failure. Do not activate two pipelines or automatic provider retries.

### B. Page/version relevance

Add a narrow evidence-requirements contract to the isolated prototype: requested version(s), publication window/current-as-of time, permitted authoritative domains where requested, and required distinct source coverage. Derive these explicitly from the prototype's inputs rather than creating a universal query parser or another model verifier. Validate version identity and publication/date provenance against fetched material; snippets, a domain match or a high lexical score cannot satisfy them. Report unknowns rather than guessing.

### C. Evidence selection and sufficiency

Reuse existing Safe Fetch, trafilatura, passage building and BM25-style lexical ranker. Add a requirement-aware acceptance step around them, continuing through the existing small candidate budget when a page is navigational, outdated or incomplete. Rank for the factual target rather than broad words such as “official documentation,” with deterministic fixture checks for release dates and API changes. A positive lexical score remains technical readiness, separate from a narrowly defined coverage assessment; no static gate proves general semantic truth. Preserve distinctions among empty discovery, provider failure, fetch/extraction failure and insufficient evidence.

### D. Multi-source coverage

For explicit comparisons, allow bounded collection from two required version sources instead of always stopping at one page. Reuse exact-source slices and evidence records; ensure global reference/ordinal uniqueness and one fixed total excerpt budget before packing. Do not simply concatenate independently numbered `web_1` sets or claim one page is two independent sources. If the existing budget cannot fulfill the request, return a transparent incomplete-evidence result. Preserve exactly the evidence set supplied to the model for subsequent provenance persistence.

### E. Model synthesis and grounding

Retain the current Qwen endpoint, existing single-system-message composer and untrusted-evidence packer. No prompt-tuning loop, additional model/agent, automatic retry or new async system. Only invoke generation when requirements are met or an explicitly designed partial-answer mode clearly states unmet requirements. A lost client response remains uncertain; no canonical-turn resubmission follows automatically. Keep user commit, assistant commit, evidence persistence and derived dense-write ordering unchanged; Hindsight and Memory A/B remain outside this prototype.

### F. Source presentation in Open WebUI and reuse decision

The current Pipe returns `reply` and has an Arena-specific side channel. It does not forward a validated Web source map. The API exposes evidence refs/status/counts, but those do not by themselves provide a user-visible ref-to-URL/excerpt mapping. A minimal bridge should expose the exact used refs, safe public URLs/titles and relevant evidence status, preserving session/user authorization and confirmed-persistence handling. Reuse Open WebUI's existing source/citation UI or a small read-only source block; do not generate links from unvalidated model text. Confirm the pinned Pipe event contract in an isolated integration fixture before choosing native cards. A presentation-event failure must not trigger another Corvus POST or invalidate an already committed reply.

**Existing-component comparison:** cached v0.6.5 `retrieval/web/searxng.py` already provides a SearXNG adapter, but normalizes results without preserving `unresponsive_engines`. Its middleware can generate queries and route fetched documents into files/RAG context; the retrieval router uses its own loader and, unless bypassed, vector storage. Its source UI is reusable, but enabling native search wholesale is not a transparent provider swap. The current Pipe explicitly rejects nonempty feature/file/tool fields, including WebUI search features. Removing those guards would not establish Corvus Safe Fetch equivalence, provenance or canonical ownership. No native pipeline was activated, and no claim of inferior or superior retrieval quality is made.

A new framework, embedding/reranking service or full native-search replacement adds unproven complexity. The observed defects are narrow enough to address by reusing existing retrieval components and a small coverage/status/source bridge. A wholesale native-search prototype is not required before that work can safely begin.

## G. Exact next implementation stage

**W2 — Isolated evidence acceptance and source-contract prototype; no deployment.**

1. Use the saved W1.2b/W1.3 public fixtures to implement a small typed requirements/result contract and provider-diagnostic mapping. Keep technical readiness and requirement coverage distinct. Cover Google News access denial, DDGS exceptions, genuine empty results and insufficient evidence deterministically.
2. Adapt the existing candidate loop in isolation to test requirement coverage before stopping. Hard prototype caps: at most three candidates, at most two distinct accepted sources, one total existing 3,600-character excerpt budget, unique global evidence refs. Reuse Safe Fetch/extraction/ranker and existing exact-source validation. No new search engine, inference verifier or general NLP parser. Do not relabel old `READY` as sufficient without the additional checks.
3. Demonstrate deterministic rejection of the Python 3.8 autocommit source for the requested parameter, Firefox release-index/irrelevant passages for the date task, and a single unversioned Python source for the requested two-source comparison. Add positive, explicitly labeled public-document fixture pairs for correct version/date coverage; saved incomplete evidence must remain incomplete. This is implementation contract testing, not another live benchmark.
4. Define the minimal validated used-source map for the API/Pipe presentation bridge; test against pinned Open WebUI source/citation behavior in isolation. Preserve authenticated identity mapping, no-auto-retry behavior and persistence-degradation reporting. Do not modify live Pipe guards or enable native search until that bridge is separately reviewed.
5. Review the prototype and canonical-provenance implications before authorizing repository integration or live acceptance. No new live searches or inference are required merely to implement these fixture-based contracts. Any later bounded live acceptance needs its own explicit authorization; no general provider benchmark is recommended.

Acceptance means demonstrably truthful failure/coverage handling and stable source identity within the tested scope, not universal factual verification or everyday Web reliability. No deployed product changes were made by W1.3.

### Artifact and publication review

Preserved original W1, W1.1, W1.2a/R1/R2 and W1.2b reports and artifacts. New local artifacts are the W1.3 temporary runner/fixture, preflight, result file and baseline ledger snapshot. Sanitized aggregate metrics may remain locally; raw JSON, terminal transcripts and full page content are excluded from this commit.

Only this report and its chronological Web index entry are intended for publication on `reports/web-validation`. Privacy review covers public synthetic questions, URLs, source hashes, bounded diagnostics and measurements; no passwords, API keys, tokens/cookies, private chats, personal memory, database contents or unnecessary sensitive host details are included. Lab source and runtime remain unchanged.
