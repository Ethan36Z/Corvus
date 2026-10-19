# STT-R3 — native dictation source candidate, offline only

Baseline: local R2 commit `3affe0f0899d2158a66b4259cb7295ef0a4b0810`.
Both R2 live dispatch entry points remain disabled and byte-identical to R2.
No build/deployment/restart, real microphone, inference or dependency download.

## Reuse and exact source edits

`prepare_frontend.py` accepts only the three SHA256-pinned reviewed WebUI 0.6.5
source files. It verifies all pins first and writes four prepared sources to a
separate, empty output tree; it refuses the input tree/overlapping trees or
existing output files. It never patches a running service or compiled bundle.

Prepared targets:

- Native `MessageInput/VoiceRecording.svelte`: same complete template/buttons/
  visualizer, same getUserMedia constraints and MediaRecorder interaction. Retain
  actual chunk/recorder MIME and matching filename extension. No fabricated WAV.
- Native `MessageInput.svelte`: remove only automatic submission from the existing
  VoiceRecording confirm handler. Keep appending text to the same editable prompt,
  closing recording and focusing the input. Normal manual send remains unchanged.
  The existing speechAutoSend store/preference is neither deleted nor rewritten.
- Native `apis/audio/index.ts`: retain STT route/multipart/Bearer authentication;
  add optional AbortSignal, no-store/error redirects, and static error messages.
  Remove STT error-object console logging. All TTS API code remains byte-identical.
- New `utils/corvus-dictation.ts`: small metadata and canonical-WAV validator only;
  no decoder, resampler, converter, network client, persistence or UI component.

Recorder response/event console logging is removed. Generic recorder logging and
the unused recording-download helper are also absent from the private flow.
Browser/vendor SpeechRecognition overrides fail closed before microphone access;
no external browser-recognition fallback is used. Other UI/settings modes are not
rewritten, and the preference remains available for future voice modes.

## Strict format boundary

Chunk MIME is preserved, falling back only to the recorder's reported MIME when
chunks omit it. Missing/unknown or conflicting container types fail closed.
WebM/MP4 retain their real types/extensions and are rejected before upload.

Only complete canonical PCM16 WAV at 16 kHz, mono/stereo, nonempty and no more than
120 seconds / 8 MiB passes the client validator. It checks RIFF length, fmt/data
chunks, sample encoding/alignment/rate and sample payload. It is intentionally
strict (standard 16-byte PCM fmt chunk); it never converts or weakens R2 validation.
A WAV MIME label on non-WAV bytes fails. R2 remains authoritative and unchanged.

There is therefore no claim that actual browser MediaRecorder output is usable
with R2. A successful mocked synthetic WAV tests the future composer contract,
not browser codec support or speech recognition accuracy.

## Cancellation and cleanup

Cancel/destroy invalidates a recording generation, clears confirmation and
chunks, stops the recorder/tracks/timer, closes the native visualizer AudioContext
and aborts an in-flight STT fetch. Late permission acquisition closes its tracks.
Late/stale recorder and HTTP callbacks cannot dispatch a transcript or release a
new recording's media. No cancelled audio is intentionally submitted, and late
responses after cancellation never enter the composer. Abort cannot retract an
already-sent HTTP body or stop R2's synchronous upstream worker; its server-side
cancellation/privacy limitation remains unresolved.

Dictation success emits only text to the existing confirm handler. There is no
chat submit, canonical/message/memory API, upload attachment, second composer or
custom microphone. No stored settings are modified. This is scoped dictation-log
removal, not a claim that every unrelated frontend diagnostic is hardened.

## Offline checks and limits

Prepare into a fresh temporary output directory with:

`python3 -B deploy/lab/stt/prepare_frontend.py <reviewed-source-root> <isolated-output>`

Then run `node tests/test_lab_webui_dictation.mjs <output> <reviewed-source-root>`.
The test uses existing local Svelte 4.2.19 and TypeScript 5.5.4 under the retained
WebUI build fixture, not downloaded packages. It compiles both components, checks
byte-identical recorder markup, and executes actual patched scripts/handlers in
VMs with fake MediaRecorder/media streams, synthetic Blob/File objects and mocked
APIs. Reactive scheduling/DOM mounting are not browser-E2E tested. No real
microphone, recognition service, backend or network is used by these new tests.

R2 disabled-entry/auth/storage tests and existing TTS/Pipe contracts also pass.
No full WebUI image/app build is produced. Future packaging must preserve the
existing TTS-enabled/branding baseline and R2 source pins; it is not authorized.

## Later browser-only feasibility (assessment, not implementation)

[decodeAudioData](https://developer.mozilla.org/en-US/docs/Web/API/BaseAudioContext/decodeAudioData)
accepts complete encoded file data and resamples decoded audio to its context's
rate. A bounded [OfflineAudioContext](https://developer.mozilla.org/en-US/docs/Web/API/OfflineAudioContext/OfflineAudioContext)
requesting 16 kHz could support a later decode/downmix/resample stage, followed by
explicit clamped PCM16 quantization and finite WAV header encoding. These are
possible Web Audio building blocks, not verified Safari/Chromium codec support,
resampling quality, resource bounds or cancellation guarantees. No such path was
implemented or exercised; unsupported inputs remain rejected. Actual complete
WebM/MP4 fixture decoding and target-device validation need a separate stage.

Shared Whisper --convert temp retention, host swap/core/hibernation, ingress
buffering and R2 hard-deadline/worker cleanup remain blockers to live activation.
Review-before-send is verified here only for the patched native handler and mocked
response flow. No complete product/privacy acceptance or deployment is claimed.
