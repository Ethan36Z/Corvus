# STT-R7 — final disabled Lab integration package

Baseline: local R6 c0b818fa2c72a4eeb6f8691f5e25f06eea8b87e1.
This directory prepares ONE Lab candidate. It does not deploy, enable STT,
change active configuration or provision credentials. Both exported R2 live gates
and native STT permission remain disabled. No new voice UI, converter or engine.

## Exact artifacts and reuse

`artifacts.json` pins the two locally built images, current TTS-enabled WebUI
parent and existing Node 22 builder. The R6 private Whisper image/model/command
and its 8-CPU/1088-MiB budget are reused without rebuild/inference. Images remain
local only; no dependency/model/image downloads or implementation pushes.

The WebUI derivative inherits current HTTPS/TTS/branding/Arena backend and runtime.
Only the authenticated native STT handler is replaced, plus the rebuilt native
frontend. All other audio handlers are AST-identical to the pinned active image;
TTS helper and HTTPS main.py remain byte-identical. Existing data volume, installed
Pipe, auth/session/HTTPS settings and host networking are retained. No installation
Function, chat data, Arena behavior or canonical store is changed by this package.

Source regeneration reuses the checksum-verified cached upstream archive and the
existing branding/Arena verifier, validating all 117 original patched files. The
R3 composer pin was older than current Arena UI-2; it is corrected to the exact
reviewed Memory A/B composer. The only old/new source difference was its existing
Arena properties/control. Drift is still rejected. The preparation function keeps
that control, native recorder, editable composer and no-auto-send semantics.

The active compiled TTS debug-call removal is also applied to its exact original
ResponseMessage source before rebuilding, so regeneration does not reintroduce
content logging. This is preservation of the existing fix, not a TTS redesign.
Node 22, Vite and all 989 cached dependency version entries match the pinned npm
lock; build uses cached modules read-only with networking disabled, no npm install
or Pyodide fetch. Existing packaged Pyodide assets are reused. Source maps contain
public code only, not recordings/credentials.

`prepare.py` accepts a verified branded source tree, selected public base-image
files and a fresh output directory. It verifies the current TTS audio source,
version, helper and original frontend pins before any output. It rejects existing/
overlapping output and writes isolated source/WebUI/bridge contexts plus proof.json.
The Dockerfiles are generated in those contexts; no active tree/bundle is patched.

## Fixed minimal topology

Active Lab WebUI already uses host networking for its working TTS/Pipe/Corvus
paths. Preserve it. The native helper therefore targets only:

`http://127.0.0.1:18106/v1/transcribe`

Only the authenticated bridge is published, bound to 127.0.0.1:18106. There is no
public proxy rule or unauthenticated HTTPS route. It joins:

- `corvus-stt-dictation-ingress`: bridge only; normal Docker bridge attachment
  needed for loopback publishing on this host.
- `corvus-stt-dictation-private`: internal, only bridge + private Whisper.

Whisper remains on the internal backend only, with no host ports. The bridge
continues targeting fixed `http://corvus-whisper-dictation:8080/inference`, using
R1 as its sole multipart transport. No request-controlled target, external redirect,
proxy environment, retry or legacy fallback exists. A3 remains untouched.

A temporary synthetic test verified this exact attachment pattern, private DNS,
R1 multipart against an HTTP stand-in and loopback HTTP 503 from the disabled
exported bridge. No model was loaded and no working STT gate was installed.
The internal-only initial topology did not publish a host port on this Docker
host; the bridge ingress attachment is the smallest correction. A startup
connection-reset was handled as readiness retry. All owned test containers and
networks were removed after exact identity/member checks.

The ingress attachment gives the bridge a normal network route; this package does
not claim complete container egress isolation. Application upstreams stay fixed,
and the engine remains isolated on the internal backend. This is the explicit
routing/access boundary under R6's revised application-level privacy scope.

## Runtime constraints and disabled gates

The bridge reuses the pinned WebUI Python/FastAPI/httpx/Uvicorn runtime and copies
only six existing R1/R2/R6 and stdlib storage-definition modules. No canonical API,
model, data mount or database initializer is included/invoked. Storage definitions
are imported by the unchanged R1 module, but no persistence entry point is called.

Bridge: UID 10001, read-only root, no data mounts, cap-drop ALL, no-new-privileges,
64 PIDs, core=0, one Uvicorn worker, no access logs, stdout/stderr discarded and
Docker logging none. Healthcheck inheritance is explicitly disabled (the parent
WebUI healthcheck targets a different service). Admission, size limits, timeout,
disconnect and late-worker behavior remain exactly R6. Both live gate code paths
remain inert and never load a real credential.

Bridge budget: 1 CPU / 256 MiB, memory-plus-swap equal. The packaging test peak was
158,208,000 bytes; 1.5 times that rounded up to 32 MiB is 256 MiB. A confirming
19-test run under that limit peaked at 156,794,880 bytes, no failure. This is a
bounded packaging/test profile, not a worst-case speech or concurrency benchmark.
Together with Whisper, new limits are 1344 MiB and 9 CPU quota, not reservations.
Read-only host checks found approximately 9 GiB available RAM, 16 visible CPUs,
low load and no current memory-pressure average; port 18106 was unused. Recheck
headroom immediately before approved activation; no QoS/reserved-core guarantee.

WebUI keeps its existing persistent chat volume, but the new STT path neither
caches dictation audio/transcripts nor invokes canonical writes. Container logging
is disabled in the candidate override. Historical data/cache/logs and previously
cached browser assets are not purged. Host/client swap, core/crash dumps,
hibernation, browser decoder memory/GC and old A3 converter retention remain risks.
No full privacy, immediate RAM erasure or hard worker termination is claimed.

## Focused validation

- Full offline Node 22 frontend build passed; native UI-2 recorder/composer suite:
  15 passed. No device/microphone/live inference test.
- In newly packaged bridge runtime: 8 R6 + 11 R2 auth/API/bounds/disabled-gate tests
  pass (19 methods), including actual synthetic worker timeout/admission. Repeated
  only to confirm its derived 256-MiB bound.
- Built WebUI payload: version 0.6.5, exact TTS helper/HTTPS main, unchanged non-STT
  audio AST, all branded asset hashes, Memory A/B UI and no TTS content debug call.
- Seven packaging/topology/gate/rollback tests pass using normalized merged Compose.
  Original WebUI environment (including TTS/Pipe), host networking and volume are
  unchanged. Exactly two infrastructure services are added, no other existing ones.
- Actual isolated routing test passed with a synthetic HTTP stand-in, disabled
  bridge, no models/data mounts and random loopback test port. No active Lab URL.
- R1–R6 A3/TTS/Pipe/browser/resource results are reused; no broad reruns or fresh
  inference. Runtime image/start metadata and earlier draft hashes remain unchanged.

## Rebuild inputs, without deployment

The built local images are the deployable artifacts; prefer their exact IDs.
If rebuilding is necessary, use only existing local inputs:

1. Run the existing branding verifier's --prepare-source/--archive/--arena-ui2
   against the already cached checksum-verified upstream archive into a fresh tree.
2. Copy only public audio.py, corvus_tts.py, main.py, package.json and packaged
   Pyodide assets from a stopped, no-mount pinned parent-image container. Never
   copy a deployed data volume or environment. Remove that exact temporary container.
3. Run `python3 -B deploy/lab/stt/package/prepare.py <verified-source> <public-base-files> <fresh-context>`.
4. Build frontend using the pinned Node 22 image, network=none, fresh source writable,
   cached node_modules read-only, package version 0.6.5 and no fetch/install steps.
   Run SvelteKit sync and Vite directly. Copy its build/ into the WebUI context.
5. Build both generated Dockerfiles with --pull=false --network=none from the
   already installed pinned parent. Verify output pins/proof and focused checks;
   do not silently replace artifacts.json or deploy an unreviewed rebuilt image.

Validation commands (rendering only; no real secret needed):

```
# Use a deliberately synthetic value for CORVUS_LAB_WEBUI_SECRET_KEY during render.
# Supply model-file and generated-context paths. Never print a real env/secret.
docker compose -f deploy/lab/compose.webui.yml -f deploy/lab/compose.boot.yml -f deploy/lab/compose.arena-ui2.yml -f deploy/lab/compose.https.yml -f deploy/lab/compose.tts.yml -f deploy/lab/stt/private/compose.yml -f deploy/lab/stt/package/compose.yml --profile stt-private-review config --format json
python3 -B tests/test_stt_r7_package.py <candidate-json> <retained-stack-json> <generated-context>
```

## Later authorized Lab checklist — NOT performed by R7

1. Approve the exact local commit/image IDs and residual-risk scope. Recheck active
   image/start metadata, selected nonsecret settings, model identity/permissions,
   free loopback port, headroom and ownership/absence of both new networks/services.
   Abort on runtime drift; do not fetch, pull or replace active configurations here.
2. Retain the exact current Lab image/stack and verify a protected, consistent
   WebUI-volume backup under separate authorization. Do not inspect chats or modify
   canonical Corvus data. Preserve the installed Pipe/Function and TTS configuration.
3. Prepare ONE independent high-entropy bridge credential outside Git, with reviewed
   file ownership/permissions and read-only distribution to WebUI and bridge only.
   Do not reuse browser JWTs or the WebUI signing key. Do not print its contents.
4. Explicitly authorize the minimal backend-only gate wiring: supply that credential
   and `whisper_text` to R6 create_app; supply the same credential via a fixed local
   bridge callable to the native handler. No request/env toggle exists in these
   artifacts. Keep both gates closed until this wiring and secret handling are
   reviewed/tested. This is an intentional activation change, not a missing package
   dependency. The native frontend needs no further rebuild for that wiring.
5. Preview the exact seven-file stack order shown above with private settings
   without printing them. Do not apply a project-wide up/down. Under approval,
   create only private Whisper/bridge and the two owned networks; verify no engine
   host port, actual ownership/member list, RO mounts, cgroups and logging. Record
   exact full IDs and image/config identities for rollback.
6. Recreate only Lab WebUI with the retained volume/auth/HTTPS/TTS/Pipe settings.
   Confirm TTS and Arena are unchanged. Leave native STT permission false until a
   separately approved gate/permission transition. Recheck the exported disabled
   endpoints before any enabling. No existing A3/Kokoro/Corvus/Hindsight restart.
7. Authorize bounded public synthetic speech acceptance and the gate/permission
   transition explicitly. Test auth/Chinese-English/WAV/size/error/disconnect,
   no storage/logging, review-before-send and target browsers/Safari/iPhone. Clear
   old browser assets by controlled reload. No private recordings for acceptance.

## Scoped rollback — plan only

Close both dictation admissions and native STT permission first. Stop the bridge
and its private engine, and verify old work has ended before any retry/recovery.
Retain all original A3 services, models and volumes. Restore only Lab WebUI's
retained image/stack with STT disabled and the same existing volume; no database
restore/migration, canonical deletion or broad stack teardown.

`rollback_plan.py` consumes selected Docker inspect metadata and prints a plan;
it never executes commands. It accepts only full IDs for the two expected new
Compose services, exact image IDs, Lab project and io.corvus.stt.owner=r7-lab.
It rejects Production, legacy corvus-whisper, wrong images/labels and duplicates.
Network removal is planned only after fresh inspection proves zero consumers and
correct new names/owner/project. Run container and empty-network phases separately;
never infer emptiness from the original plan. Stop on uncertain ownership.

Do not execute printed commands without separate authorization. Never run prune,
remove volumes, force-remove unknown resources or use compose down. Restarting a
bridge while its old engine still processes a cancelled request can defeat
admission; the paired stop/verification rule prevents that recovery overlap.
No runtime rollback is needed for this offline task.
