# STT-R2 — Authenticated WebUI adapter and stateless bridge, offline only

Experiment: **STT-R2 Open WebUI adapter**

Date: **2026-10-19**

Verdict: **STT_R2_ADAPTER_READY_OFFLINE**

Baseline: local-only R1 commit `688a8bbd94a96239daa50c9277521ea22c706196`

Local implementation commit: `3affe0f0899d2158a66b4259cb7295ef0a4b0810`

## Result and boundary

A minimal server-side native WebUI adapter and separate authenticated Corvus
bridge were prepared and tested offline. Both exported dispatch entry points
remain **disabled by construction**. No build, deployment, actual network
routing, live Whisper traffic or complete dictation/privacy acceptance occurred.

The tested input profile is deliberately limited to validated canonical PCM WAV.
This verdict does not claim current browser MediaRecorder codec compatibility,
UI integration, shared-service privacy or operational readiness.

The [R1 reuse report](2026-10-19-stt-r1-legacy-reuse.md) and its existing local
worktree were read/reused. The new worktree `/tmp/corvus-stt-r2-integration`, branch
`integration/stt-r2-webui-adapter`, starts at R1 rather than rebuilding its seam.
Earlier environment/codec/storage investigations were not repeated.

## Reused components and architecture

```text
native authenticated WebUI /api/v1/audio/transcriptions
  -> bounded in-memory multipart parser
  -> authenticated binary HTTP request to a fixed private bridge target
  -> standalone Corvus bridge using its own R1 code/runtime
  -> existing transcribe_audio_bytes()
  -> existing Whisper multipart /inference protocol
  -> {"text": "..."} to the existing composer contract
```

WebUI and Corvus do not import Python across container boundaries. The WebUI
helper imports only its own router-local helper/protocol module. The bridge
imports the existing R1 transport in the Corvus code/runtime. A shared protocol
source is copied into each package during a future separately reviewed packaging
step; it contains limits/validation, not a second Whisper multipart transport.

Only `app/transcription.py` from R1 constructs Whisper multipart. Its contents,
A3 attachment workflow, conversation runtime, prompt/language defaults and error
semantics are unchanged in R2. The bridge supplies a bounded, no-proxy/no-redirect
opener through R1's existing injection seam. It does not call the canonical chat
API or add an endpoint to `app.playground_api`.

## Exact six-file implementation scope

| File | Prepared behavior |
| --- | --- |
| `app/stt_protocol.py` | Common in-memory request/WAV/text validation, fixed bounds and sanitized no-store failures. |
| `app/stt_bridge.py` | Standalone ASGI app with service-token authentication before body reading; R1 dispatch with fixed Whisper target and bounded reply; exported app disabled. |
| `deploy/lab/stt/webui.py` | Native multipart-file/text adapter and authenticated HTTP client to the separate fixed bridge target; default handler disabled. |
| `deploy/lab/stt/prepare_audio.py` | Exact-source transformation of only the native transcription function; retain verified-user dependency while replacing UploadFile/File with raw Request to avoid framework spooling. |
| `deploy/lab/stt/README.md` | Offline packaging contract, authentication/network prerequisites, strict input profile and unresolved privacy/activation gates. |
| `tests/test_lab_webui_stt.py` | Eleven synthetic mocked ASGI/auth/bounds/persistence/error/source-preservation contracts. |

No Dockerfile, Compose activation override, service launcher, HTTPS proxy route,
frontend/microphone change, dependency install or new converter/engine/model was
added. No files were copied into a running service.

## Authentication, targets and no-spooling behavior

Public source was selected from the exact existing TTS-enabled 0.6.5 image:
`sha256:72252f095805fa8aebb6ed17e7fb44c3746e9d2a289ec3ff395769aad0c44e3b`.

- Native `audio.py` SHA256:
  `807cb1e61894e272eaabf66ffebc13ee64c4f34fb132fda981b2eb6d9404286d`.
- Native `auth.py` SHA256:
  `ec3ecf0d378517689a78cb98ed4c00e6e7d7d53a102098f0299d2eb361442f29`.

The pinned transform retains the native `/transcriptions` route and
`Depends(get_verified_user)` role check. The new raw Request signature removes
the File/UploadFile parameter, so the adapter can authenticate and stream-count
the body before in-memory multipart parsing, without Starlette's upload spooling.
All other native audio handlers, including the existing TTS wrappers, are AST-
identical after the transform. Unknown source is rejected rather than patched.

The native JWT/user lookup is not reimplemented. Tests mock user lookup but execute
the pinned verified-role function; user/admin succeed, missing/pending/blocked
identities fail. Native auth's own user lookup/last-active semantics remain
outside Corvus canonical chat/memory persistence. No claim of zero native auth
metadata writes is made.

The separate bridge requires one exact independent Bearer service credential,
checked with constant-time comparison before audio is read. No browser JWT,
cookie, user ID or original filename is forwarded. No real credential was read
or generated; tests use only an explicitly synthetic credential.

Targets are fixed in code:

- WebUI to `http://corvus-stt-bridge:8106/v1/transcribe`.
- Bridge to `http://corvus-whisper:8080/inference`.

Request fields cannot override either target. The WebUI HTTP client disables
proxy environment use, redirects and retries. The R1 opener likewise disables
proxy use/redirects, checks the exact final target and bounds response reads.
Whisper receives a fixed `dictation.wav` filename and the existing language-auto/
prompt behavior. There is no unauthenticated bridge route exposed through HTTPS
or added to the existing public/canonical API by this change.

No runtime credential/network wiring is provided at R2. A future bridge must
publish no host/HTTPS port, use a private local network with only the required
participants and a separately provisioned high-entropy service secret, and disable
access/body/debug logging. That topology and secret distribution remain untested
and undeployed. A credential length/character check is not proof of entropy.

## Input/output profile and inert live gate

The native request remains one multipart `file`, and the response is text JSON
for the existing editable composer. Original filenames are discarded. The
checkpoint accepts only finite, complete PCM16 RIFF/WAVE at 16 kHz, mono/stereo,
nonempty and at most 120 seconds. Invalid/truncated WAV, other formats, unknown
multipart fields and encoded uploads are rejected. No format is relabeled or
converted.

Bounds are 8 MiB audio, 8 MiB plus 16 KiB native multipart body, 64 KiB upstream/
bridge response, and 16 Ki transcript characters subject also to encoded response
size. The actual streamed request is counted even without a trustworthy length
header. Upload body reading has a five-second deadline. These are new dictation-
profile limits and do not alter A3 admission or promise model-service capacity.

The exported bridge is `create_app()` without token or transcriber. The native
helper has no default bridge callable. Both return disabled failures before
upstream dispatch; there is no environment, header or query enable switch. Tests
supply authenticated mocked dispatch explicitly in process. Future live wiring
requires a separate reviewed change after the privacy gate is resolved.

Successful results and adapter errors are no-store. The new path has no recording
or transcript file cache, attachment/artifact creation, Corvus SQLite access,
chat/Pipe/Hindsight call or content-logging operation. This does not establish
that shared Whisper, external ingress buffering or the unchanged frontend is
privacy-safe.

## Offline tests and actual results

Across the final isolated test groups, **67 distinct unittest methods and four
existing A3 executable contract scripts passed**. These were not counted as one
single all-in-one run. The 11 new methods also passed in the exact pinned WebUI
image runtime: Python 3.11.12, FastAPI 0.115.7, httpx 0.28.1.

| Group | Result |
| --- | --- |
| New STT adapter/bridge | 11 passed: authenticated native role acceptance/rejection; bridge token rejection before body consumption; one existing R1 multipart request and correct Chinese/English text; request/audio/response limits; invalid/truncated input; storage/spooling/SQLite/artifact/message prohibition; sanitized Whisper/bridge errors; redirect/timeout/fixed-target controls; disabled exported entry points; exact source patch preservation. |
| Existing R1 byte transport | 9 passed unchanged. |
| Existing Lab WebUI TTS | 22 passed unchanged, including auth, privacy/log/cache, cancellation and exact-source/frontend/Pipe/Arena preservation contracts. |
| Existing Open WebUI Pipe | 25 passed unchanged, including its fresh-process synthetic memory-path test and stubbed-runtime API boundary. |
| Existing A3 scripts | Transcription adapter, voice runtime, voice API and vision/text runtime scripts passed in a fresh isolated process; provenance/order/text behavior remain intact. |
| Scope/static checks | Six-file implementation only; Python AST/whitespace checks; R1 transport/runtime and existing TTS/Pipe sources unchanged. |

All Whisper/bridge HTTP exchanges were mocked or in-process ASGI simulations.
No real Whisper endpoint, chat/model endpoint, recording or canonical data was
used. The test guards prohibited persistence/file/spooling operations in the
new STT path and checked logs for a synthetic transcript sentinel. Legacy A3/Pipe
tests intentionally used only isolated temporary synthetic database state.
No global claim of zero SQLite activity across those legacy tests is made.

The host sandbox initially stalled a trivial FastAPI threaded dependency even
without STT code/audit hooks. The same diagnostic passed outside the sandbox;
ASGI suites were then run there with network/model/deployed-data guards retained.
An initial blanket subprocess denial blocked Pipe's existing fresh-process test;
the harness was narrowed to allow only its exact reviewed recipe with synthetic
paths and additional child network/model/data guards. A mixed-suite reload of
R1's exception class then invalidated a legacy voice exception identity; rerunning
the unchanged A3 scripts in a fresh process passed. No production code or existing
test was weakened to bypass these harness issues.

The pinned-runtime container used only selected public code/source fixtures,
read-only mounts, no network, no model/deployed data and the existing local image.
It was not an image build or full WebUI application startup. The source-copy and
pinned-test containers were identity-checked and removed; no Docker volume or
prune was used. One fixture-preparation attempt stopped before any container was
created because the repository uses namespace packages; its fixture list was
corrected before the successful pinned test run.

## Remaining privacy/product blockers and next step

Shared Whisper still uses `--convert` and retains the known persistent temporary-
file failure/death behavior. It was not changed or invoked. Host swap, core
collection, hibernation/crash dumps and ingress/proxy buffering are not accepted
by these backend tests. **All new live STT traffic remains disabled.**

The WebUI-to-bridge HTTP hop has a 30-second total deadline. The synchronous R1
urllib hop has a per-operation socket timeout, not a demonstrated hard total
deadline. Cancelling an ASGI request cannot forcibly terminate an already-running
thread; it may retain audio until completion/timeout. Resource/cancellation
hardening must precede any live activation; no cleanup guarantee is inferred.

Current MediaRecorder output may be WebM/MP4 despite a WAV label. Such input fails
this strict PCM profile. Browser codec acceptance and any seekable conversion
boundary remain separate work; A3 behavior is unchanged. No live microphone/
browser/composer acceptance or recognition accuracy is claimed.

No frontend was edited. In particular, existing speech auto-send preferences and
transcript-console behavior require later review before live UI activation.
Review-before-send is preserved as a future acceptance requirement, not newly
enforced by this backend-only checkpoint. No automatic submission is activated.

The smallest next step is an offline native recorder/format/composer contract
plan against this server seam, retaining mocked dispatch and reusing existing
controls. Resolve format support and enforce review-before-send/no transcript
logging in that later UI scope. Shared Whisper privacy, cancellation/resource
bounds and private authenticated deployment wiring must be accepted separately
before any new live request. Do not add another STT engine or deploy R2 now.

## Git, preservation and reporting

Local implementation commit `3affe0f0899d2158a66b4259cb7295ef0a4b0810` remains
unpublished on `integration/stt-r2-webui-adapter`; its worktree is clean. All five
earlier STT worktrees retained identical HEAD/status and draft-content SHA256
manifests, including R1 and all uncommitted O_TMPFILE/volatile-storage drafts.
Lab remains clean at `4f8013af2c8e73774fcef91c2510e5808c1fd2c2`.

No deployment, service restart, dependency/model/image download, production/demo
change or canonical data access occurred. TTS/Kokoro, Arena, Hindsight, Qwen and
running WebUI/Whisper were not modified. Only this sanitized report and the
multimodal index are published on `reports/web-validation`; no code branch is
pushed and no force push is used. Private data, credentials, prompt contents and
raw transcripts/terminal logs are excluded from publication.
