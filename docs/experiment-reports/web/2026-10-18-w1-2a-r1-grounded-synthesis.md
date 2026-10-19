# Corvus W1.2a-R1 — Grounded synthesis retry

Experiment: **W1.2a-R1**

Date: **2026-10-18**

Related Lab baseline: `975645963291ec992d64df0474a3ee9d0ba33dcd`

Reporting branch baseline: `3e4019a4ca788314a514fb6d879735ed3a1ff71f`

**Final verdict: W1_2A_R1_PASS_WITH_CONSTRAINTS**

The corrected existing message composition produced two complete, readable,
source-citing answers. Strict grounding acceptance remains unmet: both answers
contain material assertions not established by the supplied evidence. This verdict
accepts the repaired request path and a bounded demonstration of single-source
explanation, with the quality constraints below; it does not establish reliable
daily-use Web answering or multi-source synthesis.

## A. Root cause and correction

[Original W1.2a](2026-10-18-w1-2a-grounded-synthesis.md) retained two HTTP-error
attempts with no answers. The captured English error was “System message must be
at the beginning.” Its temporary harness had separated instructions and evidence
into two system messages.

R1 reused the existing `_compose_working_messages` logic from
`app/working_context.py` unchanged. The existing pure function and its two pure
helpers were extracted by AST and executed without importing storage/recall
initialization. Instructions and evidence were merged into one initial system
message; the user question followed. No second composer was implemented.

Instructions, packed evidence, questions and generation settings were identical
to W1.2a. The corrected message layout was the intervention. The failed report
was not overwritten or reclassified.

Lab branch/HEAD and clean worktree matched the expected baseline. Reporting
branch/worktree was clean at its baseline. Shared Qwen health returned HTTP 200;
read-only container metadata matched the prior model/image and command settings.
No service was restarted or reconfigured.

## B. Offline message-format and evidence verification

Both tests passed before any new inference:

- Exactly two messages, with roles `system`, `user`.
- Exactly one system message, first; no duplicate system messages.
- System content exactly equaled unchanged instructions plus the unchanged packed
  evidence, joined through the existing composer.
- User content exactly matched its prescribed question.
- Empty recent and historical evidence lists; no personal memory or Hindsight.
- Identical system/evidence content for Chinese and English.

The three original complete W1 excerpts matched their recorded SHA256 hashes
again, in both preserved metrics artifacts and the W1 report. Nothing was
refetched; no provider search ran.

Source: [Python documentation: compression.zstd](https://docs.python.org/3/library/compression.zstd.html).

| Reference | Characters | Verified SHA256 |
| --- | ---: | --- |
| `web_1` | 1114 | `b8558551a5c8ff547e342ce76bdcb2dd65ac29d00620e1fceeb6b9f7bcb8335a` |
| `web_2` | 1185 | `42f43b0165ba196df9105b0b118fe1534678c61570ff64223d576ec4b606bfe3` |
| `web_3` | 1184 | `e3eb7a4e1025d64be157aee49cfbd5d2994ba44ee409f78489693d803adc6078` |

All references identify the **same page**. Total excerpt text: 3,483 characters;
existing packed representation: 4,933 characters. Packed evidence SHA256:
`748d533f294b43ccbb0892ec829bb1f4055bcc76a6b18ec3ce004500a274246d`.

The excerpt explicitly says “Added in version 3.14”; the unversioned `/3/` source
was not independently established as a complete version-frozen 3.14 snapshot.
Some extracted whitespace and a partial passage ending remain unchanged.

Isolation used fresh subprocess environments and temporary home/data/cache paths.
Audit guards rejected database/subprocess activity, deployed-data/credential reads
and unexpected writes; network dispatch was restricted to shared local Qwen.
Proxies and HTTP redirects were disabled. Observed connection events: one local
health check and two local completion requests; no isolation violations recorded.
No deployed Corvus `/api/chat`, canonical database, personal history, Hindsight,
DDGS, SearXNG or external HTTP endpoint was used.

## C. Chinese result — full generated response

Question:

> Corvus，Python 3.14 新增的 compression.zstd 模块有什么用？普通开发者什么时候会需要它？

Observed: HTTP 200; finish_reason `stop`; no retry. The answer below is reproduced
in full without factual correction. Scores and identified weaknesses follow it.

> Python 3.14 新增的 `compression.zstd` 模块旨在为开发者提供一套完整的工具，用于处理 Zstandard（zstd）压缩格式。根据官方文档，Zstandard 被描述为一种“针对实时压缩场景设计的快速无损压缩算法”，其性能目标是在达到 zlib 级别甚至更好的压缩率的同时，实现更快的压缩速度 [web_1]。
>
> 对于普通开发者而言，这个模块的核心价值在于它简化了与 zstd 格式的交互，无需依赖外部 C 库或第三方 Python 包即可直接利用系统底层的压缩能力。具体应用场景和可用功能如下：
>
> **1. 文件读写与流式处理**
> 如果你需要处理 `.zst` 文件（由 `zstd` 命令行工具生成）或原始压缩流，该模块提供了 `open()` 函数和 `ZstdFile` 类。这使得你可以像操作普通文本或二进制文件一样，以二进制（`'rb'`, `'wb'`）或文本模式打开压缩文件进行读写 [web_2]。
> *   **实际推断**：这意味着你可以轻松地将现有的日志文件、数据库备份或配置文件转换为 zstd 格式以节省存储空间，并在应用程序中直接读取这些压缩数据，而无需编写复杂的解压逻辑。
>
> **2. 增量压缩与解压**
> 对于需要处理大数据流或实时数据的应用（如网络传输或日志收集），模块提供了 `ZstdCompressor` 和 `ZstdDecompressor` 类。这些类支持增量压缩和解压，允许数据分块处理，而不是必须等待整个数据集加载到内存中 [web_1]。
> *   **实际推断**：这在处理大型文件上传、实时数据管道或内存受限的环境中非常有用，因为它允许边读边写，降低了内存峰值占用。
>
> **3. 一次性压缩与解压**
> 对于简单的脚本或一次性任务，`compress()` 和 `decompress()` 函数提供了最直接的接口，用于将字节数据压缩或解压 [web_1]。
>
> **4. 高级参数控制与字典管理**
> 该模块还包含 `CompressionParameter`、`DecompressionParameter` 和 `Strategy` 类，允许开发者精细控制压缩级别和策略 [web_1]。此外，它还支持 `train_dict()` 和 `finalize_dict()` 函数以及 `ZstdDict` 类，用于训练和管理 Zstandard 字典。
> *   **实际推断**：如果你需要针对特定类型的数据（如重复性极高的日志格式或特定的二进制协议）优化压缩率，你可以使用 `train_dict()` 生成专用字典，然后在压缩或解压时通过 `zstd_dict` 参数传入，从而获得比通用压缩更高的效率 [web_3]。
>
> **需要注意的限制**
> 虽然该模块功能丰富，但官方文档明确指出它是一个**可选模块**。如果你的 Python 发行版中缺少它，说明你的 CPython 构建未包含此功能，此时你需要查阅分发商提供的文档或检查系统要求 [web_2]。此外，所有操作均基于 `zstd` 算法，这意味着生成的文件必须遵循该标准，且解压端必须拥有对应的字典（如果使用了自定义字典）或兼容的解压参数 [web_3]。
>
> 总结来说，当你的项目需要利用 Zstandard 的高压缩比和实时处理能力，且希望避免引入外部依赖时，Python 3.14 的 `compression.zstd` 模块就是首选工具。

## D. English result — full generated response

Question:

> Explain Python 3.14's compression.zstd module naturally. What does it provide, and when would a developer use it?

Observed: HTTP 200; finish_reason `stop`; no retry. Full unedited response:

> Python 3.14 introduces the `compression.zstd` module, which offers native support for the Zstandard (zstd) compression algorithm. This module is designed for scenarios requiring fast, lossless compression with compression ratios that generally exceed those of `zlib`, making it particularly suitable for real-time applications [web_1].
>
> The module provides a comprehensive toolkit for handling compressed data. At its core, it includes functions for one-shot compression and decompression via `compress()` and `decompress()`. For more complex workflows, it offers `ZstdCompressor` and `ZstdDecompressor` classes that support incremental processing, allowing data to be compressed or decompressed in chunks rather than all at once [web_1].
>
> For file handling, the module includes an `open()` function and the `ZstdFile` class. These allow developers to read from or write to `.zst` files created by the external `zstd` utility, as well as handle raw compressed streams directly [web_1][web_2]. The `open()` function supports various modes, including reading (`'rb'`), overwriting (`'wb'`), appending (`'ab'`), and exclusive creation (`'xb'`), and can accept either a file path or an existing file object [web_2].
>
> Advanced users can fine-tune the compression process using `CompressionParameter`, `DecompressionParameter`, and `Strategy` classes. These allow for setting specific parameters like the compression level, which can be configured either directly via the `level` argument or within an `options` dictionary for more granular control [web_1][web_3]. Additionally, the module supports dictionary-based compression through the `ZstdDict` class. Developers can use `train_dict()` to generate a dictionary from sample data and `finalize_dict()` to create a finalized dictionary, which can then be passed to `compress()` or `decompress()` to improve efficiency on specific data types [web_1][web_3].
>
> A developer would use this module when they need to integrate Zstandard compression directly into their Python applications without relying on external libraries like `zstandard` or `pyzstd`. It is particularly useful when working with Python 3.14 or later, where this functionality is built-in. However, it is important to note that this is an optional module; if it is missing from a specific CPython installation, the developer should consult their distributor for documentation or requirements [web_2].
>
> While the module supports advanced features like dictionary training, the provided documentation does not specify the exact performance gains or compatibility details with other compression formats beyond the general description of Zstandard's capabilities [web_1].

## E. Quality evaluation — reviewer judgments

Rubric retained from W1.2a: **0** absent/incorrect; **1** poor; **2** mixed;
**3** good; **4** strong. These are qualitative judgments on two actual outputs,
not automated benchmark measurements. No aggregate score is calculated.

| Dimension | Chinese | English | Basis |
| --- | ---: | ---: | --- |
| Factual accuracy | 2 | 3 | Core API descriptions are mostly consistent; dependency/performance assertions exceed the excerpts. |
| Evidence grounding | 2 | 2 | Supported API facts are mixed with unsourced comparisons, dependency assertions or named alternatives. |
| Natural conversational quality | 3 | 3 | Readable explanations, not raw search-result dumps; both remain long and API-inventory oriented. |
| Information synthesis | 3 | 2 | Chinese connects features to practical scenarios; English mostly organizes and paraphrases the API inventory. Single-source scope only. |
| Citation correctness | 2 | 3 | Most API citations match; citation presence does not support the comparative or dependency overclaims. |
| Uncertainty handling | 2 | 3 | Both mention optional installation; English acknowledges missing measurements/compatibility details. Categorical claims still weaken calibration. |

### Chinese: material support gaps

Conservative reviewer count: **3 unsupported/overstated material claim groups**:

1. “无需依赖外部 C 库或第三方 Python 包” asserts dependency independence not
   established by the excerpts. In particular, absence of an external C-library
   requirement must not be inferred from a Python standard-library API.
2. “实现更快的压缩速度” adds comparative speed language without a measured
   comparison or established comparator. The excerpt describes a fast algorithm
   targeting real-time scenarios; it supplies no speed benchmark.
3. “就是首选工具” makes a categorical recommendation, reinforced by avoiding
   external dependencies, without comparative evaluation or workload evidence.

The explicitly labeled practical inferences about logs, backups, incremental
processing and trained dictionaries add useful explanation. They are treated as
illustrative reasoning rather than measured results. Dictionary/decompression
compatibility wording is also only partly supported by the truncated passage;
no new compatibility acceptance is inferred from it.

### English: material support gaps

Conservative reviewer count: **2 unsupported/overstated material claim groups**:

1. “compression ratios that generally exceed those of zlib” turns the source's
   target of zlib-level and better ratios into a generalized outcome. The supplied
   material does not establish that empirical comparison.
2. Replacing “external libraries like zstandard or pyzstd” introduces named
   alternatives and a dependency/replacement claim absent from the excerpts.
   This could be framed as a separately qualified practical inference, but it was
   presented without that qualification or supporting evidence.

The optional-module warning and explicit absence of exact performance gains are
useful caveats, but they do not repair an earlier unsupported generalization.

These counts group related assertions rather than count repeated phrases. They
are a bounded review against the supplied excerpts, not an exhaustive external
fact-check. Unsupported here does not necessarily mean false in the wider world.
No new searches or sources were used to adjudicate the answers.

### What the outputs demonstrate

**Observed:** both responses explain API capabilities in their requested language
and use supplied source references. The Chinese response goes beyond mechanical
paraphrase through labeled use-case reasoning. The English response is coherent
but closer to a documentation summary. Neither is a raw search-results list.

**Inference:** the current 9B model can produce a natural single-source explanation
when given readable evidence, but it does not reliably obey evidence-only claims
or fully calibrated recommendations under this prompt.

**Unverified:** multi-source integration, conflict resolution, wider factual
accuracy, performance across questions, ordinary daily-use reliability and remote
WebUI presentation. One page and one sample per language cannot establish them.

## F. Timings, model and bounded resource use

Existing model: Qwen3.5-9B Q5_K_M, alias `corvus`, via llama.cpp
`server-cuda12-b10630`; image ID
`sha256:c50a38601c8bbb6dcb2fdbe60ee336faea7c7c7e11a1d5a6396993783617d911`.
Existing context: 8,192 tokens; one parallel slot; threads 8; GPU layers 99;
batch/microbatch 512; prompt cache disabled. Matching BF16 projector remained
loaded with projector offload disabled; this experiment was text-only.

Per-request settings: temperature 0, top_p 1.0, seed 42, max_tokens 768,
stream false, enable_thinking false; HTTP timeout 60 seconds and wall alarm
75 seconds. No persistent model configuration changed.

| Measurement | Chinese | English |
| --- | ---: | ---: |
| Client request wall seconds | 11.247 | 8.488 |
| Server prompt-processing seconds | 0.727 | 0.656 |
| Server generation seconds | 10.314 | 7.825 |
| Prompt tokens | 1336 | 1338 |
| Completion tokens | 729 | 556 |
| Total tokens | 2065 | 1894 |
| Reported cached tokens | 0 | 0 |

Two new calls completed sequentially. Both finished with `stop`, rather than a
reported token-limit finish. There were no retries, extra model calls or searches.
The cumulative ledger now records four Qwen request attempts: two historical
HTTP-error attempts plus these two completions. Discovery/fetch counters remain
at W1's original expenditure. Prior reports retain their historical counters.

Client wall time includes local request overhead and prompt/generation work;
server timings have their own measurement boundaries. No latency percentile or
language-speed ranking is inferred from two samples with different output lengths.

## G. Remaining limitations and privacy

- This is one source and one completion per language; no multi-source synthesis
  or statistical reliability claim is supported.
- Source facts, source targets and model inferences were not always separated.
  Citation markers alone are insufficient evidence of grounding.
- This experiment changed the temporary message layout, not deployed Corvus.
  No canonical persistence lifecycle, chat history, Pipe or remote WebUI behavior
  was tested.
- The prompt asks for evidence-only accuracy yet leaves room for plausible prior
  knowledge; full grounding acceptance remains unmet.
- Public source excerpts, synthetic questions and generated answers only are
  archived. No credentials, secrets, private chats, memory records, raw terminal
  transcripts, raw metrics or account-specific paths are published. Audit guards
  are application controls, not a complete OS syscall trace.

## H. Recommended next step

Retain the existing model and single-system composer. No observed result
justifies another model, agent or framework.

The smallest improvement to test separately is a bounded instruction revision:
retain source wording such as “targets” rather than turning it into a guarantee;
omit dependency and named-alternative claims absent from evidence; label
illustrative use cases and recommendations as inference. Use a short claim-to-
excerpt review with regression assertions for these specific failure patterns.
Do not introduce a second composer, new infrastructure or automatic retries.

A future authorized comparison should keep the same evidence/questions/settings
and compare the revised instruction, then extend to additional sources/questions
before making product-reliability claims. No more calls were made in this stage.

Traceability: [W1.2a failed attempt](2026-10-18-w1-2a-grounded-synthesis.md),
[W1 live validation](2026-10-18-w1-live-validation.md), and
[W1.1 control repair](2026-10-18-w1-1-control-repair.md).
