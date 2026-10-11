# H1.7d-3c — Controlled Hindsight foreground-admission rollout (rolled back)

Date: 2026-10-10 local time. Verdict: BLOCKED during startup acceptance; automatic rollback passed. The original Hindsight runtime is restored and no real admission lifecycle was exercised.

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

Verdict: BLOCKED — validated derived image and rollback recipe retained; live rollout was automatically rolled back and stopped before real admission acceptance.
