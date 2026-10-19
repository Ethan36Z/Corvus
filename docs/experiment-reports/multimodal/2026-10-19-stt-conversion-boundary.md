# STT conversion boundary — stdin pipe compatibility gate

Experiment: **STT conversion boundary simplification**

Date: **2026-10-19**

Verdict: **STT_CONVERSION_BOUNDARY_BLOCKED**

Reviewed Lab baseline: `4f8013af2c8e73774fcef91c2510e5808c1fd2c2`

## Decision

**C++ changes are avoidable for Whisper's existing in-memory audio-reader path,
but the proposed strict stdin/stdout ffmpeg boundary fails the A3 compatibility
gate.** A valid synthetic M4A decoded with seekable input but produced only an
empty WAV header through stdin. Crucially, ffmpeg returned exit status zero in
both cases. Nonzero exit status alone is not a sufficient conversion validator.

Per the requested Step 1 stop condition, no Step 2 converter/adapter was
implemented and no Step 3 integration suite was run. No switch to shared Whisper
without `--convert` was prepared or activated. No source or deployment changes
were made to running services.

The completed [STT-1 integration report](2026-10-19-stt1-whisper-offline-integration.md)
and [STT-1a.2 storage report](2026-10-19-stt1a2-volatile-storage.md) were read first.
The broad investigation and prior storage lifecycle experiments were not repeated.

## Exact pinned-source contract

Selected public source/build files were read from an isolated local container of
Whisper image
`sha256:caf0cd77c922e9c53f10a9bc17c2f74cc2295d12e7b0f96b630fb3b3c55a0026`,
with no network, model or deployed-data mounts. No server/model was started.

| Evidence | SHA256 |
| --- | --- |
| `examples/server/server.cpp` | `903bf6a6904301a698e0db79c0a72f25bca5bc7c3953b493eb09a68683e53356` |
| `examples/common-whisper.cpp` | `852fbc77d2461322a82b9c571cf4703bac3c78c5c51d3a90e80792ce0c04e313` |
| Public `build/CMakeCache.txt` | `84bdcc5b52c89bfd6121fff59ef06c01df07579a358729c8ed97af30a17f3707` |

`server.cpp` defaults `ffmpeg_converter` to false; omitting `--convert` selects
the else branch at the inference upload handler. It passes
`audio_file.content.data()` and `.size()` to the byte-buffer overload of
`read_audio_data`, rather than generating a filename or calling `convert_to_wav`.

`common-whisper.cpp:166–179` initializes miniaudio with
`ma_decoder_init_memory`, requests float32 decoded samples at the existing
16 kHz Whisper sample rate, and selects mono or two channels according to the
existing stereo/diarization flag. Both file and memory reader paths use the same
frame-reading helper. The existing ffmpeg conversion target is 16 kHz signed
16-bit PCM WAV. Canonical little-endian PCM16 RIFF/WAVE at 16 kHz is therefore
the intended interchange; this report does not claim a new exhaustive codec list
or live-reader acceptance test. A future prototype must validate finite RIFF
lengths and real decoded frames before forwarding.

The selected byte-buffer reader path does not open/write named audio temp files
or call the external converter. This is a source-level finding about that audio
path, not proof that every unrelated server feature/logging option is private.
The build cache reports `WHISPER_COMMON_FFMPEG=OFF`; direct M4A support must not be
assumed for the memory reader. Removing `--convert` while keeping A3 uploads raw
would be an unvalidated compatibility change.

## Existing A3 contract and available tools

The reviewed A3 adapter validates/reads an existing retained attachment, accepts
`audio/*`, and posts the original bytes with multipart `file`, `language`,
`response_format=json` and optional `prompt` to `/inference`. It creates a derived
TRANSCRIPT artifact associated with the original attachment. Existing mocked
contract coverage includes M4A labeled `audio/mp4`. The current contract does not
require MP4 faststart or fragmented MP4, and supplies no browser-only container
restriction. A valid trailing-moov M4A is consequently an input class that cannot
be silently excluded.

Any future preprocessing must change only the bytes sent to Whisper, preserve
the retained original attachment and its provenance, retain Chinese/English
language/prompt semantics, and avoid invoking the attachment/artifact workflow
from reviewed-text dictation. No language/model behavior was changed or inferred
from the synthetic noise test.

| Runtime | Availability checked |
| --- | --- |
| Existing pinned Lab WebUI image | `/usr/bin/ffmpeg` 5.1.6-0+deb12u1, `/usr/bin/ffprobe`, and importable PyAV. No download or package install. |
| Corvus host adapter environment | No ffmpeg/ffprobe found on PATH; current project virtualenv has neither PyAV nor imageio_ffmpeg. This is a separate packaging gap, not evidence that no copy could exist anywhere on the host. |
| Whisper image | Existing converter/source reused for contract knowledge; no C++ rebuild or model operation. |

The synthetic format gate used the exact existing WebUI image
`sha256:72252f095805fa8aebb6ed17e7fb44c3746e9d2a289ec3ff395769aad0c44e3b`.
It did not import/start the WebUI application or access its volumes.

## Bounded public synthetic compatibility experiment

One temporary, network-disabled, read-only, capability-dropped container was
used for the format gate. Its memory and memory-plus-swap limits were both
256 MiB and core soft/hard limits were zero. These are synthetic experiment
limits, not proposed model-service budgets or proof of host dump suppression.
No model/deployed-data mounts, pulls, builds or inference were involved.

A seeded public synthetic noise generator produced 20 seconds of AAC in ordinary
M4A/MP4 with trailing `moov`. A Linux anonymous memfd supplied seekability for
fixture generation and the control. It was closed in a finally block. No regular
input/output audio file was created, no private audio was used, and no sample
payload is published. This memfd was a diagnostic control, not an implementation
of the requested all-pipe converter.

Fixture size: **653,558 bytes**. `mdat` type offset: **40**; trailing `moov` type
offset: **649,043**. SHA256:
`f58f7c9177f1f3435ff84184228180b7697783aba50b250c2c2ed00e2c79b673`.
This counterexample is only 20 seconds and below 1 MiB; it does not depend on an
extreme duration or large upload allowance.

Every ffmpeg subprocess used a fixed argument vector without a shell, captured
stdout/stderr, fixed PCM16/16 kHz/mono WAV output, and a 15-second deadline.
The same decoder/output options were used for both input access methods.

| Case | Exit | Output bytes | Actual result |
| --- | --- | --- | --- |
| Seekable anonymous-descriptor M4A input | 0 | 640,420 | WAV with readable PCM16, 16 kHz, mono sample payload. |
| Identical M4A bytes on `pipe:0` | 0 | 78 | WAV header only, no PCM frames; captured diagnostics identified a partial file. **Compatibility failure.** |
| Generated WAV fed back through stdin | 0 | 640,420 | Readable PCM16, 16 kHz, mono sample payload; stdin conversion itself works for the WAV control. |

Trailing metadata can require a decoder to seek back to earlier media data.
These measurements establish that the tested ordinary M4A does not survive this
strict nonseekable input path. No claim is made that every M4A fails, or that no
other demuxer strategy could ever support this fixture. The proposed simple
boundary is not accepted without a demonstrated strategy preserving this case.

The output WAV headers from stdout used streaming length sentinels, reporting
2,147,483,647 nominal frames through Python's WAV reader. Actual sample reads,
not declared lengths, distinguished the positive controls from the empty result.
A future prototype should validate actual samples and reconstruct a bounded WAV
with correct finite lengths, rather than forward the streaming header blindly.

The probe initially summarized only the exit code as acceptance; that summary
was corrected from the already recorded sample-validation evidence. Audio
measurements were unchanged, and no additional conversion run was needed.
Raw diagnostics were not published.

## What was not implemented or validated

There is no converter implementation, A3 preprocessing change, dictation route,
Whisper startup override or code commit. Timeout/cancellation/process-death,
malformed input, upload/output limit, log-canary and adversarial converter tests
were not run as a Step 3 suite because Step 1 failed. Subprocess deadlines in the
gate are containment, not timeout/cancellation acceptance tests.

Existing A3 executable scripts were not rerun in this gate; the seekable-versus-
pipe counterexample is the new compatibility result. No dictation canonical-write
or TTS/Pipe regression pass is claimed. Those files and behaviors were not changed.
No live Whisper endpoint, recognition accuracy, browser recorder or model was tested.

## Residual privacy and next smallest step

The memory-reader route can avoid Whisper's named conversion files without C++
changes, provided every client sends validated compatible audio and a future
separately authorized startup omits `--convert`. It does not resolve host swap,
core collection, hibernation/crash dumps, upstream diagnostics or other service
privacy boundaries. No host settings were changed and no mandatory property is
waived. A3's intentional retained original evidence is distinct from an unwanted
conversion temp file.

The smallest next scope is a **seekable-memory conversion prototype** preserving
this M4A fixture: evaluate existing PyAV over a bounded BytesIO, or ffmpeg with a
bounded anonymous seekable input descriptor and stdout output. That is a change
to the strict stdin-only proposal and must be explicitly selected before work
continues. Keep the original A3 evidence, validate actual decoded duration/output,
rebuild finite WAV headers, and retain the required timeout/cancellation/logging
matrix. Resolve Corvus-host converter packaging without adding an STT engine or
model. No Whisper.cpp patch is indicated by this gate.

## Isolation, cleanup and publication

A clean separate worktree was created at `/tmp/corvus-stt-boundary-integration`
on `integration/stt-conversion-boundary`, based on the reviewed baseline. It
remains clean at that baseline with **no local code commit**. Only local public-
source copies, synthetic diagnostic scripts and sanitized gate measurements are
retained outside Git.

The public-source inspection container and format-gate container were removed
after verifying their exact IDs, image identities, experiment labels and absence
of data mounts. The format container's absence was confirmed after removal. No
Docker volume was created and no prune was used.

All files in the preserved STT-1a and STT-1a.2 draft directories matched their
before/after SHA256 manifests. `integration/stt1-whisper-webui` also remained
clean and untouched. Lab remained clean at the reviewed baseline. Production,
Demo, Whisper, Qwen, Hindsight, WebUI and Kokoro were not changed or restarted.
No private recordings, credentials, historical files or canonical data were read.

Only this sanitized engineering report and the chronological multimodal index
are committed/pushed to `reports/web-validation`. No implementation branch is
pushed, and no deployment is authorized or performed.
