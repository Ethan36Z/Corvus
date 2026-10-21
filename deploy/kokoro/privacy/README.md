# Kokoro logging privacy derivative — prepared only

The base is the exact installed CPU image digest in `Dockerfile`. There are no
new dependencies, model changes or modifications to upstream synthesis/API code.
`source-lock.json` pins every installed API Python file; a mismatched base fails
the build. Keep upstream license notices inherited from the base image.

The original entrypoint optionally runs `download_model.py`, then starts Uvicorn
using the existing virtual environment. `launch.py` preserves that provisioning
command and the same host/port/application/lifespan. It selects the existing
virtualenv interpreter directly instead of invoking `uv run --no-sync`.
No inference or download is performed during the offline build/tests.

Before application/dependency imports, `guard.py` redirects process stdout/stderr
file descriptors to `/dev/null` and retains a private non-inheritable descriptor
only for fixed-schema JSON diagnostics. This also contains native writes, new
stream handlers and child-process output. Loguru and standard logging emit only
fixed severity/component identifiers and bounded source-line numbers. Request
outcomes add bounded HTTP status/duration; no path, query, headers, bodies,
message strings, exception strings, traceback locals, phonemes or audio are sent
to the sink. Standard logging never formats record arguments. Python warnings,
uncaught/thread/unraisable errors have content-free diagnostic hooks.

This deliberately loses free-form troubleshooting text and native-library output.
It does **not** hide application ERROR/WARNING events: severity, component and
pinned-source line remain, plus request failures and process exit status.
There is no hash of private text, no redaction heuristic, and no request-local
stdout swap that could race concurrent requests. `API_LOG_LEVEL` cannot restore
content logging. A failure in the safe sink has no raw-output fallback.

The pinned main module configures logging at import; output is already contained,
then the launcher reinstalls metadata sinks before lifespan/request processing.
The Kokoro package also resets Loguru at import; its import occurs under the same
containment. No runtime source change or logging sink reset occurs on the inspected
speech path. The fixed output boundary is process-wide, including other endpoints.

## Offline checks

Build only from the already present pinned base, with `--pull=false --network=none`.
Run `tests/test_kokoro_logging_privacy.py` in the derivative with `--network none`,
read-only rootfs, a temporary `/tmp`, dropped capabilities, no-new-privileges, and
only the integration checkout mounted read-only. Override the entrypoint with the
existing Python interpreter; never run normal model startup in these tests.
Actual route, text, chunk and WAV conversion code is exercised with fake model /
phonemizer / managers. Also run existing TTS-1 and Corvus adapter contracts.

## Activation boundary and shared clients

There is intentionally no active Compose edit or service restart here. Kokoro is
shared: Corvus Production, Demo and Lab use its existing loopback speech endpoint;
the prepared WebUI adapter is an additional future client. Deployment requires
separate operator approval covering the shared service, a fresh drift/config check,
protected image/Compose recovery metadata, and a bounded synthetic live/privacy
acceptance plan. Keep port `127.0.0.1:8105:8880`, model/voice mounts, environment,
API formats and all clients unchanged. Do not enable Lab Read Aloud first.

For rollback, restore only the exact prior Kokoro image/entrypoint in its existing
stack; do not restore databases or delete volumes. The old image retains the
privacy blocker: keep private Read Aloud disabled if reverting. Historical Docker
logs are neither inspected nor removed by this patch. Downloads may still occur
at future normal startup when the existing `DOWNLOAD_MODEL=true` setting is kept;
offline tests do not validate provisioning, warmup, audio quality or live clients.

The boundary covers this pinned process's stdout/stderr logging; it is not a
sandbox against malicious code deliberately opening files or `/proc/*/fd/*`.
Future code/dependency/logging changes require renewed review. Request validation
and API error response bodies are unchanged; clients must not log private error
bodies. Existing explicitly requested download-link files are unchanged; the
private TTS-1 client disables download links and receives transient audio only.


## Retained TTS runtime configuration — local closure

`compose.runtime.yml` saves the already deployed TTS-2.2 Compose packet as
non-sensitive configuration. It uses only the existing external network and
read-only local community voice mount, CPU mode, loopback 8105, af_mica/z defaults
and Docker `unless-stopped`. No voice/model bytes or user text/audio are included.
It is not applied during closure.

Observed image: `sha256:94d19bad32ccb34df77cccc2f5c9bc4ebd1a225878be2522d27b16edc5ae3c44`.
The installed guard, launcher, verifier and source lock match this branch's
existing `7c0b5d0` files exactly. The image/model cache stays outside Git.
Before any future separately authorized reuse, verify that the retained tag
resolves to that image or rebuild using the existing pinned privacy Dockerfile;
never silently pull a mutable replacement. The Compose file creates no new
storage or model and must not be applied as a project-wide up/down operation.
