# Voice V1 — opt-in half-duplex Call overlay

Status: **READY_FOR_LAB_ACTIVATION; not deployed**.
Full Vite/static build and independent candidate image passed offline checks.
See [Lab activation plan](LAB_ACTIVATION.md) and [build evidence](build-readiness.json).
Base: `93315415cf9efb541108e6f4fbcd3eb5967c9823`.

Reliability and Memory Integrity First. Latency Optimization Second.

This is an overlay for the existing reviewed Open WebUI 0.6.5 frontend, not a
second chat runtime. It reuses the native Call entry/panel container,
`VoiceRecording.svelte`, its current WAV normalizer/validator and authenticated
STT route, `submitPrompt`, the Corvus Pipe, and the installed Kokoro Read Aloud
route. Canonical SQLite, Hindsight, admission, Personality, Web and Arena code is
unchanged. No raw audio is added to the Corvus attachment store: as in dictation,
only the reviewed transcript is sent as a normal text turn. Unsent audio is
transient, not a promised archived memory.

## Behavior

One turn at a time:

`Idle → Listening → Transcribing → Review → Thinking → Synthesizing → Speaking → Idle`

The user explicitly records, stops/transcribes, edits if needed and sends. The
microphone is released before waiting for the saved reply or speaking. Repeat
with **Record a turn**. Ordinary Dictation remains editable/manual-send even if
its old speechAutoSend preference is true. The Call loop keeps transcription and
submission separate (`transcribed` / `send`); a later Call-only automatic mode
can call `send` after transcription without changing Dictation or adding another
backend. There is no auto-submit setting in this first release.

- **Cancel recording** aborts local transcription/normalization and discards late
  media callbacks; no chat request has been submitted.
- **Stop speaking** aborts the TTS fetch, stops playback and releases its object
  URL. Already admitted upstream compute may continue; it is not a model-slot
  cancellation mechanism.
- **End call** releases media but does not call stopResponse or cancel submitted
  chat/background memory. The existing chat request may finish after hangup.
- Submission is attempted once. Errors or a five-minute UI wait ceiling yield
  **Unknown** and block further Call sends. There is no automatic retry. End the
  call and inspect the conversation before any manual recovery. A validated late
  completion unlocks the loop but is not played unexpectedly.
- A speech failure leaves the saved text available. **Replay saved reply** retries
  only TTS/playback, never the chat. Autoplay refusal is a visible speech error.
- UI correlation survives layout remount/hangup through an EventTarget-scoped
  WeakMap. This is not durable request idempotency or browser-crash recovery.
- Speech requires a fresh matching native response ID, matching user parent,
  Corvus model, full matching content, done state and no native error. The existing
  Pipe must continue rejecting non-NORMAL persistence. Partial chat events are
  never spoken. Native WebUI SSE delivery is retained; true token streaming is
  not implemented.

Errors are shown without private provider text. New Call code has no content
logging or client storage writes. In Corvus mode the old native Call lifecycle,
continuous recording, optional emoji request and browser-Kokoro initialization
are bypassed. Other models retain native behavior. Native authentication and
permission checks are retained.

## Preparation and default-off gate

`prepare_frontend.py` checks all five source SHA-256 pins before writing anything.
Inputs are the reviewed **already STT-patched** frontend (including its current
composer), not an arbitrary upstream archive. It writes seven overlay files and
`voice-v1-proof.json` to a fresh separate directory; it does not copy a whole
application, build an image or touch the source tree.

```bash
python3 -B deploy/lab/voice-call/prepare_frontend.py \
  /path/to/reviewed-webui-source /tmp/fresh-voice-v1-overlay
```

Apply only those output files to another disposable copy of that verified source,
keeping the existing STT normalization, TTS, HTTPS, branding, Vision and Arena
packaging. Rebuild with the existing pinned dependencies. **Build-time** selection:

```text
VITE_CORVUS_VOICE_CALL=true
```

Absent/other values disable Corvus Call before microphone acquisition. The gate
is for exact model ID `corvus_pipe`. Setting an environment variable on an already
built container does not change a Vite-baked flag. No active env file or Compose
configuration is included or modified here. The exact pin check fails on upgrade;
review the source change rather than force-applying this overlay.

Generated native edits are limited to:

1. Call entry: Corvus-only gate and direct entry, avoiding legacy microphone probe
   and browser-TTS model loading.
2. CallOverlay: gated Corvus panel; skip old lifecycle for Corvus.
3. ChatControls: pass existing history; key both responsive layouts by model ID.
4. VoiceRecording: optional Call-only phase/error events, default false.
5. Audio client: optional fifth AbortSignal for TTS, preserving the existing body,
   auth and old callers; STT and other audio routes stay exact.

The two new files are the small presentation coordinator and Call panel. No
backend endpoint, queue, memory worker, model setting or prompt is introduced.

## Offline checks

Use Node 24 (the existing Node stripTypeScriptTypes harness), Python unittest and
the **existing locked** Svelte 4.2.19 / TypeScript 5.5.4 / esbuild 0.25.1 packages.
`CORVUS_FRONTEND_PACKAGE` is a package.json next to the test dependency node_modules.
Do not install these dependencies into the live source or rebuild a running image.

```bash
node tests/test_voice_call.mjs
CORVUS_VOICE_V1_SOURCE=/path/to/reviewed-webui-source \
  python3 -B tests/test_voice_call_package.py
CORVUS_FRONTEND_PACKAGE=/path/to/compiler/package.json \
  node tests/test_voice_call_compile.mjs /tmp/assembled-disposable-source
CORVUS_FRONTEND_PACKAGE=/path/to/compiler/package.json \
  node tests/test_lab_webui_dictation.mjs /tmp/assembled-disposable-source /path/to/reviewed-webui-source
CORVUS_FRONTEND_PACKAGE=/path/to/compiler/package.json \
  node tests/test_voice_call_browser.mjs /tmp/assembled-disposable-source
```

The assembled disposable source must include the unchanged existing
`corvus-normalize.ts` and `corvus-dictation.ts`, in addition to overlay outputs.
The browser uses a fresh Chrome profile, fake media device, synthetic WebM/PCM,
real native Svelte recorder/converter and simulated APIs. It directly mounts the
native CallOverlay; it checks two turns, manual edit, save-before-speech, zero
chat-abort calls, and released tracks/URLs. This is not a real microphone,
model, authenticated deployed WebUI or acoustic listening acceptance.

## Known risks and Lab acceptance prerequisites

The pre-existing BackgroundTasks → durable retain-intent gap remains: a process
crash after canonical persistence but before intent fsync can omit background
submission; reconciliation has no automatic startup/timer integration. This work
neither replaces the flow nor guarantees end-to-end memory completion. Existing
operation UUID/fingerprint, retry/deferral semantics and original message ordering
are untouched. P0.2 BLOCK is unchanged.

Serial model contention and CPU STT latency remain. Recording format limits are
not an interactive latency guarantee; long recordings can hit the existing Bridge
deadline and require a shorter new recording. Browser/network interruption after
submission can leave an unknown result. No generated answer is claimed saved
without the existing successful Pipe path; unacknowledged work needs verification.

Before any separately authorized Lab activation:

- Recheck Lab isolation, current image/source/Function/valves and all dirty files;
  use only the reviewed Lab `corvus_pipe` bound to API 18096 and current STT/TTS.
- Produce and inspect the full WebUI build/image through existing packaging,
  with sufficient **bounded** offline build resources. This gate now passed with
  a 3 GiB old-space cap; retain the verified candidate/provenance in the activation
  plan rather than rebuilding or deploying an unverified artifact.
- Snapshot the existing Lab WebUI artifact/config/data and prepare image-only
  rollback. Do not restore databases or cancel accepted memory work.
- Verify real login, permission handling, Chinese/English microphone/edit/send,
  saved text, Kokoro playback and repeated turns on the actual client browser.
  Include stop, hangup, timeout/unknown and ordinary text/Dictation regression.
- Observe memory processing progress and existing backlog/failures without
  destructive live fault injection. Do not declare the known recovery gap closed.

Future rollback disables this build-time mode or restores the reviewed prior
Lab frontend image, under separate deployment authorization. It never deletes
conversation records, ledger identities or accepted Hindsight operations.
