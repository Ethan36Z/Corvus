# H1.7d-3c — Controlled Hindsight foreground-admission rollout

Date: 2026-10-10 local time. Current verdict: PASS after the explicitly authorized H1.7d-3c-r1 retry. The patched runtime is live and one durable BUSY → DEFER → IDLE/grace → same-operation COMPLETED lifecycle passed. The first-attempt history below records the prior safe automatic rollback; it is not the current runtime state.

## Strict preflight

Lab was clean on `lab/ow2e-console` at `47201c609ce183f31dd61e529c9905c18d95c88b`. Production was clean on `main` at `c315d0e767e31fde3c82ba4dfb08659a268c267a`. Lab durable async retain was enabled. The Corvus retain ledger had ten lines, one previously completed logical operation and zero unresolved intents. Both publishers were healthy and the host aggregate was trustworthy IDLE. Lab/Production APIs, :8095 and Hindsight were healthy.

Installed `hindsight-api-slim` was exactly 0.10.1. All ten live guarded upstream/dependency hashes matched `deploy/hindsight-patches/0.10.1/manifest.json`; the admission module was absent and Hindsight had no registry mount. Bank `corvus-hindsight-lab-v1` was readable, with eight documents, nine memories and ten operations, all completed. There was no active background work.

## Original runtime and exact preservation

Original container: `hindsight-lab`, ID `336680f1d0a7a4dfb531f818976e969b6e1c7e55861fec4b605401df295a8bfe`.

Original image and repository digest:

- `sha256:b4d3b76f363aa40cf348450e7f8f52a50653008731b99824b14623a196182e73`;
- `ghcr.io/vectorize-io/hindsight@sha256:b4d3b76f363aa40cf348450e7f8f52a50653008731b99824b14623a196182e73`.

Full inspect snapshots were captured before mutation in `/tmp/corvus-h17d-3c/before.json` with mode 0600. They include command/entrypoint, full environment, user, ports/networks, mounts, restart policy, security/capability settings, labels, resource constraints, healthcheck and working directory. Environment values are not copied into Git.

The preserved runtime uses command `[/app/start-all.sh]`, null entrypoint, user `hindsight` (UID/GID 1000:1000), working directory `/app`, localhost `127.0.0.1:8888` and `127.0.0.1:9999`, network `hindsight-lab`, and restart policy `unless-stopped`. Persistent mounts are `hindsight-lab-data:/home/hindsight/.pg0` and `hindsight-lab-cache:/home/hindsight/.cache`. No Docker healthcheck is configured. All inspected security, capability, logging and resource constraints were cloned rather than guessed; model/provider/routing settings were unchanged.

The only intended semantic changes were the derived image, readonly registry bind and three admission settings. A stopped-container probe found Docker's unset `OomKillDisable` normalization to false. Both representations enable normal OOM killing; the strict validator accepts only that equivalent default and rejects any other host/security/resource difference. The failed initial preparation probe did not stop/restart the original. Dynamic endpoint IDs/addresses are Docker allocations, not newly configured network semantics.

## Guarded derived image

Local base tag: `corvus-hindsight-base:0.10.1-b4d3b76f363a`, verified against the original immutable image ID. A first BuildKit attempt using a bare sha256 FROM was rejected as a registry name before any live mutation; no image download succeeded. The corrected recipe uses the cached local tag, `--pull=false`, network-disabled build steps and the daemon-local legacy builder. No packages, models or unrelated upstream sources were downloaded.

Derived tag: `corvus-hindsight:0.10.1-h17d3b-47201c6`.

Derived ID: `sha256:344abefa75512314309102e9d0391a0a346a6258d538bbbd881620cc5da69689`.

Derived size: 3,607,396,794 bytes, adding 2,445,057 bytes to the base. The six validated modified/new modules and readonly verification metadata are layered over the exact cached base; runtime user/command/environment are inherited.

The base image lacks Git. The existing hash-guarded unified patch was applied offline with host Git to files copied from a stopped scratch container. Inside the build, distribution/version and every original hash were checked before all replacement bytes were verified/installed. Full patched/dependency hashes were verified afterward. Actual final-image sources were copied out and passed 28 reader/gate tests plus 27 control-flow tests. Scratch verification ran with no networking, live bank or persistent data mounts.

Artifacts are in `deploy/hindsight-runtime/0.10.1/`: Dockerfile, guarded builder/installer/runtime verifier, exact inspected-container recreation/rollback recipe, focused preservation tests and deployment instructions. The validated H1.7d-3b patch itself was not altered.

## Recreation and startup failure

The replacement's full Config, HostConfig, configured network properties and mount identities were validated while it was stopped and the original was still serving. Only then was the original stopped with 60-second graceful-shutdown allowance and retained under rollback name `hindsight-lab-h17d3c-rollback-336680f1d0a7`.

Temporary patched container ID: `26f0b32a2f4196a5ab6fcf820917a1abefded8359e57843c2f80d2568f9f8523`. It started healthy with the original data/cache volumes and routing. Installed version remained 0.10.1 and all eleven patched/dependency source hashes passed runtime verification.

The bind `/run/corvus-foreground:/run/corvus-foreground:ro` was verified by Docker inspect with `RW=false`. Configured admission values were:

```text
CORVUS_FOREGROUND_REGISTRY_DIR=/run/corvus-foreground
CORVUS_FOREGROUND_EXPECTED_PUBLISHERS=lab,production
CORVUS_FOREGROUND_IDLE_GRACE_SECONDS=30
```

Startup acceptance then failed because the operator helper used the existing `state.run()` subprocess timeout of 30 seconds around a standalone reader test that necessarily waits strictly beyond its 30-second recovery grace (bounded internally at 35 seconds). The process was killed at 30 seconds with `subprocess.TimeoutExpired`. Trustworthy reader IDLE and explicit EROFS write-open rejection were not reported and must not be claimed as verified.

The defect was in the acceptance harness timeout, not a demonstrated source-hash or bank failure. This does not prove the remaining reader acceptance would pass: it still must be completed. The timeout has been corrected offline to 45 seconds, retaining the reader's 35-second bound. The corrected helper has NOT been executed.

Task step 6 requires rollback and STOP on acceptance failure. Accordingly, no further recreation, no real memory operation and no BUSY acceptance were attempted.

## Automatic rollback and postflight

Automatic rollback stopped/removed only the replacement without removing volumes, restored the original container name and started the retained original. This exercised the rollback mechanism rather than merely describing it. The original image was not deleted.

Readonly postflight confirmed original container ID, image, full Config, full HostConfig and both original mounts restored **exactly**. Original source hashes still match the frozen upstream manifest, no admission mount/settings are active, and Hindsight is healthy/unpatched. Hindsight PID changed from 2884 to 299027 due to the authorized stop/restart and rollback; restored start time is `2026-10-11T00:36:44.559235755Z` (October 10 locally).

Bank remains eight documents and nine memories; the same ten operations are completed with unchanged operation listing. The Corvus ledger remains unchanged with zero unresolved intents. No retain/consolidation operation was created by startup or rollback. Hindsight's existing provider connection verification can make its normal startup probe; it is not a retain/consolidation operation or real admission acceptance.

Lab PID 13671, Production PID 2831871 and :8095 process PID 2867 were unchanged, as were their configuration, container identities and service files. Production repository/private SQLite/dense state and Lab canonical evidence were unchanged. Both foreground publishers remain live/healthy/idle; registry contents/inodes and the host aggregate IDLE are unchanged. Neither Lab nor Production was restarted; model endpoints :8095/:8106/:8107 were not restarted. No reboot, Reflect, routing change, bank change or push occurred.

## Real acceptance evidence: NOT RUN

- BUSY observation: not run; no temporary test publisher was started.
- Durable retain UUID/child UUID: none generated/submitted.
- Retry count / next_retry_at: not applicable; no new operation.
- Provider send while BUSY: not tested.
- Grace/resume/same-UUID completion: not tested.
- No duplicate, replacement, retry or replay was created.

A purpose-built Lab tracker seam and one-shot synthetic async-retain script were prepared under `/tmp/corvus-h17d-3c/accept-once.py` but never executed. They do not represent a successful live acceptance or change the running Corvus retain path.

## Rollback readiness and next action

The original container/image/configuration and shared data volumes are currently restored. A future successful rollout can retain the same original under its rollback name and use the documented `runtime.py --rollback` command, without deleting persistent data. The private before snapshot and derived image remain available; no host-only configuration snapshot is committed as a fake deployment file.

Four offline recipe tests pass, covering original input preservation, exact intended differences, the equivalent OOM default normalization, and rejection of changed routing, writable registry, resources/security or data mounts. Source/deployment syntax and `git diff --check` passed.

Next action is to explicitly resume H1.7d-3c after fresh preflight and corrected startup acceptance, then prove one real BUSY → DEFER → IDLE/grace → same-operation COMPLETED lifecycle. Do not proceed to H1.7e bounded consolidation until that passes. The known residual race remains: an admitted memory call cannot be preempted when foreground arrives afterward; no arbitration/cancellation was implemented here.

First-attempt verdict: BLOCKED — validated derived image and rollback recipe retained; that rollout was automatically rolled back and stopped before real admission acceptance.


## H1.7d-3c-r1 — Timeout-only correction and successful rollout

Fresh preflight verified clean Lab `lab/ow2e-console` at `0b217c7ed6067808f48470241524c3844eaf9b52`, clean Production `main` at `c315d0e767e31fde3c82ba4dfb08659a268c267a`, the exact restored original Hindsight runtime, eight documents/nine memories, ten completed operations, zero unresolved Corvus intents, healthy live publishers and trustworthy host IDLE. Lab async retain remained enabled. Peer service/model/container identities and private/canonical data matched the saved baseline.

Only the rollout harness timing changed: startup health and outer admission acceptance horizons are **75 seconds**; the standalone reader observation loop is bounded at 70 seconds with one-second polling. Admission idle/recovery grace remains **30 seconds**. Neither the version-pinned patch nor runtime admission semantics/configuration changed. The historical 45-second offline adjustment above was superseded by this explicitly requested 75-second horizon.

The exact existing derived image `sha256:344abefa75512314309102e9d0391a0a346a6258d538bbbd881620cc5da69689` was reused, with no rebuild/download. A network-disabled scratch verifier and live post-recreation verifier confirmed distribution 0.10.1 and all eleven patched/dependency hashes. The previously passed 55 reader/gate/control-flow tests still correspond to these identical bytes. Four runtime-preservation regression tests passed again.

Docker access was available to the operator account; no sudo helper or password bypass was needed. Reviewed helpers and private snapshots are under `/tmp/corvus-h17d-3c-r1/`, with the before snapshot mode 0600. Only Hindsight was stopped/recreated. Its new container is `d10028ca1b99d0ae02d4bd43cd2a81b8bdd65248600948481bd58a8485949f99`, PID 364304, started `2026-10-11T01:24:28.356295738Z` (October 10 locally).

The stopped original remains `hindsight-lab-h17d3c-rollback-336680f1d0a7`, with its full original Config, HostConfig, mounts and image reverified exactly. The current runtime validator passed: only derived image, readonly registry bind and the three admission settings differ semantically. Model routing, command/entrypoint, user, ports/network, persistent/cache volumes, restart/security/resource settings and original environment remain preserved.

Startup acceptance observed reader `UNKNOWN → IDLE` after **30.026358 seconds**, recognizing both expected publishers as UID/GID 1000:1000. Docker mount inspection showed `RW=false`; opening the existing `registry.json` for write without truncation or writing failed with **EROFS (errno 30)**. Bank stayed eight documents/nine memories and all ten operation records remained unchanged before the real test. No retain/consolidation was triggered by restart.

## One real durable admission acceptance

A purpose-built safe seam exercised the real Lab `ForegroundActivityTracker` and registry publisher in a separate test process, without a chat request or changes to the live Lab/Production publishers. Its logical name was `lab-admission-acceptance`, with process identity `368850-59859604-14313b9f6abf41ee8a4983348974dfb8`. The configured expected set stayed `lab,production`; the protocol also recognizes trustworthy additional busy publishers. Its generation context held the actual kernel busy lock with count one, then published count zero/finish time and closed lifetime resources. Stable stale lock files were retained, not deleted or replaced. Only runtime scheduling metadata was published.

Exactly one synthetic async retain POST was submitted while BUSY. No canonical Corvus turn or invented message provenance was used. Content was:

> H1.7d-3c synthetic admission acceptance marker: the temporary test codename is Copper Falcon 386. This is operational test data, not a personal fact.

The context explicitly identified synthetic operational acceptance, with `source=corvus-lab-admission-acceptance`, `synthetic=true`, `test=H1.7d-3c`. The exact request and client UUID were appended/fsynced before POST in the task-local `/tmp/corvus-h17d-3c-r1/admission-ledger.jsonl`, separate from the unchanged live Corvus retain ledger.

- Bank: `corvus-hindsight-lab-v1`.
- Client/parent operation UUID: `7d4326b3-fb95-4090-9434-2b228cf163e4`.
- Executable child UUID: `46a7fb59-84de-4c45-b52f-d43fdcdb60bf`.
- Document: `corvus-lab:h1-7d-3c:admission:7d4326b3-fb95-4090-9434-2b228cf163e4`.
- Request fingerprint: `32807406880faea9ae53092e3ad57446bdd0831811f7100280a340a228f32d77`.
- Final executable-payload SHA256 (sorted JSON): `aea00685b94bb04435992502eabb464565a7c591d9fecd3e2a9bd8fb18dfb0ee`.

The HTTP acknowledgement validated `success=true`, `async=true`, bank, one item and the same pre-recorded operation UUID. Parent/child rows are normal durable fan-out for this one submission, not replacement operations.

Timeline (UTC; all events occurred October 10 locally):

1. `01:27:34.265893`: fsynced BUSY observation, active count one.
2. `01:27:34.299540`: fsynced submission acknowledgement for the same UUID.
3. `01:27:34.764949`: worker log `Task 46a7fb59-84de-4c45-b52f-d43fdcdb60bf deferred ... foreground admission: BUSY`. Child returned to pending, `next_retry_at=01:28:04.763870`, retry count **0**, error null. Status observation at `01:27:36.312318` still showed BUSY/pending, with no terminal completion.
4. Publisher finish watermark was monotonic `598598.384211274`, approximately `01:27:36.333512` UTC using the paired BUSY wall/monotonic observation. The generation exception path correctly released BUSY; final metadata count is zero and all lifetime ownership was released when the test process closed.
5. `01:28:05.041248`: natural worker eligibility encountered reader recovery grace and deliberately deferred as `UNKNOWN`, setting `next_retry_at=01:28:35.040280`, without retry consumption. Reader recovery on removal of the test publisher conservatively starts a grace anchor; the first scheduled attempt cannot bypass it.
6. `01:28:35.335031`: the **same child** resumed naturally. The first model slot selection was `01:28:35.357765`; the only model inference dispatch was task **6503** at `01:28:35.482758`, about **59.149 seconds after finish**, beyond the unchanged 30-second grace. No model slot launch occurred during BUSY or grace. The model logs emit slot dispatch/timing rather than HTTP access lines, so proof uses actual model execution plus the worker's pre-provider defer evidence, not an assumed POST log format.
7. `01:28:37.214542`: child completed, about **60.881 seconds after finish**; parent completed when its one child completed. Final retry counts remain **0**, with no error. Retain extracted zero facts and tracked the synthetic document. COMPLETED proves successful processing/storage, not nonzero facts or semantic quality.

### Observation harness corrections, with no replacement work

The one-shot test script stopped after its real BUSY defer because the status query omitted `include_payload=true`; the API correctly returned `task_payload=null`, and the harness attempted to index it. Its `finally` closed the tracker and the already-durable operation continued naturally. A separate read-only observer queried the **same** parent/child with `include_payload=true`, confirmed completion, validated content/context/metadata/document and timestamp-to-event-date conversion against the fsynced request, and inspected retained logs. No resubmission, replacement UUID, manual worker retry or extra model request was made.

That observer also corrected an evidence-parser assumption: this cached llama.cpp runtime logs slot dispatches rather than `/v1/chat/completions` access lines. This changed observation only. Admission source, grace, fail-closed policy and provider behavior were unchanged. The deferred API observations do not contain a payload hash because payload inclusion was omitted; unchanged payload is supported by the verified worker `_defer_operation` SQL (which changes scheduling/claim fields only), same child identity across all worker logs, and the final stored exact original request material. No before/after payload-hash observation is claimed.

The operation itself completed within approximately 61 seconds of foreground finish, within the original 180-second acceptance bound. Subsequent inspection reconstructed that timeline from retained logs; it did not restart an observation window to permit more work. The task-local ledger now also records terminal completion. The live Corvus ledger remains unchanged with zero unresolved intents.

## Result, isolation and rollback

Bank: **8 → 9 documents**, **9 → 9 memories**. The synthetic document is preserved. Naturally queued consolidation `ed88e44a-e221-4041-8220-f739ab1fd77d` completed with **0 processed**, no additional model inference and retry count zero. It was not manually triggered. Operations are **10 → 13**: one client parent, its one retain child and that naturally queued consolidation. All three are completed/error-free, and all ten original operation records remain unchanged. There is one logical retain submission, no duplicate, no replay, no replacement UUID, no chat request and no Reflect.

Final read-only postflight reverified healthy patched Hindsight/version/source hashes, exact configured runtime and exact stopped rollback container. Host aggregate is trustworthy IDLE with active count zero and both expected publishers live/healthy. Existing registry file hashes/inodes and real publisher identities are unchanged; only the separate test publisher's own stable files/finish metadata were added. No private conversation/user data entered the registry.

Lab PID **13671**, Production PID **2831871** and :8095 PID **2867**, their service/configuration, all other model-container identities, Lab canonical data, live retain ledger and Production private SQLite/dense state remain unchanged. Production HEAD/worktree are unchanged and clean. No other service/model was restarted, no systemd/runtime configuration was changed, no reboot or push occurred.

Rollback remains ready and does not delete volumes or the synthetic acceptance document:

```sh
python3 -B deploy/hindsight-runtime/0.10.1/runtime.py --snapshot /tmp/corvus-h17d-3c-r1/before.json --image sha256:344abefa75512314309102e9d0391a0a346a6258d538bbbd881620cc5da69689 --rollback
```

No rollback was performed after successful acceptance. Raw private inspect/configuration snapshots and full observations remain under `/tmp/corvus-h17d-3c-r1/`; secrets are not committed.

This proves no new memory inference began while foreground was already BUSY, and durable deferred work resumed under the same operation after grace. It does **not** prove preemption/arbitration against foreground arriving after admission. That residual race remains provisionally accepted; bounded consolidation is still the next engineering objective, **H1.7e**, and was not implemented here.

Verdict: **PASS** — exact cached patched runtime deployed with readonly registry access and unchanged 30-second grace; one durable BUSY/defer/grace/resume lifecycle reached COMPLETED with zero retry consumption and preserved isolation.
