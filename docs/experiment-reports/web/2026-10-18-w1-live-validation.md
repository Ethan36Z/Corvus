# Corvus W1 — Isolated Live Web Reliability Validation

Experiment: **W1**

Date: **2026-10-18**

Related Lab baseline: `975645963291ec992d64df0474a3ee9d0ba33dcd`

> Public archive copy. Account-specific checkout paths are replaced with
> `<lab-checkout>` (or `$LAB_CHECKOUT` in the historical command). Local `/tmp`
> artifacts are referenced for provenance only and are not included in this
> archive. The baseline identifies the local experiment checkout; it may not
> resolve on GitHub because its commits were unpublished. Verdicts, measurements
> and acceptance boundaries are preserved.

**Final verdict: W1_BLOCKED_WITH_REASON**

The experiment stopped after its first DDGS plan because a DDGS backend attempted a destination absent from the experiment allowlist: `grokipedia.com`. The guard blocked this request before dispatch. DDGS caught the exception internally and continued; the harness observed the violation at the plan boundary, after an allowed official-documentation fetch. No subsequent plan or Qwen turn ran. This is an experiment-control limitation, not proof of an unsafe Corvus Safe Fetch request or a malicious destination.

## A. Isolation verification

- Repository: `<lab-checkout>`; branch `lab/ow2e-console`; starting HEAD `975645963291ec992d64df0474a3ee9d0ba33dcd`.
- Git worktree was clean before and after execution; whitespace check passed.
- Preflight health GETs: Lab WebUI, Lab API, SearXNG and shared Qwen each HTTP 200. No deployed chat endpoint was called.
- A fresh subprocess used an empty inherited environment except PATH/LANG/bytecode control. HOME, XDG_CACHE_HOME, HF_HOME, HF_MODULES_CACHE, TORCH_HOME, TMPDIR and CORVUS_DATA_DIR were redirected under `/tmp/corvus-w1-isolated` before application imports.
- Temporary root mode 0700; experiment files mode 0600. No private credentials were supplied. HF/Transformers offline flags were set; Hindsight disabled; foreground registry publication unset.
- Python audit hooks blocked writes outside the isolated root, forbidden deployed-data/credential reads, non-isolated SQLite connections and subprocess creation. No filesystem/database isolation violation was observed.
- Phase A imported retrieval components only; storage initialization, deployed recall, Hindsight and Personality compilation were not invoked. No API server was created. Phase B never ran, so no synthetic SQLite persistence lifecycle was exercised.
- These are application-level controls, not a network namespace or full OS syscall audit. The Rust DDGS transport was instrumented at its Python request boundary.

## B. Query/provider comparison

Only 1 of 16 planned provider/query plans executed. SearXNG has no live-search result in this run; no comparative win rate or provider ranking can be calculated.

| Case | Frozen discovery query | DDGS | SearXNG |
|---|---|---|---|
| 1 | Python 3.14 documentation compression.zstd module | READY; experiment safety stop | NOT RUN |
| 2 | Python sqlite3 autocommit 官方文档 | NOT RUN | NOT RUN |
| 3 | Python latest stable release release date official | NOT RUN | NOT RUN |
| 4 | Firefox 当前 稳定版 发布日期 官方 | NOT RUN | NOT RUN |
| 5 | NASA official news releases past seven days | NOT RUN | NOT RUN |
| 6 | 洛杉矶 最近七天 新闻 日期 | NOT RUN | NOT RUN |
| 7 | Ontario California seven day weather forecast | NOT RUN | NOT RUN |
| 8 | Python 3.13 3.14 concurrent.futures changes official documentation | NOT RUN | NOT RUN |

The questions are the eight W0 public-information cases; queries were frozen to isolate discovery from live intent/query-rewrite inference. No query rewrite or intent model calls ran.

## C. Per-query retrieval evidence

Case 1 question: “Search the official Python 3.14 documentation: what does compression.zstd provide?”

- DDGS returned 5 normalized valid results; rejected count 0. URL validity is not an answer-quality score.
- Preferred official host rank: 1.
- Selected and fetched URL: `https://docs.python.org/3/library/compression.zstd.html`.
- HTTP 200; 129,943 bytes; no page redirects; extracted text 28,872 characters.
- Three selected evidence excerpts, 3,483 characters total, all from the same official page.
- This demonstrates usable retrieval for one narrow case only. The unversioned `/3/` URL does not by itself establish Python 3.14 version fidelity; that was not adjudicated. No generated answer was evaluated.

Returned sources in normalized order:

- Rank 1: https://docs.python.org/3/library/compression.zstd.html
- Rank 2: https://docs.python.org/3/library/compression.html
- Rank 3: https://wiki.tahlwyn.zone/content/docs.python.org_en_2025-09/docs.python.org/3.14/library/compression.zstd.html
- Rank 4: https://pyzstd.readthedocs.io/en/latest/
- Rank 5: https://pypi.org/project/zstd/

Selected excerpt samples (shortened for review; exact excerpts and hashes in metrics):

- `web_1`: compression.zstd — Compression compatible with the Zstandard format¶ Added in version 3.14. Source code: Lib/compression/zstd/__init__.py This module provides classes and functions… SHA256 `b8558551a5c8ff547e342ce76bdcb2dd65ac29d00620e1fceeb6b9f7bcb8335a`.
- `web_2`: functions and theZstdDict class to train and manage Zstandard dictionaries. - The CompressionParameter ,DecompressionParameter , andStrategy classes for setting advanced (de)compre… SHA256 `42f43b0165ba196df9105b0b118fe1534678c61570ff64223d576ec4b606bfe3`.
- `web_3`: to setting CompressionParameter.compression_level in options. Usebounds() oncompression_level to get the values that can be passed for level. If advanced compression options are ne… SHA256 `e3eb7a4e1025d64be157aee49cfbd5d2994ba44ee409f78489693d803adc6078`.

## D. Provider failure breakdown

- DDGS auto discovery is itself multi-backend, not one HTTP request to DuckDuckGo.
- Observed allowed transport responses: Wikipedia 200, Mojeek 200, Yahoo 307→307→200, Startpage 200 twice, Google 403, Brave 429, DuckDuckGo HTML 200.
- Ten DDGS HTTP dispatches were recorded, across seven distinct hostnames. Two observed redirect hops were counted.
- Google 403 and Brave 429 are observed transport statuses; this run did not establish their precise causes. HTTP 200 alone is not engine-result quality evidence.
- The unexpected Grokipedia attempt was blocked and excluded from dispatched-request counts. Inspection after stopping confirmed the installed DDGS package includes a Grokipedia engine. Its legitimacy as installed code does not override the experiment stop rule.
- DDGS caught the guard exception, and the plan still returned results. Thus a security stop must latch outside ordinary provider-error fallback and be checked before any subsequent fetch; the initial harness only checked after the plan.
- No page-fetch or extraction failure occurred in the one fetched candidate.
- SearXNG health/config GETs succeeded; no SearXNG search ran, so there are no per-query engine diagnostics or observed upstream search request counts.
- SearXNG advertised 264 engine entries, 80 enabled. Enabled relevant-category inventory: general=9, news=6. Inventory is not observed fan-out.
- SearXNG internal engine HTTP fan-out/retries cannot be counted or strictly capped from the client request boundary alone. A resumed comparison must explicitly bound selected engines or add read-only transport telemetry without changing the live service; engine result names alone are only a lower bound.

## E. Grounded answer evaluation

Phase B NOT RUN: 0 of the authorized maximum 8 Qwen inference turns. Useful evidence existed, but the mandatory safety stop took precedence. No live inference, no automatic retry and no answer samples were produced.

| Dimension (0–4) | Result |
|---|---|
| Factual accuracy | NOT EVALUATED |
| Evidence support | NOT EVALUATED |
| Natural conversational quality | NOT EVALUATED |
| Information synthesis | NOT EVALUATED |
| Citation correctness | NOT EVALUATED |
| Uncertainty calibration | NOT EVALUATED |

- Sources retrieved as search hits: 5; pages fetched: 1; source pages selected for model evidence: 1; sources actually used by a generated answer: NOT APPLICABLE (no answer).
- Unsupported material answer claims: NOT EVALUATED, not zero.
- One source may suffice for case 1, but no synthesis judgment was made. Multi-source case 8 did not run.

## F. Natural synthesis evaluation

No evidence about Qwen’s natural explanation, bilingual answer quality, claim attribution, or relationship synthesis was collected. Neither fluent paraphrasing nor grounded conversational synthesis can be credited. Single-page selection remains a code-established constraint, not an observed answer-quality failure in this run.

## G. Latency and resource observations

| Measurement, case 1 DDGS | Seconds |
|---|---:|
| Discovery call | 3.983 |
| Page fetch | 0.252 |
| Extraction | 0.102 |
| Total retrieval | 4.342 |

One sample only: no comparative medians, p95 or generation-latency statistics are warranted. No Qwen inference resource load was introduced.

| Budget | Used | Approved / experiment cap |
|---|---:|---:|
| Initial plans | 1 | 16 |
| Provider calls | 1 | 32 |
| Candidate fetches | 1 | 48 |
| Candidate-fetch HTTP dispatches | 1 | 96 harness cap |
| DDGS HTTP dispatches | 10 | 128 global / 10 per plan |
| SearXNG search HTTP calls | 0 | 32 harness cap |
| Qwen turns | 0 | 8 |

- Candidate page redirects retain Corvus’s maximum three hops per fetch. Discovery redirects were limited to two per DDGS request chain, with a global redirect counter cap 64.
- Each plan had a 45-second alarm; Phase A had a 900-second admission deadline. A completed plan took 4.342 seconds. These process-level deadlines are not proof that a provider’s swallowed exception cancels all internal work immediately.
- DDGS engine concurrency was limited to one worker; initial provider plans were sequential. This and stricter transport caps are experiment constraints, not changes to deployed provider configuration.
- SearXNG service-internal transport counts are excluded from client HTTP caps and remain unmeasured because no search ran.

## H. Security and persistence checks

- The Grokipedia request did not pass the destination guard. The official documentation candidate used Corvus Safe Fetch with public-IP validation, pinned transport and normal TLS checks.
- No unsafe fixture destination was requested. Offline Phase C was NOT RUN after the safety stop; W0’s earlier controls are historical evidence, not W1 passes.
- Intent failure→NO_WEB and provider-failure→NO_RESULTS defects remain established by W0; they were not re-executed here.
- No deployed canonical database, session history or private conversation content was read by the experiment. No deployed database writes, chat calls, Hindsight operations, service mutations, network configuration changes or repository edits were performed.
- Lab/Private/Demo database file size, inode and modification timestamp matched preflight at postflight. This is metadata-only evidence, not a full SQLite/WAL transaction audit or a guarantee against unrelated concurrent service activity.
- No temporary SQLite persistence test ran. Canonical user-first/assistant-after-generation ordering therefore has no new W1 runtime acceptance result.

## I. Recommended Web architecture

**Observed:** one DDGS plan found and extracted the official source despite 403/429 responses from other discovery backends. No live SearXNG comparison or answer evaluation exists.

**Inference:** this sample supports retaining DDGS as a candidate; it neither establishes everyday reliability nor justifies provider substitution. Provider fan-out and swallowed backend failures require explicit experiment-level handling.

**Unverified:** whether discovery, extraction, evidence selection, or Qwen synthesis dominates real failures; whether SearXNG is materially better; whether one-page selection harms the representative multi-source answer; and native WebUI retrieval performance.

Do not replace or activate a component on this evidence. Complete a corrected isolated comparison before applying W1’s decision rules. Native WebUI remains a future separately isolated candidate, not a measured winner.

## J. Smallest next implementation/test step

Fix only the temporary experiment controls: enumerate the installed DDGS engine inventory before dispatch; review an explicit destination policy; latch stop conditions outside exceptions swallowed by provider code; check the latch before candidate fetches and every later dispatch. Resolve SearXNG upstream fan-out observability/bounds explicitly. Do not modify deployed Corvus or search services.

The mandatory stop boundary has been reached. Do not automatically widen the allowlist, restart the harness, repeat case 1, or consume further query/inference budgets. Resume only as a new operator-directed experiment with prior expenditure retained in its accounting.

Artifacts:

- `/tmp/corvus-w1-report.md` — this complete report.
- `/tmp/corvus-w1-metrics.json` — sanitized public retrieval evidence, transport statuses, isolation guard record and database file metadata.
- `/tmp/corvus-w1-isolated/phase-a.json` — original partial phase metrics.
- `/tmp/corvus-w1-run.py` — temporary harness; not a production change.

**Final Git status: clean. No commit or push.**

Subsequent offline control repair: [W1.1 report](2026-10-18-w1-1-control-repair.md). This does not upgrade the W1 verdict.
