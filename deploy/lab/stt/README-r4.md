# STT-R4 — browser WAV candidate, offline only

Supersedes R3's format-rejection-only candidate; preserves its native UI,
review-before-send, authentication, cancellation and no-log behavior. Both R2
entry points remain disabled, with no environment/header switch to enable them.
No service/image/shared Whisper or canonical data changes are included.

## Narrow implementation

`prepare_frontend.py` retains all original WebUI 0.6.5 source SHA256 pins and safe
isolated output rules. It now adds `src/lib/utils/corvus-normalize.ts` from
`normalize.ts` and calls it from the existing native recorder handler. The
recorder template/composer/API source changes relative to R3 remain unchanged;
only the recorder script gains normalization and capture limits. No new UI,
transport, converter service, package, engine or model is introduced.

Input metadata remains the real MediaRecorder chunk/recorder MIME and container.
Supported input families are WebM, MP4 and PCM16 RIFF WAV, contingent on actual
browser decoding. PCM WAV preflight allows 8–96 kHz mono/stereo, standard fmt16.
Other containers fail closed, including formats the R3 metadata helper can name.
Declared RIFF/MP4/WebM element sizes are checked before decode. Unknown WebM
Segment length is supported; other unknown-length WebM elements are rejected.
This is a conservative container boundary check, not a complete codec parser or
integrity checksum. A shortened stream ending exactly on a valid block boundary
may be indistinguishable from a legitimately shorter recording; decoder-tolerated
bitstream damage is not universally detectable. Tested corrupt and byte-truncated
fixtures are rejected. Do not claim arbitrary truncation/corruption detection.

`OfflineAudioContext(1, 1, 16000).decodeAudioData()` supplies resampling using the
browser decoder. Output must actually report 16 kHz and one/two channels, be
nonempty and no longer than 120 seconds. Stereo is explicitly averaged, then
finite samples are clamped and quantized to signed PCM16. A new mono WAV Blob is
encoded with exact finite RIFF/data lengths and validated by the existing client
validator before upload. R2 server validation stays authoritative and unchanged.
Encoded input is never relabeled to pretend it is WAV.

## Bounds, cancellation and memory limits

- Encoded Blob input: nonempty, at most 8 MiB, before arrayBuffer/decode.
- Native recorder requests one-second chunks, caps accepted chunk accumulation at
  8 MiB and cancels at 120 elapsed counter ticks. Timeslice/timer scheduling and
  browser-internal recorder buffers are not hard realtime/memory guarantees.
- Output: 1–1,920,000 frames; at most 3,840,044 bytes, including 44-byte header.
  Validate frame/channel/rate/output bounds before allocating the output WAV.
- One normalization operation per loaded module. A 15-second logical deadline
  aborts result delivery. A still-running native decoder keeps the slot occupied
  until its promise settles; subsequent normalization fails closed.
- Abort stops result delivery promptly, and guards every later stage. PCM encoding
  yields/checks abort every 16,384 frames. Native decode is not synchronously
  cancellable by this code. Do not describe timeout/abort as decoder termination.

[decodeAudioData](https://developer.mozilla.org/en-US/docs/Web/API/BaseAudioContext/decodeAudioData)
requires complete encoded data and returns a decoded/resampled buffer. Its
[specified algorithm](https://webaudio.github.io/web-audio-api/#dom-baseaudiocontext-decodeaudiodata)
decodes on a decoding thread; no AbortSignal or application allocation cap is
provided. The context's length=1 configures its render buffer, not a one-frame
cap on decoding. Duration/channel validation happens after native allocations.
8 MiB of compressed input is not a hard decoded-memory bound. Maliciously long
or multichannel compressed content could exhaust renderer/native resources first.
The latch and deadline limit accepted operations/results, not native allocation,
CPU, garbage-collection timing or host swap/dump exposure. There is no claim of
immediate RAM erasure or a hard decoder resource envelope.

Cancel/destroy and recording-generation guards prevent late decoded/transcribed
results entering the composer. Abort cannot retract an HTTP body already sent or
stop R2's synchronous upstream worker. No retry/fallback/storage/logging is added.
The original speechAutoSend preference remains stored; dictation never submits.

## Reproducible offline validation

Prepare into a fresh isolated output tree:

```
python3 -B deploy/lab/stt/prepare_frontend.py <reviewed-WebUI-source> <fresh-output>
node tests/test_lab_webui_dictation.mjs <fresh-output> <reviewed-WebUI-source>
node tests/test_browser_wav.mjs
node tests/test_browser_wav_chrome.mjs
```

Native script tests use the already installed Svelte/TypeScript fixture toolchain.
The Chrome test launches the existing Linux binary with a fresh disposable
profile, CDP pipe, URL blocking and background networking disabled. It does not
open deployed URLs, request microphone permission or disable the Chrome sandbox.
It removes its own exact fresh profile after browser exit. It writes synthetic
output evidence under `/tmp`, never user audio. No browser/packages are installed.

`tests/fixtures/stt-r4-synthetic.json` contains synthetic audio only: WebM/Opus from
a 440 Hz oscillator connected to a MediaStreamDestination/MediaRecorder in Chrome
155; AAC/M4A from a 0.5-second 440 Hz, 48 kHz stereo signal encoded with an existing
offline ffmpeg image. The latter has mdat before moov and was generated in a
network-disabled, read-only container with no mounts, using memfd. That exact
identity-checked container was removed. FFmpeg is test-fixture generation only;
there is no application/server-side FFmpeg dependency or conversion path.

Results: 15 native frontend contracts, 11 mock WebAudio/PCM tests and 6 actual
Chrome test groups pass. The native Svelte components compile and helper files
pass strict TypeScript checking. Three real normalized outputs also pass unchanged
R2 `validate_audio`. Existing R2/TTS/Pipe regressions: 11 + 22 + 25 pass in isolated
synthetic storage with zero live network/model/deployed-data access violations.

Actual Chrome 155.0.8059.84 decodes WebM/Opus, trailing-moov MP4/AAC and PCM WAV.
It reports WebM/Opus recording support, but not the tested AAC recorder MIME.
AAC decoding success does not imply AAC recording support. The 48 kHz stereo
WAV test yields exactly 1,600 mono frames from 4,800 input frames; a constant-level
resampling check allows 8 PCM units for browser filter ripple (observed 3).
Mock tests verify exact quantization/clamping/downmix values separately.

No real microphone, Safari/iPhone/Mac/Firefox acceptance, mounted native DOM,
full WebUI build, language accuracy or live transcription is validated. Both R2
gates, shared Whisper --convert retention, server cancellation/ingress buffering,
host swap/core/crash-dump/hibernation and target-device privacy acceptance remain
open. Browser memory bounds above are explicit limitations, not waived privacy
requirements. No live activation or complete privacy acceptance follows R4.
