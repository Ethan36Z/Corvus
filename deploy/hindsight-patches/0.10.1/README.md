# Hindsight 0.10.1 foreground admission and intentional deferral

**Offline artifact; not deployed.** This combined patch preserves H1.7d-3a control flow and adds H1.7d-3b admission. Reflect remains deferred. No service, registry mount, bank, model, or running configuration was changed.

## Source and application guards

The patch is pinned to the installed `hindsight-api-slim` 0.10.1 build. `manifest.json` records SHA-256 hashes of ten frozen upstream/dependency files, all expected outputs, and the observed container/image/configuration fingerprints. The new `hindsight_api/engine/foreground_admission.py` has a null upstream hash: it must be absent before application. `foreground_admission.py` in this artifact is the exact source introduced by the unified patch. The manifest also pins the canonical Corvus registry protocol producer used by the interoperability tests. No upstream source tree is vendored.

The isolated source root contains `pyproject.toml` and `hindsight_api/`, corresponding to `/app/api`. Copy **only** manifest entries whose `upstream_sha256` is non-null into two fresh offline directories (one pristine, one to patch). Create parent directories locally, then use `docker cp hindsight-lab:/app/api/<relative-file> <offline-api-root>/<relative-file>`. Copying out does not edit the container. Confirm the installed distribution read-only with `docker exec hindsight-lab python -B -c 'from importlib.metadata import version; print(version("hindsight-api-slim"))'`.

With Python 3.11+ and Git, from the Corvus Lab repository:

```sh
python3 -B deploy/hindsight-patches/0.10.1/apply.py --root /tmp/offline-hindsight-api --check
python3 -B deploy/hindsight-patches/0.10.1/apply.py --root /tmp/offline-hindsight-api --apply
python3 -B deploy/hindsight-patches/0.10.1/apply.py --root /tmp/offline-hindsight-api --verify-patched
python3 -B deploy/hindsight-patches/0.10.1/test_admission.py --source /tmp/offline-hindsight-api
python3 -B deploy/hindsight-patches/0.10.1/test_control_flow.py --source /tmp/offline-hindsight-api --upstream-source /tmp/pristine-hindsight-api
```

Do not apply the diff directly. The helper verifies distribution/version, **every** input hash, and introduced-file absence before any writes; it then checks/applies the patch and verifies every output hash. Drift, unexpected introduced files and repeated application are rejected. The diff uses zero context (`--unidiff-zero`); exact hashes supply the source guard. In-place `/app/api` application is refused. An interrupted application must be discarded/recreated, not guessed into validity. A future replacement image/container rollout requires separate authorization.

## Optional configuration

Vanilla behavior is preserved when `CORVUS_FOREGROUND_REGISTRY_DIR` is unset or empty: admission is disabled and performs no registry/clock-domain I/O. To enable the future deployment, set:

```text
CORVUS_FOREGROUND_REGISTRY_DIR=/run/corvus-foreground
CORVUS_FOREGROUND_EXPECTED_PUBLISHERS=lab,production
CORVUS_FOREGROUND_IDLE_GRACE_SECONDS=30
```

Expected publishers default to `lab,production`; grace defaults to 30 seconds and must be positive and finite. Invalid enabled configuration defers rather than disabling the gate. The directory will need a read-only bind mount; existing 0700 directory and 0600 file permissions, UID/GID access and all other container settings must be preserved. This task has not installed that mount or configuration.

## Standalone read-only reader

The introduced module imports standard-library APIs and Hindsight's `DeferOperation` only. It does not import Corvus, call HTTP, write files, sleep, or access canonical/private data. It opens the actual protocol-v2 directory/header, per-process metadata, and stable lifetime/health/busy/fault lock inodes read-only, nonblocking, close-on-exec and without following the final symlink. Shared-lock probes detect publisher exclusive ownership. Fork hooks close inherited reader descriptors without unlocking the parent's descriptions; cached readers are process-bound.

The reader returns only `IDLE`, `BUSY`, or `UNKNOWN`. `IDLE` requires every configured expected logical publisher to be live and healthy, coherent metadata/count/lock ownership, matching boot/time domain and process/start/file identity, stable directory/lock identities, restrictive permissions, and elapsed completion/recovery grace. PID/start metadata is matched to the unique process record and kernel-backed lifetime ownership; the reader does not require host PIDs to be visible in the container's PID namespace.

Healthy busy ownership gives `BUSY`. Missing, dead, degraded, malformed, unreadable, inconsistent, unsupported or unverifiable state gives `UNKNOWN`; absence of busy ownership never implies idle. Historical valid records whose locks are all released cannot satisfy expected health or remain busy. They retain completion history and trigger one observed recovery grace; malformed history still fails closed. The registry is a scheduling protocol among trusted host publishers, not protection against malicious same-UID writers.

Thirty seconds must elapse strictly beyond the latest valid monotonic completion timestamp **and** reader-local first observations of publisher identities. Reader start, publisher restart/new identity, directory replacement, or recovery from uncertainty therefore cannot instantly grant `IDLE`. Missing initial completion history remains `UNKNOWN`; it is not replaced with an invented finish time. Clock regression, future/regressing watermarks and boot/time-domain mismatch fail closed. Grace returns `UNKNOWN` immediately, without sleeping. A reader restart intentionally delays memory eligibility again.

## Admission and durable deferral

`engine/llm_wrapper.py::_attempt_permits` checks after all operation/global permits are acquired and immediately before yielding to the provider attempt. Each OpenAI-compatible retry enters this hook again; provider retry/backoff code is unchanged. Only trustworthy `IDLE` is allowed. All other decisions raise `DeferOperation`, scheduling UTC `exec_date` up to 30 seconds later (bounded by configured grace), with no wait while holding permits. Exit-stack cleanup releases permits even when admission raises before yielding. The generic wrapper does not record deliberate defer as a provider failure.

Configured providers without the upstream per-attempt hook are conservatively deferred before send, rather than letting hidden retries bypass admission. With configuration absent those providers retain their original behavior. This patch gates generative wrapper calls without adding Reflect functionality or filtering only consolidation; the current shared llamacpp/OpenAI-compatible path supports the hook.

H1.7d-3a semantics remain: retain aggregation gives `DeferOperation` precedence over completed ordinary sibling errors (latest `exec_date`, input-order tie break), logging ordinary errors rather than discarding them. Streaming peers settle/cancel and defer cannot produce a false final partial checkpoint. Previously committed chunks remain recoverable. Consolidation rethrows before metrics, retries, failed-fact classification or bisection; committed batches persist and remaining batches stay eligible. Existing engine/worker routing returns work to pending with `next_retry_at`, unchanged identity/payload and no retry increment. No worker SQL or provider retry implementation is patched.

Durable async retain is a deployment prerequisite: synchronous retain does not provide the same durable deferral contract. Production retain has not been converted here. Real-bank partial-commit acceptance and bounded consolidation behavior remain separate work; these offline tests do not establish production readiness.

## Race and validation limits

The gate prevents starting a memory attempt while foreground is already busy or within grace. Foreground can arrive immediately after the check or during an admitted call. It provides no preemption or perfect arbitration. That residual race is accepted provisionally for bounded quiet-window use; cancellation/requeue and model-server arbitration remain deferred.

The harness executes complete selected upstream functions and dispatch/streaming closures through AST, with fake SDK, storage, tracing and SQL collaborators. New tests use the canonical Corvus publisher only as a **test producer** in temporary directories; introduced Hindsight runtime code has no Corvus dependency. Tests prove read-only access, identities, permissions, crash/restart recovery, both publishers, overlap/grace, actual retry-loop gating, defer propagation, permit release, disabled configuration and unchanged ordinary errors. Existing patched/pristine regression comparison and application guards remain. No live registry, bank, HTTP model endpoint or external dependency is used. This is focused offline validation, not a full upstream service/database acceptance suite.
