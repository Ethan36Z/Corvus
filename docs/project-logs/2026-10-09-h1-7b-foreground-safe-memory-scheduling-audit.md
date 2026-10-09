# H1.7b — Foreground-safe memory scheduling audit

Date: 2026-10-09

Baseline: `lab/ow2e-console` at `24ea6e392af81f0e993e2dc76bb7bed2e957f930`

Audit verdict: **PASS WITH CONSTRAINTS**. This seals the completed read-only
audit and records the conservative first daily-use implementation decision.
It does not implement scheduling or change runtime configuration. The expected
branch, HEAD, and clean worktree were verified before creating this log.

The [H1.7a provisional architecture freeze](2026-10-09-h1-7a-provisional-hindsight-architecture-freeze.md)
remains in force: canonical Corvus SQLite evidence, Corvus-owned recent context,
Hindsight derived memory intelligence, and trusted provisional Qwen3.5-9B for
foreground chat, retain extraction, and consolidation. Reflect remains deferred.

## 1. Current post-response lifecycle

The real Corvus path is:

- `app/playground_api.py:post_chat` runs the foreground turn in a request
  thread, persists the successful assistant reply, and registers
  `app/hindsight_shadow.py:schedule_shadow_recall` for eligible completed text
  turns. Starlette runs the background task after sending the response.
- `app/hindsight_shadow.py:run_shadow_recall` performs shadow recall, appends
  the comparison record durably through `append_observation` in a threadpool,
  then invokes `retain_completed_turn`. The comparison append uses a file lock
  and fsync; append failure skips retain. A linked retain outcome is appended
  afterward.
- `retain_completed_turn` submits the canonical completed turn to Hindsight
  with `async:false`. This waits for extraction/storage, not subsequent
  consolidation. It is an in-process Corvus background task, not a durable
  Corvus work queue; its client timeout cannot prove a remote write stopped.

Installed Hindsight 0.10.1 source under `/app/api/hindsight_api` establishes the
downstream path:

- `api/http.py:api_retain` calls `engine/memory_engine.py:retain_batch_async`
  for the synchronous retain contract. Extraction and fact storage complete
  before `_submit_post_insert_maintenance` queues automatic consolidation.
- `_submit_post_insert_maintenance` checks observation/auto-consolidation
  settings and calls `submit_async_consolidation`. **Retain does not wait for
  consolidation to complete.**
- The embedded `worker/poller.py:WorkerPoller` runs as an async task in the
  Hindsight API process and claims persisted operations. The engine dispatches
  `_handle_consolidation` to
  `engine/consolidation/consolidator.py:run_consolidation_job`.

These background stages can overlap a later foreground request. Foreground
generation, Hindsight retain extraction, and consolidation currently resolve
to the **same single Qwen3.5-9B llama.cpp inference slot**. Corvus foreground
is outside Hindsight's global LLM semaphore. Post-response execution protects
the previous reply from waiting; it does not reserve capacity for the next one.
Production also shares this model endpoint, so a Lab-only signal would not
represent every foreground consumer. See the
[H1.6b contention audit](2026-10-07-h1-6b-foreground-background-contention.md).

## 2. Activity signals and admission seam

Corvus has **no existing foreground activity counter or last-active state**:
there is no process-wide active-generation count or reusable last-start/end
timestamp. Per-turn status and the comparison log's file lock do not provide
generation admission control. Foreground activity can be tracked cheaply at
the request/model-client boundary, including model calls used for query rewrite.

llama.cpp `/slots` exposes global model occupancy; the audit confirmed one
8192-token slot. It does not identify Corvus foreground activity, provide
session/global Corvus scheduling state, or supply full foreground-aware
admission semantics. A snapshot also has a check/start race.

Delaying Corvus's post-response task or checking only before retain does not
control already queued consolidation, reconciliation, or chained rounds.
Checking only when consolidation is submitted similarly misses execution
that occurs later. The effective admission seam is Hindsight execution, with
checks before memory LLM work actually starts and between subsequent calls.
Hindsight's existing semaphore limits its own concurrency but does not give
Corvus foreground priority; the current model-server queue does not do so either.

**Active consolidation cannot currently be preempted by foreground arrival.**
Hindsight operation cancellation is cooperative at checkpoints between batches.
The audited cached llama.cpp build, `10630` / `d222767c7`, supports cancelling
model work when its HTTP connection closes (`tools/server/server-context.cpp`
and `server-queue.cpp`). Corvus/Hindsight have no coordinated foreground-triggered
abort-and-requeue path, and cancellation is not seamless pause/resume.

Consequently, **idle admission alone cannot guarantee zero foreground waiting
once a memory LLM call is active**. Output bounds reduce exposure but do not
create preemption or eliminate unexpected arrivals during a maintenance window.

## 3. Durability, recovery, and starvation

Hindsight already provides persisted `async_operations`, durable unconsolidated
facts, `DeferOperation`, restart recovery, and maintenance reconciliation.
`worker/poller.py:_defer_operation` returns an operation to pending with
`next_retry_at`, without consuming a retry or treating deferral as a failure.
Stable-worker restart recovery reclaims interrupted processing, subject to
recovery limits; reconciliation can enqueue eligible unscheduled consolidation.
**A new queue or worker framework is not required.**

Corvus's current background continuation can be lost on process exit. Canonical
SQLite evidence and successfully fsynced comparison/outcome records survive,
but there is no automatic Corvus replay cursor. A timeout or missing outcome
requires checking remote completion/provenance before replaying a retain.
Future integration must distinguish durable acceptance from successful completion.

Facts marked `consolidation_failed_at` are excluded from automatic consolidation
and require explicit recovery. A worker operation marked `completed` can still
contain failed facts, as the
[H1.6a OutputTooLong audit](2026-10-07-h1-6a-consolidation-output-too-long.md)
demonstrated. Pending age and fact-level failures matter alongside operation state.

Continuous foreground activity can starve background work indefinitely.
**Quiet maintenance windows and durable deferral are acceptable provisional
daily-use behavior.** Preserve pending work, make backlog/failures visible,
and use an explicit quiet window instead of forcing long memory work ahead
of conversation. Deferral must not silently discard work or mark it failed.

## 4. Verified consolidation bounds

The audited deployment and resolved bank settings establish:

- Shared model context: **8192 tokens**.
- `HINDSIGHT_API_CONSOLIDATION_MAX_COMPLETION_TOKENS`: **unset**.
- `HINDSIGHT_API_CONSOLIDATION_LLM_REASONING_EFFORT`: **unset**.
- Source-fact budget: **4096 tokens**.
- Per-observation source-fact budget: **256 tokens**.
- LLM batch size: **8**.
- Consolidation LLM parallelism: **4**.
- Global Hindsight LLM concurrency: **1**.
- `HINDSIGHT_API_CONSOLIDATION_MAX_TOKENS=512`: retrieved-observation budget,
  **not a completion budget**.

Additional installed controls are a fetched batch size of 50, a round limit of
100 memories, a 180-second per-phase transport timeout, three inner retries,
and three outer consolidation attempts. OutputTooLong fails fast on an unchanged
batch; adaptive splitting can follow. The 7200-second consolidation worker
ceiling extends with progress and is not an absolute whole-job deadline.

The prior failure used **4129 input + 4063 output tokens = 8192**, exhausting
the context. Before daily-use consolidation is enabled, address it with an
explicit completion-token cap, consolidation reasoning `none`, and a preflight
of the exact rendered input plus output budget plus safety margin against the
8192-token context. Fixed prompts, source fidelity, and the real consolidation
schema must remain intact.

This is a candidate remedy requiring validation, not a proven quality fix.
A smaller cap can still truncate output; reasoning `none` was not established
as the original root-cause remedy. Reject incomplete/schema-invalid results
and preserve observable failure/recovery rather than applying partial output.

## 5. First daily-use architecture decision

The first implementation is intentionally conservative:

- **Reuse Hindsight's durable async/defer infrastructure.** Do not build Celery,
  Redis, or a new worker/queue framework.
- **Foreground conversation has priority.** Admission signaling must account
  for consumers sharing the foreground slot, not only one Lab request path.
- **Retain extraction remains Qwen3.5-9B.**
- **Consolidation remains Qwen3.5-9B.** Admit long consolidation only during an
  **explicit quiet/maintenance window**, and bound generation/context before
  enabling it for daily use.
- **Foreground-triggered abort/requeue is DEFERRED, not rejected.** The first
  daily-use implementation does not depend on introducing that mechanism.
- **Do not adopt a small model.** The H1.7a research stop rule remains in force.
- **Reflect remains deferred**, outside the normal retain lifecycle.

The first daily-use baseline optimizes for **correctness and foreground
responsiveness, not maximal automatic background throughput**. The quiet-window
decision narrows the earlier audit recommendation: automatic abort/requeue is
future work, while durable deferral and explicitly admitted, bounded maintenance
are the first implementation boundary. Foreground priority is a required
implementation policy, not a claim that the current runtime already enforces it.

## 6. Reversibility and next engineering objective

Canonical Corvus SQLite remains the Evidence Log, recent context remains
Corvus-owned, and Hindsight remains derived state. Preserve canonical provenance
and the historical-provider fallback. Withholding or deferring unsafe derived
work must not compromise foreground replies or canonical evidence. No provider
switch, model replacement, recovery, or derived-state rebuild is performed here.

The next engineering objective is:

> Implement the smallest reversible daily-use safety layer using existing Hindsight
> durability: foreground activity/admission signaling, quiet consolidation admission,
> and bounded consolidation generation.

Implementation and validation belong to the next task. This seal adds only this
audit log: no application code, Hindsight configuration, inference, bank mutation,
service restart, test-endpoint stop/start, host reboot/shutdown, or push is performed.
