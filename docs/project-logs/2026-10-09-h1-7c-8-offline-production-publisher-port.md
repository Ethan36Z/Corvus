# H1.7c-8 — Offline Production publisher port and validation

Date: 2026-10-09

Production baseline: clean `main` at
`f453ed161994c8131bf8d9ed7c43cc15914176cf`.
Lab reference: clean `lab/ow2e-console` at
`21adce7e00b1a1fc0683eb9c568598a0a0cb0966`.
Production was healthy before the offline port.

## Isolation and candidate scope

The candidate is a standalone local clone at
`/tmp/corvus-h17c-8-production`, branch
`integration/h1-7c-8-production-publisher`, created with
`git clone --no-hardlinks --no-checkout` from the live Production repository
and checked out at the exact Production baseline. This is an equivalent isolated
checkout, not a linked worktree: its Git objects, index, and branch refs are
independent. Nothing was committed to or edited in the live Production repository.

New files port the proven Lab foreground tracker and registry core unchanged,
along with their four focused test files. Three existing Production modules have
only these changes:

- `app/conversation_runtime.py`: import the tracker wrapper and wrap only
  `generate_fn(model_messages)` inside `process_turn`.
- `app/playground_api.py`: start publication before startup preparation and close
  it in the API lifespan's `finally` block.
- `app/runtime_config.py`: add the three optional registry environment settings.

The existing Production conversation implementation and API are preserved.
Lab's historical-recall timing fields, Hindsight shadow integration, background
tasks, research, and deployment configuration were not ported. The Production
service unit is unchanged in this candidate. Publication is disabled unless
`CORVUS_FOREGROUND_REGISTRY_DIR` is explicitly set.

## Protocol and failure behavior

`app/foreground_activity.py`, `app/foreground_registry.py`, and the resulting
`app/runtime_config.py` are byte-identical to the sealed Lab reference.
Removing the narrow new hooks from the other two modules produces the exact
original Production source. There is no second registry protocol implementation.

The version-2 registry retains stable lock inodes, PID/start/UUID identity,
logical publisher names, lifetime and health ownership, local count publication,
and completion watermarks. Kernel flock release handles crashes. Missing or
degraded expected publishers yield UNKNOWN; healthy expected publishers without
busy ownership yield IDLE; healthy active publishers yield BUSY. Consumers must
also honor the recovery/idle-grace anchor.

Ordinary initialization and publication failures log and permit foreground
generation and persistence. Completion publication failures preserve replies and
original errors. The local counter still balances concurrent and exceptional
calls. No path, logical slot, or expected-publisher set is enabled by default.

## Offline tests

The existing Production virtualenv supplied installed dependencies, while all
application imports came from the isolated checkout. Tests used temporary data
directories and fake model functions. `HF_HUB_OFFLINE=1` and
`TRANSFORMERS_OFFLINE=1` were set, and a temporary `sitecustomize` guard rejected
network connections in test processes and children. No inference or real bank
operations were performed.

Focused discovery of `test_foreground_*.py`: **81 tests passed**, including the
78 proven Lab tracker/registry/publication tests and three Production checks:

- Disabled publication exactly matches original Production result dictionaries,
  model inputs, persistence/dense events, and exception behavior across success,
  model failure, unexpected failure, assistant persistence failure, and dense failure.
- Production-slot initialization failure preserves a successful reply and both
  persistence calls while the aggregate remains UNKNOWN.
- Actual mixed processes import the sealed Lab reference and isolated Production
  implementation, sharing only a temporary registry. They prove missing peer
  UNKNOWN, healthy IDLE, overlapping BUSY count 2, then 1, then 0, crash UNKNOWN,
  fresh restart identity and recovery, and graceful-stop UNKNOWN.

Focused command used the existing Production Python with `-B -m unittest discover
-s tests -p 'test_foreground_*.py'`, an explicit isolated `PYTHONPATH`, temporary
`CORVUS_DATA_DIR`, and `CORVUS_REFERENCE_LAB_ROOT` for the optional mixed-reference
test. That test skips when the reference path is not supplied.

Ten unchanged Production regression scripts passed: vision conversation, voice
conversation, web conversation, automatic web mode, web mode, web query rewrite
runtime, voice API contract, web API contract, startup schema/lifespan, and TTS API
contract. Each ran separately with a bounded timeout and the offline guard.
`git diff --check` and staged diff checks passed.

## Exact later deployment requirements — not applied

Deploy the reviewed candidate through a separately authorized Production rollout.
Add these environment settings to the canonical Production unit and its installed
counterpart, preserving existing settings:

```ini
Environment=CORVUS_FOREGROUND_REGISTRY_DIR=/run/corvus-foreground
Environment=CORVUS_FOREGROUND_REGISTRY_PUBLISHER=production
Environment=CORVUS_FOREGROUND_REGISTRY_EXPECTED_PUBLISHERS=lab,production
```

The existing Production unit runs as ethan:ethan with `ProtectSystem=full` and
`PrivateTmp=true`; `/run` is writable and visible. No additional sandbox allowance,
bind path, tmpfiles change, or new runtime directory is required for the current
unit. Do not add service-owned `RuntimeDirectory` cleanup.

Installing a changed unit requires `systemctl daemon-reload` and a controlled
restart of **only `corvus-api.service`** for Production activation. Preserve port
8096, data root, model URL, restart policy, and all other existing configuration.
Audit fresh deployment prerequisites and startup recovery before that restart.

After Production publication is verified, the corresponding later Lab unit change
is exactly:

```ini
Environment=CORVUS_FOREGROUND_REGISTRY_EXPECTED_PUBLISHERS=lab,production
```

This replaces Lab's current `lab` value. Loading the changed Lab environment
would require a separately controlled Lab restart after daemon reload; neither
change occurred in this task. Future admission consumers must independently
require both logical slots. Hindsight mounting/admission remains a later task.

## Live-state evidence and limitations

Read-only before/after fingerprints establish unchanged live repository branches,
HEADs, tracked index entries, and clean worktrees; unchanged service PIDs,
invocation/start identities and configuration hashes; unchanged installed units,
tmpfiles entry, registry file contents/inodes/permissions; and unchanged Hindsight,
foreground, and CPU-test container identities/configuration/mounts. Both API
health responses remain OK. Production PID is `5373`; Lab PID is `2705518`.

Evidence and regression logs are retained under `/tmp/corvus-h17c-8-evidence`.
This candidate is offline and not deployed. No service reload/restart, Production
main change, live registry publication, Hindsight change, model request, bank
mutation, download, reboot, or push was performed. Compatibility tests do not
replace a controlled live rollout acceptance check. Existing non-preemption and
untracked-caller limitations remain.

Verdict: **PASS** for offline port and validation; deployment remains separate.
