# TTS-2.3 — Lab WebUI TTS activation

Date: **2026-10-19**

Verdict: **TTS23_LAB_ACTIVATED_WITH_CONSTRAINTS**

The operator authorized the protected backup, reviewed TTS promotion, Lab WebUI-only
recreation and at most one synthetic speech request. The prepared image is now
active, the authenticated endpoint passed, and privacy/persistence checks passed.
**Mac/iPhone/browser acceptance remains pending. No STT or Vision work followed.**

## A. Reviewed references and exact promotion

- [TTS-1 offline integration](2026-10-18-tts1-kokoro-offline-integration.md)
- [TTS-1.1 packaging correction](2026-10-19-tts1-packaging-baseline-review.md)
- [TTS-2 deployment preflight/backup plan](2026-10-19-tts2-deployment-preflight.md)
- [TTS-2.1 logging hardening](2026-10-19-tts2-1-kokoro-logging-hardening.md)
- [TTS-2.2 hardened Kokoro activation](2026-10-19-tts2-2-kokoro-activation.md)

Fresh Lab and TTS integration worktrees were clean at their expected commits.
Exact ancestry and the aggregate eight-file scope were checked. Lab was
fast-forwarded through only these two reviewed commits:

1. Starting Lab: `50a63850f83506724aaff4c2af4f50811d00d646`.
2. TTS-1: `3793b13d1f6855d5df7a3b139d47036b1879e4e0`.
3. TTS-1.1/final Lab: `4f8013af2c8e73774fcef91c2510e5808c1fd2c2`.

No Kokoro privacy implementation commit or unrelated branch was promoted. No new
implementation commit was needed. Lab/main/implementation branches were not pushed.

| Image | Exact verified identity |
| --- | --- |
| Original WebUI | `sha256:453f9f2c4cee37c5e0d158ed3fcbdfc1e099bc6ef55ab47a7cbcce8b7331df76` |
| Prepared/active WebUI | `sha256:72252f095805fa8aebb6ed17e7fb44c3746e9d2a289ec3ff395769aad0c44e3b` |
| Unchanged active Kokoro | `sha256:94d19bad32ccb34df77cccc2f5c9bc4ebd1a225878be2522d27b16edc5ae3c44` |

No image was rebuilt or pulled. Open WebUI stays pinned to 0.6.5, retaining its
existing branding, HTTPS/PWA and Arena UI-2.1 base.

## B. Deployment preconditions

Before backup/promotion:

- Exact original/target images and four-file active Compose provenance matched.
- The persistent volume was `corvus-lab-open-webui-data` at `/app/backend/data`,
  with Lab WebUI its sole container consumer.
- Installed `corvus_pipe` was active, owned by the existing operator, with source
  SHA256 `68967bd0ed499aaf2ecce38bc6afc80c3fc3cdeb805aab6a57182a2e907af861`.
- Pipe endpoint stayed on Lab port 18096, `WEB_MODE=auto`, Arena enabled.
- Native Web search, STT, call and upload defaults were disabled.
- Native authentication, existing secret, Secure cookies, SameSite=Lax and public
  HTTPS URL were present; persistent config remained disabled.
- Native WebUI task listing showed zero active tasks. Foreground registry metadata
  showed zero active foreground requests. Canonical metadata was stable across a
  prerequisite interval. No chat/Qwen request was submitted.
- Hardened Kokoro was healthy with the expected project/image; its retained
  original rollback container was stopped.
- All seven scoped health checks passed and sufficient backup space was verified.

Only required configuration/identity/activity metadata was inspected. No private
conversation columns, stored passwords, cached audio/text contents or personal
memory were selected or printed.

## C. Fresh protected backup — verified before promotion

The reviewed opaque volume backup method was used:

1. Create a fresh exclusive recovery directory, mode **0700**, with files **0600**.
2. Record original image/container/Compose metadata, exact volume, service
   identities and aggregate canonical baseline. Secret-bearing recovery metadata
   stays protected locally and is never included in Git/report artifacts.
3. Briefly pause **Lab WebUI only**. An isolated helper using the existing local
   image, no network, read-only source volume, dropped capabilities,
   no-new-privileges and no Docker log persistence streamed the opaque archive
   directly into the protected host file. No application/model was started there.
4. Unpause WebUI in `finally`, including failure paths. Source metadata stayed
   stable while the archive was produced. Confirm normal health afterward.
5. Read all archive members/bytes, validate sizes, safe paths/link targets and
   member types. Verify SQLite integrity on protected copies with the archived
   WAL/journal state, without selecting private rows. Never restore original data.

| Backup measurement | Observed result |
| --- | --- |
| Logical volume bytes before archive | 241,924,890 |
| Archive bytes | **242,073,600** |
| Archive members | **89** |
| Archive SHA256 | `d951a24ffcdd77b2d4d42a3dbe1c0a85a180b723975e32bc3c2497ab864dd63c` |
| Pause/unpause interval | **1.382 s** |
| SQLite consistency | **webui.db and Chroma SQLite copies both passed integrity_check** |
| Source metadata during archive | Stable |
| Recovery manifest/permissions | Verified |
| Post-backup WebUI and shared-client health | All seven checks HTTP 200 |

The exact restricted recovery location and operation journal are retained locally;
private archive, SQLite verification copies and configuration are not published.
Original user conversations, authentication, installed Pipe and volume contents
were preserved. Corvus canonical memory and Arena data were not restored/rewritten.

## D. Actual activation

After backup verification, Lab fast-forward promotion completed cleanly. Compose
recreated **only** `open-webui` in project `corvus-lab-open-webui`, with:

1. `compose.webui.yml`
2. `compose.boot.yml`
3. `compose.arena-ui2.yml`
4. `compose.https.yml`
5. `compose.tts.yml`

Execution used `up -d --no-deps --no-build --pull never --wait --wait-timeout 180
open-webui`. Durable admissions/results were recorded before/after runtime actions.
No deployment retry or rollback was needed.

The exact prepared image became healthy on the same persistent volume. Comparing
actual old/new environment showed exactly the four reviewed changes:

| Setting | Active value |
| --- | --- |
| AUDIO_TTS_ENGINE | `corvus-kokoro` |
| AUDIO_TTS_MODEL | `kokoro` |
| AUDIO_TTS_VOICE | `af_mica` |
| USER_PERMISSIONS_CHAT_TTS | `true` |

The authentication secret compared equal without being printed. HTTPS, both
Secure-cookie flags, both SameSite=Lax settings, existing auth/signup policy,
loopback HOST/PORT and other permissions remained unchanged. STT, call, file
upload and native Web search remained disabled. Browser-Kokoro was not selected;
no auto-play setting or persistent user preference was changed.

Kokoro, Qwen, Corvus APIs, Hindsight, Production/Demo, FoxGate and Cloudflare were
not restarted or reconfigured. Kokoro's container identity/start time remained
unchanged, under project `corvus-kokoro-privacy`. Its stopped original recovery
container was preserved. No parent-stack Kokoro or prune operation was run.

## E. Acceptance trace and authentication

The first temporary acceptance helper incorrectly expected HTTP 401 when no
native token was provided. It stopped on an assertion **before any speech
request**; its preserved result recorded `synthesis_attempts=0`.

Read-only diagnosis confirmed the pinned native `get_current_user` explicitly
returns **403, Not authenticated** for a missing token, and the live voice-list
probe returned 403. This was a test expectation error, not an auth bypass or
service defect. Only the temporary expectation was corrected; all initial records
were preserved. The still-unused speech budget was then exercised exactly once.
No uncertain synthesis or deployment operation was retried.

Authentication checks used short-lived native-format JWTs for the installed
Pipe's existing operator owner, signed inside the WebUI container with the
existing key. Tokens stayed in memory, expired after two minutes and were never
printed, saved or forwarded to Kokoro. No account/password/API key was created,
no verification dependency was bypassed and no auth setting changed. Native
user-activity bookkeeping may update WebUI's last-active field; this is distinct
from canonical Corvus messages and is not described as zero database activity.

| Check | Result |
| --- | --- |
| Missing native token, voice endpoint | **403**, matching pinned source |
| Valid temporary native token, voice endpoint | **200**, exact single af_mica voice schema |
| Authenticated speech endpoint | **200**, real native verifier path |
| FoxGate unknown host | **404** |
| FoxGate unauthenticated API | **401** |
| Origin listener | Still **127.0.0.1:3003** |

This is native-token endpoint acceptance over loopback, not interactive password
login, external FoxGate login, Secure-cookie browser or end-to-end HTTPS acceptance.

## F. Exactly one synthetic WebUI speech request

The final helper issued one POST to native `/api/v1/audio/speech`, using only:

> 这是 Corvus 通过网页界面的公开语音测试。TTS23-CANARY-20261019。

Client fields were `input`, `model=kokoro`, `voice=af_mica`. The reviewed adapter
controlled the upstream destination and `lang_code=z`, speed 0.95, WAV/nonstreaming
format and disabled download links. The call had a 3-second connect timeout,
60-second total deadline and 8-MiB response cap, with redirects/proxies/retries off.

| Measurement | Observed result |
| --- | --- |
| Actual speech requests across both helpers | **1**, zero synthesis retries |
| HTTP status | **200** |
| Complete request time | **2.103 s** |
| MIME | **audio/wav** |
| Cache-Control | **private, no-store** |
| X-Content-Type-Options | **nosniff** |
| WAV bytes | **410,106** |
| PCM | **24 kHz, mono, 16-bit**, 205,014 frames |
| Audio duration | **8.542 s** |
| Payload/header validation | Nonempty/nonzero PCM and correct finite RIFF/data lengths |

The WAV was handled in memory for validation, not written to the WebUI volume or
published. No private conversation text/audio, chat turn or Qwen inference was used.
Audible quality and playback behavior were not assessed from byte validation.

## G. Privacy, identity and persistence verification

- Metadata inventory of persistent non-database regular files before/after the
  actual speech request was unchanged. Existing cache contents were not read.
  Thus no new persistent audio/text cache file or other non-database output was
  observed for this request. Old caches were neither inspected nor deleted.
- WebUI chat count was unchanged. Native auth's normal activity bookkeeping is
  allowed; this does not imply the whole WebUI database is byte-identical.
- Production/Demo/Lab canonical message counts, maximum-ID watermarks and main
  database/WAL size/mtime metadata matched the pre-deployment baseline. **No
  canonical conversation writes were observed in the measured window.**
- Installed Function ID, owner, complete source, valves and active flag compared
  equal against the protected pre-deployment SQLite copy. Endpoint, auto Web mode,
  Arena and reviewed Pipe hash remained intact.
- Corvus API service identities and Kokoro identity/start time were unchanged.
- All seven health checks returned 200 after deployment and acceptance: Kokoro,
  Lab WebUI, three Corvus APIs and Production/Demo web roots.

Existing offline TTS/packaging results are referenced rather than rerun or counted
as fresh live tests. This stage did not force live timeout/failure/cancel behavior,
read historical private logs, or claim universal absence of all possible future
logging/cache behavior. The hardened upstream remains the TTS-2.2 deployed image.

## H. Rollback readiness and ownership boundaries

No rollback was required. The protected original four-file stack, original image,
existing secret reference, persistent volume and verified archive remain available.

If needed, use the same project/environment file with only the original four
Compose files and `up -d --no-deps --no-build --pull never --wait --wait-timeout 180
open-webui`. Verify original `453f9f…` image, same volume, auth/HTTPS, Pipe and health.
Keep promoted TTS source files unused if necessary; do not reset unrelated history,
restore whole databases, delete messages/volumes, regenerate secrets or restart
shared services for a presentation failure.

Kokoro ownership remains separate. Do not run parent-stack Kokoro up/down/recreate
or indiscriminate prune operations. Preserve its retained original container and
TTS-2.2 recovery material; this WebUI stage does not authorize their cleanup.

## I. Remaining browser acceptance and next step

- Mac browser and iPhone PWA Read Aloud, actual listening, stop/replay, cancellation,
  background playback and user-gesture behavior remain **NOT_VERIFIED**.
- Existing devices must close old clients and hard-reload/refresh cached assets.
  The prepared frontend removes the old speech-text debug call but retains the
  compiled asset filename; an already loaded/cached old script is not erased by
  container recreation. Verify refreshed client assets before private use.
- Confirm manual Read Aloud and auto-play off in the operator's browser. No user
  preferences were inspected or changed here.
- Native-token acceptance does not establish external HTTPS cookie/session or
  FoxGate-plus-WebUI browser authentication. No remote credential test was run.
- The existing 4000-character, 60-second and 8-MiB limits and uncertain-outcome/
  no-retry policy remain. A lost client connection does not prove that Kokoro
  stopped computing; no canonical chat retry should follow a TTS failure.
- No long-duration contention, subjective Chinese/English quality, native-error
  injection or statistical reliability claim is made.

Next is bounded operator/browser acceptance of the deployed manual Read Aloud
controls using public synthetic text, not STT/Vision implementation. Only this
sanitized report and its index are published on `reports/web-validation`; no code
branch, private backup, token, raw database/cache or media artifact is pushed.

**LAB_TTS_ACTIVE; LOCAL_NATIVE_ENDPOINT_ACCEPTED; BROWSER_ACCEPTANCE_PENDING.**
