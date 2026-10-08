# H1.6b-2 — Memory-model isolation audit

Date: 2026-10-08

Baseline: `lab/ow2e-console` at `da83df679e7e676d48e1be84907b29280915da4b`

Audit verdict: **PASS WITH CONSTRAINTS**. Native operation-level model isolation
is established; small-model quality, GPU fit, and CPU latency remain unverified.
This seal summarizes the completed report at `/tmp/corvus-h1-6b-2-report.txt`.
The audit was not rerun. The repository baseline was verified clean before
creating this documentation file.

## Native routing and current topology

Hindsight natively supports per-operation provider, model, base-URL, and API-key
isolation through separate clients and routing keys for retain extraction,
consolidation, and Reflect. Operation overrides fall back to global defaults;
internal substages do not each have independent routing.

All three operations currently inherit the same global configuration:
provider `openai`, model alias `corvus`, and base URL
`http://corvus-llama:8080/v1`. They resolve to the same llama.cpp process running
`Qwen_Qwen3.5-9B-Q5_K_M.gguf` used by Corvus foreground generation at
`http://127.0.0.1:8095`.

Retain extraction uses the `HINDSIGHT_API_RETAIN_LLM_` routing family, while
Reflect uses `HINDSIGHT_API_REFLECT_LLM_`; each has `PROVIDER`, `BASE_URL`,
`MODEL`, and `API_KEY` keys. Consolidation can be independently routed using:

- `HINDSIGHT_API_CONSOLIDATION_LLM_PROVIDER`
- `HINDSIGHT_API_CONSOLIDATION_LLM_BASE_URL`
- `HINDSIGHT_API_CONSOLIDATION_LLM_MODEL`
- `HINDSIGHT_API_CONSOLIDATION_LLM_API_KEY`

The consolidation client falls back directly to global Hindsight defaults,
not the retain override. Consolidation semantic deduplication follows that
client. A separate compatible endpoint is supported without Corvus application
changes. Routing settings are server-level, rather than bank/request-level
model selectors; applying them later requires a Hindsight reload/restart.

## Isolation constraints

Global Hindsight LLM concurrency is currently **1**, through
`HINDSIGHT_API_LLM_MAX_CONCURRENT=1`, with operation concurrency overrides
unset. Its global semaphore serializes Hindsight LLM calls across endpoints.
Corvus's foreground client is outside that semaphore.

Redirecting consolidation alone would leave retain extraction on the shared
foreground server. Separate endpoints separate request queues, but using the
same GPU can still create compute contention. Isolation does not itself fix
the consolidation `OutputTooLong` failure or establish memory quality.

## Hardware and small-model feasibility

The completed audit recorded this hardware snapshot:

- NVIDIA GeForce RTX 2080 Ti: **11264 MiB** total VRAM.
- Approximately **3103 MiB** VRAM free.
- Approximately **19005 MiB** system RAM available.
- Current llama-server GPU allocation: **6474 MiB**.

Another full 9B GPU copy at the observed allocation does not fit current free
VRAM. A smaller GPU model's fit remains unverified after weights, KV cache,
and runtime buffers are accounted for.

A CPU-resident small memory model is technically plausible, but quality and
latency are unverified; CPU and memory-bandwidth contention also remain.
1B/3B-class models are plausible for text extraction, subject to reliable
schema-shaped JSON and accurate facts, entities, and dates. Consolidation has
higher quality risk because observation comparison, conflict resolution,
creates/updates/deletes, and source references must be correct.

The frozen failed consolidation fixture had approximately **4129 input
tokens**, so a **4096-token context replacement is insufficient**. Destination
context must accommodate both input and output. Reflect's tool calling and
multi-call reasoning require a separate, deferred evaluation.

## Architecture conclusion and smallest next experiment

**Native operation-level isolation is available.** No option has been selected
or applied.

The smallest next experiment is **ONE isolated CPU-only small-model
consolidation capability trial using the frozen real failure fixture**, without
invoking Hindsight or mutating any bank. Use the existing incident prompt/schema
and one-fact/three-observation input for one bounded, zero-retry chat-completion
request to an isolated test endpoint. Inspect schema validity, source-ID
correctness, whether proposed observation changes are justified, finish reason,
token usage, elapsed time, and RAM use. Do not apply returned operations.

This trial is proposed only and was not executed. It requires no real or
disposable bank; the failed fact remains unrecovered and Reflect is excluded.
The existing report records the bank at 7 documents, 7 memories, 23 links,
zero pending operations, and one failed consolidation.

This documentation seal makes no application-code or Hindsight-configuration
changes, launches/downloads no models, invokes no inference, mutates no bank,
and performs no service restart, host reboot/shutdown, or push.
