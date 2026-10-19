# OW-N1.1 — Native RAG answer feasibility with frozen evidence

Date: **2026-10-18**

Verdict: **OW_N1_1_RAG_NOT_BETTER**

Two authorized local completions succeeded using the actual pinned Open WebUI 0.6.5 RAG template, context-numbering loop and system-message helper. Both answers are readable, mostly document-grounded summaries, but each contains a material error despite explicit supporting text being present. Neither demonstrates a meaningful natural-answer improvement over the earlier Corvus experiments. **Do not build a public-egress subsystem on these results. Recommend the already reviewed W2.1 source-first MVP for the next separately controlled Lab activation stage.** No deployment was performed.

“Not better” is the product adoption judgment for this bounded trial, not a statistical claim that native RAG is inferior. Earlier questions/evidence differ, and no same-question Corvus-versus-native model comparison was authorized. The result does demonstrate that the pinned native assembly works with the current model and does not by itself solve factual/version grounding.

## A. Baseline, reuse and exact scope

- Lab branch `lab/ow2e-console`, HEAD `975645963291ec992d64df0474a3ee9d0ba33dcd`; clean before/after inference. No Lab source or installed Function changed.
- Reporting branch `reports/web-validation`, starting HEAD `e632f7bf0b8aefd708b85dcd9bed759666f361db`; initially clean.
- Complete [OW-N1 report](2026-10-18-ow-n1-native-search-validation.md) and relevant [W1](2026-10-18-w1-live-validation.md), [W1.2a-R1](2026-10-18-w1-2a-r1-grounded-synthesis.md), [R2](2026-10-18-w1-2a-r2-grounding-improvement.md), [W1.2b](2026-10-18-w1-2b-provider-comparison.md), [W1.3](2026-10-18-w1-3-retrieval-architecture-decision.md), [W2](2026-10-18-w2-evidence-acceptance-prototype.md) and [W2.1](2026-10-18-w2-1-web-mvp-integration.md) findings informed this trial. Historical reports, artifacts and W1 counters were preserved.
- Existing Qwen container metadata reported healthy, with `server-cuda12-b10630`, Qwen3.5-9B Q5_K_M, alias `corvus`, context 8,192 and one parallel slot. Runtime arguments matched the existing configuration. No model configuration/restart, extra model or health-HTTP call was needed.
- Open WebUI remained **0.6.5**. No newer code, dependency or license change was introduced. The prior source/container hash comparison is recorded in OW-N1; the five native source files used by this preparation were also frozen and rechecked unchanged after inference.

### Reused native assembly

The temporary harness extracted these pure bodies by AST from the pinned source, without importing application/storage modules:

1. `retrieval/utils.py::get_sources_from_files`, using its inline `docs` bypass branch.
2. The exact context-initialization/numbering loop from `utils/middleware.py::process_chat_payload`, wrapped only to make that existing block callable.
3. The unchanged `config.py::DEFAULT_RAG_TEMPLATE` string.
4. `utils/task.py::prompt_template` and `rag_template` for native placeholder substitution.
5. `utils/misc.py::add_or_update_system_message`, the native non-Ollama composition path.

Each request had exactly one initial system message and then the exact user question. No Corvus/custom instruction was added to the system prompt. Native RAG template SHA256: `34d24ff1e62c7aa74cc7e40330da2ccf1b2faaeee7567421a48f7c01d668cff2`. Extracted pure-body module SHA256: `cc53a874a774f829074f058b9f7023fab1746e1f788588e7ef1ce264bf4a6d8e`.

### Explicit substitutions and omissions

- Discovery, live Web loading and extraction were **not run**. Inputs were exact slices of already saved trafilatura-extracted public pages, not newly extracted native-loader pages or search snippets.
- Excerpt selection was frozen manually by exact page offsets to bound context. This is not a test of native ranking or automatic answer coverage. No evidence text was rewritten.
- Both helper-query generations were frozen offline; no model was called for search/retrieval queries. Vector/embedding/file-store operations were forbidden stubs; inline documents never reached them.
- Only the pure RAG assembly was executed, not a WebUI server, authenticated chat route, background task or browser. Model dispatch used a fixed local completion transport after native message assembly; it did not invoke the native upstream HTTP router or Corvus Pipe.
- Source identity received the small temporary metadata correction described below. No deployed code, frontend, prompt template or source-card component was edited.
- No canonical persistence lifecycle was simulated. This experiment evaluates generation from frozen evidence, not native search, browser citations, live retrieval or canonical ownership acceptance.

## B. Verified public evidence

The W2 public snapshot file was cross-checked against the original W1.2b/W1.3 result artifacts: original artifact SHA256 matched the saved fixture witness, the entire extracted-page object matched its original extraction record, and the text hash matched. No refetch/search occurred.

| Test | Saved fetched source | Extracted page characters | Verified page-text SHA256 |
| --- | --- | ---: | --- |
| A | [Official sqlite3 snapshot](https://docs.python.org/zh-cn/3/library/sqlite3.html) | 40,682 | `a7f78107d0614e93e45065c0c200910b7c8ceee707d327e25cca426c5e02c46f` |
| B | [Official concurrent.futures snapshot](https://docs.python.org/3/library/concurrent.futures.html) | 24,417 | `7ea260d0bc100e69fea3fff1f7a795e74eee4a718d5ad7ee9c8577dd728fc5b2` |

Both URLs are unversioned `/3/` paths. Historical titles identified newer development documentation; neither is a frozen 3.13 or 3.14 page. Links identify the recorded fetched URL, not a guarantee that today's page bytes are unchanged. Test B has **one source**, containing explicit version-change notes. Separate 3.13/3.14 sources were unavailable and not invented.

Exact zero-based, end-exclusive selected ranges and hashes:

| Test / excerpt | Range | Characters | SHA256 |
| --- | --- | ---: | --- |
| A1 | 5576–6101 | 525 | `bd17ea9b4ef56cc602a47613980a263044b03c783b70ea93a85ffac25c78f43c` |
| A2 | 38997–40682 | 1,685 | `b7a0206045a1c2115c23c3667a18335ccc5cb7fae216eec1bb5b998dd2d66b4e` |
| B1 | 1369–2777 | 1,408 | `18b15b6460680e804fcb2e2dd30550fa71af6440520271de574b04406f482c99` |
| B2 | 7279–7391 | 112 | `40901a3d1febdbb1ad9ab592964b36649cc9428e1a5998dbf9075c720ceebeaa` |
| B3 | 8312–8655 | 343 | `3dee31b0732943d5ced6e4f7b2b3b6c72c5d1a37669e46531de2f41c25069e1d` |
| B4 | 15839–17086 | 1,247 | `57e6abdcac90a2f312cc480c72aa67ec238d12504147d0132716f00c2b3b5095` |

A includes the parameter/default/introduction notes and transaction-control explanation. B includes `map(buffersize)`, the 3.13 thread-worker formula, the 3.14 interpreter-pool introduction and process-pool change notes/termination methods. B2 lacks its parent executor heading, and B4 likewise begins at change notes rather than the full class heading. This selection limits how confidently the input alone identifies the two `max_workers` scopes; no missing heading was fabricated. The explicit 3.14 label on the process-start change is nevertheless present and unambiguous.

## C. Isolation, controls and calls

### Narrow model connection without an egress broker

The worker ran in Bubblewrap's fresh user/network/mount namespaces, with no network routes, no deployed volumes or host home/config/runtime directories, no Docker socket, a cleared environment, read-only system libraries/executables and read-only reviewed experiment artifacts. Home/data/cache/temp paths pointed to temporary private locations. It imported only standard-library modules and the extracted native pure bodies.

A small host coordinator opened **one connected socket to literal loopback port 8095 per admitted case** and supplied that socket as the worker's standard-input descriptor. The worker checked its peer and could send only the fixed `POST /v1/chat/completions` transaction through that capability. It could not create routes or contact arbitrary internal services. No listening proxy, HTTP forwarding endpoint, public-egress path or background service was created. Host-side audit guards rejected other network destinations, DNS, databases and private-data paths; worker guards rejected new network connections/DNS, databases and subprocesses.

Before inference, an inert Unix socket pair successfully exercised the same HTTP request/response code in the networkless namespace. It verified the exact native-assembled payload and completion path without any TCP listener or model request. Direct-connection attempts were denied, absent host paths/empty routes were asserted, and fixture, template, module and payload hashes were checked. No application-level URL check was relied on to isolate Web fetching; no Web fetching existed here.

The model remains the existing shared service; these boundaries isolate the runner, not other users' model scheduling or service internals. No inference result is a security proof for future public-page ingestion.

### Admission and bounds

- An exclusive lock and a new experiment ledger prevented duplicate execution.
- Each case's admission counter/pending marker was atomically written and fsynced **before socket connect and dispatch**. An existing live ledger refuses a fresh run; completed cases cannot be admitted again; pending outcomes block later admission; a third admission is rejected.
- Exactly **two admissions**, cases A then B, one request each. Both HTTP 200, finish reason `stop`; ledger pending state cleared after each completed response. No retry or uncertain outcome occurred.
- A single immutable payload was verified against offline preflight before send. HTTP redirects were never followed. The fixed transport has no reconnect/retry loop.
- Limits: 6,000 evidence characters, 6,500 wrapped context characters, 10,000 system-plus-user characters, 40,000 request bytes and 2 MiB response bytes. Socket read timeout 90 seconds; worker wall alarm 100 seconds; parent wait cap 110 seconds. Maximum output 1,024 tokens per call.
- Temporary artifact directory mode 0700; results/ledger mode 0600. No private memory, credentials, session history, Hindsight, deployed chat endpoint, database, search service or public HTTP endpoint was accessed.

Observed live operations: **two local Qwen completion requests, zero other experiment HTTP requests, zero external searches and zero public-page fetches**. The inert fake completion is explicitly excluded from the model count. Historical W1 accounting was not modified or reset.

Preparation initially used the wrong name for the historical `extraction` measurement field and stopped on an offline assertion, before any model/network operation. Correcting that field lookup preserved the original page object/hash checks. The preflight was rerun after adding a before-send payload-integrity assertion; both preflight runs used only inert fixtures. No failed live attempt was discarded.

## D. Citation identity: reproduction and minimal correction

Using an actual saved SQLite excerpt, an actual saved futures excerpt and the SQLite excerpt again, the unchanged native loop produced IDs **`1,1,1`**, reproducing OW-N1. All three lacked `file_id` and therefore shared the `None` key.

The only correction was to populate each inline document's existing `metadata.file_id` with `public-web:` plus SHA256 of its **recorded, previously fetched URL** before the native inline-source formatter ran. The unchanged loop then produced **`1,2,1`**. Distinct fetched URLs get distinct stable keys; repeated excerpts from one fetched URL share a citation. No URL came from model text or an unverified result snippet. Different-URL mirror independence is not established by this key.

The source keys are stable; native numeric IDs remain response-local first-occurrence ordinals, not global persistent citation IDs. Same ordering reproduces the same IDs; source order changes can change numbers. No frontend rebuild or global numbering scheme was added.

Each actual answer test intentionally had only one fetched page. Its multiple exact excerpts correctly shared **`[1]`**. All generated numeric references were in range, and neither model answer generated a source URL. The trusted mapping for A's `[1]` is the saved SQLite URL; for B it is the saved futures URL. This proves identity/mapping for these inputs, not truthful claim attribution or browser/card rendering.

## E. Test A — SQLite autocommit

Question:

> 请根据提供的官方 sqlite3 文档片段，自然解释 autocommit 参数：False、True 和 LEGACY_TRANSACTION_CONTROL 有什么区别，提交、回滚和 isolation_level 会怎样工作？请给出来源。

HTTP 200, complete answer, no retry. Full model response, **without correction**:

> 根据提供的官方文档片段，`autocommit` 参数的三种模式（`False`、`True` 和 `LEGACY_TRANSACTION_CONTROL`）在事务控制行为上有显著区别，具体解释如下：
>
> ### 1. `autocommit = False` (推荐模式)
> 这是兼容 PEP 249 的标准事务控制方式，也是文档推荐的做法。
> *   **事务开启**：`connect()`、`commit()` 和 `rollback()` 方法会隐式开启一个新事务（使用 `BEGIN DEFERRED` 语句）。
> *   **提交与回滚**：必须显式调用 `commit()` 来提交事务，显式调用 `rollback()` 来回滚事务。
> *   **关闭连接**：如果关闭连接（`close()`）时存在未提交的更改，系统会隐式执行回滚。
> *   **isolation_level 的作用**：在此模式下，`isolation_level` 属性**没有任何作用**。
>
> ### 2. `autocommit = True` (SQLite 自动提交模式)
> 在此模式下，SQLite 的自动提交机制被启用。
> *   **事务行为**：`commit()` 和 `rollback()` 方法将**没有任何作用**。
> *   **注意**：这种模式与 `autocommit = False` 下的 PEP 249 兼容行为不同。如果需要查询底层 SQLite 是否处于自动提交模式，应使用 `Connection.in_transaction` 属性。
>
> ### 3. `autocommit = LEGACY_TRANSACTION_CONTROL` (保留旧行为)
> 这是默认值，旨在保留 Python 3.12 之前的行为。
> *   **控制方式**：事务行为由 `isolation_level` 属性控制。
> *   **isolation_level 的工作机制**：
>     *   **非 None 值**：在执行 `execute()` 或 `executemany()` 中的 `INSERT`、`UPDATE`、`DELETE` 或 `REPLACE` 语句之前，会隐式开启新事务。其他语句不会隐式开启事务。提交和回滚仍需通过 `commit()` 和 `rollback()` 方法。
>     *   **None 值**：完全不会隐式开启任何事务，使底层 SQLite 库处于自动提交模式（但仍允许用户通过显式 SQL 语句手动管理事务）。
> *   **executescript()**：无论 `isolation_level` 为何值，该方法在执行脚本前都会隐式提交任何挂起的事务。
>
> ### 总结对比
> | 参数值 | 事务开启方式 | commit/rollback 作用 | isolation_level 作用 | 推荐程度 |
> | :--- | :--- | :--- | :--- | :--- |
> | **False** | 显式调用方法时隐式开启 | 正常有效 | 无效 | **推荐** |
> | **True** | 始终开启 (SQLite 自动提交) | 无效 | 无效 | 特定场景使用 |
> | **LEGACY** | 取决于 isolation_level | 正常有效 (当 isolation_level 非 None) | **完全控制** | 兼容旧代码 |
>
> **来源：**
> 上述信息均基于提供的文档片段 [1]。

### Review against supplied evidence

Supported: the PEP 249-compatible `False` behavior, explicit commit/rollback, implicit rollback on close, `True` making those methods ineffective, and legacy delegation to `isolation_level`. The explanation is organized and usable in parts, but mostly a documentation outline/table rather than natural connected conversation.

**Material error:** the summary table says `True` has “始终开启 (SQLite 自动提交)” as its transaction-opening behavior. This conflates enabled autocommit mode with an always-open transaction. The supplied text assigns an always-open transaction to **False**, not True. Earlier correct bullets do not cancel the contradictory table.

**Additional support gap:** the table limits legacy `commit/rollback` effectiveness to `isolation_level` being non-None. The excerpts do not establish that restriction; they explicitly allow manual SQL transactions when `isolation_level=None`. This qualifier can mislead users about manually managed transactions. Counted separately as one unsupported material qualifier, not a newly executed SQLite behavioral test.

Citation `[1]` resolves to the right page, but the global assertion that all of the answer follows that source includes the incorrect/unsupported table. There is no meaningful uncertainty disclosure around these errors. The future-default warning present in the input is omitted; no current-version default verification beyond the snapshot was performed.

## F. Test B — concurrent.futures changes

Question:

> 请根据提供的官方 concurrent.futures 文档片段，用中文自然解释 Python 3.13 和 3.14 的主要变化，分别说明哪些变化属于哪个版本，并给出来源。如果现有材料不是两个独立版本的官方页面，请明确说明，不能声称已完成两版文档逐项核对。

HTTP 200, complete answer, no retry. Full model response, **without correction**:

> 根据提供的文档片段，这些内容并非两个独立版本的完整官方页面，而是混合了多个版本变更说明的文档片段。因此，无法声称已完成对 Python 3.13 和 3.14 文档的逐项核对。以下是基于现有材料整理出的主要变化：
>
> **Python 3.13 的主要变化：**
> 1.  **`max_workers` 默认值调整**：`max_workers` 的默认值改为 `min(32, (os.process_cpu_count() or 1) + 4)` [1]。
> 2.  **进程启动方式调整**：`ProcessPoolExecutor` 的默认进程启动方法（start method）不再使用 `fork`。如果必须使用 `fork`，需要显式传递 `mp_context=multiprocessing.get_context("fork")` [1]。
> 3.  **`os.cpu_count()` 与 `os.process_cpu_count()` 的区别**：`max_workers` 默认计算逻辑从 `os.cpu_count()` 改为 `os.process_cpu_count()` [1]。
>
> **Python 3.14 的主要变化：**
> 1.  **新增 `InterpreterPoolExecutor`**：新增了 `InterpreterPoolExecutor` 类，它是 `ThreadPoolExecutor` 的子类，每个工作线程拥有独立的解释器来执行任务 [1]。
> 2.  **新增 `map` 方法的 `buffersize` 参数**：`Executor.map()` 方法新增了 `buffersize` 参数，用于限制尚未产生结果的已提交任务数量，当缓冲区满时，迭代会暂停直到缓冲区有结果被产出 [1]。
> 3.  **新增 `terminate_workers()` 和 `kill_workers()` 方法**：新增了这两个方法，分别用于立即终止或杀死所有存活的工作进程，并释放相关资源 [1]。
> 4.  **`map` 方法默认值变更**：虽然文档片段主要提及 3.14 新增 `buffersize`，但结合上下文，`map` 方法的 `buffersize` 参数是在 3.14 版本中引入的 [1]。
>
> **其他版本变更（非 3.13/3.14）：**
> *   **Python 3.15**：修复了一个死锁问题（gh-115634），该问题发生在子进程达到 `max_tasks_per_child` 限制退出后，仍有任务在队列中等待时 [1]。
> *   **Python 3.5**：`map` 方法新增了 `chunksize` 参数 [1]。
>
> **说明：**
> 上述总结仅基于提供的文档片段。由于材料是混合的，并未提供 Python 3.13 和 3.14 的独立完整页面，因此无法确认这两个版本之间是否存在其他未列出的变更，也不能保证列表的完整性。

### Review against supplied evidence

Supported: the provided worker formula/count-function changes, addition of interpreter pools and `buffersize`, and process-termination methods. It explicitly acknowledges that the material is not separate complete 3.13/3.14 pages and does not claim a full cross-version comparison. That caveat was explicitly requested, so it is not evidence of spontaneous uncertainty detection.

**Material version error:** under **Python 3.13**, it assigns the process-pool default start-method change away from `fork`. The supplied excerpt explicitly labels that change **3.14**. This is a wrong cited version assignment, not merely missing coverage or ambiguous input.

**Additional support gap:** the heading “map 方法默认值变更” suggests a default-value change, while the accompanying text merely repeats that `buffersize` was introduced in 3.14. The input establishes parameter addition and its behavior, not that heading's default-change assertion. Counted as one unsupported/misleading material label.

The answer does not label which executor each of its two 3.13 worker-count bullets belongs to. This is an important usefulness limitation; the selected excerpts' missing parent headings contribute to it, so it is not presented as a pure model failure. Listing the `buffersize` addition twice and adding unrelated 3.5/3.15 changes make the response less focused. Those other-version facts are in the evidence and are not counted as fabricated.

All numeric citations exist, but `[1]` attached to the wrong 3.13 start-method claim does not support it. Correct citation identity is therefore distinct from correct claim-to-evidence correspondence.

## G. Quality evaluation and measurements

Rubric: **0** absent/incorrect, **1** poor, **2** mixed, **3** good, **4** strong. These are descriptive reviewer judgments on the full actual responses, not automated verification or an aggregate benchmark.

| Dimension | A: SQLite | B: futures | Reason |
| --- | ---: | ---: | --- |
| Natural conversational quality | 2 | 2 | Readable Chinese; largely outline/table/list summaries rather than useful conversational synthesis |
| Factual accuracy | 2 | 2 | Mostly correct details mixed with one clear material contradiction/version error per answer |
| Evidence grounding | 2 | 2 | Important supplied facts used, but explicit evidence is contradicted and additional labels overreach |
| Information synthesis | 2 | 2 | Organization is present; A's summary distorts a core relationship, B's version grouping is wrong |
| Citation correctness | 2 | 2 | All IDs valid; source claims/cited version not consistently supported |
| Uncertainty/limitations | 2 | 3 | A misses its errors; B clearly discloses the requested missing-version-source limitation while still misdating a change |
| Answer usefulness | 2 | 2 | Useful partial explanation, requiring human correction before reliance on transaction/version details |

Conservative material-problem grouping: **A: one contradicted assertion plus one unsupported qualifier; B: one wrong version assignment plus one unsupported/misleading heading.** Omissions, repetition and input-heading loss are listed separately rather than inflating an unsupported-claim count. No exhaustive external fact check, universal semantic verifier, quality confidence interval or multi-source synthesis claim is made.

| Measurement | A: SQLite | B: futures |
| --- | ---: | ---: |
| Evidence characters | 2,210 | 3,110 |
| Native wrapped context characters | 2,259 | 3,209 |
| System plus user characters | 3,966 | 4,930 |
| Prompt tokens, reported | 1,353 | 1,226 |
| Completion tokens, reported | 688 | 611 |
| Total tokens, reported | 2,041 | 1,837 |
| Cached prompt tokens, reported | 0 | 0 |
| Model prompt processing, reported seconds | 0.755 | 0.621 |
| Model decode, reported seconds | 9.650 | 8.558 |
| Worker HTTP transaction, observed seconds | 10.591 | 9.341 |
| Admission-to-result, observed seconds | 10.659 | 9.406 |
| HTTP / finish reason | 200 / stop | 200 / stop |

Generation settings: `temperature=0`, `top_p=1.0`, `seed=42`, `max_tokens=1024`, `stream=false`, `chat_template_kwargs.enable_thinking=false`, model alias `corvus`. No truncation or retry was observed. Latencies describe these individual serial calls, not median/p95 or comparative performance. Existing Qwen configuration was unchanged; server timing includes the service's own accounting rather than a separate GPU profiler.

## H. Decision and cheapest next action

**Observed:** pinned native RAG assembly plus the current local Qwen can produce complete, readable source-citing answers in roughly nine to eleven seconds for these contexts. The citation-key fix works offline. B handles an explicitly requested source-coverage limitation. Both answers nevertheless contradict material facts supplied in context, and presentation remains mostly structured paraphrase.

**Inference:** query/transport integration and a source-card frontend would not by themselves correct these generation errors. A larger egress subsystem is not justified as the next product investment. This is consistent with prior R1/R2 observations of readable answers with mixed grounding; this trial does not demonstrate a meaningful improvement. Because evidence/questions differ, it cannot establish a controlled ranking of the two prompts or all native/Corvus behavior.

**Recommendation:** proceed to the separately authorized **controlled Lab activation/acceptance of W2.1's source-first MVP**, using the existing local `integration/w2-web-mvp` checkpoint `50a63850f83506724aaff4c2af4f50811d00d646` and its documented paired API/Pipe requirements. Its fallback can show fetched, validated sources with limitations and honest provider failure without depending on flawless synthesis. Do not activate native search alongside it.

The minimum next stage is runtime-drift preflight and protected rollback/backup review, followed by operator-approved Lab-only promotion, matched Function update and default-off backend-flag activation, preserving existing auth/session mapping and canonical ownership. [W2.1](2026-10-18-w2-1-web-mvp-integration.md) records exact deployment requirements and rollback ordering. No branch promotion, Function edit, flag change, restart or real chat is authorized/performed by this report.

Retain these two complete outputs and frozen source hashes as regression examples. Do not spend another general benchmark or same-document prompt-tuning round before delivering that working baseline. Native presentation/assembly can be reconsidered later through a small reviewed adapter if product evidence justifies it; do not build a new model, verifier, agent, frontend or retrieval framework now.

## I. Limits, safety and publication

- Two questions, one completion each, one model/seed, frozen hand-selected evidence. No statistical reliability, current-page freshness, live retrieval success, multi-source integration or browser/citation-card acceptance.
- Both sources are unversioned snapshots; B has no separately fetched version sources. Source text is preserved exactly, including extraction whitespace and the limited heading context described above.
- Native discovery/extraction/ranking, full middleware/task execution, WebUI authentication, Pipe and canonical persistence were not exercised. No memory integration acceptance follows from a direct model response.
- The unchanged default native RAG policy permits using model knowledge when context lacks an answer. No evidence-only policy replacement or post-generation verifier was introduced.
- Lab, Production/Demo, Hindsight, Arena, FoxGate/Cloudflare, services, credentials, databases and model configuration were unchanged by this experiment. No private conversation or memory was read. The runner's only live destination was the authorized model; no external HTTP/search occurred.
- Postflight verified the frozen native files, two completed ledger entries, no pending outcome and valid in-range citation IDs. This is not an audit of unrelated concurrent service activity or a deployed database checksum check.
- Only this manually reviewed sanitized report and its index entry are committed/pushed on `reports/web-validation`. Full generated answers here concern synthetic questions and public Python documentation. No raw terminal/metrics dump, private data, credential, token/cookie, model secret or code branch is published. Historical reports and verdicts remain intact.

Local temporary runner/artifacts remain outside the repository. No public-egress broker was built. **Final operational boundary: REPORT_ONLY; NOT_DEPLOYED.**
