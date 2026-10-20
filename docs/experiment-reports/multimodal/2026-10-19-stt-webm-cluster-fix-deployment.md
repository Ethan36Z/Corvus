# STT Lab — WebM streaming Cluster fix deployment

Date: 2026-10-19 (Lab operator timezone).

Verdict: **READY_FOR_MAC_ACCEPTANCE**.

The corrected Lab WebUI is healthy and private STT admission remains open.
Public synthetic Chinese and English requests pass. Real Mac microphone,
editable composer and manual Send acceptance remain **PENDING**; this report
is not STT_LAB_USER_ACCEPTED. No canonical chat was submitted for acceptance.

## Confirmed failure and minimal fix

Mac Chrome's caught exception identified `corvus-normalize.ts` rejecting element
`0x1F43B675`, WebM Cluster, because its size was unknown. The browser was running
the new recorder bundle. This directly establishes the latest failure before
native audio upload; earlier evidence of old JavaScript and mislabeled WebM
must not be used to attribute this later failure to browser caching.

The existing browser converter now permits unknown-sized Segment at the root
and unknown-sized Cluster directly within Segment. A streaming Cluster ends
at the next recognized Segment-level sibling or the bounded parent end; repeated
Clusters do not grow recursive depth. Other unknown-size elements remain rejected.
Encoded-size, decoded-duration, WAV-output, depth, element-count, timeout,
cancellation and authoritative backend PCM WAV validation remain.

Local-only implementation commit: `953d7c853a876d296bf776ce63637d0ad708111d`, branch
`fix/stt-webm-unknown-cluster`. Five committed files: the existing
`deploy/lab/stt/normalize.ts`, three existing regression scripts and the existing
synthetic fixture JSON. Only the normalizer's runtime source changes. No backend
converter, engine, model, authentication or microphone UI was introduced.

Offline evidence: the identical synthetic streaming fixture fails before decoding
on the old code and reaches decoding after the fix. Fifteen normalizer/boundary
and fifteen native recorder/composer tests pass; seven installed Linux Chrome
155 browser groups pass. Unknown-size and finite-size versions produce identical
PCM WAV bytes. The actual recorder onstop path with synthetic input produces
PCM16, 16 kHz, mono File/FormData; the unchanged native handler/strict validator
and mocked bridge accept it. Cancellation, editable insertion and no auto-send
regressions pass. Strict TypeScript checks and native Svelte compilation pass.
These are Linux/offline results, not target-device microphone acceptance.

## Resume, build and recovery protection

After the usage-limit interruption, the preserved work directory, successful
Vite log, generated build and running/stopped container state were reconciled.
The existing Node 22 offline frontend build had finished successfully and its
identity-scoped helper was absent. Its completed artifacts were reused; the
frontend was not rebuilt. Source-map content matches the exact committed fix.
The cached R7 source/assets differ only in the normalizer source, preserving
branding, Arena, Pipe and TTS frontend patches.

Pinned dependencies and images were reused without installing packages, models
or images. The replacement image inherits the current wired WebUI backend and
only replaces `/app/build`. An initial BuildKit packaging attempt interpreted the
bare SHA image ID as a repository and failed resolution; it downloaded no image.
The local-ID legacy builder completed the same narrow derivative successfully.

The earlier protected backup was retained. The fresh consistent backup already
completed before interruption was reused after checksum, permission, original
container/configuration and rollback-image verification. It contains the complete
242,073,600-byte WebUI volume archive and protected image/configuration/environment
snapshots; both SQLite integrity checks passed. The backup's WebUI-only pause was
1.808 seconds. Recovery directories/files remain 0700/0600. No conversation rows
were inspected, no volume was removed, reset or restored, and no old backup was
replaced. Frontend-only rollback preserves the current live data volume rather
than overwriting newer user data with an archive.

## Final deployment identities

| Component | Container ID | Exact image ID |
| --- | --- | --- |
| Lab WebUI | `25afa4a67ba7591bac1250e86173a0ca822db4b8a1088c9477ec60418fdd61e5` | `sha256:4b0451913d93774af57defe40873f29323239ef83ed7dfd8f405abe7b4f7ad17` |
| Unchanged private bridge | `ae40a734c973aa643369637d9df486e6d1a63710545ee8c7c62d8033f1cbaa5e` | `sha256:5d3cd6aff2db1a9712ce98669942d093858640298e9c04903f3cee3b510dc6b2` |
| Unchanged private Whisper | `2ff3bcc648fde90aa61a3f5a63b8a64ec11188afcde6c127a5f7ece43602cf07` | `sha256:caf0cd77c922e9c53f10a9bc17c2f74cc2295d12e7b0f96b630fb3b3c55a0026` |

Previous STT-enabled WebUI image
`sha256:88330ac2e1aa941386d8d2aaff5640f77d7343557969b74452798a6968bc60de`
is retained locally as the immediate rollback target.

Only Lab WebUI was recreated, using the existing scoped Compose invocation
with `--no-deps --no-build --pull never open-webui`. All environment values,
secret mounts, named data volume, host networking, UID 0, dropped capabilities,
security settings and native STT permission were preserved. The independent
consumer credentials and WebUI-only owner validator were reused without rotation,
permission broadening or disclosure. Admission was closed briefly for replacement
and reopened only after health/configuration checks.

The first replacement passed health and credential access but the operational
checker compared environment arrays in order. Docker reordered identical values,
triggering conservative WebUI-only restoration. Private comparisons confirmed
identical key/value maps and mounts, and the image inherited identical backend
environment. The checker was corrected to compare all values by key and mounts
by destination. The same built image was then installed successfully under the
existing authorization. This was a checker representation mismatch, not an
observed authentication, STT or TTS failure. No other service was restarted in
either attempt. The narrow operator scripts and rollback records remain retained;
no new implementation commit or implementation push was required.

## Focused live checks

| Check | Observed result |
| --- | --- |
| WebUI health / credential initialization | Healthy; strict fixed-path consumer credential read passes |
| Native configuration/authentication | Authenticated native cookie configuration returns private/server STT permission; unauthenticated native route 403 |
| Bridge authentication | Authenticated invalid-WAV probe 400; unauthenticated bridge 401 |
| Public Chinese WAV | HTTP 200, nonempty, existing public phrase check passes; 4.252 s; engine CPU 32.372 s |
| Public English WAV | HTTP 200, nonempty, existing public phrase check passes; 4.172 s; engine CPU 32.047 s |
| Corrupt / unsupported / oversized / over-120s | 400 / 400 / 413 / 400 |
| TTS | Authenticated public synthetic speech HTTP 200, finite mono PCM WAV at 24 kHz, private/no-store |
| Pipe / Arena | Existing active Pipe source/settings/owner-role fingerprint retained; Pipe model remains available; native frontend preservation evidence reused |
| Recording cache | Before/after audio-cache/upload metadata unchanged; no historical audio opened |
| Other services | All 25 other running-container IDs, images and StartedAt values match preflight |

Mixed-language quality remains the prior Retry 3 **QUALITY_REVIEW_REQUIRED**;
it was not reclassified or needlessly rerun for this parser fix. Previous online
provider-fault/timeout/cancellation evidence is reused. No fault injection or
restart of the unchanged engine/bridge occurred for this deployment.

Private engine/bridge memory peaks remain 938,053,632 / 58,789,888 bytes, within
unchanged 1088 / 256 MiB limits. Sampled current memory was approximately 656 /
51 MiB and sampled swap usage was zero. Existing 8/1 CPU limits, no-convert,
read-only storage, no engine host port and fixed authenticated routing are retained.
Docker logging remains disabled for the private services. The temporary native
acceptance token generated privately for checks was removed; no credentials,
audio content, transcript text, conversation data or backup content is published.

## Frontend delivery and actual gateway boundary

The new recorder/normalizer bundle is **`DMIyRNix.js`**. The running origin serves
that exact built artifact and the new index HTML. The corrected source map and
compiled bundle contain the bounded streaming-Cluster logic. A native-authenticated
client receives the new HTML at the WebUI origin.

The actual Lab gateway configuration still authenticates via FoxGate, forwards
to that fixed origin, and has `proxy_cache off`. An unauthenticated request for
the new asset through the gateway correctly returns 401. No authentication bypass
was used. At final checking, no authenticated gateway 200 for the new asset had
yet been observed in the filtered asset/status metadata. Thus authenticated Mac
HTTPS asset loading remains part of user acceptance, not a fabricated browser pass.
External unauthenticated host access policy is not evidence of an internal STT fault.

Production, Demo, legacy A3 Whisper, Qwen, Hindsight, Kokoro, private bridge,
private dictation Whisper, gateway/auth services, and all other running containers
retain their original identities and start times. Existing data, images, models,
credentials, backups and earlier worktrees/drafts remain retained. No Docker prune,
project-wide down, unrelated restart, dependency/model download or code-branch push
occurred. Only this sanitized documentation is published to reports/web-validation.

## Scoped recovery and Mac handoff

Immediate rollback uses the retained previous STT-enabled image and reviewed
Compose/mounts/environment, preserving the named WebUI volume. Close admission,
recreate only WebUI with that retained image, verify native/TTS/Pipe/Arena health,
and reopen the prior working STT admission. Do not invoke the old full-stack
Retry 3 rollback that removes the private bridge/engine. Retained deployment
operations include this WebUI-only rollback and can privately regenerate a fresh
short-lived native acceptance credential for verification; service credentials
and backup material are unchanged.

Open **https://lab-corvus.foxluma.com**. Follow legitimate Lab FoxGate login and
then Open WebUI login. Refresh the page after deployment. Use the existing
composer microphone, confirm a short Chinese recording, and check that recognized
text appears in the editable composer without sending. Repeat in English, check
cancellation, then manually Send only when the user chooses. Mixed-language is
optional quality review; iPhone Safari is deferred. Do not share credentials or
private recordings with the agent. Keep the private STT services running for use.
Only the user's successful real microphone and manual-send confirmation can change
the status to STT_LAB_USER_ACCEPTED.

Host/client swap, core/crash dumps, hibernation, browser decoder allocation/erasure,
worker cancellation limits and legacy A3 converter retention remain the previously
approved residual risks. This frontend fix does not claim to eliminate them.
