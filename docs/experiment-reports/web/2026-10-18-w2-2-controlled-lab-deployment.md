# W2.2 — Controlled Lab Web MVP activation attempt and rollback

Date: **2026-10-18** (operator timezone; backup timestamps are UTC 2026-10-19).

Verdict: **W2_2_BLOCKED_ROLLED_BACK**

**The source-first MVP is not active.** Preflight, protected backups and offline regressions passed. The reviewed code was briefly promoted and the existing Lab Pipe was updated successfully. Activation then stopped because the privileged helper could not start: `sudo -n` returned **“a password is required.”** No systemd feature override was created, no API restart occurred, and the backend flag was never enabled. The original Pipe/valves and exact Lab Git baseline were restored in the reviewed order.

The native-search decision remains unchanged: adopt W2.1 for a future controlled Lab activation; do not continue native-search experiments or build an egress broker. This checkpoint is a failed activation with verified rollback, not successful deployment or browser acceptance.

## A. Baseline and reviewed scope

Read the complete published [W2.1 integration](2026-10-18-w2-1-web-mvp-integration.md), [OW-N1](2026-10-18-ow-n1-native-search-validation.md) and [OW-N1.1](2026-10-18-ow-n1-1-native-rag-answer-test.md) reports and the integration branch's deployment/rollback document.

- Lab started clean on `lab/ow2e-console`, HEAD `975645963291ec992d64df0474a3ee9d0ba33dcd`.
- Local integration branch `integration/w2-web-mvp` was clean at `50a63850f83506724aaff4c2af4f50811d00d646`.
- Exact integration ancestry was verified: baseline → `9b374cf2ef46ea08399b124e0c2a725d96c92a38` (W2) → `50a63850f83506724aaff4c2af4f50811d00d646` (W2.1). W2's tree matched original prototype commit `01dd02e1aa826d49bd628891641892f3450b698f` without a content difference.
- The two reviewed commits change fourteen files. No additional source changes, new merge commit or repeated cherry-pick were introduced.
- Reporting branch `reports/web-validation` started clean at `524b41464e83ed5cd182b3e6c3e2ac1d2675db49`.

The active Lab service unit matched its tracked deployment file. The API used the Lab checkout/virtual environment, Lab-only data directory and loopback port 18096. The model endpoint remained the existing loopback service on port 8095. The foreground registry's existing read-only lock-aware reader reported IDLE with zero active turns.

An initial count of publisher JSON files included a stale prior-process record. The actual registry reader distinguishes stale records using ownership locks and confirmed one healthy expected Lab publisher; no registry records were removed or rewritten by this preflight.

The installed `corvus_pipe` source hash exactly matched the starting Lab source. Its existing installation ID was present, endpoint was Lab-only, timeout 300 seconds, `ARENA_ENABLED=true`, and `WEB_MODE=off`. Owner, active/non-global flags and instance identity were recorded privately for preservation checks. No private chat records were queried.

Lab WebUI and the shared model reported healthy in Docker. Lab and Production API health returned HTTP 200/status OK before mutation. Native search was disabled through `ENABLE_WEB_SEARCH=false` and `ENABLE_PERSISTENT_CONFIG=false`; the selected database search-enable field was null. The running image remained `corvus-open-webui:0.6.5-arena-ui2.1-https-r03b` with its original persistent volume.

## B. Protected backups and recovery boundaries

Verified recovery set: **`<protected-Lab-backup-root>/w2-2-20261019T042442Z/`**. The exact local path is retained in the private deployment evidence and operator handoff. Parent/set directory mode 0700; recovery files and manifest mode 0600. Nothing in that recovery set is committed or published.

The set contains eleven recovery files plus a checksum manifest:

- Online SQLite snapshots of WebUI, its existing Chroma database and canonical Lab SQLite.
- A non-database WebUI volume archive, with the live databases/WAL/SHM excluded and consistent snapshots kept separately.
- Original Function row/source/valves, including identity and owner needed for scoped restoration.
- Copies of the Lab shadow-recall and Arena append logs, without inspecting their records.
- Protected existing WebUI environment/signing configuration, original Lab API service unit, baseline Git identifier and a baseline code archive.

Validation observations:

| Check | Result |
| --- | --- |
| WebUI SQLite backup `integrity_check` | `ok` |
| Chroma SQLite backup `integrity_check` | `ok` |
| Canonical SQLite backup `integrity_check` | `ok` |
| Non-database volume archive | 37 regular files; 241,142,554 logical bytes fully read for validation |
| Internal archive links | 15; all resolved to regular files inside the archive |
| Live non-database volume metadata during export | Stable |
| Original Pipe source/valves against preflight | Matched |
| Protected manifest checksums | All verified before mutation and before Function maintenance |
| Disk space after backup | 527,019,986,944 bytes available |

No service was paused for backup. SQLite's online backup interface provided each database's consistent snapshot; the copies are not claimed as one cross-database atomic transaction. No new chat was submitted, and foreground idleness was checked. These are recovery checkpoints, not authorization to overwrite later user data.

Two preliminary backup guards stopped: the first detected the additional Chroma SQLite file; the second rejected archive links pending review. Metadata comparison showed the Chroma path/size and all fifteen internal links already existed in the prior protected R0.5b backup. The final method explicitly snapshots both WebUI databases and validates internal link targets. The earlier incomplete directories were retained and are not labeled verified recovery sets. No unsafe external link was followed.

**Routine rollback must not restore whole databases.** Disable the backend feature first, restore only the Function/valves and code as necessary, and retain all canonical turns, volumes, secrets and later user data. Whole-database/archive restoration is reserved for a separately reviewed recovery incident.

## C. Operations performed and exact failure

1. Created/verified backups and ran the reviewed guarded offline tests before promotion.
2. Verified the supported local Function admin API. Maintenance used 120-second authorization tokens constructed only in memory from the existing Lab signing material and existing administrator identity. Tokens, keys, account identifiers and private values were never printed or published; no user, persistent API key, stored credential or authentication configuration was created/changed.
3. Fast-forwarded only the Lab branch to the exact integration tip. No code branch was pushed.
4. Updated the existing Lab Function through Open WebUI's native update handler, which refreshes its loaded Function cache. A database-only patch was deliberately avoided because it could leave the cached old module running.
5. Set the supported existing valve `WEB_MODE` to `auto`. Enum support was checked in source and the loaded valve schema. The API endpoint, instance ID, owner, original creation time, active/global flags, Arena setting and timeout were preserved. All other valve values matched their backup.
6. Attempted to execute the narrowly scoped privileged helper that would create `corvus-lab-api.service.d/60-web-mvp.conf`, set only `CORVUS_WEB_MVP_ENABLED=TRUE`, reload manager metadata and restart only Lab API.
7. `sudo -n` exited before the helper ran because an operator password was required. The helper's pending/complete markers were absent, no drop-in existed, and the original Lab API PID was still active. The feature flag was confirmed absent from its environment.

The command tool had authorized the requested operation; the failure was the host's actual sudo authentication requirement, not an automatic approval-review rejection. No alternative privileged mechanism or broader permission change was attempted.

**Preflight omission:** noninteractive root availability should have been checked before code/Function promotion. The runtime/source preflight did not establish that OS privilege, so this attempt unnecessarily reached a partial activation before rollback. Future resumption must establish approved execution of the exact privileged service action first, without collecting an operator password in an experiment artifact.

There was no uncertain mutating request or automatic retry. Function update/valve writes returned success and were checked. The failed privileged command definitively never ran its helper. Health GETs and read-only reconciliation were separate from chat operations.

## D. Rollback performed and verified final configuration

Rollback followed the reviewed boundary:

1. Verified the backend remained feature-off, its original PID was unchanged and no drop-in existed. No service restart was needed to disable a flag that was never enabled.
2. Restored the exact original Pipe source and valves through the same native cache-refreshing admin handler. The original source hash and owner/identity/flags/valves were verified.
3. Returned only the clean Lab checkout to `975645963291ec992d64df0474a3ee9d0ba33dcd` using `git reset --keep`. The reviewed integration branch remains intact at `50a63850f83506724aaff4c2af4f50811d00d646`. No canonical data, untracked user files, volume or credential was deleted/restored.
4. Repeated health/configuration checks and compared the private baseline fingerprints and runtime metadata.

| Final active item | Observed state |
| --- | --- |
| Lab Git branch / HEAD | `lab/ow2e-console` / `975645963291ec992d64df0474a3ee9d0ba33dcd`; clean |
| W2.1 code availability | Preserved on local integration branch; unpushed; not active |
| `CORVUS_WEB_MVP_ENABLED` | Unset in the unchanged running API; MVP not enabled |
| Lab-only systemd feature drop-in | Not created |
| API service | Original process still running; loopback port 18096 |
| Existing Function | `corvus_pipe`, original source restored and loaded cache refreshed |
| Pipe backend | `http://127.0.0.1:18096/api/chat` |
| `WEB_MODE` | **`off`**, restored |
| Timeout / Arena | 300 seconds / enabled, unchanged |
| Instance identity / owner / installation flags | Preserved |
| Corvus discovery provider | Existing default DDGS; no provider override/switch |
| Native Open WebUI search | Disabled; persistent config remains disabled |
| WebUI image / persistent volume | Existing 0.6.5 HTTPS UI-2.1 image and original volume retained |

The installed Function's update timestamp and administrator last-active metadata were naturally touched by native admin operations. The WebUI database is therefore **not claimed byte-identical** to preflight. Credentials, conversation contents and ownership were not rewritten, and the full database was not restored to undo those maintenance timestamps.

## E. Offline tests and health/configuration evidence

The unchanged integration branch's existing offline driver ran:

```text
test_web_acceptance.py
test_web_mvp.py
```

Final guarded result: **60 passed, zero failed, one explicitly skipped** (61 discovered methods). This is 19 evidence-acceptance tests plus 41 passing MVP/inherited Pipe tests. The skipped existing fresh-subprocess test is excluded from passes because the driver prohibits subprocesses.

The first command-sandbox run passed the evidence suite and reached the existing ASGI-boundary test, then exited at the driver's 30-second deadline with the previously documented thread-wakeup stall. It is not counted as a passing complete run. The same unchanged guarded driver passed outside that sandbox, retaining denied network/private-data access, synthetic-only test SQLite, disabled Hindsight and forbidden embedding construction. It reported no network/private-access violations. There was no retry of a live chat or provider request.

Coverage includes all three MVP outcomes; provider-failure/empty distinction; partial-source limitations; version/date rejection; bounded candidate continuation; unique references and exact provenance; model-link/citation filtering; normal-chat compatibility; canonical ordering/one pair in synthetic fixtures; no automatic retries; and inherited Pipe endpoint/auth/session/Arena boundaries. No additional 19-script regression pass is claimed for this deployment attempt; those earlier results remain historical W2.1 evidence.

Post-rollback:

- Lab API, Production API and Lab WebUI health requests returned HTTP 200; API status/model status were OK.
- Both monitored API PIDs were unchanged. **No API service was restarted**, including Lab.
- All ten monitored containers retained their original start times and remained running: Lab WebUI, Lab FoxGate Gateway/Auth, Production/Demo frontends, Private/Demo gateways, shared Qwen, Lab Hindsight and SearXNG. Containers with configured health checks reported healthy. No health status was invented for containers without one.
- Canonical `corvus.db`, local shadow-recall log and Arena log fingerprints matched their pre-mutation values. No private contents/fingerprints were published. This is a file-level comparison, not an audit of unrelated service activity.
- The existing Lab authentication environment file matched its protected copy internally; no signing key or secret fingerprint was emitted.
- The service unit again matched the original tracked file; no new listener, container, route, native search setting or model configuration was introduced by these operations.
- Lab Git whitespace and clean-worktree checks passed. The integration worktree/source was not rewritten.

No real or synthetic deployed chat turn, Web search, page fetch, model inference or deployed canonical write was submitted. Fixture tests used isolated temporary storage; health/admin requests are not reported as chat acceptance.

## F. Remaining activation and browser acceptance requirements

**Immediate blocker:** approved root execution is needed for the exact Lab-only environment override and Lab API restart. The ordinary command-execution approval did not supply Linux sudo authentication. Do not rerun a partial/uncertain activation blindly or assume the retained helper can activate the now-rolled-back checkout by itself.

For a new controlled attempt:

1. Verify effective privilege for the scoped service operation **before mutation**. Recheck Git/runtime drift, foreground idleness, backups and actual installed Function/valves; use a fresh phase/checkpoint so old successful/rollback markers are preserved.
2. Promote only the reviewed two-commit history again after confirming it is not already active; update the paired existing Pipe and valve values without changing identity/authentication/Arena. Retain the feature-first rollback boundary.
3. Create the Lab-only flag override, reload manager configuration and restart **only** Lab API under the approved privileged path. Verify actual process environment, correct code/data paths, health, native-search-disabled state and unchanged existing services before declaring activation.
4. Only after activation succeeds, conduct separately authorized browser acceptance: saved-chat source fallback and trusted links; transparent search failure; ordinary no-Web chat; existing dual authentication/HTTPS/Socket delivery; UI-2/Arena isolation; and uncertain-outcome behavior without automatic resubmission. Any real or synthetic chat/search needs its own explicit execution authorization because this attempt prohibited them.

Source-first fallback remains the chosen product baseline. Ordinary WebUI requests lack explicit structured requirements and will normally show sources with limitations rather than guaranteed natural synthesis. No native-search experiment, egress broker, additional model/framework or broad benchmark is needed to resolve this **operational privilege** blocker.

## G. Publication and preserved boundaries

Only this sanitized report and its chronological index entry are committed/pushed on `reports/web-validation`. No Lab/main/code push, force push, backup, token, password, key, private conversation, raw metrics or database contents is published. Existing reports remain unchanged.

Production/Demo, FoxGate/Cloudflare, Hindsight lifecycle/banks, Arena behavior and shared Qwen configuration were not modified. Protected backups and temporary deployment artifacts remain available locally. **Final state: ROLLED_BACK; MVP_NOT_ACTIVE; BROWSER_ACCEPTANCE_NOT_RUN.**
