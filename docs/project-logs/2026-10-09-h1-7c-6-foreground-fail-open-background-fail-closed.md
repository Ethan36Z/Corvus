# H1.7c-6 — Foreground fail-open / background fail-closed registry semantics

Date: 2026-10-09

Baseline: `lab/ow2e-console` at
`e8a8536ebb2d9a67dbbc82d708179c0e039d529f`; expected branch, HEAD,
and clean worktree verified before editing.

Verdict: **PASS** for the intended single-host, explicitly configured publisher
contract. The H1.7c-5a failure-policy deployment blocker is resolved in code and
offline tests. This does not authorize or perform deployment or Hindsight admission.

## Previous behavior and audit finding

H1.7c-5 initialized the publisher in API lifespan before canonical startup
preparation. Initialization errors could prevent API startup. Failed begin
publication rolled back the local activity increment and returned
`FOREGROUND_REGISTRY_UNAVAILABLE` before sending a foreground model request.
Completion failures preserved replies and original model errors, but subsequent
foreground requests through the poisoned publisher were blocked.

The H1.7c-5a audit found that simply suppressing those exceptions was unsafe:
the old reader accepted an initialized empty registry as IDLE, and a failure
before creating publisher records could leave exactly that state. Existing fault
locks also could not guarantee UNKNOWN if fault signaling itself failed.

## Foreground policy and integration

`app/foreground_activity.py:ForegroundActivityTracker` retains the existing
process-local count, immutable snapshots, monotonic timestamps, and serialized
transitions. The `process_turn` step-5 generation seam is unchanged; the shared
model client is not globally instrumented.

Ordinary registry initialization, validation, lock, write, and publication
errors now log a clear diagnostic and permit foreground generation. A degraded
publisher remains degraded, with no automatic publication retry or replacement
during live requests. Local increments are not rolled back for metadata errors;
completion still decrements in `finally`, including overlapping requests and
model exceptions. Replies, original model errors, and normal SQLite persistence
are preserved. Completion-publication errors do not discard the reply.

API lifespan continues to use the existing start/stop hooks. Publisher startup
failure no longer prevents canonical startup preparation or serving chat. The
publisher does not require an aggregate IDLE read before joining: missing peers
or malformed peer state can keep background admission UNKNOWN while foreground
remains usable. Registry header and owned-file validation remain in the core.

Process lifecycle misuse remains an error: explicitly using an inherited tracker
or entering after shutdown is distinct from a scheduling-metadata failure.
`KeyboardInterrupt`/`SystemExit` are not suppressed; interrupted entry still
balances the local count. Disabled publication retains the existing local-only
behavior and performs no registry initialization or I/O.

## Configuration and expected logical publishers

The optional configuration follows the existing environment style:

- `CORVUS_FOREGROUND_REGISTRY_DIR`: existing opt-in directory setting; unset,
  empty, or whitespace-only disables publication. No default path is added.
- `CORVUS_FOREGROUND_REGISTRY_PUBLISHER`: logical publisher slot, for example
  `lab` or `production`. A configured path without a valid logical name produces
  a logged initialization failure while foreground remains usable.
- `CORVUS_FOREGROUND_REGISTRY_EXPECTED_PUBLISHERS`: comma-separated logical
  names for the registry reader contract, for example `lab,production`.

Tests and future independent consumers inject `expected_publishers` directly
into `ForegroundRegistry`; the tracker also accepts injected logical name,
expected set, directory, and clock. Neither `lab` nor `production` is hardcoded
as required by the core. A reader without a nonempty expected contract returns
UNKNOWN. A Lab-only test contract can accept healthy Lab, but a shared-host
consumer protecting both services must independently require both slots even
before Production is publishing. Expectations must not be inferred from whatever
records happen to exist, or reduced automatically when a service disappears.

Logical names are stable across process restarts and correspond to unique
configured service/worker slots. The current deployments have one API process
each; additional workers would need distinct configured slots and a complete
expected set. Two live records using the same logical slot return UNKNOWN.
Unconfigured callers remain outside the registry; this is not an inference-server
arbitrator or a security boundary against other processes running as the same user.

## Registry data model, liveness, and degradation

The volatile registry format is now version **2**. Each unique PID/start-ticks/UUID
process identity has strict JSON metadata containing logical publisher name,
local count, last-finished timestamp, and stable lock-file inode identities.
Existing `.busy` and `.fault` files are retained; `.live` and `.health` files add
separate kernel ownership for lifetime and trustworthy publication.

- `.live` is held exclusively for the publisher lifetime, including degradation.
  It distinguishes a live degraded publisher from stale files left after exit.
- `.health` is held exclusively only while published state is trustworthy.
  Publication closes this descriptor **before** fallible guard acquisition,
  validation, busy locking, or metadata writes. Health is reacquired on the same
  inode only after successful metadata publication and correct busy transition.
- `.busy` is held while successfully published local count is positive. Normal
  1→0 publishes the finish watermark before releasing busy ownership.
- `.fault` remains a best-effort degradation signal, now acquired nonblocking.
  Even if this signaling fails, the live-but-unhealthy publisher makes the reader
  return UNKNOWN. Integration also explicitly degrades a publisher after a
  publication exception as a defensive fallback.

The global registry guard continues to serialize writes against read snapshots;
writer contention remains bounded by the existing one-second guard timeout.
Readers remain nonblocking and read-only. Health withdrawal during an update
may conservatively yield UNKNOWN. No daemon, heartbeat, queue, database,
network service, or model-server coordination was introduced.

Crash/exit automatically releases kernel locks. Descriptors retain close-on-exec
and at-fork cleanup; child cleanup closes descriptors without unlocking the
parent's open-file descriptions. Restart creates a fresh process identity.
Normal tracker shutdown retains ownership until active calls drain, then closes
resources. No lock file is replaced or deleted, and peer history is preserved.

## Aggregate read and idle grace

Trustworthy IDLE requires every configured expected slot to have a live healthy
publisher, all live publishers to be trustworthy, no owned busy lock, and valid
metadata including finish timestamps. BUSY reports the sum of trustworthy live
counts when the full expected contract is satisfied. Missing/degraded expected
publishers, malformed/unreadable/orphan state, ownership inconsistencies,
duplicate live logical slots, and boot/time-domain mismatches return UNKNOWN;
UNKNOWN exposes no purported trustworthy active count.

Stale records cannot satisfy expected presence or keep a crashed process BUSY.
A healthy replacement can restore the slot while stale valid history preserves
the finish watermark. Any live degraded predecessor still causes UNKNOWN,
even when another process with the same logical name has registered.

The reader observes one conservative grace per process identity, including
healthy newly observed/replacement identities and stale records. This covers a
replacement after failed initialization or first publication left no exact
finish timestamp. Grace is reader-local and resets on reader restart; it does
not fabricate an actual finish timestamp. Future admission must inspect
`idle_grace_anchor` (maximum valid finish/observation grace), not just IDLE.

Version-1 or malformed registries are not automatically migrated or repaired.
They remain UNKNOWN until an explicit, quiescent repair. Foreground remains
available during that condition. Stable directory and lock inode identity are
still mandatory. Admission is a point-in-time signal; it cannot preempt memory
generation already admitted before later foreground arrival.

## Offline validation

`.venv/bin/python -B -m unittest discover -s tests -p 'test_foreground_*.py' -v`:
**78 tests passed**:

- 10 unchanged local tracker/conversation tests.
- 30 registry-core tests, adapted to the required logical health contract and
  UNKNOWN for missing/crashed expected publishers.
- 25 publisher integration tests using fake foreground generation/persistence,
  including API startup failure tolerance, pre-registration initialization
  failure, writer-only permission denial, first/busy write failure, busy-lock and
  fault-signaling failure, completion failure, original-error preservation,
  invalid optional configuration, restart grace, overlap, shutdown, and fork.
- 13 focused health-contract tests: missing/unspecified expectations; Lab only;
  Lab+Production; both idle/either busy; stale idle records; live degradation
  despite failed fault signaling; guard failure; duplicate slots; malformed
  health metadata; missing lifetime ownership; actual idle/busy subprocess
  crashes and healthy replacements; and old-schema rejection.

All tests use temporary directories; subprocesses are disposable test publishers.
No real inference or `/run` access is required.

**10 existing offline regression scripts passed**: personality runtime, vision
conversation, voice conversation, web conversation, web mode, web auto,
web query-rewrite runtime, web intent gate, web query rewrite, and startup schema
ensure. They use fake model calls and temporary canonical databases where needed;
the regression environment disables publication and model downloads.

`git diff --check` and staged whitespace checks passed.

## Deployment status and next step

**Still disabled by default and not deployed.** `/run/corvus-foreground/` was not
created. Neither running Lab nor Production is publishing. No Production,
systemd/tmpfiles, service environment, Hindsight, bank, model endpoint, or host
power state was changed. No inference, downloads, service restarts, or push occurred.

Hindsight remains disconnected. Its future independent reader must use the
complete expected logical-publisher contract and defer on UNKNOWN, BUSY, or
idle grace; it must not import Corvus internals or access canonical/private data.

Next step: **controlled `/run` provisioning and Lab-only publisher rollout**,
with explicit logical configuration and no-inference acceptance checks. Production
rollout and complete host-wide coverage are prerequisites for eventual Hindsight
admission. This task implements neither rollout nor admission.
