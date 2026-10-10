# H1.7d-1 — Hindsight foreground-admission integration audit

Date: 2026-10-09

Audit verdict: **PASS WITH CONSTRAINTS**. This document seals the completed
read-only audit; it does not implement admission or change deployment state.

Verified repository baselines:

- Lab: `lab/ow2e-console` at `21adce7e00b1a1fc0683eb9c568598a0a0cb0966`, clean.
- Production: `main` at `c315d0e767e31fde3c82ba4dfb08659a268c267a`, clean.

The host-wide Lab + Production foreground registry is deployed and healthy.
Both publishers were live, healthy and idle; the aggregate expected set
`lab,production` returned trustworthy `IDLE` with active count zero. The shared
`:8095` endpoint was healthy and unchanged. Hindsight remains disconnected from
the registry, with no admission behavior active. Its container identity, image,
configuration and mounts matched the completed rollout snapshot.

Installed Hindsight is **0.10.1**, with source under
`/app/api/hindsight_api`. The provisional architecture remains unchanged:
canonical Corvus SQLite evidence, Hindsight derived memory intelligence,
Qwen3.5-9B for retain and consolidation, and Reflect deferred.

## Exact admission seam

The common seam is `engine/llm_wrapper.py::_attempt_permits` at line 167.
Admission belongs after `_acquire_permits` at line 172 and immediately before
the context yields to the upstream request at line 174.

Every upstream attempt, including retries, must recheck admission after acquiring
the applicable operation/global LLM permits. Current global LLM concurrency is
**1**. When configured, the operation permit is acquired before the global
permit. Corvus foreground generation remains outside those permits.

Retain extraction and consolidation use `LLMConfig.call`; Reflect also uses
`call_with_tools`. The current OpenAI-compatible provider enters the attempt
context before sends at
`engine/providers/openai_compatible_llm.py:1257,1337,1666`. Permits are released
before provider retry/backoff. The SDK has retries disabled; Hindsight owns the
attempt loops. The configured timeout is 180 seconds per phase, not a hard
overall operation deadline.

Checking before semaphore acquisition would leave a stale admission decision
while queued. Checking only at operation submission would miss later execution,
retries and subsequent model calls.

## Durable deferral and stage-specific prerequisites

`WorkerPoller` and `DeferOperation` already provide persisted pending work in
`async_operations`. `worker/poller.py::_defer_operation` at line 1032 sets the
operation back to pending, records `next_retry_at`, and clears worker ownership.
Proper deferral neither consumes retries nor marks the operation failed. The
worker can claim it again when due. Restart recovery and reconciliation already
exist; interrupted-processing recovery remains subject to its own retry limits.
A new queue/framework is unnecessary.

### Retain extraction

Corvus currently submits retain with `async:false`
(`app/hindsight_shadow.py:273`). This synchronous HTTP path has no durable queued
operation to defer at the proposed gate. Raising worker-only `DeferOperation`
there would not create durable pending work.

Hindsight already exposes async retain submission through `api_retain` and
`engine/memory_engine.py::submit_async_retain` at line 21773. **Durable async
retain must be implemented before admission is enabled for retain extraction.**
Submission acceptance must be distinguished from completed storage, with stable
operation identity and outcome tracking.

Intentional deferral must also survive extraction error handling:
`engine/retain/fact_extraction.py:2636` currently aggregates failures and can
replace the control exception with an ordinary error. Streaming retain can
commit earlier chunks before a later extraction is deferred. Partial-commit,
idempotent recovery and exception propagation must be tested before rollout.

### Consolidation

Consolidation is already durable background work, with unconsolidated source
facts and persisted operations. However,
`engine/consolidation/consolidator.py:3265` currently catches `DeferOperation`
as a batch failure. It must explicitly pass through **before** failure metrics,
retry, adaptive bisection or failed-fact logic. Admission must never turn an
intentional deferral into permanently failed source facts.

With correct propagation, earlier committed batches remain committed and
remaining eligible facts stay pending. The existing gather/cancel cleanup must
continue to prevent sibling work from surviving the deferred dispatch.

### Reflect

Reflect remains deferred from normal use. Direct synchronous Reflect requests
are not durably queued by worker deferral. Its broad error handlers can also
absorb control exceptions; any later admission support must propagate a
controlled denial rather than retrying, synthesizing around it, or claiming
durable deferral that did not occur.

## Registry reader and idle grace

Use a standalone, protocol-compatible **read-only** reader for the deployed
registry protocol. Do not import Corvus application internals, add an HTTP API,
or access canonical/private data. A shared neutral package is a possible later
refactoring, but is unnecessary for the first integration.

The expected logical publisher set is `lab,production`. The reader must preserve
the protocol's `BUSY` / `IDLE` / `UNKNOWN` semantics and validate lifetime,
health and busy locks, stable inode identity, boot/process identity, completion
watermark and recovery grace. Stale records alone cannot prove live health.
Use a long-lived reader instance; recreating it per attempt would continually
reset its reader-local recovery grace.

The provisional idle grace is **30 seconds**, a conservative architecture choice,
not a measured optimum. A memory LLM attempt is permitted only when:

- The registry is trustworthy `IDLE`.
- Both expected publishers are live and healthy.
- No foreground activity exists.
- The latest completion/recovery anchor is older than 30 seconds.

Fail closed and defer on `BUSY`, `UNKNOWN`, missing/degraded publishers,
malformed/unreadable registry state, identity mismatch or registry read failure.
Missing initial completion watermark and publisher restart/recovery require a
fresh recovery grace; absence of a finish timestamp must not mean immediate
admission. After a healthy expected set has been observed for the full recovery
grace, its recovery anchor can supply the initial bound. Reader restart likewise
restarts recovery grace. Unknown state never becomes permission through age alone.

Use monotonic time within the validated clock domain for grace calculations.
Durable deferral can schedule a finite recheck using `next_retry_at`, without
holding LLM permits while sleeping or consuming provider retries.

## Race and first-rollout policy

Per-attempt checking greatly narrows the race by checking after semaphore waits
and again on each retry. A foreground request can still arrive immediately after
admission or while an admitted memory call is running. Admission cannot preempt
that call and cannot guarantee zero foreground waiting.

Zero-race protection requires model arbitration or foreground-triggered
cancellation/requeue. That stronger mechanism remains **DEFERRED** for the
provisional daily-use baseline. The residual race is acceptable only within the
conservative baseline of bounded calls and quiet consolidation maintenance;
actual foreground waiting remains a limitation to observe.

The first-rollout policy is to gate **all Hindsight generative calls sharing
`:8095`**, including extraction, **only after durable async retain is available**.
Consolidation-only or duration-selected gating leaves extraction contention.
Full gating delays memory freshness but preserves durable work and foreground
priority. Continuous foreground use can starve background work; quiet maintenance
windows remain acceptable provisional behavior. Reflect stays deferred.

## Later deployment requirements

Hindsight needs a read-only mount of the existing runtime registry:

```text
--mount type=bind,src=/run/corvus-foreground,dst=/run/corvus-foreground,readonly
```

The current deployment is standalone Docker; no Compose configuration was
identified. A reviewed deployment recipe must preserve the inspected container
configuration. The actual runtime UID/GID is `1000:1000` with identity mapping,
which permits access to the existing `ethan:ethan` directory mode `0700` and files
mode `0600`. No permission change is needed. The reader must never write.

Container recreation is required to add the mount; restart alone is insufficient.
Preserve the exact cached image, complete environment, network, named data/cache
volumes, localhost port bindings, command/user, restart policy and security
settings. Validate cross-container lock visibility and clock identity during the
later controlled rollout. No recreation or mount was performed by this audit.

## Architecture ordering and next engineering work

1. Implement durable async retain, including outcome tracking and recovery tests.
2. Add consolidation `DeferOperation` passthrough.
3. Add the standalone read-only registry reader and compatibility tests.
4. Add per-attempt foreground admission with control-exception propagation.
5. Add the read-only registry mount through a controlled Hindsight rollout.
6. Complete bounded consolidation generation/context behavior.
7. Perform daily-use acceptance.

This ordering does not authorize active daily-use consolidation before its
completion/context bounds and quiet admission have been validated. Explicit
completion limits, reasoning disabled, and rendered input + output + safety-margin
preflight remain prerequisites from H1.7b.

Likely affected components are the standalone reader/deployment recipe,
Hindsight LLM wrapper, consolidation/extraction control-exception handling,
Reflect denial handling where applicable, and Corvus durable-retain submission
and outcome tracking. This sealing task changes only this project log: no code,
runtime configuration, registry state, services, containers or banks are changed,
and no inference is run.
