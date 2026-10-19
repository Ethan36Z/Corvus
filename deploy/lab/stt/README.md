# STT-R2 — offline-only native WebUI adapter and stateless bridge

Baseline: local R1 commit `688a8bbd94a96239daa50c9277521ea22c706196`.
No build, deployment or live traffic is authorized. The active Lab is untouched.

## One existing Whisper transport, separate container boundary

Native authenticated `/api/v1/audio/transcriptions`
→ bounded in-memory multipart parser in `webui.py`
→ binary HTTP POST to fixed `http://corvus-stt-bridge:8106/v1/transcribe`
→ standalone `app.stt_bridge` in the Corvus code/runtime
→ existing R1 `transcribe_audio_bytes()`
→ fixed `http://corvus-whisper:8080/inference`.

Only R1 builds Whisper multipart. WebUI imports only its own router helper and a
copy of the shared protocol module; it does not import Python from another
container. `app.stt_bridge` never imports/registers the canonical playground API,
chat runtime, Pipe, Hindsight, model or attachment/artifact workflow. Importing
R1 still imports its existing attachment definitions; the new path calls none.

## Two independent auth boundaries; disabled by construction

`prepare_audio.py` recognizes only the exact TTS-enabled pinned 0.6.5 audio.py
SHA256 `807cb1e61894e272eaabf66ffebc13ee64c4f34fb132fda981b2eb6d9404286d`.
It replaces only the native transcription function, retaining its native
`Depends(get_verified_user)` dependency and route. The new raw Request signature
removes File/UploadFile so multipart parsing cannot spool before this dependency.
It leaves all other audio handlers, including active TTS, unchanged. Native auth
retains its own user lookup/last-active semantics; this is not Corvus canonical
chat/memory persistence. Tests substitute only that user lookup, not the verified
role check. No test role header is implemented in production code.

The standalone bridge checks a single exact Bearer credential with constant-time
comparison before reading audio. No browser JWT, cookie, user ID or filename is
forwarded to it or Whisper. Bridge credentials must eventually be independent
cryptographically generated high-entropy service secrets (for example 32 random
bytes represented as 64 hex characters), never a built-in/shared browser token.
No real secret was created/read for this task.

**Exported bridge `app = create_app()` has no token or transcriber and always
rejects traffic. The native helper likewise has no bridge callable by default.**
There is no environment/header/query enable switch. All successful tests supply
synthetic credentials/callables explicitly in process and mock network I/O.
Future live wiring requires a separately reviewed code/configuration change after
the shared Whisper privacy gate; importing or copying these files cannot enable it.

No HTTPS proxy route, main-API inclusion, Compose port publication or service
launcher is added. Any future bridge must run only on a dedicated private local
network with the WebUI/Whisper participants, publish no host/HTTPS port, use a
separately provisioned secret and disable access/body/debug logging. Membership,
credential distribution and topology have not been deployed or accepted here.
Do not route this standalone app through existing unauthenticated Corvus API paths.

## Deliberately narrow input/output contract

This backend checkpoint accepts canonical PCM16 RIFF/WAVE only: 16 kHz, mono or
stereo, nonempty, at most 120 seconds, finite consistent RIFF length and complete
sample payload. Maximum audio is 8 MiB, native multipart body is 8 MiB + 16 KiB,
upstream/bridge response is 64 KiB and transcript is at most 16 Ki characters
(subject also to the encoded response limit). Upload streaming has a five-second
body deadline; declared Content-Length cannot bypass the actual byte counter.
These are new dictation-profile limits, not changes to existing A3 admission.

The native request remains one multipart `file` and the response remains
`{"text": "..."}` for the existing composer contract. Unknown fields, encoded
payloads, corrupt/truncated WAV and other audio formats are rejected. Original
filenames are discarded; Whisper sees only `dictation.wav`. Language auto and
R1's existing prompt behavior remain intact. No decoder/converter is added.

**This does not validate the current MediaRecorder codecs.** Existing browser
recordings may contain WebM/MP4 despite a WAV label; they fail this strict profile.
Do not relabel them, silently treat them as PCM, remove --convert or claim native
browser dictation acceptance. Format support/metadata needs its later explicit
scope. A3 raw recording retention/provenance remains exactly as R1.

No application audio/transcript file cache or database is used; responses and
sanitized errors are no-store. Both HTTP hops have fixed targets, no proxy-env
use, no redirects and no retries. No public endpoint/Whisper option can be passed
by request metadata. The bridge invokes R1 with a bounded opener; R1 itself and
its legacy error/protocol behavior are not modified. Upstream bodies/error text
are never returned or logged by these helpers.

The WebUI HTTP hop has a 30-second outer deadline and bounded streamed reply.
R1's urllib hop has its existing per-operation socket timeout (30 seconds here),
not a proven hard total deadline. ASGI cancellation cannot forcibly stop an
already-running synchronous worker; it may continue until upstream completion or
timeout. This is an explicit remaining activation/privacy/resource limitation,
not a child/process cleanup guarantee. No new live request is allowed at R2.

Host swap, core collection, hibernation/crash dumps and shared Whisper conversion
files remain unresolved. No claim of nonswappable process memory, immediate
upstream cleanup, complete privacy acceptance or production readiness is made.
No frontend is edited. Existing speech auto-send and transcript-console behavior
need later review before any live UI activation; review-before-send is not newly
enforced by a backend-only adapter. Nothing here submits chat or changes preferences.

## Offline packaging and validation

For a future derivative only, the exact-source transform would copy `webui.py`
as `open_webui/routers/corvus_stt.py` and `app/stt_protocol.py` as
`open_webui/routers/corvus_stt_protocol.py`, then patch only the pinned native
transcription function. The standalone Corvus bridge uses its own installed R1
app/protocol files. No image is built and no files are copied into running services.
No new dependency is required by either tested Python environment.

`tests/test_lab_webui_stt.py` exercises native auth/ASGI, service authentication,
one R1 multipart request, request/audio/response bounds, no persistence/spooling,
sanitized errors and inert defaults. It uses selected public audio/auth source
fixtures under `/tmp/corvus-stt-r2-source`, read from the pinned local image only.
Existing R1/A3, TTS and Pipe tests are run with isolated synthetic data and mocked
I/O. Tests never call deployed Whisper, a chat/model endpoint or Hindsight.

The shared Whisper --convert retention blocker must be resolved before future
live wiring. The smallest next review is an offline recorder/format and native
composer contract plan using this strict server seam; retain mocked dispatch and
do not activate automatic submission or a new STT engine.
