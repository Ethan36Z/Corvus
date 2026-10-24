# Hindsight recovery references — Corvus v1 closeout

This file supersedes the old `/tmp/.../before.json` availability claims in the
historical README and rollout logs. See `recovery-resources.json` for the exact
non-secret container/image references inspected on this host. These are local
resources, **not registry availability guarantees or database backups**.

- The current bounded-consolidation runtime remains healthy, unmodified.
- Both previous containers remain stopped and retained, with their original
  Docker configurations and images. Do not start a retained container alongside
  the current one against shared data volumes.
- `/tmp/corvus-h17e-1/before.json` and
  `/tmp/corvus-h17d-3c-r1/before.json` no longer exist. Historical rollback CLI
  examples that require them must not be run as if they still existed.
- Existing `runtime.py` is the guarded plan/validate/deploy/rollback recipe;
  `build.py`, the combined hash-guarded patch and verification manifests remain
  the software reconstruction source. No Hindsight core redesign is introduced.

## Before a future authorized runtime operation

Use the existing Docker-inspection/private-snapshot workflow documented in
README, with a **persistent, private directory outside Git** (0700 directory,
0600 files). Preserve current and retained-container metadata plus exact image
IDs. Inspect output contains secrets: never print it, commit it, attach it to
an issue or replace missing metadata with guesses. Verify identities, all
mounts, ownership, network/security/resource settings and image availability
against the intended recovery target before constructing a guarded plan.
A current-runtime snapshot is not the missing pre-upgrade snapshot and must not
be passed to the old rollback command as a substitute. Retained containers can
supply their own recipe metadata only after explicit operator review.

Preserve data backups separately using the existing consistent private backup
procedure; source/image recovery does not restore private database contents.
If a required original snapshot, image or validated backup is unavailable, stop
that operation and report the gap. Do not recreate, prune, rename, start or
remove Hindsight containers/volumes merely to close source documentation.

## Reliability limits retained

Original messages and durable retain intent are different persistence stages.
The existing BackgroundTasks -> durable-intent handoff window and absent
automatic startup/timer reconciliation are not repaired here. Existing ledger
reconciliation tools and H1 acceptance cover specific post-intent scenarios,
not every crash window or end-to-end memory integrity. Shared Qwen inference
may wait; no scheduler, preemption or memory routing changes were made.
