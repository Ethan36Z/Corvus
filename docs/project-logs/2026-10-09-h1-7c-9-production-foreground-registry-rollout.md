# H1.7c-9 — Controlled Production foreground registry publisher rollout

Date: 2026-10-09

Verdict: **PASS** for Production publisher deployment and no-inference acceptance.
Hindsight remains disconnected; Lab's expected-publisher configuration remains
`lab` as required by this task. No memory admission or scheduling was enabled.

## Verified baselines and exact code deployment

Production began clean on `main` at
`f453ed161994c8131bf8d9ed7c43cc15914176cf`. Lab remained clean at
`21adce7e00b1a1fc0683eb9c568598a0a0cb0966`, with its live, healthy, idle publisher.
The offline candidate checkout `/tmp/corvus-h17c-8-production` was clean at
`f2408963881624c6e52c43d266438772beae5020`, with the exact Production baseline
as parent. Both APIs and `:8095` were healthy; the runtime registry and peer
fingerprints matched the sealed Lab-only state.

Rollback reference `rollback/h1-7c-9-production` preserves the original Production
HEAD. The reviewed commit was fetched locally and installed with a fast-forward
merge onto Production `main`. Before deployment configuration edits, HEAD was
exactly the candidate and its tree matched
`642709d80e3a868db7ee05de1e981f91426b9fad`. No publisher code was reimplemented
or changed. The patch contained only the validated tracker/core/integration,
focused tests, and offline validation log; unrelated Lab/Hindsight changes were
excluded. Publication remained disabled in the old running Production process.

## Production service configuration

The canonical `deploy/systemd/corvus-api.service` and installed
`/etc/systemd/system/corvus-api.service` received exactly three added lines:

```ini
Environment=CORVUS_FOREGROUND_REGISTRY_DIR=/run/corvus-foreground
Environment=CORVUS_FOREGROUND_REGISTRY_PUBLISHER=production
Environment=CORVUS_FOREGROUND_REGISTRY_EXPECTED_PUBLISHERS=lab,production
```

All existing settings remain intact: ethan:ethan, port 8096, Production private
data root, model URL `http://127.0.0.1:8095`, `ProtectSystem=full`, `PrivateTmp`,
and restart-on-failure behavior. The existing sandbox permits `/run` publication;
no `ReadWritePaths`, bind path, tmpfiles change, or `RuntimeDirectory` cleanup was
added. Installed unit ownership/mode is root:root `0644`.

The neutral registry remains ethan:ethan `0700`, with regular ethan:ethan `0600`
files. Its directory inode and all existing Lab/header/guard file identities and
contents were preserved. No shared lock inode was replaced or deleted.

## Preflight and privileged activation

Read-only preflight verified the reviewed committed tree, the isolated three-line
unit diff, exact imported configuration values, runtime permissions, healthy idle
Lab, unchanged private data, unchanged peer containers, and disconnected Hindsight.
Production's canonical maximum and operational dense cursor were both 283. The
real classifier reported all 283 IDs CURRENT with embedding loading explicitly
forbidden and SQLite opened immutable/read-only. Startup had no tail work.

The validated H1.7c-8 candidate passed 81 focused tracker/registry/publication tests
and ten Production conversation/runtime/API regression scripts offline. The exact
deployed code preserves those results. Configuration import and helper syntax
checks passed, as did `git diff --check` and staged diff checks. Non-root unit
verification returned success with an unrelated protected timer read warning;
the privileged helper verified the candidate and installed unit before activation.

Noninteractive sudo required a password, so activation paused without changing
the installed unit or service. The operator subsequently ran the reviewed command:

```sh
sudo /usr/bin/python3 -B /tmp/corvus-h17c-9/rollout.py
```

The helper repeated preflight, installed only the Production unit, verified it,
performed the required daemon reload, and restarted only `corvus-api.service`.
It then ran read-only post-restart acceptance. No restart was retried. Lab,
Hindsight, `:8095`, `:8106`, and `:8107` were not restarted; no reboot occurred.

## Actual post-restart acceptance

- Production PID changed from `5373` to `2831871`, start ticks `52241404`,
  invocation `04a5bc114d2a49aaa7af7bb5e5d94acb`.
- Production publisher identity:
  `2831871-52241404-4b3a398908e446aa914f8f1469f83d1e`, logical slot `production`.
- Lab retains PID `2705518` and publisher identity
  `2705518-51688217-fa14a7f9548c4b41a9e34476938e6281`.
- Each publisher has independent stable busy/fault/live/health lock inodes.
  Lifetime and health locks are owned; busy and fault locks are unowned.
  Both local counts are 0. Metadata PID/start identities match the actual services.
- Expected set `lab,production` returns trustworthy **IDLE**, aggregate count 0.
  No foreground completion was submitted, so both last-finished values remain null;
  future consumers must still honor the observation/recovery idle-grace anchor.
- Strict metadata fields contain only process identity, logical slot, counts,
  timestamps, and inode identities; no private conversation or user content appears.
- Production and Lab APIs are healthy. Production startup reports zero recovery
  batches, zero indexed messages, progress 283, and caught up true.
- Production private database hash, canonical-table hashes, and dense file
  identity/size/mtime fingerprints are unchanged.
- Lab's unit hash, environment/configuration, PID/invocation/start identity,
  health response, publisher state, and existing registry files are unchanged.
  Its expected set is still `lab`; no Lab reload or restart was performed.
- `:8095` is healthy with unchanged slot state and container/configuration identity.
  Both CPU test endpoints' container fingerprints remain unchanged.
- Hindsight's container, configuration, and mounts are unchanged. There is no
  registry mount, and `/run/corvus-foreground` is absent inside the container.

Independent acceptance reproduced the operator's result exactly. Its first run
passed the checks but could not overwrite the operator's root-owned output file;
the same checks then saved a separate user-owned `after-verified.json`, leaving
the original record unchanged. Evidence, original unit, reviewed helpers, and
before/after fingerprints are retained under `/tmp/corvus-h17c-9`.

No model completion, embedding inference, retain, consolidation, Reflect, bank
mutation, intentional live fault, service crash test, model download, or push was
performed. Existing offline tests prove missing/degraded expected-publisher
UNKNOWN, foreground fail-open publication failures, crash lock release, and
rejection of stale liveness; those failures were not injected into live services.

## Rollback readiness and next step

The original unit is saved at `/tmp/corvus-h17c-9/production-unit.before`, and
the original code commit remains reachable through the rollback reference.
`/tmp/corvus-h17c-9/rollback.py` is a reviewed, unexecuted operator helper that
restores only the original installed Production unit, reloads systemd, and restarts
only Production. This disables publication while retaining compatible candidate
code. Reconcile the canonical repository unit with any actual rollback afterward.
Never remove the shared directory or another publisher's lock files. Readers
requiring Production correctly become UNKNOWN if its live ownership disappears.
Any full code rollback requires a separately reviewed Git operation using the
preserved baseline; no destructive reset is part of this rollout.

Next step: separately transition Lab's expected set to `lab,production` and verify
the shared contract. Hindsight read-only mounting/admission remains a later task.
Already-running memory inference still cannot be preempted by this registry.
