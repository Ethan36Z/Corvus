# STT-R4 — Browser-only canonical WAV normalization

Date: 2026-10-19

Verdict: **STT_R4_BROWSER_WAV_READY_OFFLINE**

Deployment/live transcription: **not authorized; both R2 live gates remain disabled**.

## Baseline and bounded scope

Based on local R3 `0489bd7409f5e6a95a41acf42027fca651a1e658`, using the complete
[R3 report](2026-10-19-stt-r3-native-dictation-ux.md). Earlier STT environment and
codec investigations were not repeated. Implementation is isolated from active
Lab and all earlier worktrees/drafts.

Local-only implementation commit: `83ca1d38836a45088fa6574ed177b1064a0cd87d` on
`integration/stt-r4-browser-wav`. Seven changed files:

- `deploy/lab/stt/normalize.ts`
- `deploy/lab/stt/prepare_frontend.py`
- `deploy/lab/stt/README-r4.md`
- `tests/test_lab_webui_dictation.mjs`
- `tests/test_browser_wav.mjs`
- `tests/test_browser_wav_chrome.mjs`
- `tests/fixtures/stt-r4-synthetic.json`

No implementation branch was pushed. All seven earlier STT worktrees retain their
HEAD/status and privacy/storage draft hashes. Active Lab remains clean. No
running services, shared Whisper startup, Production/Demo, host security settings,
model, TTS or Pipe configuration was modified. No dependencies/browsers/images
were downloaded. No live Whisper inference or actual microphone was used.

## Reuse and resulting behavior

The original source-pinned WebUI 0.6.5 recorder and composer remain. The preparer
still verifies every source SHA256 before isolated output and rejects changed
sources/overlapping or existing output targets. It now writes a fifth prepared
source, `src/lib/utils/corvus-normalize.ts`, and invokes it in the native recorder
script. The prepared recorder template, composer and native audio API changes
relative to R3 remain unchanged. No custom microphone or second composer exists.

Actual input chunk/recorder MIME is preserved. WebM/MP4 bytes are never relabeled
WAV. The normalizer checks input metadata/container boundaries, decodes complete
encoded bytes through `OfflineAudioContext(1, 1, 16000).decodeAudioData()`, verifies
the resulting frame/rate/channel bounds, explicitly averages stereo channels and
encodes finite clamped signed PCM16 samples into a new mono WAV Blob. RIFF/data
lengths are exact. The existing client WAV validator is applied before the native
authenticated multipart request; the unchanged R2 server validator remains
authoritative. No second Whisper transport or server-side converter is added.

Successful text enters the existing editable composer without automatic send.
`speechAutoSend` stays stored and is not overridden globally. R3 generation,
abort, media/visualizer cleanup, sanitized error and no-transcript-log behavior
remain. Cancelled/stale normalization results cannot dispatch a transcript or
invoke the transcription API. No attachment/artifact, canonical chat or memory
API is added. Native authentication and TTS API source remain byte-identical to
R3; both exported R2 live dispatch gates remain byte-identical and disabled.

## Resource bounds and explicit limitations

| Boundary | Implemented enforcement |
| --- | --- |
| Encoded normalization input | Nonempty, at most 8 MiB before arrayBuffer/decode |
| Native capture | One-second chunk requests; cancel above 8 MiB accepted chunks or 120 elapsed counter ticks |
| Output format | PCM16, 16 kHz, mono, finite standard 44-byte WAV header |
| Decoded/output bounds | 1–1,920,000 frames; at most 3,840,044 output bytes, checked before WAV allocation |
| Concurrent work | One pending normalization per loaded module; other requests fail closed |
| Logical deadline | 15 seconds; suppress results and abort subsequent JS encoding; native decoder may continue |
| PCM loop | Yield/check cancellation every 16,384 frames; reject nonfinite samples |

The browser recorder may allocate a chunk before its size can be checked.
Timeslice/timer scheduling is not hard realtime, and the latch is per module,
not a cross-tab/browser limit.

The [documented decode API](https://developer.mozilla.org/en-US/docs/Web/API/BaseAudioContext/decodeAudioData)
returns decoded/resampled audio from complete encoded input. Its
[specified decoding algorithm](https://webaudio.github.io/web-audio-api/#dom-baseaudiocontext-decodeaudiodata)
provides no application allocation cap or AbortSignal. Context length=1 does not
bound decoded frames. Duration/channel checks occur after native allocation.
Thus an 8 MiB encoded cap does not establish a hard decoded-memory or CPU bound.
An unusually long/multichannel compressed file can exhaust renderer resources
before rejection. No quantitative peak-memory guarantee was demonstrated.

Cancellation rejects result delivery promptly in tests, but cannot synchronously
terminate native decoding. The operation latch stays held until that promise
settles, including after timeout/abort. A hung native decoder can leave the module
unavailable, deliberately without a concurrent fallback. Garbage collection and
immediate RAM erasure are not guaranteed. After an HTTP request starts, abort
cannot retract bytes already sent or stop R2's synchronous upstream worker.

Preflight validates declared RIFF/MP4/WebM element bounds with bounded traversal.
It accepts unknown-size WebM Segment but rejects other unknown-length elements.
Input PCM WAV is deliberately limited to standard fmt16 PCM16, mono/stereo at
8–96 kHz; other containers fail closed. This is not a full codec parser/checksum:
stream truncation exactly on a valid block boundary can resemble a shorter valid
recording, and decoder-tolerated damage is not universally detectable. Tested
malformed and byte-truncated cases fail closed. Arbitrary bitstream integrity is
not claimed, nor silently accepted as a completed mandatory privacy property.

## Offline evidence

| Validation | Result |
| --- | --- |
| Native recorder/composer/auth/error/cancellation contracts | 15 tests passed |
| Mock WebAudio, PCM math, limits, deadline and decoder latch | 11 tests passed |
| Installed Chrome codec/conversion groups | 6 groups passed |
| Actual Chrome outputs through unchanged R2 validate_audio | All 3 passed |
| Patched Svelte compilation | Both native components compile |
| Strict TypeScript checking | Normalizer and existing WAV helper pass |
| Existing R2 backend gates/auth/storage | 11 tests passed |
| Existing TTS contracts | 22 tests passed |
| Existing Pipe contracts | 25 tests passed |
| Regression isolation guard | Zero live network/model/deployed-data access violations |
| Git checks | Whitespace and exact implementation/report scope verified |

Native tests execute actual prepared scripts with mocked media/HTTP, including
successful compressed-input normalization through mocked decoding, editable
composer insertion, no auto-send, no canonical API writes, cancellation during
decode/permission/HTTP and stale results. Mock tests verify exact clipping,
quantization, stereo averaging, byte limits before decode, output allocation
bounds before sample reads, excessive decoded duration after native allocation,
sanitized decoder errors and a latch held through late native completion.

Actual browser: installed **Chrome 155.0.8059.84**, headless Linux, with its sandbox
retained, a fresh profile, CDP pipe, URL blocking and background networking disabled.
Final test profiles are removed after browser exit. No deployed URL or microphone
permission is requested. Results:

| Synthetic input | Actual normalized output |
| --- | --- |
| Complete WebM/Opus fixture | 1,920 mono frames, 16 kHz, 3,884-byte PCM16 WAV |
| Complete AAC in M4A/MP4, mdat before trailing moov | 8,000 mono frames, 16 kHz, 16,044-byte PCM16 WAV |
| 4,800 stereo frames at 48 kHz PCM WAV | Exactly 1,600 mono frames, 16 kHz, 3,244-byte PCM16 WAV |

Chrome also rejects corrupt/unsupported/mislabeled/declared-truncated samples,
over-duration decoded WAV and output allocation violations. Pre-cancelled decode
and cancelled chunked PCM encoding deliver no result. The stereo constant-level
resampling check permits 8 PCM units for filter ripple; observed difference was
3. Exact quantization math is separately checked without a browser resampler.
An initial one-unit resampling assertion was too strict and corrected to this
explicit tolerance. Initial mock module-scope extraction was also corrected;
final suites pass, with no failures hidden.

The browser supports the tested WebM/Opus recorder MIME but reports no recorder
support for the tested AAC MIME. AAC decode success is not AAC recording support.
Firefox 158 is installed but was not exercised; Safari/Mac/iPhone are untested.
Actual recorder-produced target-device MP4, fragmented variants and other codec
profiles remain browser compatibility gaps. Unsupported variants fail closed.
No mounted native DOM/end-to-end device acceptance, full WebUI application/image
build, recognition accuracy or Chinese/English inference was attempted. The
existing multilingual Whisper transport/model remains unchanged.

Fixtures contain only synthetic audio. WebM was generated from a browser 440 Hz
oscillator through MediaStreamDestination/MediaRecorder without microphone use.
Trailing-moov M4A was generated from a 0.5-second 440 Hz, 48 kHz stereo signal using
ffmpeg in one existing-image, network-disabled/read-only container with no mounts
and memfd output. The exact identity-checked container was removed. This was test
fixture generation, not an application/server converter. Only synthetic fixtures
and test evidence are persisted; the application path uses in-memory Blobs and
buffers with no persistent recording/transcript cache or logs added.

## Privacy gates and smallest path toward live acceptance

R4 establishes bounded accepted input/output and the demonstrated browser format
bridge, not complete private dictation acceptance. Shared Whisper still uses
`--convert`; failure-file retention/immediate reclamation remains unresolved.
Browser decoder allocation/erasure, host swap/core/crash-dump/hibernation, server
hard deadlines/worker cancellation, ingress buffering and target-device privacy
acceptance remain open. No host protections were changed or newly claimed.
Both live entry points must stay disabled.

The smallest next step is offline target-browser acceptance with the same public
synthetic WebM/MP4 fixtures and native recorder/composer, especially Safari/iPhone
AAC and fragmented MP4, plus a documented decision on the native decoder resource
limit. Resolve the shared Whisper temporary-file/privacy and server cancellation
gates before any separately authorized packaging/live acceptance. No deployment
or automatic submission follows this report.
