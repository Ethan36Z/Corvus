# STT Lab — Controlled activation and scoped rollback

Date: 2026-10-19.

Verdict: **STT_LAB_ROLLED_BACK**

The authorized Lab activation reached the first authenticated public synthetic
transcription. It returned HTTP 503 before a successful transcription. Admission
was immediately closed; Lab WebUI was restored to its original image/configuration
and existing data volume, and only the new owned STT services/networks were removed.
**Private dictation is not active or accepted. No second activation was attempted.**

## Baseline and authorized scope

Followed the complete [R7 checklist](2026-10-19-stt-r7-lab-preflight.md), local R7
`4be6907622e9f0634e5b1c327ae5054cca9200ef`, and the user's explicit Lab-only
activation/backup/credential/rollback authorization. R1–R7 frontend builds,
contracts, private-engine topology and resource evidence were reused. No new
engine, converter, frontend build, microphone interface or architecture was added.

Application-level delivery scope was no conversion temporary audio files, no
persistent dictation cache or content logs, authenticated fixed routing, bounds
and scoped failure. System/client persistence and legacy A3 issues remained
explicitly outside acceptance. Their risks were not waived or claimed solved.

A separate R7-based worktree preserves the backend-only candidate. Local-only
commit **`6dfc5225574fc28073917546f3f07d4b364cb958`** records its six passing
focused tests and the known live failure/rollback boundary. It is a **blocked
candidate, not an activation-ready fix**, and was not pushed.

Exact changed files:

- `app/stt_protocol.py`
- `app/stt_active.py`
- `deploy/lab/stt/activation/webui_active.py`
- `deploy/lab/stt/activation/prepare.py`
- `deploy/lab/stt/activation/compose.yml`
- `deploy/lab/stt/activation/README.md`
- `tests/test_stt_activation.py`

## Preflight and protected recovery

Read-only checks found no material drift from reviewed R7: correct clean local
commit and pinned images; existing model's 487,601,967 bytes and SHA-256 matched;
original Lab image/container/configuration and sole existing data volume matched.
Fifty selected nonsecret settings matched, including authentication, HTTPS-cookie,
TTS and Pipe configuration. No conflicting STT services/networks existed and
loopback port 18106 was free. Approximately 9.3 GiB RAM was available, with 16
visible CPUs and low load. No private conversations, recordings or credential
values were inspected during preflight.

Before mutation, an opaque consistent volume/configuration backup was created in
a protected operator directory outside Git. WebUI was paused for 1.414 seconds
while its sole-writer volume was archived read-only, then unpaused. The
242,073,600-byte archive had every member read/validated, safe paths/links and
stable paused metadata. Copied `webui.db` and `chroma.sqlite3` passed SQLite
integrity checks without querying conversation rows. Manifest/hash checks passed;
backup directory/file permissions were 0700/0600. Original full container/merged
configuration, private environment, five Compose files and image identity were
retained privately for recovery. No backup content or secret values are published.

A new independent 256-bit service credential was generated outside Git and
read-only distributed; it did not reuse a JWT signing key. Its owner was UID 10001,
mode 0400. A separate operator-owned admission marker defaulted closed in both
wrappers. Short-lived native test authentication was retained only in protected
files and local acceptance-token files were removed after verification.

## Candidate wiring and runtime evidence

The native verified-user route delegates to the existing R2 parser/bridge client,
using the independent credential. The new bridge wrapper supplies existing R6
`whisper_text` and R1 `transcribe_audio_bytes()` to `create_app()`. No canonical
chat, attachment, transcript artifact, SQLite or memory API was added. Fixed local
targets, bounded PCM-WAV validation, response limits, no redirects/retries and no
legacy fallback remained. No request/env value can select an upstream.

R7's successful frontend/image payload was reused. Two backend-only derivative
images were built entirely from existing local R7 images, without pulls, package
installs, model downloads or frontend regeneration:

| Role | Immutable image identity |
| --- | --- |
| Original/restored Lab WebUI | `sha256:72252f095805fa8aebb6ed17e7fb44c3746e9d2a289ec3ff395769aad0c44e3b` |
| R7 disabled staging WebUI | `sha256:6a1d1843c52be7b5a1a66d503a8c16514f617d4a478ddd9dc6e09b45858487db` |
| Attempted wired WebUI | `sha256:88330ac2e1aa941386d8d2aaff5640f77d7343557969b74452798a6968bc60de` |
| Attempted wired bridge | `sha256:5d3cd6aff2db1a9712ce98669942d093858640298e9c04903f3cee3b510dc6b2` |
| Private/unchanged pinned Whisper | `sha256:caf0cd77c922e9c53f10a9bc17c2f74cc2295d12e7b0f96b630fb3b3c55a0026` |

Actual new runtime, before removal:

- `corvus-whisper-dictation`, container
  `862a6f561f3e09c151012336b877ee1582c0b1fb38fffd937463ba19f6c76a30`:
  healthy; no `--convert`; no host port; only the owned internal backend network;
  one read-only model-file mount; read-only root; eight CPU quota; 1,088 MiB
  memory and equal memory-plus-swap. Actual cgroup `memory.swap.max=0`, current 0.
- `corvus-stt-bridge`, container
  `af493aa5ad18837fa46d3c03f83a526ffe67afdaa106770a5a990249d12d4686`:
  fixed private Whisper target; only 127.0.0.1:18106 ingress; backend plus owned
  ingress network; one worker and existing one-request admission; one CPU,
  256 MiB/equal memory-plus-swap; read-only root/secret mounts. Actual cgroup
  `memory.swap.max=0`, current 0. Bridge credential validation worked under UID 10001.

Owner/project/service labels, exact network membership, no engine publication,
actual mount/resource settings and disabled Docker logging were checked. New
engine/bridge constraints do not establish host-wide no-swap/dump guarantees.
R6's measured budget was retained; no new inference RSS/latency measurement was
obtained because activation failed before successful transcription. Final
post-rollback host available RAM was 9,590,640 KiB. No concurrent A3/TTS/STT QoS
claim is made.

## Test sequence and decisive blocker

| Check | Actual result |
| --- | --- |
| Focused wiring/auth unit tests | Six passed locally; same six passed in actual bridge image with network disabled and actual read-only secret mounts; local six rerun passed after rollback |
| Staged R7 Lab image, STT closed | Healthy; unauthenticated native audio 403; authenticated STT 503; TTS voice preserved; Pipe model available |
| Public synthetic TTS fixtures | Chinese, English and mixed-language generation each HTTP 200; finite 24 kHz mono PCM16 WAV; diagnostic canonical 16 kHz WAV fixtures of 3.807/3.302/2.570 seconds |
| Pipe/Arena technical preservation | Exact installed Pipe source/settings fingerprint retained; active model and existing Arena configuration preserved |
| Wired Lab, admission still closed | Healthy; unauthenticated native 403, authenticated native/bridge closed 503; only environment change was native STT permission |
| Admission open, direct bridge without authentication | HTTP 401, as required |
| First authenticated native STT, public Chinese WAV | **HTTP 503; acceptance failed; no retry** |
| Offline exact WebUI identity/capability diagnostic | PermissionError opening the UID-10001/0400 credential, sanitized HTTP 503 reproduced |
| Failure response | Admission closed, original Lab restored, owned new services/networks removed and rollback verified |

**Verified blocker:** existing WebUI runs UID 0 with all capabilities dropped.
The secret is readable only by UID 10001. UID 0 without DAC override cannot read
another owner's 0400 file. `service_token()` therefore fails closed with 503.
Bridge-only packaged tests passed because they ran as UID 10001; mocked native
unit tests did not cover actual WebUI filesystem identity. The closed-marker
checks also intentionally stopped before secret reading, so they did not expose
this mismatch before admission opened. The isolated post-rollback diagnostic
used the exact derivative WebUI image, UID 0, dropped capabilities, read-only
credential mount and no network; no secret value was printed.

An initial verification helper used the wrong name for the existing native STT
permission; the corrected actual setting was `USER_PERMISSIONS_CHAT_STT`. A
post-rollback helper initially compared ordered environment lists; normalized
key/value comparison passed. These were checker errors, not runtime changes.
External HTTPS initially expected 200 but returned Cloudflare 401; the local
health route remained 200. Those observations are reported separately.

No successful STT transcript, English/mixed STT accuracy, invalid/oversized live
validation, provider timeout/failure, request cancellation, live cache/log privacy,
or mounted-browser composer/manual-send acceptance was obtained. Existing R1–R7
offline evidence remains historical evidence, not fresh live acceptance. The
synthetic diagnostic WAV files are public test artifacts, not a product recording
cache. No real microphone or private audio was used. No chat was submitted.

## Executed rollback and current state

Admission was closed before rollback. Only Lab WebUI was recreated on its retained
original image and original five-file configuration, preserving the existing
`corvus-lab-open-webui-data` volume. Original environment values, host networking
and mounts compare equal after normalization; native STT permission is restored
false. No database reset or volume restore/deletion was needed.

Only recorded new container IDs were stopped/removed after checking exact image,
owner, project and service identities. Only the two owned empty STT networks were
removed after membership/ownership checks. Final inspection confirmed both new
container IDs and networks absent. No project-wide up/down or Docker prune ran.
Protected backup and local candidate images remain retained, not active.

Current restored Lab container:
`f030903208454567919b79c43bb09347bcdbd0eec101cefd877c4d919037c361`,
healthy on original WebUI image `72252f095805...` above. The original pre-change
container identity was `225c1b257ec6a9685564ac2c6bc09ac238d3f6be8161c5f0afa8af5cb7b8bcb4`;
container recreation was authorized and identity was necessarily changed.

Rollback verification passed native authentication (unauthenticated audio 403),
TTS voice listing and a public synthetic speech response (HTTP 200, WAV), Pipe
model availability and exact technical Pipe/settings fingerprint, existing Arena
configuration, local health 200, original environment/network/mounts and closed
STT admission. This is not a fresh end-to-end Arena comparison or canonical-chat
exercise. Public HTTPS root and health returned Cloudflare 401 from this host;
an authenticated external browser session was not available/claimed.

Unchanged services:

- Legacy A3 Whisper container `51448dd0de959645e3a11433d5c58444e8b6c0dd2bed37d59dcf26ec4585edc5`,
  pinned Whisper image above, original start unchanged.
- Kokoro container `72c8931661a11883f1dbb484933c61358ec7056a252208b8b95f315a2e8a3958`,
  image `sha256:94d19bad32ccb34df77cccc2f5c9bc4ebd1a225878be2522d27b16edc5ae3c44`,
  original start unchanged. Only authorized public synthetic TTS requests were made.

Active Lab and R7 Git worktrees remain clean; nine earlier STT worktrees retain
HEAD/status and recorded draft hashes, including uncommitted O_TMPFILE work.
Production, Demo, A3, Qwen, Hindsight, Arena configuration and Kokoro configuration
were not changed/restarted. No implementation branch or image was pushed.

## Smallest next action and remaining acceptance

Do not reactivate this image. Prepare a narrowly reviewed credential-distribution
fix: separate read-only copies of the same independent credential with each
consumer's existing owner (WebUI UID 0, bridge UID 10001), fixed per-consumer
owner/mode validation, and actual-image tests under both deployed users and
capability policies. Keep dropped capabilities, existing WebUI UID/data ownership
and authenticated fixed targets. Do not add DAC override, world-readable secrets,
legacy fallback or bypass validation. Test open and closed admission against both
actual images before another separately authorized controlled activation.

After that fix, repeat only the failed/unreached controlled gates: synthetic
Chinese/English/mixed transcription, live bounds/fault/cancellation/privacy,
resource observations and authenticated mounted native recorder/composer/manual
send/TTS/Pipe/Arena acceptance. Mac Safari and iPhone Safari remain **PENDING**;
no target-device behavior or complete dictation acceptance is claimed.

Residual host/client swap and core/crash dumps, hibernation, browser decoder
pre-validation allocations/memory persistence, synchronous inference continuing
after request cancellation, and legacy A3 conversion retention remain unresolved.
No host security setting was changed, and volatile memory is not equated with
immediate cleanup or a complete privacy guarantee.

## Publication boundary

Only this sanitized report and the multimodal index are published to
`reports/web-validation`. No credentials, raw runtime configuration, private
backup, conversation data, audio content or content-bearing logs are included.
The local activation candidate is preserved with its failure status; no further
activation, implementation or realtime voice work followed this rollback.
