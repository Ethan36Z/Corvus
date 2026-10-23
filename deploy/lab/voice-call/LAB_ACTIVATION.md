# Voice V1 — build gate and Lab image-only activation plan

2026-10-23. **BLOCKED_RESOURCE / NOT_READY_FOR_LAB_ACTIVATION**.
This is preparation, not deployment authorization. No candidate image exists.
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

## Build completion gate (not met)

All 990 applicable cached packages were restored with lock-integrity checks;
111 incompatible-platform optional packages were omitted. The lock is unchanged.
The complete Vite invocation, with the opt-in flag enabled, ran twice. Both SSR
passes transformed 1214 modules; both client passes exhausted the 512 MiB V8 heap
inside a 768 MiB container (exit 139). Disabling sourcemaps/compression reporting
in the disposable build copy did not complete the client build. Partial SSR
output is not a deployable application. No larger-budget build was started.

Host available RAM was approximately 1.3 GiB with swap full. The user chose to
keep current resources and report the blocker. Do not stop services/apps, alter
swap or keep retrying. Resume only under a separately suitable bounded build
budget (at least 3 GiB available host RAM is a conservative starting condition,
not a guarantee). Require an exit-0 **full** Vite/adapter-static build, unchanged
lock and reviewed warnings before packaging. Use the existing verified static
Pyodide assets; do not download/upgrade dependencies. Record the config used.

Build workspace: `/home/ethan/srv/build/corvus-voice-v1-f6d94ff/source`.
Pinned Node 22 builder image:
`sha256:35d1e2d251585b806c41f71d0933d7ba3afb6374ee3745523c2ae406480f6bc7`.
Full lock SHA-256:
`d140bb9648ff22a039826c710fc5bfa4e5e36b8660ea6e97c9253025cbb1ead9`.
The already assembled source has a verified seven-file Voice overlay; 347 mapped
application sources matched the deployed frontend before applying it.

After full success, prepare a clean packaging context containing only the output
`build/` and `Dockerfile.candidate`. Confirm `index.html`, immutable bundles,
existing branding/assets and the Vite-baked Voice gate; run the existing compiler,
package, Dictation, Call and Vision checks. Build offline with no dependency
installation and the independent tag `corvus-lab-webui:voice-v1-f6d94ff-candidate`.
Never overwrite a current tag or package `.svelte-kit/output/server` as `build/`.
The recipe's presence checks do not replace the exit-0 build requirement.

Inspect the resulting image without starting its server: compare all backend
file hashes against the base, particularly audio/STT/TTS/Vision, main.py and
models/files.py; inspect image config for inherited entrypoint/environment.
Account separately for the unchanged mounted STT protocol. Save immutable
candidate ID and build provenance. These image checks remain pending.

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
