# Hindsight 0.10.1 foreground admission and bounded consolidation

**Version-pinned artifact, deployed through the guarded derived-image recipe.** This combined patch preserves intentional deferral and foreground admission, and adds H1.7e per-attempt consolidation bounds. Reflect remains deferred. See the [bounded-consolidation record](../../../docs/project-logs/2026-10-10-h1-7e-bounded-consolidation.md) for runtime identity and the one bank-independent frozen-fixture replay.

## Source and application guards

The patch is pinned to the installed `hindsight-api-slim` 0.10.1 build. `manifest.json` records SHA-256 hashes of ten frozen upstream/dependency files, all expected outputs, and the observed container/image/configuration fingerprints. The introduced `hindsight_api/engine/foreground_admission.py` and `hindsight_api/engine/consolidation_budget.py` have null upstream hashes: both must be absent before application. The correspondingly named artifact files are the exact source introduced by the unified patch. The manifest also pins the canonical Corvus registry protocol producer used by the interoperability tests. No upstream source tree is vendored.

The isolated source root contains `pyproject.toml` and `hindsight_api/`, corresponding to `/app/api`. Extract **only** manifest entries whose `upstream_sha256` is non-null from a stopped scratch container created from the exact cached immutable upstream base into two fresh offline directories (one pristine, one to patch). Create parent directories locally, then use `docker cp <stopped-scratch>:/app/api/<relative-file> <offline-api-root>/<relative-file>`. The live container is already patched and is not a pristine patch input. The existing build recipe performs this extraction without running the scratch command, mounting data, or downloading anything. Confirm the installed distribution read-only with `docker exec hindsight-lab python -B -c 'from importlib.metadata import version; print(version("hindsight-api-slim"))'`.

With Python 3.11+ and Git, from the Corvus Lab repository:

```sh
python3 -B deploy/hindsight-patches/0.10.1/apply.py --root /tmp/offline-hindsight-api --check
python3 -B deploy/hindsight-patches/0.10.1/apply.py --root /tmp/offline-hindsight-api --apply
python3 -B deploy/hindsight-patches/0.10.1/apply.py --root /tmp/offline-hindsight-api --verify-patched
python3 -B deploy/hindsight-patches/0.10.1/test_admission.py --source /tmp/offline-hindsight-api
python3 -B deploy/hindsight-patches/0.10.1/test_control_flow.py --source /tmp/offline-hindsight-api --upstream-source /tmp/pristine-hindsight-api
python3 -B deploy/hindsight-patches/0.10.1/test_bounded_consolidation.py --source /tmp/offline-hindsight-api
```

Do not apply the diff directly. The helper verifies distribution/version, **every** input hash, and introduced-file absence before any writes; it then checks/applies the patch and verifies every output hash. Drift, unexpected introduced files and repeated application are rejected. The diff uses zero context (`--unidiff-zero`); exact hashes supply the source guard. In-place `/app/api` application is refused. An interrupted application must be discarded/recreated, not guessed into validity. A future replacement image/container rollout requires separate authorization.

## Optional configuration

Vanilla behavior is preserved when `CORVUS_FOREGROUND_REGISTRY_DIR` is unset or empty: admission is disabled and performs no registry/clock-domain I/O. The deployed admission settings are:

```text
CORVUS_FOREGROUND_REGISTRY_DIR=/run/corvus-foreground
CORVUS_FOREGROUND_EXPECTED_PUBLISHERS=lab,production
CORVUS_FOREGROUND_IDLE_GRACE_SECONDS=30
```

Expected publishers default to `lab,production`; grace defaults to 30 seconds and must be positive and finite. Invalid enabled configuration defers rather than disabling the gate. The directory will need a read-only bind mount; existing 0700 directory and 0600 file permissions, UID/GID access and all other container settings must be preserved. The deployed bind is read-only; H1.7e preserved it and the 30-second admission grace unchanged.

## Standalone read-only reader

The introduced module imports standard-library APIs and Hindsight's `DeferOperation` only. It does not import Corvus, call HTTP, write files, sleep, or access canonical/private data. It opens the actual protocol-v2 directory/header, per-process metadata, and stable lifetime/health/busy/fault lock inodes read-only, nonblocking, close-on-exec and without following the final symlink. Shared-lock probes detect publisher exclusive ownership. Fork hooks close inherited reader descriptors without unlocking the parent's descriptions; cached readers are process-bound.

The reader returns only `IDLE`, `BUSY`, or `UNKNOWN`. `IDLE` requires every configured expected logical publisher to be live and healthy, coherent metadata/count/lock ownership, matching boot/time domain and process/start/file identity, stable directory/lock identities, restrictive permissions, and elapsed completion/recovery grace. PID/start metadata is matched to the unique process record and kernel-backed lifetime ownership; the reader does not require host PIDs to be visible in the container's PID namespace.

Healthy busy ownership gives `BUSY`. Missing, dead, degraded, malformed, unreadable, inconsistent, unsupported or unverifiable state gives `UNKNOWN`; absence of busy ownership never implies idle. Historical valid records whose locks are all released cannot satisfy expected health or remain busy. They retain completion history and trigger one observed recovery grace; malformed history still fails closed. The registry is a scheduling protocol among trusted host publishers, not protection against malicious same-UID writers.

Thirty seconds must elapse strictly beyond the latest valid monotonic completion timestamp **and** reader-local first observations of publisher identities. Reader start, publisher restart/new identity, directory replacement, or recovery from uncertainty therefore cannot instantly grant `IDLE`. Missing initial completion history remains `UNKNOWN`; it is not replaced with an invented finish time. Clock regression, future/regressing watermarks and boot/time-domain mismatch fail closed. Grace returns `UNKNOWN` immediately, without sleeping. A reader restart intentionally delays memory eligibility again.

## Admission and durable deferral

`engine/llm_wrapper.py::_attempt_permits` checks after all operation/global permits are acquired and immediately before yielding to the provider attempt. Each OpenAI-compatible retry enters this hook again; provider retry/backoff code is unchanged. Only trustworthy `IDLE` is allowed. All other decisions raise `DeferOperation`, scheduling UTC `exec_date` up to 30 seconds later (bounded by configured grace), with no wait while holding permits. Exit-stack cleanup releases permits even when admission raises before yielding. The generic wrapper does not record deliberate defer as a provider failure.

Configured providers without the upstream per-attempt hook are conservatively deferred before send, rather than letting hidden retries bypass admission. With configuration absent those providers retain their original behavior. This patch gates generative wrapper calls without adding Reflect functionality or filtering only consolidation; the current shared llamacpp/OpenAI-compatible path supports the hook.

H1.7d-3a semantics remain: retain aggregation gives `DeferOperation` precedence over completed ordinary sibling errors (latest `exec_date`, input-order tie break), logging ordinary errors rather than discarding them. Streaming peers settle/cancel and defer cannot produce a false final partial checkpoint. Previously committed chunks remain recoverable. Consolidation rethrows before metrics, retries, failed-fact classification or bisection; committed batches persist and remaining batches stay eligible. Existing engine/worker routing returns work to pending with `next_retry_at`, unchanged identity/payload and no retry increment. No worker SQL or provider retry/error classification is changed; bounded preflight is inserted inside each existing provider attempt.

Durable async retain is a deployment prerequisite: synchronous retain does not provide the same durable deferral contract. Production retain has not been converted here. Real-bank partial-commit acceptance remains separate work. The bounded frozen replay below does not establish general memory quality or production readiness.

## Race and validation limits

The gate prevents starting a memory attempt while foreground is already busy or within grace. Foreground can arrive immediately after the check or during an admitted call. It provides no preemption or perfect arbitration. That residual race is accepted provisionally for bounded quiet-window use; cancellation/requeue and model-server arbitration remain deferred.

The harness executes complete selected upstream functions and dispatch/streaming closures through AST, with fake SDK, storage, tracing and SQL collaborators. New tests use the canonical Corvus publisher only as a **test producer** in temporary directories; introduced Hindsight runtime code has no Corvus dependency. Tests prove read-only access, identities, permissions, crash/restart recovery, both publishers, overlap/grace, actual retry-loop gating, defer propagation, permit release, disabled configuration and unchanged ordinary errors. Existing patched/pristine regression comparison and application guards remain. No live registry, bank, HTTP model endpoint or external dependency is used. This is focused offline validation, not a full upstream service/database acceptance suite.


## Opt-in consolidation budget

Exact deployed settings (normal retain/foreground reasoning remains unchanged):

```text
CORVUS_CONSOLIDATION_CONTEXT_LIMIT=8192
CORVUS_CONSOLIDATION_SAFETY_MARGIN_TOKENS=256
HINDSIGHT_API_CONSOLIDATION_MAX_COMPLETION_TOKENS=1024
HINDSIGHT_API_CONSOLIDATION_LLM_BATCH_SIZE=1
HINDSIGHT_API_CONSOLIDATION_LLM_REASONING_EFFORT=none
HINDSIGHT_API_CONSOLIDATION_LLM_EXTRA_BODY={"chat_template_kwargs":{"enable_thinking":false}}
```

`CORVUS_CONSOLIDATION_CONTEXT_LIMIT` absent means the new budget feature is disabled. Configured, `consolidation` and `consolidation_dedup` OpenAI-compatible attempts enter existing permits/admission, then count the **final** provider request (including soft-schema injection, JSON hints and extra body). The same model-server origin supplies `/props`, `/apply-template` and `/tokenize` with `add_special=true, parse_special=true`. Model alias and context must match. Counting has a five-second overall deadline, no generation or HTTP retry. There is no character/tiktoken estimate. The actual provider transport emits `max_tokens` on the current custom OpenAI base URL; the native llamacpp provider uses `max_completion_tokens`.

Allowed completion is `min(configured cap, explicitly requested cap if present, 8192 - rendered input - 256)`, with a minimum useful completion of 512. Token limits remain separate from `CONSOLIDATION_MAX_TOKENS=512`, which is retrieval budget. Every attempt, including a real provider retry, recomputes this bound. Unknown tokenizer/configuration, model/context mismatch, unsafe extra-body model/message/token override, or fewer than 512 completion tokens causes `DeferOperation` before send. No facts are truncated, dropped or marked failed by budget preflight.

Existing batching is configured to one source fact first; effective Lab bank config confirms batch size one with no overrides. If a single fact plus recalled observations still cannot fit, preserve durable pending work and defer. This can require operator attention rather than automatic progress; no new queue/scheduler or unsafe singleton bisection is introduced. Ordinary model/schema failures retain their existing finite retries/bisection behavior. Prior batch commits survive deliberate defer.

For these two consolidation scopes only, final request parameters force `reasoning_effort=none` and `chat_template_kwargs.enable_thinking=false`. Provider wrapping is counted with those same settings. After counting, foreground admission is checked again immediately before send, inside the same permits. BUSY/UNKNOWN/grace still defer; no preemption or perfect arbitration is added. Logs record input, allowed completion, margin, context, reserved total and actual request parameter without logging fact text.

The final-image tests passed: 14 budget tests, 28 admission tests and 27 defer/control-flow tests. Ten ordinary-error tests also pass on pristine upstream, seven runtime-preservation/upgrade tests pass, and the earlier frozen schema/source-ID validation passes. The one real frozen replay through installed `_consolidate_batch_with_llm` used 4131 input + 1024 allowed output + 256 margin = 5411 <= 8192; provider usage confirmed the exact input count. It stopped after 161 output tokens in 4.321 seconds with one valid grounded UPDATE. No operations were applied and bank/operation records stayed unchanged. These are per-attempt generation bounds, not a total consolidation wall-time guarantee or a general semantic-quality certification.
