# Voice V1 — build and Lab deployment preparation

2026-10-23. **BLOCKED_RESOURCE / NOT_READY_FOR_LAB_ACTIVATION**.

Application `f6d94ffe48b2e07bd1adf0c5dc776850bb9c1980`, branch
`feature/voice-v1-half-duplex`, remains unchanged. Reviewed coordinator, native
integration and Pipe commit validation: one submit, no automatic retry, unknown
result locks Call, stop/hangup cancel media only. Complete matching saved replies
are required for speech. Per-target UI correlation is not durable idempotency.
No implementation correction was identified in this review.

## Build evidence

Verified 347 deployed frontend application source-map entries against the cached
source, restored 990 applicable packages from locked integrity-checked cache and
applied only the seven-file overlay. Two complete Vite invocations passed the
1214-module SSR phase but exhausted the 512 MiB V8 heap during client production
build (768 MiB container cap, exit 139). The second used a disposable config with
sourcemaps/compression reports off. Neither yielded a complete frontend.

Host RAM available was approximately 1.3 GiB and swap full. At the user's direction
resources/services were left as-is; no larger-budget attempt was started. No
candidate image was created. Reserved tag:
`corvus-lab-webui:voice-v1-f6d94ff-candidate`. Partial output is not releasable.

## Compatibility evidence and limits

Twenty existing isolated backend suite modules completed: **261 unittest cases,
259 passed / two existing offline-subprocess skips**, plus six module-level
assertion scripts. This includes Web W1/source boundaries/Plan C intent/W2,
Personality profiles/P0.4/runtime, Pipe, Arena, STT transport/WebUI, TTS, async retain
and reconciliation. Initial Arena UI2 setup lacked its pinned upstream archive;
adding the verified cached fixture yielded UI1 15/15 and UI2 4/4, without changing
code. Final suites used bwrap with no network/private runtime data. Arena archive
suites allowed only reviewed preparation/git-apply in writable disposable source;
they were not run under the acceptance guard that forbids subprocesses.

The Vision frontend test also passed actual native Svelte compilation and mocked
upload/save/dispatch/cancel/error contracts on the full assembled candidate source.
Existing V1 evidence remains: coordinator 17/17, Dictation 19/19, package 9/9,
five-component compilation/strict TS and fake-device two-turn Chrome test. These
are offline compatibility results, not real deployed microphone/model acceptance.
A temporary URI-aware acceptance guard copy was used for synthetic SQLite fixtures;
repository guard and memory code are unchanged.

Live WebUI image is `sha256:2427456fa33f5eccf8a854f9ad37f3af05f0cc443ae6348468f136a25a0745dc`.
Its current explicit Compose environment/image matched the running container.
The planned derivative replaces frontend `/app/build` only. Existing backend,
private Bridge/Whisper and mounted STT protocol remain. In particular integration
commit `688a8bb` is not deployed to the Lab API by this plan; source-level transport
tests do not certify its real deployment. Current Corvus Pipe points to API 18096,
Web auto/Arena enabled, with no new model/personality/routing overrides.

## Deployment boundary

`deploy/lab/voice-call/LAB_ACTIVATION.md` contains build gates, exact current base,
image-only candidate/rollback commands, fresh protected-state/consistent-backup
requirements and minimal real acceptance. The Dockerfile/Compose files are
unexecuted preparation recipes. No active configuration, code, services, database
or image tags were changed. No push/merge. A metadata snapshot is not a private
SQLite/volume backup; that fresh verified backup remains a future deployment gate.

Reliability and Memory Integrity First. Latency Optimization Second. The existing
BackgroundTasks -> durable retain-intent gap and lack of automatic reconciliation
remain; memory completion is not guaranteed. Stop/hangup does not cancel accepted
chat/memory work. P0.2 BLOCK is unchanged. No scheduling/performance change.

Local evidence: `/tmp/corvus-voice-v1-stage-ku_7qzxo/` (compatibility logs and
sanitized provenance), `/tmp/corvus-voice-v1-vite-default.log`,
`/tmp/corvus-voice-v1-vite-bounded.log`, and build workspace
`/home/ethan/srv/build/corvus-voice-v1-f6d94ff/`. Logs contain synthetic/offline data.
Machine-readable sanitized summary: `deploy/lab/voice-call/build-readiness.json`.

## Final protected-state check

Read-only before/after comparison found no differences in integration/main/Lab
HEAD, status, index or tracked/untracked hashes; all **28** current dirty Lab
files were preserved. Lab API PID 828169, Production PID 6052 and Demo PID
1006708, process environments/drop-ins, Docker daemon and existing container
identities/configuration match the current-task snapshot. Lab WebUI remains
healthy on its original immutable image. Rendered candidate Compose differs
only at `/services/open-webui/image`; rendered rollback has no differences.
No candidate tag or temporary build container exists. Evidence:
`/tmp/corvus-voice-v1-stage-ku_7qzxo/final-verification.json`.
