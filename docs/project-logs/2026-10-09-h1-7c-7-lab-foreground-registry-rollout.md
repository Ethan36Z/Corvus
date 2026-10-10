# H1.7c-7 — Controlled Lab-only foreground registry rollout

Date: 2026-10-09

Committed baseline: `lab/ow2e-console` at
`6a33858c03b71ef31bce9e7c905a079dea31a277`. The initial Lab worktree was
clean. Production remained clean on `main` at
`f453ed161994c8131bf8d9ed7c43cc15914176cf` throughout the rollout.

Verdict: **PASS WITH CONSTRAINTS**. Only Lab publishes. This is not yet a
host-wide admission signal protecting Production, and Hindsight remains disconnected.

## Runtime provisioning and Lab configuration

The operator ran the reviewed privileged provisioning helper
`sudo /usr/bin/python3 -B /tmp/corvus-h17c-7/provision.py`. It created
`/etc/tmpfiles.d/corvus-foreground.conf` as root:root, mode `0644`, containing:

```text
d /run/corvus-foreground 0700 ethan ethan - -
```

Targeted `systemd-tmpfiles --create` provisioned `/run/corvus-foreground/`
as ethan:ethan (UID/GID 1000), mode `0700`. The directory was initially absent
and empty after provisioning. Its inode remained `1510542` through restart.
No service-owned `RuntimeDirectory` cleanup was added and no peer lock inode
was replaced or deleted. Boot recreation requires no reboot for this rollout.

The canonical repository unit `deploy/lab/corvus-lab-api.service` and installed
`/etc/systemd/system/corvus-lab-api.service` received exactly these settings:

```ini
Environment=CORVUS_FOREGROUND_REGISTRY_DIR=/run/corvus-foreground
Environment=CORVUS_FOREGROUND_REGISTRY_PUBLISHER=lab
Environment=CORVUS_FOREGROUND_REGISTRY_EXPECTED_PUBLISHERS=lab
ReadWritePaths=/run/corvus-foreground
```

The write allowance permits publication under Lab's `ProtectSystem=strict`.
The service remains ethan:ethan, single-worker, localhost port 18096, with
`Restart=no`. No new network endpoint or application-code change was introduced.
The tmpfiles entry is host-only state; this log records it without inventing a
canonical repository deployment file for `/etc`.

## Validation pause, dense watermark audit, and restart

Provisioning and unit installation completed before daemon reload. The rollout
then paused because the existing read-only dense readiness validator required
progress equal to the canonical maximum: progress was 10, maximum was 12.

H1.7c-7a inspected immutable/read-only SQLite and the real dense classifier.
IDs 11/12 were the successful H1.5b conversation turn, already CURRENT with
matching hashes, pinned model/revision/dimension/schema, and provenance metadata.
All 12 canonical messages had matching dense rows. `process_turn` indexes its
turn directly without advancing the tail-worker cursor; this was benign
bookkeeping lag rather than an index inconsistency. Startup skips CURRENT rows
before embedding-model loading and advances only operational progress.
The audit recommended SAFE_TO_RESUME; no cursor repair was performed manually.

The operator subsequently ran the reviewed
`sudo /usr/bin/python3 -B /tmp/corvus-h17c-7/restart-lab.py` and confirmed completion.
The helper revalidated unit syntax, installed configuration, runtime permissions
and directory identity, unchanged Production unit/process, and an idle model slot.
It performed `systemctl daemon-reload` and restarted only
`corvus-lab-api.service`. Lab PID changed from `2921247` to `2705518`, with a
fresh invocation/start identity. No other service or model endpoint was restarted.

## Actual publisher and acceptance results

Read-only live acceptance verified:

- Publisher identity: `2705518-51688217-fa14a7f9548c4b41a9e34476938e6281`,
  logical slot `lab`, PID `2705518`, start ticks `51688217`.
- Kernel lifetime and health locks are owned; busy and fault locks are unowned.
- Published active count is 0; last-finished is null because no foreground
  completion was submitted during acceptance.
- Expected set `lab` returns trustworthy **IDLE**, count 0. Expected set
  `lab,production` returns **UNKNOWN** because Production is not publishing.
  Consumers must still honor the registry observation/idle-grace anchor.
- Registry header, guard, publisher metadata, and four lock files are regular
  ethan:ethan files with mode `0600`; the directory remains `0700`.
- Strict metadata contains only runtime identity, counts, timestamps, and inode
  identities, with no conversation content or private user data.
- Lab `/api/health` reports OK. Startup recovery reports one batch, `indexed=0`,
  progress 12, caught up true. The post-restart read-only readiness check passes:
  12 canonical messages, 12 dense rows, progress 12. No embeddings were required.
- Production stays healthy with PID `5373` and the same invocation, configuration,
  unit-file hashes, clean repository HEAD, and private data root. Its process has
  no registry settings and no Production publisher record exists.
- `:8095` remains healthy and idle, with the same container identity/configuration
  and task ID `5099`. Both `:8106` and `:8107` container fingerprints are unchanged.
- Hindsight's container/configuration/mount fingerprints are unchanged. No registry
  bind mount exists and `/run/corvus-foreground` is absent inside the container.

No completion, retain, consolidation, Reflect, or bank mutation was executed.
No intentional runtime fault or fake foreground activity was injected into Lab.
The existing offline tests establish foreground fail-open behavior and UNKNOWN
for missing, degraded, malformed, or untrustworthy expected publishers; future
background consumers must defer on UNKNOWN. Hindsight does not consume this signal.

## Tests and unit checks

- Foreground tracker/registry/publisher suite: 78 tests passed using
  `.venv/bin/python -B -m unittest discover -s tests -p 'test_foreground_*.py'`.
- Lab deployment/reboot acceptance suite: 28 tests passed using bounded offline
  `test_lab_reboot_checks.py` discovery, temporary stores, and fake embeddings.
- Root `systemd-analyze verify` passed for the candidate and installed Lab unit
  before activation. Installed unit/config values and actual process environment
  match the canonical deployment settings.
- Post-restart live publisher acceptance and peer fingerprint comparison passed.
- Post-restart `deploy/lab/check_dense_readiness.py` passed read-only.
- `git diff --check` passed before committing only the Lab unit and this log.

Initial sandboxed LanceDB validation stalled; only those audit/test processes
were terminated. Bounded validation outside the sandbox produced the results
above, with no service or data repair.

## Rollback and next step

The original installed unit is preserved at
`/tmp/corvus-h17c-7/lab-unit.before`; the baseline Git commit also contains it.
To disable publication, restore the original unit as root:root `0644` to
`/etc/systemd/system/corvus-lab-api.service`, then perform an authorized
daemon reload and Lab-only restart. Reconcile the canonical repository unit
with the rollback. Preserve the shared directory, watermark, and lock files;
never delete or replace peer lock inodes. Removing expected Lab liveness must
remain UNKNOWN to readers requiring Lab.

Next step: confirm Lab stability, then perform a separately controlled Production
publisher rollout and cross-process acceptance. Only after both publishers are
verified should a read-only Hindsight mount and admission consumer be considered.
Already-running memory calls remain non-preemptible.
