# H1.6b-1 — Foreground/background inference contention audit

Date: 2026-10-07

Baseline: `lab/ow2e-console` at `ed687e3992b531baaa036a2f7ac11a86307156b4`

Audit verdict: **PASS WITH CONSTRAINTS**. Configuration and matching-build
source establish the queueing architecture; actual overlap latency was not
live-tested. No inference traffic, memory mutation, or remediation was performed.

## Current model-sharing topology

Foreground Corvus generation and Hindsight retain extraction, automatic
consolidation, and optional Reflect ultimately use the same `corvus-llama`
process: `Qwen_Qwen3.5-9B-Q5_K_M.gguf`, alias `corvus`. Corvus reaches it at
`http://127.0.0.1:8095`; Hindsight uses `http://corvus-llama:8080/v1`.
Docker maps these addresses to the same server.

The effective llama.cpp runtime exposes **one inference slot** with an
8192-token context. There is no Corvus application-level foreground priority,
no preemption of active Hindsight generation, no consolidation pause/resumable
yield mechanism, no model-server priority configured for foreground Corvus,
and no arbiter between the consumers. FastAPI HTTP concurrency does not provide
GPU/model concurrency.

Hindsight's worker queue and process-local LLM semaphore limit its own work;
they do not reserve inference capacity for Corvus. Its cooperative operation
cancellation is checked between batches and is not immediate model preemption.

## Verified queue behavior

The running binary reports build `10630`, commit `d222767c7`. Its command,
startup logs, `/props`, `/slots`, and matching-build scheduler source agree:
an occupied slot is unavailable to a new completion, which is deferred until
a slot releases. Continuous batching is enabled, but one slot cannot run two
generations. Neither client supplies foreground priority.

When Hindsight owns the single active model slot, a newly arriving Corvus
foreground generation queues behind it; the Hindsight generation is not
preempted. The real H1.6a consolidation incident occupied the shared model for
approximately **64 seconds**. A foreground model request reaching the server
five seconds into an equivalent call could wait approximately **59 seconds**
before generation begins, close to Corvus's **60-second model HTTP timeout**.
This could cause severe visible latency or timeout. API preparation, other
queued work, and generation duration determine the actual outcome.

Actual overlap latency was not live-tested. Configuration/source evidence is
sufficient to establish queueing; no live overlap test is needed merely to
reconfirm it. Source reference:
`ggml-org/llama.cpp` at `d222767c7`, `tools/server/server-context.cpp` and
`tools/server/server-queue.cpp`.

## Important interpretation

Post-response background execution means:

> The previous reply does not wait for memory work.

It does not mean:

> Future foreground work has priority over memory work.

The current shared single-slot arrangement is suitable for controlled Lab
evaluation but does not provide dependable foreground responsiveness for daily
use. Production also shares the model endpoint, so inference contention can
cross the Lab/Production service boundary even though canonical data remains
isolated. This audit did not demonstrate an overlapping Production slowdown.

## Parallel-slot caveat

Simply increasing parallel slots is not an obviously safe fix. With the current
non-unified KV/context allocation, two slots would divide the **8192-token**
context into approximately **4096 tokens per sequence**. The failed
consolidation already used **4129 input tokens**. A slots-only change could
therefore create a new context-capacity problem. Preserving context per sequence
requires context/resource validation. No configuration change was made.

## Candidate remedies — NOT adopted

In increasing architectural intervention:

1. Leave unchanged for controlled experiments and observe authorized natural use.
2. Increase model parallelism only with context/resource validation.
3. Add idle-time admission for memory work.
4. Add foreground-aware memory admission control.
5. Evaluate a dedicated smaller memory model/server.
6. Evaluate a separate full-size model/device.
7. Consider more invasive cancellation/resumable-yield support.

Idle-time scheduling prevents some contention but cannot preempt memory work
already in progress. A dedicated memory model/server separates request queues,
though same-GPU compute contention may still exist. The GPU snapshot showed
approximately **3094 MiB free**; this does not prove another model will fit.
None of these remedies has been selected or applied.

## H1 implication

The observed long consolidation, combined with verified queueing, turns
foreground/background contention from a hypothetical optimization into a real
daily-use architecture concern. The next step should determine the smallest
supported way to isolate or lower the priority/cost of Hindsight memory-model
work before long-term daily use. Do not perform a live overlap test merely to
reconfirm known queue behavior. Remediation, H1.5c, and H1.7 have not started.
