# H1.7c-3 — Shared foreground registry core

Date: 2026-10-09

Baseline: `lab/ow2e-console` at `17c7e1221cccc0685faca964f9479a714dca2ba0`

Verdict: **PASS** for the independently tested registry core. The expected
branch, HEAD, and clean worktree were verified before editing. This implements
the primitive selected in
[H1.7c-2](2026-10-09-h1-7c-2-shared-foreground-activity-bridge-audit.md),
without deployment or admission integration.

## API and integration boundary

`app/foreground_registry.py` provides `ForegroundRegistry(path)`, explicit
`initialize()`, read-only `read()`, and `ForegroundPublisher(registry)`.
There is no default path, environment activation, import from the conversation
runtime, or automatic directory creation. Initialization requires an existing
directory and refuses to initialize unrelated/nonempty state.

`ForegroundPublisher.publish(active_foreground_count,
last_foreground_finished_at)` accepts the process-local tracker's state.
Publisher operations are thread-safe, but a future wrapper must serialize the
local transition, snapshot, and publication together so old snapshots cannot
overtake newer ones. Successful publication must precede the model request;
failure must prevent that request. Publisher lifetime is explicit, with
`close()` or context-manager cleanup.

`app/foreground_activity.py` and its instrumentation seam are unchanged. The
registry is not wired into them in this step; no running service behavior
changes. Tests demonstrate local tracker snapshots including overlapping
counts, without adding a second local counting implementation.

## Registry data model

- `registry.lock`: stable registry serialization inode.
- `registry.json`: version 1 header with host boot ID, monotonic time-namespace
  offsets, and registry lock device/inode identity.
- Each publisher has a lifetime identity comprising PID, Linux process start
  ticks, and a random UUID. Independent restart creates a new identity.
- `<identity>.json`: identity, PID/start ticks, local active count, last-finished
  monotonic timestamp, and both publisher lock device/inode identities.
- `<identity>.busy`: stable kernel-owned busy lock.
- `<identity>.fault`: stable kernel-owned publication-failure lock. It allows
  readers to see UNKNOWN even when metadata cannot be written.

Completed publisher records remain, preserving the maximum valid
last-finished timestamp across independent restarts. Stale positive counts
without busy ownership are excluded from the aggregate. There is no PID-only
liveness check or timestamp lease that could expire a live long request.

`RegistrySnapshot` is immutable and exposes state, trustworthy aggregate count,
latest valid finish timestamp, recovery-grace timestamp, and an UNKNOWN reason.
`idle_grace_anchor` is the maximum of the normal finish and recovery timestamps.
No idle-grace policy or scheduler is implemented.

## Locking and publication semantics

Readers hold a shared registry flock while validating metadata and probing
publisher lock ownership. Reads do not write files or create lock files; they
return UNKNOWN immediately on registry lock contention. Writers hold an
exclusive registry flock briefly, with a one-second bounded acquisition wait.
The per-publisher mutex serializes its own updates and close operations.

On transition from zero to positive count, the publisher acquires its exclusive
busy flock before committing metadata. It holds ownership through overlapping
local calls. On return to zero, it commits the finish timestamp and zero count
before releasing busy ownership. Metadata uses temporary-file write/flush/fsync
and atomic replacement; lock files are never replaced or deleted by the core.
Decreasing count requires a finish timestamp, and timestamps cannot regress or
be in the future relative to the supplied clock.

Directory-relative opens reject symlinks and nonregular files. Reads validate
header/record shape, integer counts/identities, finite timestamps, duplicate JSON
keys, lock identities, and clock domain. Metadata is limited to 64 KiB per file.
Unexpected files or partial publisher records are not treated as idle.

## Crash and failure behavior

Linux releases busy ownership when its owning descriptors close on process
exit/crash. Stale positive metadata therefore cannot keep the registry BUSY.
The reader records the first observation of each such publisher as one
recovery-grace timestamp, without changing the persisted files. Repeated reads
do not restart grace. A reader restart conservatively starts a new grace for
still-present stale positive records; the exact crashed-call finish time is
unavailable.

Descriptors use close-on-exec. Registered at-fork cleanup closes all inherited
registry descriptors, including transient serialization descriptors, in the
child without unlocking the parent's open-file descriptions. Inherited
publishers cannot be reused; inherited registry reads return UNKNOWN before
touching inherited thread mutexes. Child processes must create their own
registry instances and publishers.
Stable directory and lock identities must be preserved by future provisioning.

Malformed, unreadable, missing, mismatched, or inconsistent state returns
**UNKNOWN**, with no claimed aggregate count. UNKNOWN takes precedence even
when another publisher is valid and busy. An initialized, consistent empty
registry is IDLE; an uninitialized or missing directory is UNKNOWN.

A publication exception poisons that publisher and acquires its fault flock;
readers return UNKNOWN until ownership closes. Failed publishers cannot resume
publishing. Closing an active/failed publisher preserves its record and invokes
the same stale-record recovery behavior as a crash. No model call is permitted
after failed initial publication. Interrupted registration or abandoned
temporary metadata remains UNKNOWN and requires deliberate repair; this core
does not guess, erase suspicious state, or implement registry housekeeping.

## Offline validation

`.venv/bin/python -B -m unittest discover -s tests -p 'test_foreground_*.py' -v`:
**40 tests passed**: 30 new registry tests and 10 existing local tracker and
foreground conversation tests.

Registry coverage includes initialized empty/idle state; active state; two real
publisher subprocesses and independent completion; concurrent publication and
reading; overlapping local counts; watermark advancement; busy-process kill;
stale metadata and one-time grace; independent restart; another live publisher
surviving a peer crash; malformed/duplicate/oversized/deep JSON; unreadable
files/directories; nonregular files and symlinks; missing/orphaned files; inode
replacement; clock mismatch; lock contention; publication/registration failure;
and live fork/exec descendants that cannot retain busy or serialization locks.
Permission tests include real inaccessible temporary files/directories.

An additional focused run checked descriptor cleanup after all registry tests:
**30 passed; zero registry-owned descriptors remained**.

**Nine existing conversation/model regression scripts passed**, with fake model
calls and offline model-download flags: `test_personality_runtime.py`,
`test_vision_conversation_runtime.py`, `test_voice_conversation_runtime.py`,
`test_web_conversation_runtime.py`, `test_web_mode_runtime.py`,
`test_web_auto_runtime.py`, `test_web_query_rewrite_runtime.py`,
`test_web_intent_gate.py`, and `test_web_query_rewrite.py`.

All registry tests use temporary directories and disposable test processes.
No real model inference, endpoint access, or `/run` access is required.
`git diff --check` and staged whitespace checks passed.

## Limits and next step

**Not deployed:** `/run/corvus-foreground/` was not created. Production is not
publishing, and Hindsight is not reading the registry. No systemd/tmpfiles,
Production repository, Hindsight configuration/source, bank state, or running
endpoint was changed. No services were restarted, no model inference was run,
and no push or host power operation occurred.

Future integration must enforce publication ordering/failure handling, validate
directory permissions and local Linux filesystem/clock assumptions, and cover
all participating processes. Auxiliary model calls remain outside the existing
foreground tracker. Registry admission will not preempt already-running memory
generation or eliminate the foreground-arrival race.

Next step: **deployment/provisioning audit and controlled Lab+Production
publisher rollout**. Hindsight admission remains disconnected.
