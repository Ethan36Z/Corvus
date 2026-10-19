# STT-1 — Whisper.cpp × Open WebUI integration blocked

Date: **2026-10-19**

Verdict: **STT1_BLOCKED**

**No STT adapter/image was implemented, committed, enabled or deployed.** Inspection
of the exact installed speech path found a mandatory upstream cleanup blocker.
A WebUI-only adapter cannot satisfy the requested privacy contract against the
current shared Whisper startup configuration. This report preserves that failure
rather than claiming offline validation of an incomplete dictation integration.

## A. Verified baseline and references

- [Multimodal reuse decision](2026-10-18-multimodal-reuse-decision.md)
- [Existing TTS integration pattern](2026-10-18-tts1-kokoro-offline-integration.md)
- [Current Lab WebUI activation](2026-10-19-tts2-3-webui-activation.md)

Lab was clean on `lab/ow2e-console` at the expected
`4f8013af2c8e73774fcef91c2510e5808c1fd2c2`.
A separate worktree/branch, `integration/stt1-whisper-webui`, was created from that
exact commit. It remains clean at the starting commit, with no STT implementation
commit. The deployed Lab checkout was not modified.

| Runtime | Verified identity/configuration |
| --- | --- |
| Lab WebUI | `sha256:72252f095805fa8aebb6ed17e7fb44c3746e9d2a289ec3ff395769aad0c44e3b`, pinned 0.6.5 TTS derivative |
| Whisper | `sha256:caf0cd77c922e9c53f10a9bc17c2f74cc2295d12e7b0f96b630fb3b3c55a0026` |
| Whisper startup | Existing multilingual `ggml-small.bin`, eight threads, language auto, no GPU, **--convert** enabled |
| Whisper filesystem | Working directory `/app`, writable container root, no tmpfs; model directory is the existing read-only bind mount |
| Whisper logging | Existing Docker json-file driver; no historical logs were read |
| Existing WebUI conversion components | ffmpeg, ffprobe and PyAV 14.3.0 already installed; no new dependency required merely to investigate format conversion |

Installed Whisper `examples/server/server.cpp` was copied as public source to
isolated temporary storage and inspected. Its SHA256 is
`903bf6a6904301a698e0db79c0a72f25bca5bc7c3953b493eb09a68683e53356`.
No private recording, cache content, conversation, credential or canonical row was
read. No HTTP transcription, chat or Qwen request was made.

## B. Existing interface contracts

### A3 transcription

`app/transcription.py` validates retained attachment identity/media/integrity,
constructs multipart `file`, `language`, `response_format=json` and optional
`prompt`, then POSTs to `/inference`. It records a derived TRANSCRIPT artifact
with the existing attachment/provenance contract. Existing Voice v1 owns raw audio
and user-first canonical ordering. It is not equivalent to reviewed-text dictation.

Reusing its producer/protocol knowledge is appropriate. Calling the complete A3
attachment/artifact workflow from a dictation button would create evidence writes
outside the requested text-only dictation contract, so it was not wired into WebUI.

### Pinned WebUI recorder and route

Inspected 0.6.5 source establishes:

- `VoiceRecording.svelte` constructs `MediaRecorder(stream)` without selecting a
  container/codec, then creates a Blob labeled `audio/wav` and a `recording.wav`
  filename. Neither operation converts the underlying recording.
- `transcribeHandler` calls the authenticated native transcription API and emits
  the response to the existing composer. It also has a transcript-bearing
  `console.log(res)` that must be removed from the private dictation path.
- Native `/api/v1/audio/transcriptions` uses `Depends(get_verified_user)` and
  writes uploaded audio under the shared transcription cache. Existing downstream
  transcription paths can also persist transcript data and log exceptions.
- The recorder result is appended to editable composer text. However,
  `MessageInput.svelte` then checks `$settings?.speechAutoSend ?? false` and calls
  `dispatch('submit', prompt)` if true. The false default is not an enforced
  review-before-send boundary for an existing true preference.

These source facts identify required narrow changes; none was silently patched or
enabled. No user preference was read or rewritten. Existing TTS remains intact.

## C. Blocking installed Whisper behavior

The installed shared service was explicitly started with `--convert`.
`server.cpp` uses the global `sparams.ffmpeg_converter`, not a per-file or
per-request opt-out. Its inference handler:

1. Copies the multipart upload into a generated `.wav` file under `tmp_dir`.
2. Uses `tmp_dir="."` by default, which resolves to writable `/app` here.
3. Calls `convert_to_wav` regardless of the upload's actual format. Even a strictly
   validated, server-normalized PCM WAV from WebUI enters this disk-write branch.
4. On conversion failure, returns HTTP 500 **without removing the input file**.

The conversion helper also uses a second `_temp.wav` output path. A failed ffmpeg
command returns before cleanup. Later removal/rename failure paths do not provide
an unconditional cleanup guard for both files. The source does remove files on
normal success and some read failures; the finding is specifically that cleanup
is missing on other reachable failures, not that every successful request leaves
a recording behind.

Relevant installed-source locations:

| Location | Contract evidence |
| --- | --- |
| `server.cpp:63,69,256–257` | Global converter and current-directory temporary-file defaults/startup flags |
| `server.cpp:318–340` | Conversion helper creates second file and returns on errors before complete cleanup |
| `server.cpp:851–865` | Upload written to disk; failed conversion returns without removal |
| `server.cpp:867–885` | Normal cleanup and separate in-memory path only when global conversion is disabled |

There is no supported request-level bypass or remote cleanup operation for this
converter path. The WebUI adapter would not know or own these generated server
paths. Upload validation and memory-only conversion in WebUI cannot guarantee
remote cleanup after disk/converter/process failures. Cancellation safety of the
conversion subprocess is also not established; it is outside the adapter's local
resource ownership.

This violates the mandatory failure-cleanup/no-persistent-recording contract.
The active service has no volatile temp mount that would change the storage
classification. No live failure was induced and no historical leftover file was
searched for or inspected. This is a demonstrated source/configuration risk,
not a claim that a particular private recording has been retained.

A fixed sanitized upload filename can avoid propagating private browser filenames
into existing service diagnostics, but cannot solve the audio-file retention.
Transcript logging is not alleged merely because a logging driver exists; the
inspected server disables realtime output by default and the running command does
not enable it. Full upstream failure/logging privacy remains a review requirement.

## D. Browser codec and review-before-send strategy — not implemented

Once the upstream blocker is resolved, the smallest WebUI integration remains:

- Reuse the existing recorder/composer and authenticated route.
- Preserve the real MediaRecorder output type/container; use supported runtime
  MIME selection and matching metadata instead of assigning a WAV label.
- Detect actual bounded container/audio data, validate allowed codec/container
  combinations and explicitly reject mismatch/corruption/unsupported input.
- Reuse already installed conversion libraries in a bounded, transient path to
  produce the Whisper input contract; do not add a model/runtime/dependency.
- Map only to fixed loopback `/inference`, with no browser credentials forwarded,
  no redirects/proxies/retries, bounded upload/duration/output and sanitized errors.
- Return text to the existing editable composer. Disable the dictation confirm
  handler's automatic submit behavior without rewriting stored user preferences.
  No chat/Pipe/canonical/attachment/Hindsight/Arena operation belongs in this path.

Actual Mac Safari/Chromium and iPhone Safari/PWA container/codec choices have not
been captured or tested in this stage. WebM/Opus and MP4/AAC are candidates for
later verification, not newly accepted format claims. Browser speech-recognition
fallbacks and any browser-side engine override must also be reviewed before
claiming all dictation stays on the local Whisper path.

## E. Offline checks actually performed

| Check | Result |
| --- | --- |
| Existing `test_transcription_adapter.py` executable contract | Passed |
| Existing `test_voice_conversation_runtime.py` executable contract | Passed |
| Existing `test_voice_api_contract.py` executable contract | Passed |
| Temporary static source boundary checks | Six checks passed, confirming converter/write/failure and recorder/auto-submit observations |
| New authenticated STT/upload/codec/deadline/cancellation regression suite | **Not implemented/run** |
| New TTS/Pipe/Arena/Web MVP integration regressions | **Not rerun**; no implementation changed, no pass claim |
| Live transcription/inference | **Zero** |
| New image build | **None** |
| Implementation commit | **None** |

The three existing A3 scripts ran with isolated temporary data/cache/home paths,
network/subprocess and deployed-data restrictions, and model-loading stubs. Final
execution reported no isolation-guard violations. Their mocks do not establish
real Whisper temp-file cleanup, browser codec support or a new WebUI integration.
The six source checks are static diagnostic checks, not a substitute for the
25 requested STT-1 implementation acceptance categories.

An initial legacy-test run completed the transcription assertions but its cleanup
hit a temporary audit-harness false positive: `shutil` used a dir_fd-relative
`os.open`, which the guard incorrectly resolved under the Lab working directory.
The temporary harness was corrected to resolve only descriptors/targets within
its isolated test root before auditing. Network/deployed-data restrictions stayed
in place. The subsequent complete three-script run passed. No repository test or
production code was changed to make it pass.

## F. Required unblock and smallest next task

First prepare a separately scoped **shared Whisper conversion privacy fix**, with
no deployment until explicitly approved. Preserve the installed engine/model,
loopback endpoint and existing A3 multipart compatibility. Review/test unconditional
cleanup of both conversion files on success, conversion/read errors, exceptions
and interruption, plus bounded conversion/cancellation and safe diagnostics.
Reuse existing conversion capability; do not add another STT engine/service.

Simply dropping `--convert` is not a safe unreviewed shortcut: other A3 clients may
send M4A or other formats relying on that shared conversion behavior. Such a
shared-service configuration change and any restart must have its own compatibility
review and operator authorization. No shared change was prepared or executed here.

After that boundary is safe, resume the narrow WebUI dictation implementation on
the existing isolated branch, inherit the exact active TTS image, pin recorder/
composer/backend transformations and run the requested offline regression matrix.
Preserve the normal Pipe, TTS, Web MVP, Arena, auth, volumes and canonical ownership.

## G. Deployment/rollback boundary and publication

There is no STT image or STT override to activate and therefore no STT deployment
or rollback command. The current TTS-enabled Lab image/configuration remains the
working baseline. Existing WebUI and Kokoro recovery arrangements are unchanged.
No shared-service, Production/Demo, authentication, networking, memory or user
preference change occurred. No container/image/volume/network pruning occurred.

The requested `integration/stt1-whisper-webui` branch is clean at
`4f8013af2c8e73774fcef91c2510e5808c1fd2c2`; that is its base, **not an STT code
commit**. No code branch is pushed. Only this sanitized blocked report and its
chronological index are published on `reports/web-validation`.

**STT_NOT_IMPLEMENTED; STT_NOT_ENABLED; SHARED_WHISPER_PRIVACY_FIX_REQUIRED.**
