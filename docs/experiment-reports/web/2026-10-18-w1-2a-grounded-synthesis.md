# Corvus W1.2a — Grounded synthesis validation

Experiment: **W1.2a**

Date: **2026-10-18**

Related Lab baseline: `975645963291ec992d64df0474a3ee9d0ba33dcd`

Reporting branch baseline: `cbcf13803a2e09f10b28de161b9f3f35b9c8784e`

**Final verdict: W1_2A_BLOCKED_WITH_REASON**

Two authorized local completion requests returned HTTP errors and no assistant
answers. The English error explicitly rejected a second system message. This is
a temporary experiment-harness prompt-layout failure, not a demonstrated inability
of Qwen3.5-9B to synthesize evidence. No retries or third call were made.

## A. Scope, baseline and isolation

Lab branch/HEAD matched the expected baseline and its worktree was clean. The
reporting branch/worktree was also clean at its baseline. Shared Qwen health
returned HTTP 200 and its existing container was healthy; no services restarted.

The experiment reused preserved public W1 evidence only. No external HTTP, page
refetch, DDGS or SearXNG search occurred. No deployed Corvus chat endpoint,
personal memory, session history, Hindsight, SQLite connection or database write
was used. Fresh subprocesses redirected data/cache/home locations to isolated
temporary directories before importing the pure evidence packer. Network guards
allowed only the shared local Qwen endpoint; redirects and environment proxies
were disabled. Python audit hooks rejected database/subprocess activity,
forbidden deployed-data/credential reads and writes outside temporary experiment
artifacts/accounting files.

Only temporary experiment files and the cumulative JSON request ledger changed
outside the reporting documentation. W1's original report/evidence metrics were
preserved; its historical discovery/fetch counters remain unchanged. Qwen request
accounting increased from zero to two, conservatively counting both rejected
attempts against the earlier eight-call envelope. No additional engine was used.

Application guards are not a full OS syscall audit. The final saved connection
event list covers the English subprocess only; it is not a cumulative two-process
connection trace. Request attempt accounting and per-test results are retained.

## B. Verified public evidence provenance

Source: [Python documentation: compression.zstd](https://docs.python.org/3/library/compression.zstd.html).

The three complete W1 excerpts were present in both preserved metrics artifacts.
Each excerpt's UTF-8 SHA256 matched its recorded metrics hash and the original W1
report hash. No new source retrieval was needed. Exact strings were retained,
including extraction whitespace and partial passage boundaries.

| Reference | Characters | Verified SHA256 |
| --- | ---: | --- |
| `web_1` | 1114 | `b8558551a5c8ff547e342ce76bdcb2dd65ac29d00620e1fceeb6b9f7bcb8335a` |
| `web_2` | 1185 | `42f43b0165ba196df9105b0b118fe1534678c61570ff64223d576ec4b606bfe3` |
| `web_3` | 1184 | `e3eb7a4e1025d64be157aee49cfbd5d2994ba44ee409f78489693d803adc6078` |

Total excerpt text: **3,483 characters**. Existing Corvus evidence packing yielded
**4,933 characters**, with source URL/title, untrusted-data boundaries and ordered
`web_1`–`web_3` references. Both requests used the exact same packed evidence.

The overview states “Added in version 3.14” and covers Zstandard compression,
file/one-shot/incremental APIs, dictionaries and advanced controls. The other
passages cover the optional-module caveat and API details. The URL is unversioned
`/3/`; its entire content was not independently established as version-frozen
Python 3.14 documentation. The excerpts do not supply developer-workload
benchmarks, comprehensive comparative recommendations or independent sources.

All three references point to one page, not three independent sources.

## C. Model configuration and request organization

Observed running model: **Qwen3.5-9B Q5_K_M GGUF**, alias `corvus`, through existing
llama.cpp `server-cuda12-b10630`.

Image ID: `sha256:c50a38601c8bbb6dcb2fdbe60ee336faea7c7c7e11a1d5a6396993783617d911`.

Existing service configuration included context 8,192 tokens, parallel slots 1,
threads 8, GPU layers 99, batch/microbatch 512, no prompt cache, and the matching
BF16 multimodal projector with projector offload disabled. This experiment was
text-only. No persistent model setting changed.

Both request settings: temperature 0, top_p 1.0, seed 42, max_tokens 768,
stream false, enable_thinking false. Each call had a 60-second HTTP timeout and
75-second wall alarm. Requests were sequential and not retried.

The temporary harness sent:

1. System message: synthesis instructions below.
2. A second system message: existing packed evidence, unchanged.
3. User message: the exact language-specific question.

This differs from the existing Corvus Working Context composer, which merges
instructions and evidence into **one initial system message**, followed by the
user message. An offline check of that existing pure composer with empty history
confirmed this shape for both questions, without application initialization,
storage, networking or another model call. The deployed composer was not changed.

The experimental instruction, identical for both requests:

> You are Corvus. Answer in the language of the user's question. Use the supplied official-documentation excerpts as your factual evidence. Explain naturally in coherent conversational prose, not as search-result lists or mechanical snippet paraphrases. Explain how the features relate to the developer's question. Distinguish documented facts from practical inferences or illustrative use cases; label the latter clearly. Do not claim performance measurements, comparisons, compatibility, or recommendations that the excerpts do not establish. Acknowledge relevant limits of the supplied material without unnecessary disclaimers. Attach the supplied [web_n] citations to claims they support; do not invent sources or citations. This is one source, not independent corroboration.

## D. Chinese test — actual result

Question:

> Corvus，Python 3.14 新增的 compression.zstd 模块有什么用？普通开发者什么时候会需要它？

**Actual assistant answer: none returned.** The client raised HTTPError.
The first harness retained the error class but did not retain the HTTP status or
server response body. Its exact server error therefore remains unknown.

Client request wall time: **0.023 seconds**. Prompt/completion token usage,
server generation time and finish reason: **unavailable**. This timing is a failed
request duration, not model generation latency. No Chinese synthesis sample exists.

## E. English test — actual result

Question:

> Explain Python 3.14's compression.zstd module naturally. What does it provide, and when would a developer use it?

**Actual assistant answer: none returned.** The separate English request returned
**HTTP 500**, type `server_error`, with this chat-template error:

> System message must be at the beginning.

Client request wall time: **0.004 seconds**. Token usage, server generation time
and finish reason: **unavailable**. No English synthesis sample exists.

The error identifies rejection of the later system message in the experimental
layout. The Chinese request used the same role layout, so the same cause is
plausible, but its missing error body prevents independently confirming that.
The English test was a distinct authorized test, not a retry of the Chinese one.

## F. Evaluation

Planned descriptive scale: 0 = absent/incorrect, 1 = poor, 2 = mixed, 3 = good,
4 = strong. **N/E means not evaluable**, rather than a zero score for model ability.

| Dimension | Chinese | English |
| --- | --- | --- |
| Factual accuracy | N/E — no answer | N/E — no answer |
| Evidence grounding | N/E — no answer | N/E — no answer |
| Natural conversational language | N/E — no answer | N/E — no answer |
| Information synthesis | N/E — no answer | N/E — no answer |
| Citation correctness | N/E — no answer | N/E — no answer |
| Uncertainty calibration | N/E — no answer | N/E — no answer |

Unsupported material claims cannot be evaluated; do not count a missing answer
as zero unsupported claims or as a fluent/grounded success. No citations or
paraphrases were generated. No averages, percentiles or numerical quality scores
are justified. A successful single-page test would still not demonstrate
multi-source synthesis, and this run did not reach even that evaluation stage.

## G. Architecture judgment

**Observed:** the current experiment's two-system-message layout was rejected in
the English test. Existing Corvus already constructs one initial system message.
That structure was confirmed offline; the corrected layout was not sent to Qwen
in this experiment.

**Inference:** prompt organization blocked evaluation; use the existing composer
rather than designing a new evidence transport. The Chinese failure may share the
same cause, but this was not independently captured.

**Unverified:** whether this 9B model can explain good evidence naturally;
whether the evidence format/content is sufficient for the requested developer
advice; factual grounding, citation quality, bilingual synthesis and uncertainty
calibration. There is no demonstrated need for another model, agent or framework.

The smallest justified next step is a newly authorized two-call repetition using
the existing one-system-message composer, unchanged evidence and questions, plus
complete bounded error capture for both calls. Add an offline role-layout
assertion before dispatch. Do not change deployed model configuration, Corvus
source, Pipe, memory ownership, Hindsight or services. No further inference is
authorized by this completed two-attempt experiment.

## H. Privacy, archive and acceptance boundaries

This report contains public source provenance, synthetic questions and model
configuration/error metadata only. It includes no private chats, personal memory,
credentials, tokens, cookies, model secrets, raw metrics files or raw terminal
transcripts. Account-specific paths are omitted. No model answers are omitted:
both requests returned none.

The local evidence/request/results artifacts remain outside Git. This checkpoint
archives documentation only, with no push or deployment. Historical W1 and W1.1
verdicts remain unchanged.

Related reports: [W1 live validation](2026-10-18-w1-live-validation.md) and
[W1.1 control repair](2026-10-18-w1-1-control-repair.md).
