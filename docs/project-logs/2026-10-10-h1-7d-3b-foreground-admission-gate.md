# H1.7d-3b — Offline foreground-registry reader and LLM admission gate

Date: 2026-10-10. Scope: version-pinned offline Hindsight patch and tests only; no deployment.

## Baselines and source freeze

Lab began clean on `lab/ow2e-console` at `b1dd20d1626231b47f1f83ebd2256a3b45816f3d`. Production remained clean on `main` at `c315d0e767e31fde3c82ba4dfb08659a268c267a`. The existing H1.7d-3a patch and successful real async-retain acceptance log were present. Lab async retain remained enabled, its only recorded operation was terminal completed, and no unresolved intent existed.

The live `hindsight-api-slim` distribution is exactly 0.10.1. All ten source/dependency hashes matched the frozen upstream manifest before editing and after testing. The source root is `/app/api`, with runtime package `/app/api/hindsight_api`; copies were handled only under `/tmp/corvus-h17d-3b/`. The manifest retains the exact upstream container/image/config/mount fingerprints and all full SHA-256 values. Live container `336680f1d0a7a4dfb531f818976e969b6e1c7e55861fec4b605401df295a8bfe` and image `sha256:b4d3b76f363aa40cf348450e7f8f52a50653008731b99824b14623a196182e73` were unchanged.

Both foreground publishers were healthy; the host aggregate was trustworthy IDLE. Lab, Production, :8095 and Hindsight health checks passed. Hindsight remained disconnected from the registry. No runtime file, environment value, mount, service, container, bank or model endpoint was changed.

## Standalone protocol-compatible reader

The combined artifact introduces `hindsight_api/engine/foreground_admission.py`. Its exact new source is also stored as `deploy/hindsight-patches/0.10.1/foreground_admission.py`. It imports no Corvus application code and makes no HTTP calls. Standard-library readonly filesystem/lock inspection and Hindsight's existing `DeferOperation` are sufficient.

Compatibility is pinned to registry protocol version 2 and canonical `app/foreground_registry.py` SHA-256 `2219148a19cb806f267b310534b78a4d150536cbf5747c355530156a9490915b`. The reader checks directory/header identity, boot ID and time-namespace offsets, exact process metadata, stable busy/fault/live/health inodes, logical publisher health, count/ownership coherence, completion history and recovery anchors. Files are opened readonly, nonblocking, close-on-exec and without following the final symlink; shared flock probes determine kernel-owned exclusive locks. Permissions remain directory 0700 / files 0600, with coherent directory/file ownership. It never creates, replaces or deletes registry files and never sleeps.

Expected logical publishers default to `lab,production` and are injectable/configurable. Unique PID/start/UUID record identity and lifetime ownership prove protocol liveness without requiring host PIDs to be visible in Hindsight's separate PID namespace. Stale well-formed records with released locks cannot satisfy expected health or keep the host BUSY. Their valid completion history and newly observed identity still contribute conservative recovery grace. Orphaned, malformed or inconsistent historical files remain UNKNOWN. This preserves the deployed protocol's restart behavior and does not claim to defend against malicious trusted same-UID writers.

The result is only `IDLE`, `BUSY` or `UNKNOWN`:

- `IDLE`: all expected publishers are present, live and healthy, all inspected state is trustworthy, no foreground count/lock is busy, and completion/recovery grace has elapsed.
- `BUSY`: trustworthy live foreground ownership/count indicates activity. Overlapping counts remain BUSY until the final completion.
- `UNKNOWN`: missing registry/publisher, dead/degraded publisher, malformed/unreadable file, unsupported protocol, boot/time-domain or PID/start identity mismatch, lock/inode/count mismatch, duplicate live identity, unsafe permissions, invalid timestamp, missing initial completion history, active grace or any inability to establish trust.

Absence of BUSY never implies IDLE. Missing initial completion history is not replaced with an invented finish time.

## Grace and configuration

The provisional grace is 30 seconds, strictly older than both the latest valid monotonic completion timestamp and reader-local first observations of publisher identities. Reader startup, newly discovered/restarted publishers, directory replacement and recovery after UNKNOWN cannot grant immediate IDLE. A reader restart intentionally begins a fresh recovery grace. Future/regressing timestamps and clock regression fail closed. The decision is returned immediately; there is no sleeping or busy-wait.

Future Hindsight configuration is:

```text
CORVUS_FOREGROUND_REGISTRY_DIR=/run/corvus-foreground
CORVUS_FOREGROUND_EXPECTED_PUBLISHERS=lab,production
CORVUS_FOREGROUND_IDLE_GRACE_SECONDS=30
```

An unset/empty registry path explicitly disables admission with no registry/clock-domain I/O. Expected names and positive finite grace are validated. When enabled, invalid configuration or read failure defers; it never silently disables protection. No setting was enabled in the live container.

## Per-attempt gate and control flow

The exact admission seam is `engine/llm_wrapper.py::_attempt_permits`: acquire operation/global permits, read the registry, then yield to the upstream attempt only for trustworthy IDLE. Installed global concurrency remains 1. Every supported provider retry reacquires permits and checks again; it is not a one-time operation-level test.

BUSY, UNKNOWN and grace raise the existing `DeferOperation` immediately, with bounded future UTC `exec_date` (up to 30 seconds, limited by configured grace). The durable worker chooses eligibility. Exit-stack cleanup releases permits on defer, including a raise before context-manager yield. Generic `LLMProvider.call` / `call_with_tools` preserve intentional defer without recording a failed provider call. No provider retry/backoff implementation or worker SQL was changed.

If an enabled provider cannot expose the per-attempt concurrency hook, the wrapper conservatively defers before send rather than allowing hidden retries to bypass admission. Configuration absent preserves its prior behavior. The shared llamacpp/OpenAI-compatible path supports per-attempt checking. This generic wrapper coverage adds no Reflect functionality; Reflect remains deferred.

The H1.7d-3a control-flow patch remains intact. Retain aggregation gives intentional defer precedence over ordinary completed sibling exceptions while logging the latter; streaming and engine boundaries preserve the exact exception. Partial successes do not fabricate terminal completion. Consolidation defer escapes before retries, bisection, failed-fact marking or failure metrics. Already committed batches/checkpoints remain preserved and remaining work stays eligible. Existing WorkerPoller handling parks the same operation as pending with `next_retry_at`, preserving payload/identity and retry count.

## Offline tests and artifact validation

All tests used temporary registry directories, fake providers/SDK/storage/SQL collaborators and isolated patched upstream functions. No live registry mutation, model inference, real retain/consolidation/Reflect or bank mutation occurred.

- New reader/gate suite: 28 tests passed. Covers both expected publishers, missing/malformed/unreadable/degraded/stale state, permissions, boot/process/protocol/inode mismatches, busy overlap, completion and recovery grace, new reader/publisher identity, missing completion history, crash lock release, readonly opens and unchanged bytes/inodes.
- Gate tests exercise the actual wrapper seam and OpenAI-compatible retry loop: IDLE permits send; BUSY/UNKNOWN/grace defer before send; permits release; ordinary provider errors retain retry behavior; foreground activity arising after one failed attempt blocks the next send. Intentional defer traverses patched retain/consolidation without bisection or failed-fact marking. Generic tool wrapper behavior is tested without running Reflect.
- Existing combined patch suite: 27 tests passed, including streaming/partial-checkpoint behavior, ordinary parser/runtime failures, worker pending scheduling, unchanged operation/retry identity and application guards.
- Pristine upstream ordinary-error comparison: 10 regressions passed.
- Canonical Corvus registry/core/health regressions: 43 tests passed.
- Source/artifact syntax compilation, pinned patch check/application/output verification and `git diff --check` passed. The applier rejects unexpected existing introduced source before writes, in addition to version/hash drift and repeat application.

Commands:

```sh
python3 -B deploy/hindsight-patches/0.10.1/test_admission.py --source /tmp/corvus-h17d-3b/patched
python3 -B deploy/hindsight-patches/0.10.1/test_control_flow.py --source /tmp/corvus-h17d-3b/patched --upstream-source /tmp/corvus-h17d-3b/upstream
python3 -B -m unittest discover -s tests -p 'test_foreground_registry*.py' -v
python3 -B deploy/hindsight-patches/0.10.1/apply.py --root /tmp/corvus-h17d-3b/upstream --check
python3 -B deploy/hindsight-patches/0.10.1/apply.py --root /tmp/corvus-h17d-3b/patched --verify-patched
```

The focused harness runs complete selected source functions/closures through AST with fake collaborators; it is not a full upstream service/database integration suite or real-bank partial-commit acceptance.

## Packaging and unchanged runtime

`deploy/hindsight-patches/0.10.1/` now contains the combined unified patch, updated source/output/protocol manifest, exact standalone reader source, application verifier, configuration/application instructions and focused test harnesses. Five existing upstream files are modified (the four H1.7d-3a files plus `llm_wrapper.py`) and one module is introduced. Ten upstream/dependency hashes are still checked. New-file absence is required before application; full output hashes are verified afterward. No upstream source tree is vendored and in-place `/app/api` application remains refused.

Postflight verified all ten live source hashes unchanged and the new runtime module absent. Service/container identities, configuration, registry contents/identities, canonical and Production data, and the retain ledger remained unchanged. No unresolved intent existed. Readonly bank counts remained eight documents and nine memories. Production stayed clean at its expected HEAD. No service restarted; the live Hindsight container is still unmodified.

## Accepted limitation and next step

The gate prevents a new memory attempt while foreground is already busy or within grace. Foreground can arrive immediately after admission or during an already-running memory call. Zero-race arbitration requires model-server coordination or cancellation/requeue; neither was implemented. This residual race is provisionally accepted for bounded quiet-window daily use, not a zero-wait guarantee.

Next step: controlled Hindsight container recreation with a read-only registry mount and the patched admission gate, preserving existing image/environment/network/volumes/security settings. Durable async-retain deferral/checkpoint acceptance and bounded consolidation remain daily-use requirements; this offline result does not establish production readiness. No rollout was performed in this task.

Verdict: PASS for the offline reader/admission artifact and focused compatibility tests.
