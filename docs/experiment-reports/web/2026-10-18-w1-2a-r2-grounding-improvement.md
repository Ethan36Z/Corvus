# Corvus W1.2a-R2 — Grounding improvement without losing naturalness

Experiment: **W1.2a-R2**

Date: **2026-10-18**

Related Lab baseline: `975645963291ec992d64df0474a3ee9d0ba33dcd`

Reporting branch baseline: `f6c30587e59f314f4a64a2c73475856f87ae59e7`

**Final verdict: W1_2A_R2_PASS_WITH_CONSTRAINTS**

The bounded comparison completed, but the instruction revision did **not** deliver
consistent grounding improvement. Chinese removed two important R1 overclaims;
English retained the performance generalization and introduced an explicit native-
library independence claim. Readability survived, but useful coverage and
single-source synthesis did not clearly improve. This verdict accepts the
completed experiment, not deployment or strict grounding acceptance of the prompt.

## A. Baseline and isolation

Lab branch `lab/ow2e-console`, expected HEAD and clean worktree were verified.
Reporting branch `reports/web-validation` was clean at its baseline. The complete
R1 report and answers were read before preparing R2. Prior reports and local R1
artifacts were preserved unchanged.

The same Qwen3.5-9B Q5_K_M model/alias `corvus` and llama.cpp
`server-cuda12-b10630` image were verified running. Image ID:
`sha256:c50a38601c8bbb6dcb2fdbe60ee336faea7c7c7e11a1d5a6396993783617d911`.
Existing context 8,192, one parallel slot, threads 8, GPU layers 99,
batch/microbatch 512, no prompt cache, and matching BF16 projector with projector
offload disabled were unchanged. The experiment was text-only. Local health was
HTTP 200. No runtime/service/model configuration changed.

Fresh subprocess environments redirected home/data/cache locations to temporary
experiment directories. No personal memory, history, Hindsight or canonical
storage was loaded. Audit guards forbade database/subprocess activity, deployed-
data/credential reads and unexpected writes; connections were restricted to local
Qwen. One local health check and two completion connections were recorded, with
no isolation violation. No deployed Corvus chat endpoint, search provider,
external page request or new model was used. Proxies/HTTP redirects were disabled.
These are application-level controls, not a complete OS syscall audit.

Both requests passed offline checks before inference: exactly one first system
message, then the exact user question; empty history; identical evidence;
unchanged settings; enforced two-new-call limit. The existing pure Corvus
`_compose_working_messages` and its helpers were reused unchanged through AST
extraction, avoiding storage initialization. Composer source/AST hashes matched
R1. No second composer, verifier, agent or retrieval system was introduced.

The same three complete W1 excerpts were reverified against their SHA256 values in
both preserved metrics artifacts and the W1 report. Exact evidence packing matched
R1: 3,483 excerpt characters, 4,933 packed characters, SHA256
`748d533f294b43ccbb0892ec829bb1f4055bcc76a6b18ec3ce004500a274246d`.

Source: [Python documentation: compression.zstd](https://docs.python.org/3/library/compression.zstd.html).

| Reference | Verified excerpt SHA256 |
| --- | --- |
| `web_1` | `b8558551a5c8ff547e342ce76bdcb2dd65ac29d00620e1fceeb6b9f7bcb8335a` |
| `web_2` | `42f43b0165ba196df9105b0b118fe1534678c61570ff64223d576ec4b606bfe3` |
| `web_3` | `e3eb7a4e1025d64be157aee49cfbd5d2994ba44ee409f78489693d803adc6078` |

No document was fetched again or rewritten. All three references identify one
page; the `/3/` URL is unversioned. The overview says “Added in version 3.14,” but
the entire snapshot was not independently established as frozen to that version.

## B. Exact instruction changes

The only model-input intervention was the instruction text below. Evidence,
questions, message composition, model and generation settings were held fixed.
The natural-answer guidance was retained verbatim; grounding guidance was revised
and a concision instruction added as authorized. No second system message was
added. The packed evidence's existing untrusted-data instruction was unchanged.

### R1 instruction

> You are Corvus. Answer in the language of the user's question. Use the supplied official-documentation excerpts as your factual evidence. Explain naturally in coherent conversational prose, not as search-result lists or mechanical snippet paraphrases. Explain how the features relate to the developer's question. Distinguish documented facts from practical inferences or illustrative use cases; label the latter clearly. Do not claim performance measurements, comparisons, compatibility, or recommendations that the excerpts do not establish. Acknowledge relevant limits of the supplied material without unnecessary disclaimers. Attach the supplied [web_n] citations to claims they support; do not invent sources or citations. This is one source, not independent corroboration.

### R2 instruction

> You are Corvus. Answer in the language of the user's question. Use the supplied official-documentation excerpts as your factual evidence. Explain naturally in coherent conversational prose, not as search-result lists or mechanical snippet paraphrases. Explain how the features relate to the developer's question. Distinguish documented facts from practical examples and inferences; present the latter as illustrative or conditional suggestions. Preserve source claim strength: a design target is not demonstrated superiority. Avoid unsupported performance comparisons, native-library independence claims, and categorical recommendations without comparative evidence. Cite [web_n] only for claims supported by that excerpt. Do not add unsupported dependency, compatibility, or named-alternative claims. Keep the explanation concise; acknowledge relevant evidence limits without disclaiming every sentence. This is one source, not independent corroboration.

The revision preserves requested-language explanation and practical reasoning,
while explicitly addressing source strength, comparisons, native-library claims,
recommendations and citation support. It is an instruction change, not an
implemented post-generation factual checker. Longer instruction text accounts
for the prompt-token difference; evidence text did not change.

## C. Chinese full answer

Question:

> Corvus，Python 3.14 新增的 compression.zstd 模块有什么用？普通开发者什么时候会需要它？

Observed: HTTP 200, finish_reason `stop`, no retry. Full unedited model answer:

> Python 3.14 新增的 `compression.zstd` 模块旨在为开发者提供原生的 Zstandard（zstd）压缩功能。根据官方文档，Zstandard 被描述为一种“针对实时压缩场景设计的快速无损压缩算法”，其目标是在保持 zlib 级别甚至更优的压缩率的同时，实现更快的压缩速度 [web_1]。
>
> 对于普通开发者而言，这个模块在以下场景中可能变得有用：
>
> 1.  **处理 `.zst` 文件**：如果你需要读写由 `zstd` 命令行工具生成的 `.zst` 文件，或者处理原始的 zstd 压缩流，该模块提供了 `open()` 函数和 `ZstdFile` 类来直接操作这些文件，支持读取、覆盖写入、追加或独占创建 [web_2]。
> 2.  **增量压缩需求**：当应用程序需要流式处理数据（例如在网络传输中实时压缩数据块）时，可以使用 `ZstdCompressor` 和 `ZstdDecompressor` 类进行增量压缩和解压，而不是等待整个数据加载完毕 [web_1]。
> 3.  **高级参数控制**：如果默认的压缩级别无法满足需求，开发者可以利用 `CompressionParameter`、`DecompressionParameter` 和 `Strategy` 类来精细调整压缩参数，或者通过 `options` 字典传递特定配置 [web_1][web_3]。
> 4.  **字典优化**：为了进一步提高特定数据集的压缩效率，模块提供了 `train_dict()` 和 `finalize_dict()` 函数来训练字典，并允许在压缩或解压时通过 `zstd_dict` 参数应用这些字典 [web_1][web_3]。
>
> 需要注意的是，这是一个可选模块。如果你的 Python 发行版中缺少它，可能需要联系分发商获取文档或确认是否已安装 [web_2]。此外，虽然文档提到该算法针对“实时压缩”进行了优化，但这属于设计目标，并不直接等同于在所有具体场景下都优于其他压缩库的实际性能表现 [web_1]。

## D. English full answer

Question:

> Explain Python 3.14's compression.zstd module naturally. What does it provide, and when would a developer use it?

Observed: HTTP 200, finish_reason `stop`, no retry. Full unedited model answer:

> Python 3.14 introduces the `compression.zstd` module, which offers native support for the Zstandard (zstd) compression algorithm. This module is designed for scenarios requiring fast, lossless compression with compression ratios that generally exceed those of zlib [web_1]. It provides a comprehensive toolkit for developers, including classes and functions for both one-shot and incremental compression and decompression operations.
>
> For file handling, the module includes an `open()` function and the `ZstdFile` class, allowing you to read from or write to `.zst` files created by the `zstd` utility, as well as handle raw compressed streams [web_1]. If you need more granular control, the `ZstdCompressor` and `ZstdDecompressor` classes support incremental processing, while `compress()` and `decompress()` functions handle single-pass operations [web_1].
>
> A developer might use this module when they need to integrate Zstandard compression directly into their Python applications without relying on external C libraries or third-party packages. The module also supports advanced features like dictionary training via `train_dict()` and `finalize_dict()` to optimize compression efficiency for specific data types, and it allows setting advanced parameters through `CompressionParameter`, `DecompressionParameter`, and `Strategy` classes [web_1].
>
> However, it's important to note that this is an optional module. If it's missing from your Python installation, you may need to check with your Python distributor or install it separately [web_2]. Additionally, while the documentation describes Zstandard as targeting real-time compression scenarios, this is a design goal rather than a guaranteed performance metric compared to other algorithms [web_1]. The module also raises a `ZstdError` exception in case of errors during compression, decompression, or initialization [web_2].
>
> In practice, you might use `compression.zstd.open()` to handle file I/O with Zstandard-compressed data, specifying modes like 'rb' for reading or 'wb' for writing, and optionally passing parameters like `level` or `zstd_dict` to customize the compression behavior [web_2]. For more complex use cases, you could leverage the `options` dictionary to pass advanced parameters documented in the `CompressionParameter` or `DecompressionParameter` classes [web_3].

## E. R1 versus R2 comparison

Reviewer rubric: **0** absent/incorrect; **1** poor; **2** mixed; **3** good;
**4** strong. Scores are descriptive judgments, not automated benchmark results.
Published R1 scores/verdict are retained; this report adds an assessment of R2
against the same supplied excerpts. No aggregate score is calculated.

| Dimension | Chinese R1 | Chinese R2 | English R1 | English R2 |
| --- | ---: | ---: | ---: | ---: |
| Factual accuracy | 2 | 3 | 3 | 2 |
| Evidence grounding | 2 | 3 | 2 | 2 |
| Natural conversational quality | 3 | 3 | 3 | 3 |
| Information synthesis | 3 | 2 | 2 | 2 |
| Citation correctness | 2 | 2 | 3 | 2 |
| Uncertainty calibration | 2 | 3 | 3 | 2 |

**Chinese judgment:** removing dependency independence and “first choice” language,
plus an explicit performance caveat, improves calibration. The remaining relative-
speed wording and over-specific dictionary-function attribution prevent full
credit. The numbered conditional scenarios are readable, but more checklist-like;
explicit one-shot APIs and R1's richer practical examples disappear. Fewer claims
therefore do not automatically earn a better synthesis score.

**English judgment:** coherent paragraphs and useful API detail remain. However,
“generally exceed” survives; native C-library independence appears; dictionary
training and missing-module installation advice exceed the excerpts. The final
design-goal caveat does not negate earlier assertions. Readability stays good,
while grounding and citation discipline remain mixed.

This supports **mixed, not consistent, grounding improvement**. Conversational
readability is broadly preserved at the same score; deeper useful explanation is
not demonstrably improved. Shorter output is not itself a quality gain.

## F. Claim/evidence analysis

Counts below group related material assertions, not repeated phrases or citation
markers. These are conservative, human-reviewable judgments against the supplied
material, not exhaustive external fact-checks. Unsupported does not necessarily
mean false in the wider world. Conditional wording does not make an unsupported
capability/dependency assertion evidence-backed.

### R1 baseline support gaps, retained for comparison

Chinese R1 had **3 material claim groups**: native/third-party dependency
independence; added comparative speed language; and a categorical first-choice
recommendation. English R1 had **2 groups**: generalized superiority over zlib
ratios and named third-party replacement/dependency claims absent from excerpts.
The full original R1 report remains authoritative for its historical review.

### Chinese R2

**Supported facts:** Zstandard compression/decompression; file and incremental
interfaces; advanced parameter classes; dictionary support; optional-module status
and consulting the distributor. These retain useful factual coverage.

**Reasonable examples/inferences:** “例如在网络传输中实时压缩数据块” is an
illustrative streaming use case, introduced as an example. Conditional wording
about needing compressed-file I/O or parameter control is practical reasoning,
not a claim of measured superiority.

**Remaining unsupported/overstated material groups: 2.**

1. “其目标是在保持 zlib 级别甚至更优的压缩率的同时，实现更快的压缩速度”
   still adds an unestablished relative-speed target/comparator. Calling it a target
   is better calibrated than claiming measured superiority, but the excerpt does
   not establish “faster” relative to another implementation. The final caveat
   helps without supplying the missing evidence.
2. “train_dict() 和 finalize_dict() 函数来训练字典” attributes training to both
   named functions. web_1 describes training/management collectively; web_3 names
   train_dict for generating a dictionary. The supplied excerpts do not establish
   that finalize_dict itself trains one. This is over-specific attribution, not a
   claim that its true full-documentation semantics were independently checked.

**Citation issues:** the first numbered item cites web_2 for a compound claim
including `.zst` files and ZstdFile; web_1 supplies those portions, while web_2
supports open/modes. The dictionary-function claim also exceeds its references.
References exist and identify the right page, but some claim-level scopes mismatch.

**Important omissions:** compress()/decompress() one-shot convenience is absent,
which matters to ordinary developers handling a small byte payload. R1's concrete
logs/backups examples and memory-use explanation are reduced. Not every advanced
API needs listing; this omission is a usefulness tradeoff, not a demand to make
answers longer or inventory every symbol.

Dependency-independence and categorical first-choice claims disappeared in this
Chinese sample. The source-strength problem was reduced, not eliminated.

### English R2

**Supported facts:** one-shot/incremental APIs, `.zst` file handling, parameter
classes, optional-module status, ZstdError and the displayed open arguments.
The last practical paragraph gives a concrete source-supported way to use file I/O.

**Reasonable inference:** “In practice, you might use ... open()” is conditional
application guidance supported by the documented interface. No benchmark gain is
claimed for that example.

**Remaining unsupported/overstated material groups: 4.**

1. “compression ratios that generally exceed those of zlib” repeats R1's stronger
   empirical generalization. web_1 describes a design target, not an observed
   generally-superior outcome.
2. “without relying on external C libraries or third-party packages” asserts a
   dependency advantage absent from the evidence, despite the explicit instruction.
   A standard-library interface is not evidence of native-library independence.
3. “dictionary training via train_dict() and finalize_dict()” over-specifies the
   role of finalize_dict, for the same evidence gap as Chinese R2.
4. “or install it separately” suggests a missing-module remedy the excerpt does
   not establish. web_2 says consult the distributor. The correct remedy may depend
   on the distribution/build; this experiment did not verify a separate install
   path. “May” softens the suggestion but does not supply that evidence.

**Citation issues:** web_1 does not support the stronger ratio claim or the precise
finalize_dict training attribution; web_2 does not support a separate-install
remedy. Named references are not fabricated, but their claim-level support is
incomplete. Several other API/mode citations are correctly scoped.

**Important omissions:** ordinary-workload examples remain sparse, and the answer
never explicitly tells the reader when a one-shot interface is sufficient versus
when incremental handling helps. It retains more API coverage than Chinese R2;
this does not itself make it more conversational or better grounded.

Named third-party alternatives disappeared, but an even broader native-dependency
claim replaced them. Performance and dependency concerns therefore did **not**
disappear across both languages. Counts use different output lengths/claim sets;
they are not normalized hallucination rates or statistical reliability estimates.

## G. Latency and token measurements

Settings unchanged: temperature 0, top_p 1.0, seed 42, max_tokens 768,
stream false, enable_thinking false. Each request retained a 60-second HTTP timeout
and 75-second wall alarm. One completion per question; no automatic retries.

| Measurement | Chinese R1 | Chinese R2 | English R1 | English R2 |
| --- | ---: | ---: | ---: | ---: |
| Client request wall seconds | 11.247 | 7.038 | 8.488 | 7.368 |
| Prompt tokens | 1336 | 1360 | 1338 | 1362 |
| Completion tokens | 729 | 439 | 556 | 477 |
| Total tokens | 2065 | 1799 | 1894 | 1839 |
| Server prompt-processing seconds | 0.727 | 0.704 | 0.656 | 0.67 |
| Server generation seconds | 10.314 | 6.158 | 7.825 | 6.69 |

Both R2 responses returned HTTP 200 and finish_reason `stop`; neither reported a
token-limit finish. Reported cached tokens were zero. There were no errors to
categorize; bounded HTTP-status/error capture was available for both calls.

R2 is shorter and faster in this pair; lower output token counts explain much of
the difference. This is not evidence of a model speedup caused by the instruction.
The longer instruction added 24 prompt tokens in each language. No percentiles,
significance test or language-speed ranking is justified.

The cumulative request ledger now records **6/8 Qwen attempts**: two W1.2a HTTP
errors, two R1 completions and two R2 completions. Historical discovery/fetch
expenditure is unchanged. Original reports retain their historical counters;
local metrics and raw artifacts are not included in the public archive.

## H. Recommendation and decision

A. **Did grounding improve?** Partially in Chinese, not consistently across both
questions. The English sample retains/adds material support gaps. The revision
is insufficient as a grounding fix.

B. **Was natural conversational quality preserved?** Readability broadly survived;
useful synthesis did not improve, and Chinese lost the one-shot API and richer
use-case reasoning. Concision alone is not success.

C. **Did unsupported dependency/performance claims disappear?** No. Chinese lost
the dependency claim but retained unestablished comparative-speed wording; English
retained ratio superiority and added native-library independence.

D. **Excessive caution or mechanical writing?** There is no disclaimer on every
sentence. Both include a bounded caveat. Chinese is more of an API checklist;
English remains documentation-summary oriented. Coherent prose still exists, but
neither demonstrates the desired product experience robustly.

E. **Further prompt tuning?** No further experiments on this same document are
recommended. Keep this failed-to-fully-improve result as a regression case. The
existing model/composer do not need replacement based on this evidence; no new
agent, framework, verifier or retrieval implementation is justified here.

F. **Move to real provider comparison?** Yes, in the next separately authorized
stage. Return to bounded DDGS/SearXNG retrieval with explicit engine selection,
retained diagnostics and W1 accounting. Measure usable evidence, source coverage,
claim support and natural explanation together on varied questions. Include
multi-source questions and expose the current first-usable-page limit rather
than silently claiming multi-source synthesis. Respect the outstanding inability
to strictly cap shared SearXNG internal HTTP requests through the query interface.

Do not deploy R2 or activate a search pipeline from this report. A new stage needs
its own concrete budgets and authorization; no additional calls/searches occurred
here. Avoid another isolated prompt loop on this single Python page unless a new
critical defect is discovered.

## I. Limitations, privacy and publication scope

- One source, one completion per language, one seed. No statistical reliability,
  multi-source synthesis, retrieval quality or daily-use acceptance is established.
- The source URL is unversioned; evidence is a preserved snapshot with extraction
  whitespace and a partial passage, not a fresh full-document validation.
- Reviewer scores and claim grouping are interpretive. Full outputs and exact
  instructions are included so another reviewer can disagree or reproduce the test.
- No deployed memory, canonical persistence, remote WebUI or Pipe behavior was
  tested or changed. Temporary counters are not deployed databases.
- Only public provenance, synthetic questions, model responses and non-sensitive
  settings are archived. No private conversation, memory, credentials, cookies,
  keys, model secrets, account-specific host paths, raw terminal transcript or
  unreviewed metrics JSON is published.
- Publication is limited to sanitized documentation on reports/web-validation.
  Lab/main branches and services are outside the publication scope.

Traceability: [R1](2026-10-18-w1-2a-r1-grounded-synthesis.md),
[original W1.2a](2026-10-18-w1-2a-grounded-synthesis.md),
[W1](2026-10-18-w1-live-validation.md), and
[W1.1](2026-10-18-w1-1-control-repair.md). Earlier reports/verdicts are unchanged.
