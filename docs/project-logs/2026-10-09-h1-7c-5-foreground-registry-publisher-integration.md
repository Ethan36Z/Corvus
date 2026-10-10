# H1.7c-5 — Foreground registry publisher integration

Date: 2026-10-09

Baseline: `lab/ow2e-console` at `7ade80adc10ce791fc8d0349602765f3981e1a92`

Verdict: **PASS** for optional publisher integration. Expected branch, HEAD,
and clean worktree were verified before editing. This connects the existing
local tracker and registry core without deploying either service or connecting
Hindsight admission.

## Configuration

`app/runtime_config.py` adds **`CORVUS_FOREGROUND_REGISTRY_DIR`**, exposed as
`FOREGROUND_REGISTRY_DIR`, using the existing environment configuration style.
Unset, empty, or whitespace-only values disable publication. There is no default
path and no implicit `/run` directory creation. A configured directory must
already exist and pass the core's initialization/validation rules.

The module singleton uses that setting. Tests can independently inject
`registry_path` and a clock into `ForegroundActivityTracker`, using temporary
directories. Configuration is read at import, consistent with existing runtime
settings; deployment will require an explicit service setting and restart.

## Publisher lifecycle seam

`app/playground_api.py:lifespan` calls `start_foreground_publication()` before
`prepare_runtime_startup()` and before serving requests. Enabled startup
initializes/validates the registry, then creates one publisher attached to the
process-local tracker. An untrusted registry blocks startup before canonical
startup preparation. No publisher descriptors or identity are created merely
by importing the activity module.

`ForegroundActivityTracker.generation()` also initializes lazily, allowing the
existing foreground conversation/CLI wrapper to use the same configured
publisher. Repeated startup calls reuse the publisher; overlapping requests do
not create additional ownership. The core retains its stable lock files and
PID/start-ticks/UUID identity.

At fork, the module replaces its singleton with a fresh idle tracker using the
same configured path. Inherited tracker instances reject use before acquiring
inherited thread mutexes. The registry core's existing at-fork and close-on-exec
handling remains responsible for closing inherited descriptors without
unlocking the parent's open-file descriptions. The child initializes its own
publisher after its final PID exists.

Lifespan cleanup calls `stop_foreground_publication()`, including when canonical
startup preparation raises. Enabled shutdown stops admission of new calls and
closes an idle publisher. If calls remain active, it retains ownership and
closes only after the final completion. Forced process exit/crash releases
kernel locks; there is no cancellation or preemption implementation.
Explicit lifecycle restart creates a fresh publisher identity while preserving
the registry's peer records and finish watermark.

## Foreground transitions

The existing `app/conversation_runtime.py:process_turn` step-5
`track_foreground_generation()` seam is unchanged. The shared model client is
not instrumented globally, and generation has no Hindsight dependency.

Tracker state updates and registry publication occur under the same local
tracker lock, so out-of-order snapshots cannot publish IDLE over active work.
The lock is released during the model call; overlapping foreground requests
remain supported.

- 0→1 increments the local count and publishes busy ownership before yielding
  to model generation.
- 1→2 and further increments reuse the same publisher and busy lock.
- 2→1 publishes the new count and completion timestamp while retaining busy
  ownership.
- 1→0 publishes the final completion watermark and releases busy ownership.

Local timestamps remain monotonic. Snapshots remain immutable and consistent;
completion timestamps update even when another call remains active. Normal
return, model errors, unexpected exceptions, and base exceptions balance local
counts. Disabled publication preserves the previous local tracking behavior
and performs no registry initialization or writes.

## Failure semantics

The integration reuses the core's fault-lock/UNKNOWN mechanism rather than
adding another persisted failure format or automatically replacing publishers.

If BUSY publication fails, the local increment is rolled back, its completion
timestamp is recorded, and model generation does not begin. The conversation
wrapper maps ordinary admission failures to the existing `ModelClientError`
handling with status **`FOREGROUND_REGISTRY_UNAVAILABLE`**. The existing user
message commit remains intact, and no fabricated assistant reply is stored.
An enabled startup initialization/read failure likewise prevents model work;
missing directories are not provisioned automatically.

If completion publication fails after model work, local cleanup still returns
the count to its correct value. The failure is logged without discarding a
valid reply or masking the original model error. The failed publisher stays
alive with its core fault ownership, so registry readers return UNKNOWN and
subsequent new model calls through that publisher are blocked. Other already
running calls can finish and preserve their replies. Repair/restart is explicit;
there is no automatic publication retry or silent fallback to IDLE.

Logs use `logging.getLogger(__name__)` and identify initialization/begin/end
phase, configured path, failure reason, and repair/restart action. They contain
no conversation content. Registry read failure remains UNKNOWN; no admission
consumer is added here. Normal shutdown closes ownership only after local work
drains, leaving the core's stale-record/recovery-grace semantics in force.

## Offline validation

`.venv/bin/python -B -m unittest discover -s tests -p 'test_foreground_*.py' -v`:
**58 tests passed**, comprising:

- **18 focused integration tests** in `test_foreground_publication.py`, using
  real temporary registries and fake `process_turn` model/persistence functions.
  They cover disabled configuration; environment-based opt-in; enabled IDLE
  startup; BUSY before fake model work; successful completion/watermark;
  lazy initialization; model/unexpected/base exceptions; overlapping calls;
  publisher/process restart; fork aggregation with fresh child state;
  publication/read failure; interrupted begin; overlapping begin failure;
  preservation of successful replies and original model errors; shutdown
  ownership retention; and API startup/cleanup ordering with canonical
  preparation mocked.
- **10 existing foreground activity/conversation tests** passed unchanged.
- **30 existing registry-core tests** passed unchanged, including real busy
  subprocess crashes, stale-record recovery, inode stability, malformed and
  inaccessible state, and fork/exec descriptor handling.

**10 existing regression scripts passed**, with fake model calls and offline
model-download flags: `test_personality_runtime.py`,
`test_vision_conversation_runtime.py`, `test_voice_conversation_runtime.py`,
`test_web_conversation_runtime.py`, `test_web_mode_runtime.py`,
`test_web_auto_runtime.py`, `test_web_query_rewrite_runtime.py`,
`test_web_intent_gate.py`, `test_web_query_rewrite.py`, and
`test_startup_schema_ensure.py`. Startup schema tests use temporary databases;
the live Evidence Log and Hindsight banks were not used.

`git diff --check` and staged whitespace checks passed. No real inference or
real `/run` registry access is required by these tests.

## Deployment status and next step

**Disabled by default and not deployed. `/run/corvus-foreground/` is not
provisioned, and neither running Lab nor Production is publishing yet.**
Production remains clean at `f453ed161994c8131bf8d9ed7c43cc15914176cf`.
No service configuration, tmpfiles, live environment, Hindsight source/config,
bank state, or endpoint runtime was changed. No services were restarted, no
models were invoked, and no push or host power operation occurred.

This is metadata integration, not background scheduling. It adds no Hindsight
admission, queue, HTTP status endpoint, cancellation, or preemption. Auxiliary
model calls remain outside the tracker. The deployment and quiet-window
constraints from
[H1.7c-4](2026-10-09-h1-7c-4-foreground-registry-deployment-audit.md)
remain in force.

Next step: **controlled Lab-only provisioning and rollout**, with explicit
configuration and no-real-inference acceptance checks before any Production or
Hindsight rollout.
