# H1.7d-2f-1 — Controlled Lab async-retain enablement

Date: 2026-10-10

Verdict: **PASS — armed, not exercised.** Durable async retain is enabled only
in Lab. No chat turn, retain submission, inference, operation-status reconciliation,
consolidation, or Reflect was initiated by this rollout.

## Baseline and before state

Read-only preflight verified clean repositories:

- Lab: `lab/ow2e-console`, `33f448da9057bdf781d1670b005b0527f347b05a`.
- Production: `main`, `c315d0e767e31fde3c82ba4dfb08659a268c267a`.
- Lab API, Production API, Hindsight, and the shared `:8095` model were healthy.
- Both foreground publishers held live/health locks, with count zero and no
  busy/fault ownership. The explicit `lab,production` aggregate was trustworthy
  `IDLE`.
- Lab PID: `2705518`; async-retain flag: **UNSET** in both the loaded unit and
  running process. The existing synchronous `async:false` path was active.
- Bank `corvus-hindsight-lab-v1`: **7 documents, 7 live memories**.
- `/home/ethan/srv/data/corvus/lab/h1-shadow-recall.jsonl`: **5 records**, comprising
  3 legacy comparison records and 2 retain outcomes; **0 retain intents**.
- Ledger SHA-256:
  `c13caf332304fe4556c709afe8bdff21ebba589d3dfd7d2d5803daabc705ccbb`.
- Dense readiness: 12 canonical messages, 12 current indexed rows, progress 12.
  Source inspection established that caught-up startup requires no embeddings.

Counts used read-only document/memory listing totals, avoiding the bank statistics
endpoint's cache-write behavior. Raw health metrics were captured; per-request
`db_acquire_ms` was excluded from equality checks because it is timing telemetry,
not configuration or runtime identity.

## Exact deployment change and restart

The sole unit change in `deploy/lab/corvus-lab-api.service` and its installed
`/etc/systemd/system/corvus-lab-api.service` representation is:

```ini
Environment=CORVUS_HINDSIGHT_ASYNC_RETAIN_ENABLED=true
```

All other Lab environment values, registry settings, bank/model endpoints, data
paths, sandbox permissions, and reconciliation scheduling remain unchanged.
In particular, Lab's configured expected publisher set remains `lab`; acceptance
independently reads the host-wide `lab,production` set.

The operator ran the reviewed helper:

```sh
sudo /usr/bin/python3 -B /tmp/corvus-h17d-2f-1/enable-lab.py
```

It revalidated the saved baseline, checked the exact one-line unit delta, installed
only the Lab unit, validated syntax, reloaded systemd, and rechecked prerequisites
before restarting **only `corvus-lab-api.service`**. Read-only application/dense
checks ran as `ethan`, not root. No registry provisioning or permission changes
were performed.

Installation: `2026-10-10T21:09:45.995630+00:00`.
Restart began: `2026-10-10T21:09:52.686667+00:00`.
Installed unit SHA-256:
`6565bebbf5588dd6cc159cd950be92a49e336895067354dc1e897b36df0f7533`.

## After-state acceptance

The helper's acceptance passed; an independent read-only acceptance repeated at
`2026-10-10T21:23:52.677058+00:00` also passed:

- Lab active/healthy, fresh PID **13671**, invocation
  `21875b6f7c374303936c983cd5f8b230`; no pending daemon reload.
- Loaded unit and actual `/proc/13671/environ` both report the flag **true**.
  The pinned configuration parser interprets this as enabled.
- Fresh Lab publisher:
  `13671-58313499-4cf4fe938e944e93ba869771a3d8a6f2`.
  Live/health locks owned; busy/fault locks free; active count **0**.
- Production publisher remains
  `2831871-52241404-4b3a398908e446aa914f8f1469f83d1e`, healthy/idle.
  Host-wide `lab,production` aggregate remains trustworthy **IDLE**, count **0**.
- Registry permissions remain directory `0700`, files `0600`, `ethan:ethan`.
  Existing directory/lock inodes and peer records were preserved. Metadata contains
  only protocol identity/activity fields, no conversation or private user data.
- Bank remains **7 documents / 7 memories**. Ledger remains **5 records / 0 intents**,
  with the identical whole-file hash. No non-retain startup records were appended.
- Lab startup dense recovery reports `OK`, caught up, **0 batches / 0 indexed**,
  progress 12. Lab canonical SQLite hash remains identical.
- Production PID **2831871**, invocation, environment, unit, clean repository,
  canonical/private state and dense files remain unchanged.
- `:8095` remains healthy with unchanged container/configuration identity and exact
  slot state, including task ID **5099**. `:8106` and `:8107` retain their container
  identities and configuration; neither was restarted.
- Hindsight remains healthy, with identical container/image/environment/network/
  mount/start identity. It remains disconnected from the foreground registry.

No async retain request occurred: the enforced pre-POST intent durability invariant
and unchanged zero-intent ledger show the submission path was not entered. Bank
counts, retain audit total (0), LLM trace total (0), and model slot state also remain
unchanged; the zero audit/trace totals are supporting observations, not standalone
proof. No chat/completion or retain endpoint was called by the helper or acceptance.
No Corvus operation-status GET or automatic retain reconciliation occurred: startup
has no reconciliation hook, as confirmed by source and integration tests. The
explicit passive reconciliation callable remains unscheduled.

## Validation and rollback

- Lab deployment/readiness regressions: **28 tests passed**.
- Feature-flagged async-retain integration: **18 tests passed**; fake HTTP/model
  behavior and temporary persistence only.
- Candidate and installed unit syntax validation: **PASS**. Non-root verification
  printed an unrelated inaccessible demo-timer warning and returned success;
  the operator's privileged validation also passed.
- Reviewed helper syntax, exact unit delta, read-only preflight, post-restart
  acceptance, and `git diff --check`: **PASS**.
- Initial sandboxed tests stalled and were terminated; the bounded offline reruns
  passed. No service process was signalled by that test cleanup.

The synchronous path remains available. For an exact host rollback, restore the
saved original unit (which unsets the flag), reload systemd, and restart only Lab:

```sh
sudo install -o root -g root -m 0644 /tmp/corvus-h17d-2f-1/lab-unit.before /etc/systemd/system/corvus-lab-api.service
sudo systemctl daemon-reload
sudo systemctl restart corvus-lab-api.service
```

Alternatively, set the flag to `false` in the Lab unit, validate/reload it, then
restart only Lab. Synchronize the repository unit with the chosen rollback setting.
The original unit is also preserved in the starting Lab commit. Rollback was not
performed. No Production/Hindsight/model service restart, bank mutation, reboot,
or push was performed.

Next step: **one controlled real Lab turn exercising durable async retain**.
This rollout proves configuration and isolation only, not real async-retain
acceptance, extraction quality, or consolidation completion.
