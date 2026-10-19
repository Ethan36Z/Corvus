# STT-R1 — Reuse the A3 Whisper transcription transport

Experiment: **STT-R1 legacy STT reuse**

Date: **2026-10-19**

Verdict: **STT_R1_REUSE_READY**

Reviewed Lab baseline: `4f8013af2c8e73774fcef91c2510e5808c1fd2c2`

Local implementation commit: `688a8bbd94a96239daa50c9277521ea22c706196`

## Result and acceptance boundary

The existing A3 Whisper request/response logic now has a reusable byte-oriented
entry point in the same module. `transcribe_attachment()` delegates to it while
retaining the original attachment validation, TRANSCRIPT attribution and return
shape. There is one multipart/HTTP implementation, with no new STT backend,
converter, service, dependency or model.

**Nine new transport/delegation tests and four existing A3 executable contract
scripts passed offline.** This is acceptance of a reusable transport seam only.
No WebUI handler, microphone UI, live dictation, shared Whisper privacy fix or
deployment is implemented or accepted. The shared conversion temporary-file issue
remains unresolved, and no new live STT traffic is activated.

## Existing work read and reused

Reviewed before editing:

- `app/transcription.py` and relevant voice ordering in `app/conversation_runtime.py`.
- `tests/test_transcription_adapter.py`, `tests/test_voice_conversation_runtime.py`
  and `tests/test_voice_api_contract.py`.
- [A3.3 Voice v1 backend log](../../project-logs/2026-09-14-a3-voice-v1-backend.md).
- [A3.3d push-to-talk Voice UI log](../../project-logs/2026-09-15-a3-3d-push-to-talk-voice-ui.md).
- [Latest conversion-boundary gate](2026-10-19-stt-conversion-boundary.md).

The original multipart builder already supplied the protocol seam, but no public
function returned transcription text without also invoking artifact persistence.
The change extracts the existing request/response statements rather than building
another adapter. The existing TranscriptionError type, filename handling,
endpoint/configuration defaults, language/prompt fields and response normalization
are reused. No environment or codec investigation was repeated.

## Exact implementation changes

The local branch `integration/stt-r1-legacy-reuse` was created in the separate
worktree `/tmp/corvus-stt-r1-integration` from the stated baseline. Its local-only
commit changes exactly two files:

| File | Change |
| --- | --- |
| `app/transcription.py` | Add `transcribe_audio_bytes(audio_bytes, *, filename, media_type, language, prompt, base_url, timeout, opener)` using the existing multipart builder and HTTP/error/response handling. Replace the corresponding block in `transcribe_attachment()` with one call to that function. |
| `tests/test_transcription_transport.py` | Add mocked transport, canonical-I/O prohibition and attachment-delegation regression tests. |

Optional arguments retain the existing defaults: language auto, configured
startup prompt, configured Whisper base URL, configured timeout and urllib
opener. The byte transport sends the existing multipart fields `file`, `language`,
`response_format=json` and optional `prompt` to `/inference`, and returns stripped
transcript text. It does not fetch/create attachments, create TRANSCRIPT rows,
open SQLite, create chat messages or update memory. It has no persistence callback.
Here “pure transport” means independent of canonical persistence; HTTP is still
its intended effect when explicitly called outside mocked tests.

The attachment function's complete signature/default expressions were checked
against the baseline and remain unchanged. It still normalizes attachment ID and
media type, validates audio attachment identity/media/integrity, reads the original
retained evidence, calls the shared transport, then creates exactly one derived
TRANSCRIPT artifact. Attachment ID, producer `whisper.cpp`, producer version,
artifact kind and returned metadata remain unchanged. A transport error propagates
before artifact creation. The original raw audio is not rewritten or replaced.

`app/conversation_runtime.py`, API orchestration and existing tests were not
modified. Their SQLite-first order remains canonical user evidence, raw attachment
link, transcription, context/model, assistant persistence and derived dense sync.
The transcript remains derived perception rather than canonical typed user text.

## Offline validation actually performed

All Whisper responses were mocked. Audio inputs were synthetic placeholder bytes,
not recordings or decoded audio. The focused runner used isolated temporary data
and cache paths, offline model settings and a model-loading stub. It denied real
network resolution/connections, subprocess execution, writes outside its synthetic
root, deployed/home reads outside code/installed dependencies, and SQLite access
outside the synthetic root. It reported **zero isolation violations** and removed
its temporary synthetic storage after the run.

| Test group | Verified result |
| --- | --- |
| Nine new unit tests | Chinese, English and mixed returned text; trimming; default/custom language and prompt; omitted empty prompt; parsed multipart filename/content type/exact byte payload; endpoint/method/timeout; existing timeout, HTTP, URL, malformed JSON/UTF-8 and empty-text errors; no retries; response-read timeout; shared transport precedes one attributed artifact; failure creates no artifact. |
| Pure-transport I/O guards | Attachment read/write aliases and underlying entry points, message persistence, store/SQLite connection and ordinary file-open operations were patched to fail throughout the transport cases. Success/error cases completed without those calls; captured stdout/stderr were empty on multilingual success. |
| Existing `test_transcription_adapter.py` | Original multipart contract, actual TRANSCRIPT attribution in an isolated synthetic SQLite database, and non-audio rejection passed. |
| Existing `test_voice_conversation_runtime.py` | Voice SQLite-first event ordering, transient transcript perception/model input and raw-evidence preservation on STT failure passed. |
| Existing `test_voice_api_contract.py` | Canonical voice marker, transcription/artifact response and existing text API compatibility passed. |
| Existing `test_vision_conversation_runtime.py` | Runtime signature, text-turn regression, vision ordering and canonical evidence preservation on link/vision failure passed. This supplies the adjacent text-path regression. |
| Static/diff checks | Python AST parsing, original attachment signature comparison, one multipart construction call site, whitespace and exact two-file implementation scope passed. |

Unit tests use subcases for languages and error variants; the count is nine
unittest methods, not nine live requests. The four legacy scripts are separate
executable contract groups, not a newly invented aggregate test-case count.
Chinese/English assertions validate text/protocol preservation, not recognition
accuracy. No real endpoint, model, conversion tool or browser was invoked.

## Remaining privacy and product blockers

The shared Whisper startup still has its existing `--convert` behavior. Its
persistent conversion-temp failure/death issue remains unchanged. The prior
stdin-only M4A incompatibility finding is also unchanged; no converter was added
and `--convert` was not removed. No private recording or historical leftover was
inspected, and host swap/core/hibernation settings were not changed.

The extracted transport deliberately preserves the legacy request and error
semantics. It is not a newly hardened upload/codec/deadline/cancellation boundary:
callers still own bounded input handling, fixed-endpoint policy, response limits,
error sanitization and user-facing privacy behavior. For example, legacy URL
failure messages retain their existing reason text. This task does not silently
change those messages or treat them as safe WebUI diagnostics.

Being able to call the transport without canonical writes does not make its
remote server's audio handling private. Do not activate new dictation traffic or
claim complete dictation/privacy validation from these mocked tests.

## Smallest next Open WebUI integration step

Prepare a narrow **mocked authenticated native transcription-route adapter** that
passes validated audio bytes and fixed metadata to this shared transport and
returns text to the existing editable composer. It must not call
`transcribe_attachment()`, `process_turn()`, attachment persistence or canonical
message/memory operations. Reuse existing recorder/composer/auth rather than add
a second STT system or microphone UI in this seam task.

Keep live traffic disabled until the separately scoped shared Whisper privacy
blocker is resolved. The later adapter must enforce bounded uploads, fixed local
endpoint, safe diagnostics and review-before-send behavior, with its own auth,
no-canonical-write and TTS/Pipe preservation tests. No such route is implemented
or activated by STT-R1.

## Git, preservation and publication

Implementation commit `688a8bbd94a96239daa50c9277521ea22c706196` is local only on
`integration/stt-r1-legacy-reuse`; it is not pushed. The new worktree is clean
after committing. All four earlier STT worktrees retained identical HEAD/status
and SHA256 manifests for their draft files, including the uncommitted O_TMPFILE
and volatile-storage candidates. No reset, clean or overwrite was used.

Lab remained clean at the reviewed baseline. Production, Demo, WebUI, shared
Whisper, TTS/Kokoro, Arena and Hindsight were not changed or restarted. No
Docker operation, dependency install, model/image download, recording or live
inference was part of this task. Tests wrote only their synthetic local state.

Only this sanitized report and the chronological multimodal index are published
on `reports/web-validation`. Raw terminal transcripts, private prompt contents,
credentials, recordings, conversations and canonical data are excluded. Reporting
publication does not publish the code branch or authorize deployment.
