# TTS-2.1 — Kokoro logging privacy hardening

Date: **2026-10-19**

Verdict: **TTS2_1_LOGGING_HARDENED_OFFLINE**

**Prepared and tested offline; not deployed.** The running shared Kokoro service
still uses its original image. Lab Read Aloud remains disabled. This checkpoint
removes the verified logging blocker in a local derivative; it does not authorize
activation or demonstrate live speech quality/browser acceptance.

## A. Verified baseline and root cause

References:

- [Multimodal reuse decision](2026-10-18-multimodal-reuse-decision.md)
- [TTS-1 integration](2026-10-18-tts1-kokoro-offline-integration.md)
- [Packaging baseline review](2026-10-19-tts1-packaging-baseline-review.md)
- [Blocked TTS-2 preflight](2026-10-19-tts2-deployment-preflight.md)

Lab remained clean on `lab/ow2e-console` at
`50a63850f83506724aaff4c2af4f50811d00d646`.
The existing TTS branch remained clean at
`4f8013af2c8e73774fcef91c2510e5808c1fd2c2`.
This work uses a separate local branch, `integration/tts21-kokoro-privacy`,
based on that exact integration commit. No previous implementation was replaced.

The installed image and inspected source were verified directly, without reading
historical logs, private conversations, credentials or media:

`ghcr.io/hsiang-han/kokoro-fastapi-zh-cpu@sha256:a675c4d280ff08002778468a2687d35c27d0a9709c6a8259afbfa573a72e7e2b`

The speech route calls `generate_audio()` for non-streaming requests; that method
uses `generate_audio_stream()`, smart splitting, the model backend and audio
conversion. The streaming route reaches the same processing components.

| Inspected path | Content-bearing exposure |
| --- | --- |
| `api/src/main.py` | API logger defaults to DEBUG; global sink prints message content |
| `routers/openai_compatible.py` | Validation, runtime, streaming, unexpected-error and temporary-output handlers interpolate raw exceptions |
| `services/text_processing/text_processor.py` | Processing/chunk DEBUG messages include original text excerpts |
| `services/tts_service.py` | No-audio WARNING and failed-chunk ERROR include text; other errors interpolate exceptions |
| `inference/kokoro_v1.py` | Generation logs include text/tokens; timestamp logs include words; errors interpolate exceptions |
| Installed `kokoro` dependency | Package resets Loguru at import; pipeline logs text/phonemes, including long-phoneme WARNING; model debug includes phonemes |
| Installed `misaki` dependency | Direct-print sites exist; not every inspected site is reachable for Chinese speech, so containment also covers direct output rather than assuming none can run |
| Framework/runtime | Uvicorn/Python logging, chained exceptions, warnings and third-party/native stdout/stderr can bypass a few edited application messages |

The container uses Docker `json-file` logging. This is a verified future content
retention risk, not evidence that a particular private utterance was logged.
Raising `API_LOG_LEVEL` alone does not cover WARNING/ERROR, exception or dependency
output paths. Existing log contents were not inspected or removed.

## B. Exact implementation and changed files

Local code commit: **7c0b5d0bbbfe993d4cd4910f1e9c1306de9e3b51** (code branch is not pushed).

Seven new files only:

- `deploy/kokoro/privacy/Dockerfile`
- `deploy/kokoro/privacy/guard.py`
- `deploy/kokoro/privacy/launch.py`
- `deploy/kokoro/privacy/verify.py`
- `deploy/kokoro/privacy/source-lock.json`
- `deploy/kokoro/privacy/README.md`
- `tests/test_kokoro_logging_privacy.py`

No upstream API/synthesis source is edited. The derivative inherits the exact
installed image, dependencies, model and license notices; it installs nothing.
The build verifies SHA256 hashes of all **30 installed API Python files**, rejecting
changed/missing/additional Python source. The immutable base digest also pins the
installed dependencies. No newer upstream code is imported.

The small launcher uses the already installed virtualenv interpreter directly
instead of `uv run --extra cpu --no-sync`. It preserves the original optional
`download_model.py` command and arguments when `DOWNLOAD_MODEL=true`, then starts
the same native FastAPI app, lifespan, host and port through Uvicorn. The existing
container has that provisioning flag enabled; no download was executed here.
Startup sequencing is tested with stubs; real provisioning/warmup is not tested.

## C. Privacy boundary and operational diagnostics

Before application/dependency imports, the guard redirects process file
descriptors 1 and 2 to `/dev/null`, retaining a private non-inheritable descriptor
for structured diagnostics. This is process-wide, not a request-local stream
swap, so overlapping requests cannot temporarily restore raw output. Native
writes, newly attached stream handlers and child-process stdout/stderr remain
contained. No temporary content file or speech cache is added.

Loguru and Python logging emit a fixed-schema JSON record containing only:

- A fixed event category and severity.
- An allowlisted component and bounded source-line number.
- For HTTP outcomes, bounded status and elapsed milliseconds.

Message text, record extras, request paths/query strings/headers/bodies, exception
strings, chained tracebacks, local variables, phonemes and audio never cross this
sink. Standard logging does not format record arguments. Loguru traceback/backtrace
diagnostics are disabled. Warnings and uncaught/thread/unraisable errors have
content-free hooks. Raw dependency output is contained even if it does not use a
logger. There is no private-content hash, redaction heuristic or raw-output fallback.

Main's original logger setup and the Kokoro package's import-time logger reset run
under containment. Metadata sinks are reinstalled after native app import and
before lifespan/request processing. No later sink reset was found in the inspected
speech path. API_LOG_LEVEL cannot restore raw message output through this launcher.

Useful WARNING/ERROR events remain visible through severity, component and pinned
source location, with failed request outcomes and process exit status. Free-form
exception and native-library diagnostic text is deliberately unavailable. This
tradeoff is narrower and more predictable than attempting to redact arbitrary
private payloads from formatted messages. Docker logging is not disabled or used
as the sanitization mechanism.

ASGI outcome observation forwards request/response messages unchanged. Errors and
cancellation propagate; no retry, alternate synthesis or extra canonical turn is
introduced. HTTP status/envelope, streaming behavior and audio codecs remain
upstream contracts, including existing error response bodies.

## D. Offline validation evidence

The final image was built with `--pull=false --network=none` from the existing
local pinned base. There was no dependency installation, external request or
model inference.

| Check | Observed result |
| --- | --- |
| New packaged-image privacy/API suite | **19 tests passed**, 0 failed, 0 skipped |
| Existing TTS-1 adapter/artifact suite, pinned WebUI image | **22 tests passed**, 0 failed, 0 skipped |
| Existing Corvus TTS adapter executable contract | Passed all 5 assertion groups |
| Existing Corvus TTS API executable contract | Passed all 6 assertion groups |
| Legacy contract isolation guard | No network, private/deployed-data read or out-of-root write violations |
| Python syntax | Four new Python files compile |
| Pinned-source verification | Build passed; negative source-tamper fixture rejected |
| Whitespace and staged scope | Passed before each commit |

The first 14-test development run passed; the final expanded 19-test run tests
files **inside the derivative image**, verifies equality with reviewed source,
and supersedes that preliminary result. Counts are not added together.

New tests use public synthetic canaries and fresh subprocesses with captured
stdout/stderr. They cover direct/native/child output; Loguru and standard logging;
exception chaining, framework logging, warnings and hostile formatting arguments;
all diagnostic severities; actual text-processing success/failure; actual chunk
WARNING/ERROR branches; actual backend generation/timestamp/error code with a fake
pipeline; real speech routes for WAV and streaming; validation/runtime/unexpected
errors; cancellation and unhandled ASGI failures; launcher startup arguments; and
source integrity/tamper rejection. Models, phonemizer, managers and provisioning
are mocked. The real WAV conversion code runs on zero-valued synthetic PCM.

Containers used network isolation, read-only root filesystems, dropped capabilities,
no-new-privileges and bounded temporary `/tmp`, with only public code/fixtures
mounted read-only. No deployed volume, model/voice host mount, personal memory or
Hindsight bank was mounted. Tests do not launch the native model lifespan.

TTS-1 regression includes native authentication, fixed destination/parameters,
Chinese `z`, voice `af_mica`, speed `0.95`, WAV MIME/validation, timeouts,
cancellation, transient handling, and unchanged Pipe/Arena patch identities.
The normal chat Pipe, Web MVP, Arena, canonical persistence and authentication
source files are outside this change. They were not rewritten or deployed.

## E. Prepared image and shared-service impact

Prepared local tag: `corvus-kokoro:tts21-privacy-offline`

Exact image ID:

`sha256:94d19bad32ccb34df77cccc2f5c9bc4ebd1a225878be2522d27b16edc5ae3c44`

The image was not pushed, started as a synthesis service or deployed. Only isolated
test containers used it with an overridden entrypoint.

The existing shared Kokoro container remains on the original `a675c4…` image, with
its original start time and `127.0.0.1:8105` mapping. Lab WebUI remains on its
original HTTPS/UI-2.1 `453f9f…` image and original start time. Lab and the prior TTS
worktrees remain unchanged and clean. No service was restarted or reconfigured.

Production, Demo and Lab Corvus API processes were checked only for the named TTS
configuration variables: none overrides the existing endpoint/model/voice/language/
speed defaults. Their inspected adapter defaults target loopback 8105 with Kokoro,
af_mica, z and 0.95. They are configured/potential clients of the shared speech
service; this is not an assertion of recent actual speech usage or an exhaustive
inventory of every possible host client. The prepared WebUI adapter is an additional
future consumer, currently disabled. No credentials were read or forwarded.

The derivative changes shared-process logging, not the speech request schema,
model algorithm, voice/language/speed, ports or clients. Its process-wide logging
policy also applies to other native endpoints. Production/Demo configuration and
runtime were not changed; future shared-service recreation would require explicit
approval even though their endpoint configurations would stay unchanged.

## F. Remaining risks and limitations

- This is offline privacy/API evidence, not successful real model startup,
  Chinese audio quality, latency, CPU contention, browser playback or iPhone PWA
  acceptance. No live synthesis/inference/chat/search request was made.
- This is a logging boundary for the pinned inspected process, not a sandbox
  against malicious code opening its own log files or deliberately reopening
  process descriptors. No file logging sink was found in the inspected speech
  application/Kokoro/Misaki paths. Future source/dependency/sink changes need review.
- Raw diagnostic text is lost; operators must use component/severity/source line,
  HTTP outcome and exit status. Optional download child output is contained;
  download failures preserve nonzero exit behavior without exception details.
- Existing API validation/error bodies are unchanged for compatibility and may
  contain supplied values. Clients must not log those bodies. The prepared TTS-1
  adapter uses sanitized failure messages and forwards no credentials.
- Upstream explicitly requested download-link audio files remain unchanged. The
  private WebUI TTS-1 client disables that option. This work does not claim to
  remove all native endpoint storage or inspect/delete historical files/logs.
- Existing optional startup provisioning is preserved, not executed offline.
  Recheck model/voice availability and provisioning policy before an authorized
  shared-service restart; do not unexpectedly pull a newer image or model.
- No end-to-end live client regression or browser acceptance is claimed. Existing
  upstream synthesis failure semantics, including swallowed chunk errors, were
  not redesigned by this logging-only change.

## G. Deployment prerequisites, rollback and recommendation

**Do not enable Lab private Read Aloud against the original unhardened service.**

Next stage: request controlled activation approval for the hardened shared Kokoro
image before TTS WebUI activation. Recheck exact image/source identity, shared
clients and current stack/environment/mounts; retain protected original image and
Compose recovery metadata. Keep the existing loopback port, model/voice assets,
CPU selection and all synthesis parameters. No Production/Demo configuration edit
is required, but shared-service downtime/compatibility requires operator approval.

After approval, use a bounded synthetic-only success/error/logging acceptance
window, inspect only that new synthetic window rather than historical private
logs, and confirm all shared clients' health and API compatibility. Then resume
the separate protected Lab WebUI backup/activation plan from TTS-2. Neither step
is authorized or performed by this checkpoint.

Rollback restores only the prior exact Kokoro image/entrypoint in its existing
stack, preserving volumes, ports and environment. Do not restore databases, delete
user data, alter canonical memory or restart unrelated services. The old image has
the known logging blocker, so keep private Read Aloud disabled if it is restored.

Only this sanitized report and its chronological index are published. The code
branch, Lab and main remain unpushed. **OFFLINE_HARDENED; NOT_DEPLOYED.**
