# Voice V1 — full build blocker resolved, candidate ready

2026-10-23. **READY_FOR_LAB_ACTIVATION**, not deployed. This supersedes the
resource-blocked status in `2026-10-23-voice-v1-build-readiness.md`; its earlier
failure evidence remains historical. Application revision:
`f6d94ffe48b2e07bd1adf0c5dc776850bb9c1980`, branch
`feature/voice-v1-half-duplex`. Preparation commit: `b415ac958aa501c2d2bb33be57fed07c82a6411b`.

## Resource-controlled full build

Explicit authorization allowed increasing only the offline build's V8 heap.
Preflight found about 6.3 GiB host available RAM, full swap, no inherited
NODE_OPTIONS and unlimited memory.max/high in session/user-slice ancestors.
The previous 512 MiB heap was an explicit per-build flag, paired with a 768 MiB
Docker cap. No running service or system-wide configuration was changed.

2 GiB old-space / 3 GiB container still exhausted V8 heap (exit 134, 83.14s).
Its peak cgroup memory was 2966634496 bytes (2.76 GiB); host minimum available
3872157696 bytes (3.61 GiB). After it exited, at least 6 GiB available RAM and
no competing large build were required for the single 3 GiB attempt.

3 GiB old-space / 4.25 GiB container **passed**, exit 0, 114.10s. Original Vite
configuration retained sourcemaps/compression reporting: SSR transformed 1214
modules, client 4544 modules, adapter-static wrote `build/`. Peak cgroup memory
4563402752 bytes (4.25 GiB, includes charged cache); minimum host available
5968793600 bytes (5.56 GiB). cgroup max events=161, oom=0, oom_kill=0. The host
safety watchdog (1.5 GiB minimum) did not trigger. Both builds had no network,
no extra swap and a two-core limit; they were sequential. No 4 GiB heap attempt
was made. Build warnings included Svelte/package metadata and large chunks;
no application or build-source workaround was introduced.

Node 22.16.0 builder and unchanged SHA-verified lock/cache were reused, including
existing static Pyodide assets rather than its network-fetch preparation step.
No dependency upgrade/install in live source. Application sources are unchanged.

## Candidate and offline proof

Tag: `corvus-lab-webui:voice-v1-f6d94ff-candidate`.
Image: `sha256:5058ab1bdfd1112c38dda284f67c76717c0d6faf5eb425e59a0229f980c3ec6d`.
Base: `sha256:2427456fa33f5eccf8a854f9ad37f3af05f0cc443ae6348468f136a25a0745dc`.
Packaging completed offline with no dependency installation; only `/app/build`
was replaced in the independent image. No current tag was overwritten.

- All 4751 frontend files (312431993 bytes) match the successful full build.
- All 349 application source-map entries match assembled source; all seven Voice
  output files match the overlay proof. Call launcher/panel are baked enabled.
  Svelte retains an unused disabled-branch factory; checking for absence of its
  text was initially too strict. Checking actual constant branch selection and
  launcher verified the gate, without changing code or rebuilding.
- All 207 backend files match base, including STT/TTS/Vision and Pipe-facing
  endpoints. Inherited runtime configuration/base-layer prefix match; old labels
  are preserved and Voice labels added. Mounted STT protocol/config are unchanged.
- Verification ran Python hashing only in no-network/read-only disposable
  containers without real data mounts. No WebUI server was started. Existing
  261-case backend compatibility (259 pass, two offline skips), six assertion
  scripts and frontend/Voice/Dictation/Vision evidence were reused.

The frontend-only image plan does not deploy API transcription refactor `688a8bb`.
No scheduling, memory flow, prompt, Hindsight or model parameter change was made.
Image parity is not deployed microphone/audio-quality or persistence acceptance.

## Protected state and activation gate

Final before/after metadata matches the preceding preparation and this task:
integration/main/Lab HEAD/status/index and all tracked/untracked hashes; all
**28** dirty Lab files; relevant service PIDs/environment hashes/dropins and all
existing container identities/configuration. Live Lab WebUI remains healthy on
the old image. Candidate Compose changes only the WebUI image; rollback Compose
renders identically to the current base. No deployment, service restart,
Production/Demo edit, database change, push or merge.

`deploy/lab/voice-call/LAB_ACTIVATION.md` retains exact image-only deployment and
rollback commands, fresh consistent backup/idle-window checks and minimal real
client acceptance. Separate activation authorization is still required. The
existing BackgroundTasks -> durable retain-intent gap, missing automatic
reconciliation and P0.2 BLOCK remain; end-to-end memory reliability and personality
quality are not certified by build/integration success.

Local evidence: `/tmp/corvus-voice-v1-stage-ku_7qzxo/heap2048/`, `heap3072/` and
`candidate/` (full logs, resource samples, manifests and protected-state proof).
Sanitized persistent summary: `deploy/lab/voice-call/build-readiness.json`.
