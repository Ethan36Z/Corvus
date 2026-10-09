# H1.7c-1 — Foreground activity tracking foundation

Date: 2026-10-09

Baseline: `lab/ow2e-console` at `f92a653ceb1027aa3de5e5bba0f3a8085f0d3f71`

Verdict: **PASS** for the process-local tracking primitive. The expected branch,
HEAD, and clean worktree were verified before editing. The
[H1.7b scheduling decision](2026-10-09-h1-7b-foreground-safe-memory-scheduling-audit.md)
remains in force; this step does not implement admission or scheduling.

## Instrumentation seam

`app/conversation_runtime.py:process_turn` wraps only step 5's user-facing
`generate_fn(model_messages)` call in `track_foreground_generation()`. Both
`app/playground_api.py:post_chat` and `app/chat_persistent.py` use this path.
Activity begins immediately before calling generation and ends after it
returns or raises, before assistant persistence and dense synchronization.

The shared `app/model_client.py` is not instrumented globally: web-intent
classification and query rewriting also use it. Context preparation, token
counting, those auxiliary model calls, and Hindsight background memory calls
are outside this narrow reply-generation signal. Existing model error handling
and the `process_turn` dependency-injection signature remain intact.

## Tracker semantics and guarantees

`app/foreground_activity.py` provides one process-local tracker and a read-only
`snapshot()` API returning an immutable `ForegroundActivitySnapshot`:

- `active_foreground_count` starts at zero. A context-managed generation
  increments before the model call and decrements in `finally`, including
  exceptional exits. Balanced scopes provide no unmatched public decrement.
- A lock protects every state update and snapshot. It is not held during
  generation, so overlapping foreground requests remain concurrent and produce
  counts of 2, then 1, then 0 as they complete independently.
- `last_foreground_started_at` records the most recent entry;
  `last_foreground_finished_at` records each completion, even when another
  generation remains active. Both start as `None`.
- Timestamps use monotonic seconds, suitable for future idle-grace calculations
  within the process. A finished timestamp alone does not mean idle: a consumer
  must also check that the active count is zero. Snapshots are consistent,
  detached copies rather than mutable/live state.

## Offline validation

- `.venv/bin/python -B -m unittest discover -s tests -p test_foreground_activity.py -v`:
  **10 focused tests passed**. Coverage includes initial idle state, immutable
  snapshots, active/finished transitions, advancing timestamps, ordinary and
  base exceptions, two overlapping real `process_turn` calls with fake
  generation, pre-generation failures, and exclusion of direct shared-client calls.
- `.venv/bin/python -B -m unittest discover -s tests -p 'test_hi*.py' -v`:
  **35 existing regression tests passed**, covering historical memory/timing
  and mocked Hindsight shadow recall/retain contracts. Async thread wake-ups
  required running outside the sandbox's local-socket restriction; all model
  and Hindsight calls remained mocked and databases/logs were temporary.
- **Nine existing regression scripts passed**, executed with the repository on
  `PYTHONPATH` and model-download offline flags: `test_personality_runtime.py`,
  `test_vision_conversation_runtime.py`, `test_voice_conversation_runtime.py`,
  `test_web_conversation_runtime.py`, `test_web_mode_runtime.py`,
  `test_web_auto_runtime.py`, `test_web_query_rewrite_runtime.py`,
  `test_web_intent_gate.py`, and `test_web_query_rewrite.py`.
- `git diff --check` and staged whitespace checks passed.

## Limits and next step

**This signal is NOT yet used to gate Hindsight.** It is process-local only,
resets on process restart, and does not aggregate API workers, CLI processes,
Production/Lab, or all traffic to the shared model server. It counts outstanding
Corvus reply-generation calls, including client waiting; client completion or
timeout does not prove remote inference has stopped.

There is no persistence, queue, scheduler, HTTP endpoint, file-based host
protocol, cross-process coordination, or cancellation/preemption in this step.
No Hindsight source/configuration or consolidation behavior changed. No real
inference, bank mutation, service restart, runtime endpoint change, download,
host reboot/shutdown, or push was performed.

Next step: **design the minimal shared/admission bridge using this primitive**,
preserving the explicit quiet-window decision, Hindsight's existing durability,
trusted Qwen3.5-9B memory paths, and deferred Reflect. This log does not implement
that bridge or establish deployed foreground priority.
