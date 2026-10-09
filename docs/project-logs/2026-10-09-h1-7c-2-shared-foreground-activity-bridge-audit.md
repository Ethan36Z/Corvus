# H1.7c-2 — Shared foreground activity bridge audit

Date: 2026-10-09

Baseline: `lab/ow2e-console` at `afcebfcaa3564f242cf1d925a8e5ec4fc0510291`

Verdict: **PASS WITH CONSTRAINTS**. The completed read-only audit identifies a
minimal host-local bridge; it does not implement or deploy it. The expected
branch, HEAD, and clean worktree were verified before creating this log.

## Verified deployment boundary

Corvus Lab and Production run on the same Linux host as `ethan:ethan`, under
independently restartable `corvus-lab-api.service` and `corvus-api.service`.
Both use the same `corvus-llama` Qwen3.5-9B process on `127.0.0.1:8095`, with
one 8192-token inference slot. Hindsight also uses that shared model process.

Lab's code root is `/home/ethan/srv/apps/corvus-lab`, with data under
`/home/ethan/srv/data/corvus/lab`. Production's code root is
`/home/ethan/srv/apps/small-vram-companion`, with data under
`/home/ethan/srv/data/corvus/private`. These data roots remain isolated; runtime
activity metadata must not require sharing either canonical database.

The existing `app/foreground_activity.py` tracker is process-local only.
`app/conversation_runtime.py:process_turn` wraps final foreground reply
generation, including exceptions and overlapping requests. Production does
not yet have this tracker or publish activity. A committed tracker is not
evidence that already-running services have loaded it.

No neutral shared runtime directory is currently provisioned. Both API units
use `PrivateTmp`, so their `/tmp` directories are not a common bridge. Lab's
service sandbox currently permits writes only to its own data root; a shared
directory requires an explicit service write allowance. Hindsight currently
has no shared host-runtime bind mount.

## Candidate findings

- **Shared file/runtime registry:** lowest-complexity viable mechanism. It can
  aggregate local foreground counts and retain a host-wide last-finished
  watermark without a daemon or access to user data. A persisted counter alone
  is unsafe after a crash; kernel-owned busy locks must establish liveness.
- **Unix socket/activity daemon:** can represent count and finish time, but
  adds a service, reconnect/resynchronization logic, and uncertainty when the
  aggregator restarts. This complexity is unnecessary for the current host.
- **HTTP status aggregation:** possible with new status publication in both
  deployments, but no existing activity status endpoint supplies this signal.
  Aggregation adds deployment, polling, and container-to-host networking
  concerns; unavailable endpoints must be treated as unknown.
- **Shared SQLite:** unnecessary and inappropriate for runtime activity
  metadata here. Existing databases are isolated. An auxiliary database would
  still need crash/liveness handling and add schema/locking complexity;
  sharing canonical databases would violate the boundary.
- **llama.cpp `/slots`:** reports model occupancy, not reliable caller
  identity. It cannot distinguish Corvus foreground from Hindsight or other
  callers, count queued foreground requests, or provide the Corvus completion
  watermark required for idle grace. It is insufficient alone and may be used
  only as an optional secondary safety check.

## Recommended bridge and crash-safety contract

Use a restricted host-local runtime registry at **`/run/corvus-foreground/`**,
provisioned with existing tmpfiles/service mechanisms. Keep the existing
process-local tracker as the correctness primitive and publish only activity
metadata. Both Corvus deployments need access to the neutral directory;
Hindsight should eventually receive read-only access, without canonical or
private user data.

The bridge must provide:

- Unique process identity records, accounting for PID reuse and host boot
  identity rather than trusting a PID alone.
- Stable per-process lock-file identity and kernel-owned `flock` busy locks
  held whenever local `active_foreground_count > 0`, before a foreground model
  request can begin. Local count publication supports cross-process
  aggregation; lock ownership is authoritative for busy state.
- A host-wide last-finished watermark preserved across independent service
  restarts, with brief registry locking and consistent metadata publication.
- Automatic loss of busy ownership on process crash when all owning file
  descriptors close. Stale positive metadata must never be trusted without
  corresponding lock ownership.
- Publication/read failures represented as **UNKNOWN/DEFER**, never silently
  IDLE. An unsuccessful publication must not leave apparently valid idle state
  that would admit background work.

Never replace or unlink locked inodes, and do not let one service's stop/restart
remove the shared directory or another service's live locks. Atomic metadata
replacement must remain separate from stable lock files. Avoid inherited lock
descriptors: duplicate or fork-inherited descriptors can retain ownership after
the originating process exits. These properties follow Linux's
[open-file-description locking semantics](https://man7.org/linux/man-pages/man2/flock.2.html).

Crash recovery cannot reconstruct the exact finish time of an interrupted
call. Apply one conservative recovery grace period per stale process instance,
not a new grace period on every read. Do not expire a genuinely live long
request merely because a timestamp is old. A client crash or timeout also does
not prove that remote inference has stopped; optional `/slots` observation can
provide a secondary occupancy check.

Validate clock/boot identity assumptions before comparing monotonic timestamps
across processes or containers. The audited API services and Hindsight had a
common boot identity and zero monotonic namespace offsets; that finding must
not become an unchecked assumption in the bridge contract.

## Future Hindsight admission consumer — not implemented

After acquiring its own LLM semaphore and immediately before **each upstream
memory LLM attempt**, Hindsight should independently read the registry using
the published file/lock contract. The audited seam is
`hindsight_api/engine/llm_wrapper.py:_attempt_permits`, after permit acquisition
and before the provider request.

If any foreground busy lock exists, the last foreground completion is inside
idle grace, or registry state is unknown, defer durable background memory work
without consuming retries. Reuse Hindsight's existing durable async operations
and `DeferOperation`; do not introduce a queue framework. Hindsight must not
import Corvus internals or read canonical/private data. Future integration must
preserve deferral through consolidation exception handling and distinguish
worker deferral from synchronous retain behavior.

This read is an admission check, not preemption. Foreground can arrive after a
memory generation has begun; admission alone cannot guarantee zero waiting.
Foreground-triggered cancel/requeue remains **deferred**. The conservative
quiet/maintenance-window policy from
[H1.7b](2026-10-09-h1-7b-foreground-safe-memory-scheduling-audit.md)
remains in force.

## Implementation risks and limits

Production does not yet publish activity; every participating Corvus instance
must adopt the bridge before it can represent host-wide foreground activity.
Independent restart behavior, permission/sandbox failures, stale records,
publication ordering, descriptor inheritance, stable inodes, clock epochs,
and one-time recovery grace require tests without inference. The current
tracker excludes auxiliary model calls, so the bridge will not by itself
represent all shared-model traffic.

The registry introduces no daemon, infrastructure framework, or canonical
memory mutation. It does not change the frozen Qwen3.5-9B memory-model decision,
enable Reflect, or implement scheduling or cancellation.

## Next engineering objective

**Implement and unit-test the shared `/run` foreground activity bridge in
Corvus, including crash recovery and cross-process aggregation, but do NOT
connect it to Hindsight admission yet.**

This sealing task created only this project log. No application code,
Hindsight configuration/source, service configuration, inference, bank state,
running endpoint, or host power state was changed. No push was performed.
