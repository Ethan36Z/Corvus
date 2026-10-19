# STT-R3 — Native dictation UX, offline candidate

Date: 2026-10-19
Verdict: **STT_R3_NATIVE_UX_READY_OFFLINE**
Deployment and live STT: **not authorized; both R2 entry points remain disabled**.

## Baseline and scope

Continue from local R2 `3affe0f0899d2158a66b4259cb7295ef0a4b0810`, using its
[completed adapter report](2026-10-19-stt-r2-webui-adapter.md) and the recorder
findings in [STT-1](2026-10-19-stt1-whisper-offline-integration.md). No environment,
codec or broad multimodal investigation was repeated.

Local implementation commit: `0489bd7409f5e6a95a41acf42027fca651a1e658` on
`integration/stt-r3-native-dictation`, based on R2 in a new isolated worktree.
This commit is local only. Four repository files were added:

- `deploy/lab/stt/prepare_frontend.py`
- `deploy/lab/stt/dictation.ts`
- `deploy/lab/stt/README-r3.md`
- `tests/test_lab_webui_dictation.mjs`

The preparer verifies all three reviewed Open WebUI 0.6.5 source SHA256 pins
before writing an isolated candidate tree. It refuses overlapping input/output
and existing output files. No running source tree, image or compiled bundle was
changed. Earlier STT worktrees, including uncommitted privacy/storage drafts,
retain their original HEAD, status and draft file hashes. Active Lab stays clean.

## Native UI reuse and exact prepared changes

The existing `MessageInput/VoiceRecording.svelte` template, buttons and visualizer
remain byte-identical. The native MediaRecorder interaction and microphone
constraints remain. No custom microphone, second composer or recording UI was
introduced.

The recorder script preserves nonempty chunk MIME, falling back only to the
recorder-reported MIME, including codec parameters. Filename extensions match the
reported container. Missing, unknown or inconsistent container metadata fails
closed. WebM and MP4 are never relabeled WAV. Transcript/event console logging,
generic recording diagnostics and an unused download helper are absent from the
private recorder flow. A browser SpeechRecognition override fails closed before
microphone acquisition instead of switching to a vendor recognition service.
Stored preferences are untouched.

In native `MessageInput.svelte`, only the dictation-confirm automatic-submit block
is removed. The recognized text is appended to the same editable prompt, the
recorder closes and input focus returns. No submit event occurs even when
`speechAutoSend` is true. The preference remains stored and available for future
voice modes; ordinary manual send behavior is unchanged.

In native `apis/audio/index.ts`, the STT helper retains its route, multipart
fields and Bearer authentication. It gains optional AbortSignal, no-store and
redirect rejection, and static sanitized errors without error-object logging.
The TTS API suffix is byte-identical. New `utils/corvus-dictation.ts` supplies
metadata validation and a strict WAV validator only, with no conversion,
persistence, extra network transport or UI.

Removal of logging is scoped to dictation and its STT API helper. This does not
claim that unrelated frontend diagnostics have been universally hardened.

## Format gate: compatibility deliberately remains closed

Only finite canonical PCM16 WAV at 16 kHz, mono/stereo, with valid RIFF length,
standard 16-byte PCM fmt chunk, byte rate, alignment and complete nonempty data
passes. Input is bounded to 8 MiB and decoded PCM duration to 120 seconds. R2's
server-side validator remains authoritative and unchanged. Corrupt WAV bytes
with a WAV MIME label fail. Compressed browser containers are rejected locally
before upload; no converter or validation bypass was introduced.

Successful synthetic WAV/mock-response tests establish the composer contract.
They do not establish that real browsers emit acceptable WAV, Chinese/English
recognition accuracy, or a usable end-to-end dictation feature. Existing A3
transport, language/prompt behavior and provenance code are unchanged; its
previous R2 evidence is reused, not described as newly executed A3 tests.

## Cancellation and privacy behavior

Cancel/destroy invalidates the current recording generation, drops pending
confirmation/chunks, stops recorder/tracks/timer, closes the visualizer audio
context and aborts a pending STT fetch. Late microphone permission closes newly
acquired tracks. Stale recorder callbacks cannot release a later recording's
media; late HTTP results cannot enter the composer after cancellation.

Cancellation before submission sends no audio. Aborting a fetch after it starts
cannot retract already transmitted bytes or terminate R2's synchronous Whisper
worker. This server cancellation limitation remains unresolved. The candidate
creates no persistent audio/transcript cache and invokes no attachment, chat,
canonical memory or artifact API. No automatic submission is activated.

Both exported R2 dispatch entry points and their disabled gates remain
byte-identical. Native backend authentication remains unchanged, including its
existing user metadata semantics; this report makes no claim of zero incidental
WebUI authentication metadata updates.

## Offline validation

All audio inputs and responses were synthetic/mocked. Existing local tools were
reused without installation or downloads.

| Check | Result and boundary |
| --- | --- |
| Frontend contract tests | 12 passed, 0 failed |
| Native Svelte compilation | Both patched components compile using existing Svelte 4.2.19 / TypeScript 5.5.4 |
| R2 auth, disabled gates, storage and bounds | 11 tests passed |
| Existing TTS contracts | 22 tests passed |
| Existing Pipe contracts | 25 tests passed |
| Backend isolation harness | Zero forbidden network, deployed-data or model-access violations |
| Source pins/output safety | All pins checked before output; changed-source rejection verified |
| Scope and preservation | Four implementation files only; prior drafts unchanged; active Lab clean |

Frontend tests execute actual prepared scripts/handlers with mocked media APIs
and synthetic Blob/File objects. They cover native markup preservation, WebM/MP4
metadata, strict unsupported/corrupt/misrate rejection, authenticated synthetic
WAV success, composer insertion with auto-send preference true, cancellation
before stop/during permission/during HTTP, destroy cleanup, stale callbacks,
browser-engine rejection, sanitized errors, redirects/cache and unchanged TTS.
No canonical send or memory API is invoked by the dictation flow.

An initial test harness reactive-block extraction error was corrected before the
final passing run. These are compiler and mocked script tests, not mounted-DOM,
reactive scheduling, actual microphone or browser end-to-end tests. No full WebUI
application/image build, running Whisper call, real recording or inference was
performed. Existing TTS/Pipe regression fixtures are isolated; their synthetic
writes do not imply access to canonical deployed data.

## Later browser decoding assessment

The documented [decodeAudioData API](https://developer.mozilla.org/en-US/docs/Web/API/BaseAudioContext/decodeAudioData)
uses complete encoded file data and resamples to the audio context's sample rate.
A bounded [OfflineAudioContext](https://developer.mozilla.org/en-US/docs/Web/API/OfflineAudioContext/OfflineAudioContext)
at 16 kHz is a possible basis for later decoding/downmixing/resampling, followed
by explicit PCM16 quantization and finite WAV encoding. This is an assessment,
not implemented or verified browser support. Target-browser container decoding,
resource limits, cancellation, quality and resulting WAV validity remain untested.

## Remaining blockers and smallest next step

Shared Whisper still runs with `--convert`; failure-file retention and immediate
reclamation remain unresolved. Host swap, core/crash dumps and hibernation risks
are not resolved or newly verified here. Ingress buffering, R2 hard deadlines and
worker cleanup also remain open. No complete privacy acceptance is claimed.
No host, shared Whisper, WebUI, TTS, Pipe, Production or Demo service was changed
or restarted; neither live STT entry point may be enabled from this result.

The smallest next step is a separately authorized, bounded browser-only
canonical-WAV prototype using complete synthetic WebM/MP4 fixtures, with explicit
input/output/duration limits and cancellation/resource tests. Preserve the native
recorder/composer and both disabled server gates. Target-device acceptance and
the shared Whisper privacy gate must be resolved before any live activation.
No deployment follows this report.
