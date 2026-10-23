# Voice V1 — build gate and Lab image-only activation plan

2026-10-23. **READY_FOR_LAB_ACTIVATION** (candidate ready; not deployed).
This is preparation, not deployment authorization. Candidate image:
`corvus-lab-webui:voice-v1-f6d94ff-candidate`
(`sha256:5058ab1bdfd1112c38dda284f67c76717c0d6faf5eb425e59a0229f980c3ec6d`).
Application revision: `f6d94ffe48b2e07bd1adf0c5dc776850bb9c1980`.

## Current boundary

Lab WebUI is Compose project `corvus-lab-open-webui`, service `open-webui`,
container `corvus-lab-open-webui`, host network. Effective Compose source:
`/home/ethan/.config/corvus-lab/chat-recovery-runtime/recovery/candidate-compose.json`.
Current immutable image:
`sha256:2427456fa33f5eccf8a854f9ad37f3af05f0cc443ae6348468f136a25a0745dc`.
The effective image and explicit environment match the running container.
Do not treat this dated observation as authorization to overwrite later changes.

The proposed deployment changes only this WebUI image. The candidate extends
that exact image and replaces `/app/build` only. Preserve all backend bytes,
entrypoint, dependencies, mounts, permissions, environment, authentication and
secrets. Preserve the data volume, both STT secret directories and the mounted
`corvus_stt_protocol.py`. No Lab Python source copy or API restart is required.
No Production/Demo/HTTPS gateway/Whisper/Bridge/Qwen/Kokoro/Hindsight restart.

The API transcription refactor `688a8bb` is in the integration/Voice source but
not in the running Lab API. Do not deploy it for this frontend acceptance. Both
Dictation and Call use the already installed native WebUI STT route, existing WAV
normalization and private Bridge. Ordinary Dictation stays editable/manual-send.
The new mode is built for exact model `corvus_pipe`, with
`VITE_CORVUS_VOICE_CALL=true`; a container environment edit cannot flip that flag.
Keep existing Personality settings, P0.2 BLOCK, Web mode and Arena valves.

## Build completion gate (met)

The previous 512 MiB limit came from explicit per-build `NODE_OPTIONS`, with a
768 MiB container cap. No inherited NODE_OPTIONS or limiting session/user-slice
memory.max/high was found. The host had approximately 6.3 GiB available RAM at
preflight; swap remained full and was not expanded. Under the user's explicit
follow-up authorization, one build at a time was attempted:

| Old-space cap | Container cap | Result | Peak cgroup memory | Minimum host available |
| --- | --- | --- | --- | --- |
| 2048 MiB | 3 GiB | V8 heap exhausted, exit 134, 83.14s | 2.76 GiB | 3.61 GiB |
| 3072 MiB | 4.25 GiB | **exit 0, 114.10s** | 4.25 GiB | 5.56 GiB |

The successful full original Vite config retained sourcemaps and compression
reports: SSR 1214 modules, client 4544 modules, adapter-static wrote `build/`.
No service/app was stopped; no extra swap/network was used. CPU was capped at two
cores, and a watchdog was set to stop only the build below 1.5 GiB available RAM.
The successful container reached its cgroup cap (161 max events), but oom and
oom_kill were both zero. Peak includes charged file cache and is not a claim
about exact JS RSS. Neither build triggered the watchdog. Existing Svelte/package
warnings and large-chunk warnings were retained; no source workaround was added.

Build workspace: `/home/ethan/srv/build/corvus-voice-v1-f6d94ff/source`.
Pinned Node 22.16.0 builder image:
`sha256:35d1e2d251585b806c41f71d0933d7ba3afb6374ee3745523c2ae406480f6bc7`.
Full lock SHA-256 (unchanged):
`d140bb9648ff22a039826c710fc5bfa4e5e36b8660ea6e97c9253025cbb1ead9`.
All 990 applicable packages came from the integrity-checked existing cache;
111 optional incompatible-platform packages were omitted. Existing verified
static Pyodide assets were reused, without running the network fetch step.

The independent candidate was packaged offline from the exact current base image,
with `/app/build` replaced only. Verified **4751 files / 312431993 bytes** against
the full build, **349 application source maps**, all **7 Voice overlay sources**,
and the baked enabled Call selector/launcher. Svelte retains an unreachable
disabled-branch factory; compiled branch selection is constant-enabled. Native
Dictation/normalizer/Vision/Chat sources are unchanged. All **207 backend files**,
base-layer prefix and inherited runtime configuration match the base. Labels are
additive. Checks ran only Python hashing in temporary no-network/read-only
containers, with no real data mounts and no WebUI server startup.

Existing offline compatibility evidence is reused: 261 unittest cases (259 pass,
two offline-subprocess skips), six assertion scripts, Vision frontend and focused
Call/Dictation/browser checks. No new personality/model conversation benchmark or
live failure injection was run. Candidate-specific parity is in
`build-readiness.json`. Rebuilds must preserve this provenance and use a new tag
if the reviewed candidate changes; do not overwrite current service tags.

## Protective snapshot and review before future activation

1. Obtain separate Lab deployment authorization and an idle Lab window. Confirm
   no other Agent/user has pending chat, upload, TTS or Arena work. Unknown or
   background work is not assumed complete; never kill accepted memory jobs.
2. Refresh metadata snapshots: Git HEAD/status/index and hashes of every tracked
   and untracked Lab file; image/container IDs, sanitized effective Compose hash,
   mounts, current Pipe content/valves hashes and all relevant service PIDs.
   Store full inspect/config securely with mode 0600 outside Git; they contain
   credentials. Do not copy chats/private memory into project logs.
3. Take a current consistent backup using the existing Lab backup procedure.
   Preserve the WebUI data volume/uploads and SQLite (including WAL consistency).
   An online SQLite backup or a reviewed quiesced snapshot is required, not a bare
   copy of a live db file. Verify the backup privately and retain the old image.
   This preparation took metadata snapshots only; no new private-data backup is
   claimed. Do not substitute a stale October 20 backup.
4. Validate the merged candidate Compose against the **current** effective
   configuration. Only `services.open-webui.image` and `pull_policy=never` may
   differ. Preserve project name, env, volumes, secrets and bind paths. Check
   the actual rendered mounts against current container inspect; relative paths
   are resolved from the existing base Compose file. Never print full config.

Once all gates pass and activation is separately authorized, the reviewed shape
of the only recreation command is (not executed during preparation):

```bash
docker compose -p corvus-lab-open-webui \
  -f /home/ethan/.config/corvus-lab/chat-recovery-runtime/recovery/candidate-compose.json \
  -f /home/ethan/srv/apps/corvus-voice-v1/deploy/lab/voice-call/compose.candidate.json \
  up -d --no-deps --pull never open-webui
```

## Minimal real acceptance and rollback

Use one labeled synthetic Lab conversation, through the actual authenticated
HTTPS browser/microphone. Check Chinese/English recording, edit/send, saved user
and assistant text, Kokoro sound, second turn, stop speaking, hangup and ordinary
Dictation/text. Check one existing Web/source-link case and Arena case; no Voice
prompt/model/valve override may alter its A/B comparison. Inspect timeouts using
offline tests rather than destructive live faults. Never automatically resend an
unknown result. Real audio perception and actual deployed request/persistence
checks remain pending; mocks are not this acceptance.

If unhealthy or functionally regressed, restore only the old WebUI image with the
same reviewed base Compose and `compose.rollback.json`:

```bash
docker compose -p corvus-lab-open-webui \
  -f /home/ethan/.config/corvus-lab/chat-recovery-runtime/recovery/candidate-compose.json \
  -f /home/ethan/srv/apps/corvus-voice-v1/deploy/lab/voice-call/compose.rollback.json \
  up -d --no-deps --pull never open-webui
```

Recheck old immutable image, health, login/text, Dictation/Read Aloud, Pipe binding,
unchanged API/other-service PIDs and protected Git hashes. Do not use `compose
down`, remove volumes or restore databases for an image rollback. Preserve new
messages, votes and accepted background operations. Database disaster recovery,
if ever needed, requires separate assessment/authorization. A normal rollback
must not erase newly accepted work.

## Limits carried forward

The existing BackgroundTasks -> durable retain-intent crash window and missing
automatic reconciliation remain. Canonical persistence/operation identity and
all retry/admission logic are untouched. This preparation does not certify
end-to-end memory completion, deployed STT-refactor compatibility or personality
quality. Serial model contention and current waiting are accepted for V1.
