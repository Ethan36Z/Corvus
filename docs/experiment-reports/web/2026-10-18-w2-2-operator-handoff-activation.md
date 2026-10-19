# W2.2 — Lab Web MVP activation through operator sudo handoff

Date: **2026-10-18** (operator timezone; final verification UTC 2026-10-19 04:59:27).

Verdict: **W2_2_LAB_ACTIVATED_WITH_CONSTRAINTS**

**The reviewed source-first Web MVP is active in Lab.** The operator installed the exact Lab-only systemd override and restarted only `corvus-lab-api.service`. Read-only verification confirmed the running process has `CORVUS_WEB_MVP_ENABLED=TRUE`, the existing Pipe has `WEB_MODE=auto`, health is OK and native Open WebUI search remains disabled. Production/Demo isolation, existing authentication, Arena and Hindsight configuration were preserved.

No live chat, search, public-page fetch or Qwen completion was submitted. Runtime configuration acceptance and offline regressions passed; **browser behavior and live provider reliability remain unverified**. The preceding [failed attempt and successful rollback](2026-10-18-w2-2-controlled-lab-deployment.md) remain recorded unchanged.

## A. Authorization, baseline and resumed checkpoint

The operator explicitly selected the [W2.1 source-first MVP](2026-10-18-w2-1-web-mvp-integration.md) following [OW-N1](2026-10-18-ow-n1-native-search-validation.md) and [OW-N1.1](2026-10-18-ow-n1-1-native-rag-answer-test.md). No architecture research, native-search experiment or egress broker was resumed.

The read-only preflight verified:

- Lab was clean on `lab/ow2e-console`, HEAD `975645963291ec992d64df0474a3ee9d0ba33dcd`.
- Local integration branch `integration/w2-web-mvp` remained clean at `50a63850f83506724aaff4c2af4f50811d00d646`.
- Exact ancestry remained baseline → W2 `9b374cf2ef46ea08399b124e0c2a725d96c92a38` → W2.1 `50a63850f83506724aaff4c2af4f50811d00d646`. W2 matched the original prototype tree at `01dd02e1aa826d49bd628891641892f3450b698f`.
- The original installed Pipe source, identity, owner, endpoint and valves matched the protected recovery copy; `WEB_MODE` was `off`.
- Lab API service/unit/environment, Production API PID and ten monitored container start times matched the rollback checkpoint. Lab/Production API and WebUI health were successful. The existing foreground registry reader reported IDLE.
- Canonical database and local shadow/Arena file fingerprints matched the rollback checkpoint before promotion. Native search remained disabled. No feature drop-in existed.
- The old privileged helper and its stale historical update markers were reviewed but **not executed**. A fresh handoff checkpoint preserved the previous attempt's artifacts.

Reporting branch started clean on `reports/web-validation` at `38f5a3b5a2a263bbeb908c096cbbebc948b19c2e`.

## B. Protected backups

The existing verified recovery set **`<protected-Lab-backup-root>/w2-2-20261019T042442Z/`** was retained. All eleven recovery-file checksums were verified again before promotion and after activation. Backup directory mode is 0700; recovery files and manifest are 0600. All three protected SQLite copies passed `PRAGMA integrity_check` again.

The set includes consistent online snapshots of WebUI, Chroma and canonical Lab SQLite; the non-database WebUI archive; original Pipe/valves/owner/identity; local shadow/Arena logs; protected authentication environment; original service unit; and baseline code/Git recovery material. The preceding report records archive validation of 37 regular files and 15 safe internal links.

No backup, credential value, private row, raw database or secret fingerprint is published. The exact local recovery path remains in the private operator evidence. Backups were not restored during this successful attempt. They are recovery checkpoints, not permission to overwrite later canonical/user data.

## C. Agent preparation and operator root action

Before mutation, the exact staged sequence and privileged commands were shown. The operator then replied **ready**, confirming availability for the immediate handoff.

Preparation performed by the agent:

1. Created a fresh private handoff checkpoint and staged a read-only two-line override.
2. Rechecked baseline, backup manifest, foreground idleness and runtime isolation immediately before promotion.
3. Fast-forwarded Lab to the reviewed integration tip, introducing only the two existing reviewed commits. No new source commit or repeated cherry-pick was created.
4. Updated the existing `corvus_pipe` through the native Open WebUI Function handler, which refreshes its loaded module cache. Installed source matched the reviewed integration source. Identity, owner, endpoint, active/non-global flags, original creation time, Arena setting and 300-second timeout were preserved; only `WEB_MODE` changed to `auto`.
5. Confirmed the supported valve enum and persisted settings, recorded the handoff as pending, and stopped before privileged actions.

Function maintenance used the previously reviewed local admin path with short-lived authorization held only in memory. No token/key was printed or stored, no user or persistent credential was created, and existing authentication configuration was unchanged. Post-root verification used read-only database metadata rather than another authenticated admin operation.

The staged override was exactly:

```ini
[Service]
Environment=CORVUS_WEB_MVP_ENABLED=TRUE
```

The operator executed the reviewed commands interactively in their own terminal:

```bash
test ! -e /etc/systemd/system/corvus-lab-api.service.d/60-web-mvp.conf &&
test ! -L /etc/systemd/system/corvus-lab-api.service.d/60-web-mvp.conf &&
sudo install -D -T -o root -g root -m 0644 \
  /tmp/corvus-w2-2-handoff/60-web-mvp.conf \
  /etc/systemd/system/corvus-lab-api.service.d/60-web-mvp.conf &&
sudo systemctl daemon-reload &&
sudo systemctl restart corvus-lab-api.service
```

The operator replied **succeeded**. Independent read-only checks confirmed a new Lab API process, its unchanged loopback command/working directory/data/model paths, the exact override contents, root ownership and mode 0644, and the expected sole drop-in path. The feature flag was present as `TRUE` in the actual process environment.

No agent sudo command, sudoers edit, password request/storage, broad root shell, old privileged helper, WebUI/container restart or model restart was used in this resumption. The agent did not execute the root command block or automatically retry it.

## D. Verified active configuration

| Item | Observed state |
| --- | --- |
| Lab branch / HEAD | `lab/ow2e-console` / `50a63850f83506724aaff4c2af4f50811d00d646`; clean |
| Backend flag | Actual Lab process `CORVUS_WEB_MVP_ENABLED=TRUE` |
| Lab API | Active/running; existing command, one worker, `127.0.0.1:18096` |
| Existing Pipe | `corvus_pipe`; source SHA256 `68967bd0ed499aaf2ecce38bc6afc80c3fc3cdeb805aab6a57182a2e907af861` |
| Pipe Web mode | `auto` |
| Pipe endpoint | `http://127.0.0.1:18096/api/chat` |
| Pipe timeout / Arena | 300 seconds / enabled, unchanged |
| Identity / owner / authentication | Preserved; signing configuration matched the protected copy |
| Discovery provider | Existing DDGS default; no provider switch |
| Native WebUI search | Disabled; persistent config remains disabled; no second discovery pipeline |
| WebUI image | Existing `corvus-open-webui:0.6.5-arena-ui2.1-https-r03b` |
| WebUI storage | Existing persistent volume retained; no recreation/data restore |
| Hindsight / model / data paths | Existing Lab settings unchanged |

The new backend process reads the reviewed flag parser at startup. This is active configuration evidence, not a deployed-turn demonstration of each presentation branch.

The installed Function's maintenance timestamps and administrator last-active metadata may change through its supported update API. The WebUI database is not claimed byte-identical. Conversation records, stored credentials and ownership were not rewritten to undo maintenance metadata.

## E. Read-only health, isolation and data checks

Final verification passed:

- Lab API, Production API and Lab WebUI returned HTTP 200. API overall/model health was OK.
- Lab API PID changed following the operator restart; the monitored Production API PID did not.
- All ten monitored containers remained running with unchanged start times: Lab WebUI, Lab FoxGate Gateway/Auth, Production/Demo frontends, Private/Demo gateways, shared Qwen, Lab Hindsight and SearXNG. Configured health checks were healthy; no health status was invented for services without one.
- API 18096, WebUI 3003, Lab Gateway 8100, Lab Auth 8101 and shared model 8095 listeners were all on `127.0.0.1`. No new public binding was configured by the override.
- Native search remained disabled after the restart. The existing WebUI process/container was not restarted.
- Foreground state was IDLE. Shadow-recall and Arena append-log fingerprints were unchanged.
- The protected backup checksums, three SQLite integrity checks and authentication-configuration comparison passed.

### Database fingerprint distinction: expected startup recovery

The initial strict file-fingerprint check stopped because canonical `corvus.db` bytes changed during the authorized restart. This was investigated read-only before accepting deployment; it was not ignored or relabeled byte-identical.

Using schema metadata, aggregate table counts and opaque per-table/index page hashes, comparison with the verified pre-activation recovery copy established:

- Canonical table/index pages were unchanged. The only changed table's pages belonged to **`dense_index_progress`**, the existing operational derived-index completion cursor.
- Schema and all table row counts were unchanged; message count and maximum message ID were unchanged. No private message, assertion or attachment content was selected/displayed for this check.
- The existing dense cursor advanced to the already-existing message tail.
- API startup-recovery health reported **OK, caught up, one batch, zero newly indexed entries**.

The existing `prepare_runtime_startup` calls the unchanged dense-tail recovery routine, whose successful catch-up advances that durable operational cursor. This explains the observed change without a new canonical turn or an Evidence Log rewrite. The database header/file fingerprint therefore differs; canonical content/schema/counts remain unchanged. This report does not claim zero SQLite writes or byte identity.

The verifier was then made explicit about this diagnosed exception: it accepts only the expected cursor advance with unchanged canonical pages/schema/counts, and still fails on other table/index changes. That read-only verification passed. No cursor or database row was edited by the verifier, and no database was restored.

No real/synthetic deployed chat, Web search, public-page fetch or Qwen completion was submitted. Health requests may perform the existing local model health check; they are not inference turns. No Hindsight lifecycle/bank, Arena behavior, Production/Demo configuration, FoxGate, Cloudflare or shared model configuration was changed. These are scoped checks, not a host-wide audit of unrelated activity.

## F. Offline regression evidence

The existing guarded driver was run against the active Lab checkout, using its existing environment and these two modules:

```text
test_web_acceptance.py
test_web_mvp.py
```

**Final fresh run: 60 passed, zero failed, one explicitly skipped; 61 discovered methods.** Breakdown: 19 evidence-acceptance tests and 41 passing MVP/inherited Pipe tests. The existing fresh-subprocess test remains skipped because the driver forbids subprocesses; it is not counted as passed.

The driver redirects writable data/home/cache/temp locations before imports, uses synthetic fixture storage, denies network/deployed-data access and subprocesses, disables Hindsight and forbids embedding-model construction. It reported no network/private-access violations. Tests ran outside the command sandbox to avoid its previously established ASGI thread-wakeup stall; no guard or deadline was removed. There was no stalled test run in this fresh post-activation execution.

Coverage includes the three MVP outcomes, version/date rejection, bounded continuation, distinct source references, exact provenance, honest provider/empty failure handling, partial-source limitations, safe source presentation, no automatic retries/duplicate canonical turns in fixtures, ordinary-chat compatibility and inherited Pipe identity/endpoint/auth/Arena guards.

These fixture API/runtime tests did not call the deployed chat endpoint or create deployed synthetic turns. They do not establish browser behavior, live provider success, full claim correctness or remote Socket reliability. No additional nineteen-script pass is invented for this checkpoint. Git whitespace checks passed.

## G. Remaining browser and product acceptance

**Configuration activation is accepted; live Web/browser acceptance is pending.** Separately authorize a small acceptance stage before claiming daily-use success:

1. In an existing saved Lab WebUI chat, verify sources-with-limitations rendering and usable links from fetched metadata. Do not mistake source presence for confirmed answer sufficiency.
2. Verify honest search/provider failure and partial-evidence presentation, plus ordinary no-Web chat compatibility.
3. Verify existing dual authentication, external HTTPS and Socket reply delivery with the unchanged WebUI/FoxGate setup. A lost connection is an uncertain outcome, not proof that persistence failed; do not resubmit automatically.
4. Confirm UI-2/Arena isolation and that native WebUI search remains off. Structured grounded-answer cases require explicitly supported requirements and evidence; ordinary Pipe requests normally take the conservative source-first fallback.

No reliability percentage, live retrieval latency, model-answer quality or browser acceptance is inferred from health endpoints and offline tests. The product choice remains source-first W2.1; no native experiment, egress broker, additional model/framework or broad benchmark is needed to complete this deployment checkpoint.

## H. Rollback readiness and publication

No rollback was needed after this successful handoff. If a later acceptance failure requires it, coordinate the scoped operator root action first: remove only the known Lab feature override, reload manager configuration and restart only Lab API. Read-only verification must confirm the backend is flag-off **before** restoring the original Function/valves and optionally the prior code baseline. Keep all canonical/user data, volumes, credentials and the legitimate dense-recovery cursor; routine rollback must not restore whole databases or delete turns.

The original protected Pipe and exact baseline `975645963291ec992d64df0474a3ee9d0ba33dcd` remain available. The reviewed integration tip remains local. Do not execute the old helper or stale checkpoint markers as a shortcut; use the actual current state and the preserved handoff evidence.

Only this sanitized final report and its chronological index entry are committed/pushed on `reports/web-validation`. No code/Lab/main branch, backups, raw database/metrics dump, credentials, tokens/cookies, private conversations or private identity values are published. The earlier rollback report retains its original verdict unchanged.

**Final operational state: LAB_MVP_ACTIVE; NATIVE_SEARCH_DISABLED; BROWSER_ACCEPTANCE_PENDING.**
