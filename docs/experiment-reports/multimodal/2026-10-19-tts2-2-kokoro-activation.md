# TTS-2.2 — Controlled shared Kokoro activation

Date: **2026-10-19**

Verdict: **KOKORO_ACTIVATED_LOCAL_ACCEPTED_WITH_CONSTRAINTS**

The operator explicitly approved the prepared retained-container procedure and
one bounded synthetic Chinese speech request. The hardened Kokoro image is now
running on the existing loopback endpoint. Local image/health/WAV/logging and
canonical-write checks passed. **WebUI TTS was not enabled or deployed.**

## A. References, scope and fresh baseline

- [TTS-2 blocked deployment preflight](2026-10-19-tts2-deployment-preflight.md)
- [TTS-2.1 offline logging hardening](2026-10-19-tts2-1-kokoro-logging-hardening.md)
- [TTS-1 adapter integration](2026-10-18-tts1-kokoro-offline-integration.md)

Fresh checks found no unexpected scoped drift:

| Item | Verified baseline |
| --- | --- |
| Lab checkout | Clean `lab/ow2e-console`, `50a63850f83506724aaff4c2af4f50811d00d646` |
| Privacy integration | Clean `integration/tts21-kokoro-privacy`, `7c0b5d0bbbfe993d4cd4910f1e9c1306de9e3b51` |
| Earlier TTS integration | `4f8013af2c8e73774fcef91c2510e5808c1fd2c2` |
| Reporting start | Clean `reports/web-validation`, `66c5006b1500dd482bcb4ccf8abeb05e13ea8a06` |
| Original shared image | `sha256:a675c4d280ff08002778468a2687d35c27d0a9709c6a8259afbfa573a72e7e2b` |
| Approved prepared image | `sha256:94d19bad32ccb34df77cccc2f5c9bc4ebd1a225878be2522d27b16edc5ae3c44` |
| Existing endpoint | Host `127.0.0.1:8105` to container port 8880 |
| Native original startup | Image Entrypoint null, Cmd `./entrypoint.sh`; actual container Path matches |
| Shared clients | Production, Demo and Lab API processes retain the same TTS defaults and service identities |

All seven scoped local health checks passed before mutation. Read-only metadata
snapshots of the three canonical databases were stable during the prerequisite
window. No conversations, private message columns, credentials, historical logs,
media or Hindsight contents were inspected.

## B. Startup and asset compatibility

The prepared image ID exactly matched the approved value. Its inherited image
environment matched the original image. Effective speech configuration preserved
CPU-only operation, `hexgrad/Kokoro-82M-v1.1-zh`, `af_mica`, language `z`, existing
voice mount, restart policy and the existing network/loopback boundary.

Both running-original and prepared-image files had identical SHA256 values:

| Existing asset | Observation |
| --- | --- |
| Model | 327,247,856 bytes; `b1d8410fa44dfb5c15471fd6c4225ea6b4e9ac7fa03c98e8bea47a9928476e2b` |
| Model JSON | 3,228 bytes, valid JSON; `bc333efa5ce4ceff433c8c8e5d027a1eca0166001e4e4a62bea2d26ff7a46890` |
| Mounted `af_mica.pt` | 523,817 bytes; `3f7ecf859dddcc64e3d04bb4c5d0d99751c991bcd864a3019abbeaf6ba68c6a3` |

The voice bind mount remains read-only. The existing English helper package was
present in both images. No new engine, dependency, model or voice was installed.

`DOWNLOAD_MODEL=true` was preserved, not silently changed. The existing helper
returns before `snapshot_download` when the model/config and voices validate;
those exact predicates passed in preflight, and the derivative already contained
the matching valid model/config. It reuses the same valid mounted voices. The
normal launcher emits a generic `download` category when entering this helper
branch; that category alone does not mean a download occurred. Existing local
assets satisfied the startup requirements. No pull/download command was issued
by the deployment controls; packet-level network telemetry was not collected.

The normal native startup includes its existing synthetic model warmup. It is
separate from the single additional HTTP acceptance request below.

## C. Protected recovery snapshot

Before stopping the service, a fresh exclusive recovery directory was created and
verified with mode **0700**, files **0600**, an SHA256 manifest, parsed JSON checks
and byte-for-byte comparisons of copied configuration. Its exact location is
retained in the local operator handoff/pointer and is deliberately not published.

Protected recovery material includes:

- Original Compose file and original container configuration/identity.
- Original and prepared image metadata.
- Approved replacement Compose file.
- Scoped service identities, health and aggregate canonical metadata baseline.
- Durable activation journal with admissions recorded before each runtime action.

The immutable images remain available. Existing voice assets were not changed.
The original container itself preserves its writable layer, assets/media and
historical Docker log history. No database restore, whole-data overwrite, image
pull, log cleanup, media deletion or historical-log inspection occurred.

## D. Executed activation and temporary ownership

The attended sequence was:

1. Recheck clean Git/image/runtime state and verify the protected snapshot.
2. Stop only the original `corvus-kokoro` container.
3. Rename it to `corvus-kokoro-rollback-tts22`, retaining it stopped.
4. Start the approved replacement as `corvus-kokoro` using a single-service Compose
   configuration, project **`corvus-kokoro-privacy`**, with `--no-deps --no-build
   --pull never`.
5. Poll only the read-only health endpoint within a 180-second readiness bound;
   stop on unexpected restart/exit/configuration differences. No recreation retry
   was used and no rollback was needed.

The standalone project was explicitly part of the approved handoff. It uses the
existing **external** `small-vram-companion_default` network and original read-only
voice mount/port mapping. No network was created. Original Production/Demo Compose
files were not edited. The durable active configuration is in the protected
recovery directory, not dependent on a disposable `/tmp` configuration file.

Readiness was observed **24.535 seconds** after the replacement startup sequence
began. This is an observed readiness interval, not a guaranteed future startup
or exact interruption duration. Speech on the shared endpoint was temporarily
unavailable; Corvus API and other services were not restarted.

## E. One synthetic speech request

The durable admission record was written before dispatch. Exactly **one HTTP
speech request** was admitted and completed, with **zero retries**. The destination
was fixed loopback Kokoro, without credentials or a deployed chat endpoint.

Public synthetic input:

> 这是 Corvus 的公开语音测试。隐私标记：TTS22-CANARY-20261019。

Parameters were `model=kokoro`, `voice=af_mica`, `lang_code=z`, `speed=0.95`,
`response_format=wav`, `stream=false`, `return_download_link=false`.

The client enforced a 3-second connect timeout, 60-second total deadline and
8 MiB response limit, with environment proxies/redirects disabled and no retry.

| Measurement | Observed result |
| --- | --- |
| Model and voice availability | Native list endpoints succeeded; kokoro and af_mica present |
| HTTP response | **200** |
| MIME | **audio/wav** |
| Complete HTTP request duration | **1.876 s** |
| Received bytes | **366,040** |
| WAV sample format | **24,000 Hz, mono, 16-bit PCM** |
| Frames | **182,981** |
| Audio duration | **7.624 s** |
| PCM payload | Nonempty with nonzero samples |
| RIFF/data lengths | Existing TTS-1 finalizer successfully normalized Kokoro streaming length sentinels |

The received byte length stayed unchanged during header normalization. The
synthetic WAV is retained only in restricted local recovery/test storage, not
published. No private audio was used. Structural/audio-payload validation is not
an auditory assessment of pronunciation, intelligibility or browser playback.

## F. New-window logging privacy acceptance

Only the replacement container's new activation/synthetic window was captured by
its exact new container identity, bounded by explicit start/end timestamps. The
retained original container's historical logs were never read or copied.

Observed window:

- **51 structured records**, all matching the content-free fixed schema.
- No canary text/marker in the window; no arbitrary message/exception/body/audio
  fields. String values were restricted to fixed event/severity/component enums;
  other values were bounded integers.
- **4 WARNING records**, **0 ERROR or CRITICAL records**.
- Warnings retained metadata only: two generic runtime warnings and two runtime
  warning records at source line 97. Their full causes could not be recovered
  from this intentionally restricted metadata. They are not described as proven
  harmless or assigned invented explanations.
- Four successful HTTP outcome records correspond to readiness, model/voice
  checks and the one speech request. They are not four synthesis calls.

This demonstrates the implemented boundary for this startup and synthetic
success request. Live failure/cancellation branches were not deliberately forced
against the shared service; the earlier offline tests remain the evidence for
those branches. One success window does not establish every future request or
future dependency's behavior.

## G. Shared clients and canonical integrity

After acceptance, all seven checks again returned HTTP 200:

- Kokoro and Lab WebUI health.
- Production, Demo and Lab API health.
- Production and Demo web roots.

The three Corvus API service identities remained unchanged. Lab WebUI container
identity/start time remained unchanged on the original HTTPS/UI-2.1 image. Its inspected
environment has no TTS engine set and a false TTS permission default. Per-user
preferences and browser behavior were not inspected. No WebUI TTS
activation, persistent setting edit, Pipe change or frontend deployment occurred.

For **Production, Demo and Lab**, before/after canonical message counts and maximum
ID watermarks matched, and main database/WAL file size and nanosecond modification
metadata matched. Queries were read-only aggregates; no private message content
was selected. Thus **no canonical conversation writes were observed across the
measured deployment/acceptance window**. This is scoped verification, not a claim
that metadata monitoring can prove arbitrary future code cannot write data.

No Corvus chat endpoint, Qwen inference endpoint, Hindsight operation or Arena
operation was called. Authentication, FoxGate, Cloudflare, credentials and shared
Qwen configuration were unchanged. Only the shared Kokoro replacement was started;
Production/Demo/Lab API services were not restarted or reconfigured.

## H. Current state and rollback readiness

| Item | Actual final state |
| --- | --- |
| Active container | `corvus-kokoro`, running, zero restarts |
| Active exact image | `sha256:94d19bad32ccb34df77cccc2f5c9bc4ebd1a225878be2522d27b16edc5ae3c44` |
| Active project | `corvus-kokoro-privacy` |
| Endpoint | Still loopback-only `127.0.0.1:8105` |
| Recovery container | `corvus-kokoro-rollback-tts22`, stopped, original identity retained |
| Recovery image | `sha256:a675c4d280ff08002778468a2687d35c27d0a9709c6a8259afbfa573a72e7e2b` |
| Recovery project/entrypoint | Original `small-vram-companion` and `./entrypoint.sh` |
| Recovery permissions | Directory 0700, every saved file 0600 |
| Lab WebUI TTS | **Disabled** |
| Rollback executed | **No** |

If rollback becomes necessary, verify identities first, stop and retain the new
container as `corvus-kokoro-failed-tts22`, rename the original recovery container
back to `corvus-kokoro`, start it and check health/configuration. Do not delete
containers/logs/media/volumes or restore databases. Do not blindly repeat a failed
or uncertain operation. Restoring the original image also restores its known
logging blocker; private Read Aloud must remain disabled.

The actual recovery path, identifiers and state-aware commands remain in the
protected local snapshot and operator handoff. No privileged operator password or
sudo interaction was needed for this authorized Docker sequence.

## I. Safe future cleanup and remaining acceptance

**Temporary ownership warning:** do not run parent-project Kokoro up/recreate/down
or indiscriminate container/image/network pruning while this arrangement remains.
The stopped rollback container still has original Compose labels; parent-stack
operations could conflict with the replacement or delete historical recovery
material. Keep both image identities and the protected active configuration.

Future cleanup requires a separate reviewed/operator-approved plan to reconcile
Compose ownership, recheck all shared clients, preserve any required historical
logs/media and decide retention explicitly. Do not automatically remove the
original container, data or recovery snapshot after a successful smoke test.

Remaining constraints:

- Four metadata-only warnings are unclassified; free-form diagnostics are
  deliberately unavailable under the logging privacy policy.
- No Mac/iPhone playback, Read Aloud button, cancellation, replay, subjective
  Chinese quality or long-running contention acceptance was performed here.
- Existing native API error bodies and explicit download-link storage retain
  upstream semantics. The prepared private adapter disables download links.
- The process logging boundary is not a sandbox against malicious dependency code
  deliberately opening its own file sink or process descriptors.
- Startup/assets and this one success request passed; there is no statistical
  reliability claim, fresh live error injection or claim of universal no-egress.

Next: separately authorize the already prepared protected Lab WebUI backup and
TTS override activation, followed by native authentication/Read Aloud/browser
acceptance. Do not enable it automatically as part of this Kokoro checkpoint.

Only this sanitized report and chronological index are committed/pushed on
`reports/web-validation`. Lab, main and implementation branches remain unpushed.
No raw logs, audio, recovery configuration, counters containing private metadata,
credentials or database contents are published.

**KOKORO_HARDENED_ACTIVE; LOCAL_SYNTHETIC_ACCEPTED; WEBUI_TTS_DISABLED.**
