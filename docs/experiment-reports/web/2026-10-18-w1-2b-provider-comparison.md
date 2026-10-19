# W1.2b — Bounded live search provider comparison

**Date:** 2026-10-18

**Verdict:** `W1_2B_VALIDATED`

Both authorized retrieval plans completed without a mandatory safety stop. Google CSE through SearXNG produced directly relevant official-documentation evidence for the requested parameter. Explicit DuckDuckGo through DDGS selected older official documentation about transaction behavior, insufficient to explain the requested `autocommit` parameter. Both returned Corvus pipeline status `READY`; that status alone is not a semantic success criterion. This is one paired question, with no model inference and no everyday reliability estimate.

## A. Experiment setup

- Lab baseline: `lab/ow2e-console`, commit `975645963291ec992d64df0474a3ee9d0ba33dcd`; clean before and after retrieval.
- Reporting baseline: `reports/web-validation`, commit `58149b66f50c80ee749a8b68af2bd327415e2c1c`; initially clean.
- Question, W0 case 2: **请查 Python 官方文档，说明 sqlite3 的 autocommit 参数。**
- Identical frozen discovery query for both providers: **Python sqlite3 autocommit 官方文档**.
- DDGS 9.16.0: supported explicit `backend=duckduckgo`, text/general search, region `cn-zh`, moderate safe search, 8-second client timeout, one worker. No `auto` or `all` selection.
- SearXNG: exactly one client search request with `engines=google cse`, language `zh-CN`, JSON response. No categories, bangs, time-range or additional engine selectors were sent. A preceding local configuration GET returned HTTP 200 and confirmed `google cse` enabled for general/web.
- Plans ran sequentially, DDGS then SearXNG, using the repaired W1.1 runner and existing Corvus adapters, orchestration, Safe Fetch, extraction and evidence selection. No alternative search pipeline was implemented.
- The existing deterministic route is named `zh-general-goc` and its plan metadata contains `engine_bang=goc`. The temporary runner deliberately passes `engine_bang=None` to SearXNG and applies the reviewed explicit-engine URL guard. The stored route name does not mean a bang or extra engine was dispatched.
- Search limit: five normalized results per provider. Existing orchestration may fetch up to three candidates per plan and stops at its first usable page. Evidence budget: up to three excerpts from that one page.
- No retries, query rewriting, intent inference, completed-case-1 repetition or Qwen calls.

## B. Isolation verification

The original W1 and W1.1 reports and repaired controls were inspected. The persistent ledger retained the original Grokipedia stop record, original expenditure and six later W1.2a/R1/R2 Qwen attempts. No stop record was cleared. There was no unresolved repaired-run mandatory stop or pending plan at admission.

The temporary runner gained only per-run admission guards and measurement wrappers. New caps were two plans, two provider calls, six candidate fetches and zero inference calls. It also rejects changed queries, repeated provider calls and non-case-2 routes. Existing cumulative limits, public-URL validation, allowed DDGS destinations, redirect controls and sticky fail-stop behavior remained active.

Eighteen offline tests passed before execution: the previous fifteen control checks, with current-ledger accounting preserved, plus three checks for the new caps/zero inference, frozen-query/single-call/plan guards and exact case-2 Google CSE selection. Mocks denied network dispatch during these tests. The underlying W1.1 control module was unchanged.

A fresh subprocess redirected writable HOME/cache/temp/data paths under the isolated temporary root before Corvus imports. Credential/proxy environment variables were stripped; Hindsight was disabled. Python audit guards prohibited deployed-data/credential reads, writes outside the isolated root, SQLite connections and subprocesses. Phase A imported retrieval components only. No personal memory, deployed recall, API server or canonical persistence path was invoked.

Observed: no filesystem, storage or mandatory destination violation; temporary root mode 0700 and result file mode 0600. These application-level guards are not a full OS/network-namespace audit. SearXNG upstream requests remain outside client transport instrumentation. No service, deployed configuration, Lab source, Production/Demo, FoxGate, Cloudflare or model setting was changed. No deployed chat endpoint was called. Unrelated concurrent service activity was not audited.

## C. DDGS results

- Discovery succeeded: five normalized valid results, zero rejected URLs. Raw pre-adapter engine-result count was not separately captured.
- Official `docs.python.org` source rank: **1**. Selected/fetched URL: [Python 3.8 Chinese sqlite3 documentation](https://docs.python.org/zh-cn/3.8/library/sqlite3.html).
- One allowed discovery HTTP dispatch to `html.duckduckgo.com`, HTTP 200. No other DDGS destination or discovery redirect was observed.
- Safe Fetch: HTTP 200, text/html, 175,295 bytes, no redirects.
- Extraction: trafilatura 2.2.0, 25,940 characters, not truncated; readable API and transaction documentation.
- Three selected excerpts, 3,209 characters total, all from this page. The leading excerpt describes older implicit-transaction behavior and `isolation_level`. Other selected passages include converters and callbacks rather than the requested parameter.
- The extracted Python 3.8 text contains neither `Connection.autocommit`, `autocommit=` nor `LEGACY_TRANSACTION_CONTROL`. General SQLite autocommit-mode text is not documentation of the requested Python connection parameter.
- **Pipeline status:** `READY`, first candidate `SELECTED`. **Question-level evaluator classification:** `NO_USABLE_EVIDENCE` for explaining the requested parameter; useful historical background only. This is a relevance/version-selection failure, not a transport/provider exception.

## D. SearXNG results

- Client search HTTP 200. Raw response: **20 results**; existing adapter retained five, all passed URL normalization, zero rejected.
- Diagnostics captured before adapter normalization: selected engine `google cse`; responding result-engine set exactly `google cse`; `unresponsive_engines=[]`. No unselected engine was reported. This does not measure every upstream request.
- Official `docs.python.org` source rank: **1**. Selected/fetched URL: [Unversioned Chinese sqlite3 documentation](https://docs.python.org/zh-cn/3/library/sqlite3.html).
- Returned title identifies Python **3.15.0**. This report does not assert that the unversioned URL is a particular stable release or pin its future contents.
- Safe Fetch: HTTP 200, text/html, 323,713 bytes, no redirects.
- Extraction: trafilatura 2.2.0, 40,682 characters, not truncated. Extracted text includes the connect signature and parameter definition, `Connection.autocommit` and `LEGACY_TRANSACTION_CONTROL`.
- Three selected excerpts, 3,466 characters total. The third gives directly relevant transaction-control guidance: the `False`, `True` and legacy modes and their relationship to explicit commits/rollbacks. This is substantive fetched evidence, not a search-title judgment.
- Selection remains noisy: the first excerpt mixes configuration constants, cursor/blob APIs and commit behavior; the second is introductory/tutorial material. The full extracted parameter definition/default is not selected as a dedicated excerpt. Available selected evidence supports a useful explanation of transaction modes, but does not establish complete coverage of every parameter detail.
- **Pipeline status:** `READY`, first candidate `SELECTED`. **Question-level evaluator classification:** `SUCCESS` for usable parameter-related evidence, with the coverage limits above. No answer was generated or evaluated.

## E. Retrieval comparison

| Measurement | DDGS / DuckDuckGo | SearXNG / Google CSE |
| --- | --- | --- |
| Normalized valid results | 5 | 5, from 20 raw results |
| Official documentation rank | 1 | 1 |
| Selected page | Versioned Python 3.8 | Unversioned /3/, title 3.15.0 |
| Fetch/extraction | Successful | Successful |
| Requested-parameter evidence | Insufficient; older transaction behavior | Directly relevant transaction modes |
| Provider/transport exceptions | None observed | None observed |
| Automatic retries | 0 | 0 |

Returned URLs in normalized order are retained for review. Only rank 1 from each provider was fetched; later URLs and their snippet claims were not validated or endorsed.

| Rank | DDGS | SearXNG |
| --- | --- | --- |
| 1 | https://docs.python.org/zh-cn/3.8/library/sqlite3.html | https://docs.python.org/zh-cn/3/library/sqlite3.html |
| 2 | https://runebook.dev/zh/docs/python/library/sqlite3/sqlite3.Connection.isolation_level | https://docs.python.org/zh-cn/3.6/library/sqlite3.html |
| 3 | https://runebook.dev/zh/docs/python/library/sqlite3/sqlite3.Connection.autocommit | https://docs.python.org/zh-cn/3.9/library/sqlite3.html |
| 4 | https://docs.pythonlang.cn/3/library/sqlite3.html | http://docs.sqlalchemy.org/en/latest/dialects/sqlite.html |
| 5 | https://liaoxuefeng.com/books/python/database/sqlite/index.html | https://docs.python.org/zh-cn/3.10/library/sqlite3.html |

**Observed:** Google CSE selected the more relevant official page for this question. Official-host rank alone failed to distinguish modern parameter coverage from old transaction-mode documentation. Explicit DDGS selection avoided the original auto-backend destination violation in this run; a different query and single sample do not prove a general reliability improvement.

**Inference:** version/API relevance and passage ranking deserve further evaluation. The first-usable-page limitation was visible: DDGS stopped at the older page once lexical selection produced nonempty evidence, rather than verifying coverage of the requested parameter. No later candidate was fetched, so this experiment does not show that continuing would have recovered better evidence. SearXNG's successful single page suffices for this narrow question; this is not a multi-source synthesis test.

**Unverified:** comparative everyday reliability, performance on other queries, benefits of multi-page selection, generated-answer grounding and Open WebUI-native retrieval performance. This sample favors Google CSE for this question only and does not justify a deployed provider substitution.

## F. Failure breakdown

| Category | Observation |
| --- | --- |
| `NO_RESULTS` | Neither discovery was empty |
| `PROVIDER_FAILED` | No provider exception recorded; SearXNG reported no unresponsive engine |
| `FETCH_FAILED` | None in the two attempted page fetches |
| `EXTRACTION_FAILED` | None; both extracted readable, untruncated documentation |
| `NO_USABLE_EVIDENCE` | DDGS semantic assessment for the requested parameter, despite pipeline `READY` |
| `SUCCESS` | SearXNG supplied directly relevant selected evidence; no model-answer success claim |

There was no mandatory safety stop, retry or hidden later plan. Existing code can collapse provider failures into top-level `NO_RESULTS`; that path was inspected but not exercised here and remains unchanged. The observed failure was semantic acceptance of an old but official page. No plausible model answer was used as a retrieval proxy.

## G. Latency and resource observations

All times are observed seconds, rounded to three decimals. Fetch and extraction were measured separately around existing functions. Total includes routing, normalization, passage ranking, selection and admission/accounting overhead.

| Stage | DDGS | SearXNG |
| --- | ---: | ---: |
| Discovery | 0.773 | 0.531 |
| Safe Fetch | 0.233 | 0.251 |
| Extraction | 0.172 | 0.295 |
| Total retrieval | 1.186 | 1.089 |

These are single observations, without cache-state controls or counterbalanced ordering. No median, p95, throughput or reliability percentage is inferred. No model workload was introduced.

| Ledger counter | Before W1.2b | New usage | Cumulative after |
| --- | ---: | ---: | ---: |
| plans | 1 | 2 | 3 |
| provider_calls | 1 | 2 | 3 |
| candidate_fetches | 1 | 2 | 3 |
| ddgs_http | 10 | 1 | 11 |
| searxng_http | 0 | 1 | 1 |
| fetch_http | 1 | 2 | 3 |
| redirects | 2 | 0 | 2 |
| qwen_turns | 6 | 0 | 6 |

The six cumulative Qwen attempts belong to earlier experiments; new inference count is zero. Original completed case 1 remains recorded; only case 2/DDGS and case 2/SearXNG were appended. Historical stop and original artifact hash were retained. Cumulative admission-clock elapsed accounting rose from 22.656 to 25.458 seconds; it excludes operator/tool wait time and is not total project wall time.

Existing controls retained: 45-second per-plan deadline, 900-second cumulative admission-clock budget; at most ten DDGS HTTP dispatches per plan; at most two discovery redirect hops per chain; normal Safe Fetch public-IP pinning and up to three page redirects. Additional new-run caps were ten DDGS HTTP dispatches, one SearXNG search client dispatch, 24 page HTTP dispatches and 20 redirects, subject to stricter existing cumulative caps. Actual usage is shown above; unused allowance was not consumed.

**SearXNG limitation:** one selected engine and one client search request do not bound all internal server-side HTTP dispatches, redirects or retries. Their actual count was not observed and must not be reported as one. Only client-call count and returned engine diagnostics are established.

## H. Remaining limitations and provenance

- One Chinese query, one execution per provider plan, no repeat trials or retries. No broader reliability or latency comparison.
- Zero Qwen calls: answer quality, citation use and grounded conversational synthesis were not assessed.
- No unsafe fixtures were requested. Existing offline controls passed; absence of a live violation does not prove universal safety.
- Search snippets and unfetched results are discovery metadata. Only fetched extracted content and selected excerpts support the semantic judgments.
- No version pin or extraction/selection improvement was implemented. A current official-host hit is not automatically the requested API version, and the unversioned URL may change.
- No deployed SQLite/WAL inspection or mutation was performed. Isolation evidence is the guarded retrieval-only path, not a new production persistence acceptance test.
- Historical W1/W1.1 and synthesis reports are preserved with their original verdicts.

Selected excerpt SHA256 hashes below make the evaluation traceable to preserved local evidence without publishing raw metrics or complete fetched pages. Character counts use Python string length.

| Provider | Reference | Characters | SHA256 |
| --- | --- | ---: | --- |
| DDGS | web_1 | 1196 | `1d49f3d27980cb69bb379762e3b00f19e68324825b81fbd9bbc66726c80d220b` |
| DDGS | web_2 | 964 | `9735acc0399cdbab27d7dca70204e9fcd59932b66ccde5aac32c26555010ff71` |
| DDGS | web_3 | 1049 | `1ccc2c0ef4861dee908bc79e7b12a0c46af82b3f8da823acd3c51bffa69f4c55` |
| SearXNG | web_1 | 1141 | `a49c6f7c9aabad4904e487d5a8b9dbf80aea8b2b17c2b615a6fe0254e0692ded` |
| SearXNG | web_2 | 1184 | `ba9dd90e0ef026962c6bdccd75255e704c7b72af6b2c4483b7fa5ede65df251e` |
| SearXNG | web_3 | 1141 | `971535bbfed085f0f7563dabf18c5b03867c6bb55da6fa340bfb4251d37918f0` |

Local artifacts: repaired `/tmp/corvus-w1-run.py`, unchanged `/tmp/corvus_w1_controls.py`, offline fixture `/tmp/test_corvus_w1_2b_controls.py`, and `w1-2b-results.json`, `w1-2b-ledger-before.json`, `ledger.json` inside the isolated W1 state directory. Original W1 report/metrics and prior results were preserved. Raw metrics and temporary scripts are not part of the public documentation commit.

## I. Recommended next step

Retain the deployed architecture. Do not switch providers from this pair alone. The smallest next step is a separately authorized small set of matching public questions testing version-specific APIs and genuinely multi-source questions, with explicit provider selection and the same fail-stop controls. Record question-level evidence sufficiency separately from `READY`, including version fidelity and passage coverage. Reuse good evidence for bounded grounded-answer evaluation only under a later inference authorization.

If Google CSE consistently improves relevant discovery across that set, consider provider-only substitution. If both providers return suitable pages but selection remains noisy or stops at incomplete evidence, address that specific selection defect. No new agent, retrieval framework, native WebUI pipeline, deployment or further single-document prompt tuning is justified by this run.

**Privacy/publication review:** documentation contains only synthetic public questions, public URLs, sanitized diagnostics, aggregate measurements, evidence hashes and evaluator judgments. No passwords, tokens/cookies, keys, private conversations, memory/database contents or unnecessary sensitive host details are included. Only this report and its index entry are intended for commit/publication on `reports/web-validation`.
