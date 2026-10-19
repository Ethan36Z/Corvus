# STT Lab — Retry 3 activation and Mac handoff

Date: 2026-10-19.

Deployment state: **STT_LAB_READY_FOR_MAC_ACCEPTANCE**

**Lab STT is running. Native STT permission and both admission gates remain open.**
Chinese and English public synthetic dictation pass the existing phrase checks.
Mixed-language quality is **QUALITY_REVIEW_REQUIRED**, not a system fault or an
accepted accuracy claim. Deployment hard gates passed; Mac user microphone,
editable composer and manual Send acceptance have not occurred. Do not mark
STT_LAB_USER_ACCEPTED until the user personally confirms those steps.

## Reused baseline and exact scope

Reused the completed [Retry 2](2026-10-19-stt-lab-activation-retry-2.md),
[credential repair](2026-10-19-stt-credential-repair.md) and
[R7 checklist](2026-10-19-stt-r7-lab-preflight.md), starting from local commit
`6a2a5eb1bab2c4c107dc34b60e2919071795bec1`. The user's explicit Retry 3 activation
and ship-to-Mac authorization covers the operations recorded here.

No frontend/backend image rebuild, dependency/model/image download, engine,
converter, microphone UI or architecture change occurred. R1–R7 suites were not
repeated. Existing private model, no-convert engine, R1 transport, R2 authenticated
bridge and R3–R4 native recorder/composer were reused.

Local-only commit **`dc46ab579be3b91b6b11cba730e5da98644bc4c8`**, branch
`integration/stt-lab-retry3`, preserves two files:

- `deploy/lab/stt/activation/live_acceptance.py`: existing operational acceptance
  script with separated mixed-quality classification, the remaining authorized
  online fault/cancellation checks, and correct native-cookie config checking.
- `deploy/lab/stt/activation/README.md`: operational instructions and Mac handoff.

This is an operator script, not a new test framework or deployed endpoint.
No implementation branch or image was pushed. No canonical chat or Hindsight
submission was made to demonstrate dictation.

## Preflight, metadata and recovery

Fresh checks matched the latest Retry 2 rollback identity/environment/mounts and
healthy original image. Three candidate images, original rollback image and
existing model identity were present/matched. Port 18106 was free; no conflicting
STT containers/networks existed. Available RAM was 9,313,884 KiB, 16 CPUs and low
load. Host swap remained an approved residual risk; no host settings changed.

The remaining metadata blocker was resolved using two temporary, network-disabled,
read-only consumer containers with their exact images and UIDs and zero added
capabilities. They only stat'ed their assigned protected directories/files;
credential contents were not read or printed by this check:

| Consumer | UID/GID | File | Consumer directory |
| --- | --- | --- | --- |
| WebUI | 0/0 | 0400, regular, 64 bytes, one link | 0700, owner 0/0 |
| Bridge | 10001/10001 | 0400, regular, 64 bytes, one link | 0700, owner 10001/10001 |

The independent existing credential was not rotated. Separate read-only sources
and the pinned WebUI-only UID-0 validator were retained; no consumer permissions
were broadened. Both metadata helpers were identity-checked and removed.

Prior backup integrity and recovery configuration verified. A fresh consistent
protected backup passed full archive checks and two SQLite integrity checks,
without querying private conversations; Lab pause was 1.491 seconds. A later
checker-induced recovery used another fresh backup (pause 1.389 seconds). Both
242,073,600-byte archives, original configuration/environment/image, earlier
backups and all recovery material remain retained privately with 0700 directories
and 0600 backup files. No volume deletion, reset or canonical restore occurred.

## Final running identities and actual isolation

| Service | Final full container ID | Exact image ID |
| --- | --- | --- |
| Lab WebUI | `13f4874bc04b594d800e23fd83e0577c717a947d97a1e8d83f6518cf9e2f4a91` | `sha256:88330ac2e1aa941386d8d2aaff5640f77d7343557969b74452798a6968bc60de` |
| corvus-stt-bridge | `ae40a734c973aa643369637d9df486e6d1a63710545ee8c7c62d8033f1cbaa5e` | `sha256:5d3cd6aff2db1a9712ce98669942d093858640298e9c04903f3cee3b510dc6b2` |
| corvus-whisper-dictation | `2ff3bcc648fde90aa61a3f5a63b8a64ec11188afcde6c127a5f7ece43602cf07` | `sha256:caf0cd77c922e9c53f10a9bc17c2f74cc2295d12e7b0f96b630fb3b3c55a0026` |

Actual inspection verified full identities/owner/project/service labels, no engine
host port, internal backend membership exactly engine+bridge, and bridge-only
ingress membership. Only bridge publishes 127.0.0.1:18106. Targets remain fixed
native loopback → authenticated bridge → private engine /inference; no request-
selected upstream, redirect, retry or legacy A3 fallback was introduced.

Engine omits `--convert`, has one read-only existing model-file mount, read-only
root, UID 10001, dropped capabilities, no-new-privileges, core limit zero, eight
CPU quota, 1,088 MiB and equal memory-plus-swap. Actual cgroups read
`cpu.max=800000 100000`, `memory.max=1140850688`, `memory.swap.max=0`.

Bridge retains UID 10001, dropped capabilities, no-new-privileges, core zero,
read-only root/secret mounts, bounded PIDs, one worker/request admission, one CPU,
256 MiB/equal memory-plus-swap. Actual cgroups read `cpu.max=100000 100000`,
`memory.max=268435456`, `memory.swap.max=0`. Actual capability mask, UID and core
checks passed. No sampled swap or OOM kills occurred. Both new services use Docker
logging none/empty log paths; process stdout and stderr point to /dev/null.

WebUI still runs UID 0 with dropped capabilities, host networking and its existing
persistent data volume. Only STT permission differs from original environment;
authentication, HTTPS settings, TTS, branding, Pipe and Arena/Memory A-B are retained.
Actual strict credential read and CLOSED admission were verified before opening.

## Online acceptance obtained

Only public synthetic WAV fixtures were used. No private/real microphone audio
was recorded or inspected by the agent; no raw transcripts were retained.

| Live check | Observed result |
| --- | --- |
| Final-instance Chinese | HTTP 200, nonempty, existing phrase check ACCEPTED; 4.342 s end-to-end, 32.935 engine CPU-s |
| Final-instance English | HTTP 200, nonempty, existing phrase check ACCEPTED; 4.141 s, 32.401 engine CPU-s |
| Mixed in earlier same-candidate Retry 3 instance | HTTP 200, 4.411 s, 36 characters; greeting/public/voice/test concepts detected; full meaning QUALITY_REVIEW_REQUIRED |
| Unauthenticated native / bridge | 403 / 401 |
| Wrong bridge credential | 401 |
| Corrupt / unsupported-format audio | 400 / 400 |
| Oversized request | 413 |
| Duration over 120 seconds | 400 |
| Request-selected upstream query | 400 before provider dispatch |
| Provider unavailable, intentionally stopped owned private engine | Sanitized native 502, 0.093 s; same owned engine restarted/restored |
| Provider paused to force deadline | Sanitized native 502 after 25.057 s; engine unpaused and admission recovered |
| Client cancellation | Client task cancelled; busy admission observed (503), recovered to validation response (400) by 4.975 s from request start |
| Final health / native cookie configuration | Healthy; native permission true, private/server STT path; admission open |
| Final TTS / Pipe / Arena | Public synthetic TTS 200/finite WAV/no-store; voice/model availability and exact technical configuration fingerprint retained |

The unavailable/deadline/cancellation checks are **actual online Retry 3 evidence**,
not offline mocks. They ran in the earlier identical-image/configuration instance:
engine `4b75423d8c90da2523a210c74eb467fb55570f5653dad23f52bc0c5adca637b2`, bridge
`48bc213fb6811f98cf7084d00d7baf0a5fbf701afcca21c5890f57b62a042f32`.
After the checker recovery described below, normal Chinese/English, live auth and
bounds, cache, current security/resources and original-function checks were
reverified on the final running IDs. Fault experiments were not unnecessarily
repeated. A cancelled caller does not prove synchronous thread/engine termination;
late work can continue and admission remains owned until the real worker settles.

Final observed cgroup memory peaks: engine **938,053,632 bytes (894.598 MiB)**,
bridge **58,789,888 bytes (56.066 MiB)**, within unchanged limits. CPU observations
are synthetic-profile measurements, not concurrency/QoS guarantees.

Mixed-quality handling does not equate HTTP 200/nonempty with accuracy. The old
keyword assertion is no longer a system exception. Only known public equivalent
renderings are automatically accepted; clearly unrelated output is QUALITY_FAIL;
otherwise QUALITY_REVIEW_REQUIRED. Current evidence detects the four expected
concepts but does not certify the full wording. No model defect or complete
mixed-language quality acceptance is claimed, and no raw result is published.
Four public branch checks exercised equivalent speech, equivalent translation,
unresolved quality and unrelated output. All protocol/privacy/auth/resource hard
checks retain shutdown/rollback behavior.

## Checker mismatch and controlled recovery within Retry 3

One final checker used Bearer on `/api/config` and assumed an authenticated
`audio` field. Pinned Open WebUI 0.6.5 reads that endpoint's user from the native
`token` cookie; without it the endpoint correctly returns public configuration.
The resulting KeyError triggered the conservative operational rollback, not a
Whisper, authentication or audio-storage failure. This was not a mixed-quality
rollback. It is recorded rather than hidden as a clean uninterrupted rollout.

The one checker was corrected and first verified against the pinned endpoint
before restoration. `native_config()` now uses the existing short-lived native
token cookie privately and verifies audio mode plus actual frontend STT permission.
No WebUI authentication or browser cookie policy was changed. Under the user's
existing Retry 3 authorization, recovery configuration matched, backup was refreshed,
and the **same** pinned candidate was restored with admission CLOSED, original
features rechecked, then admission opened and final checks passed. No extra
architecture or full R1–R7 rerun was introduced. Final state is ACTIVE, not rolled
back; no additional activation authorization was requested.

## Application privacy and preservation

Before/after WebUI audio-cache/upload metadata remained identical and empty.
No historical recording was opened. The no-convert image uses its pinned in-memory
WAV reader; read-only engine/bridge roots and no writable data/audio mounts constrain
persistent writes; no disk conversion step was invoked. Logging settings and fixed source paths were verified;
no transcript/audio content was placed in test output, reports or Git. Only
quality metadata, timing/status and resource observations were recorded.

All original data volumes, model/image files, backups and earlier worktrees/drafts
remain preserved. Nine earlier STT worktrees retain recorded HEAD/status and draft
hashes; active Lab Git and the prior activation/repair worktrees remain clean.
A3 and Kokoro exact container ID/image/start times are unchanged. No operation
modified/restarted Production, Demo, Qwen, Hindsight or Kokoro. Synthetic TTS calls
used the existing service without configuration changes. No Docker prune or
project-wide down occurred. No chat/Pipe message was sent to manufacture acceptance.
Pipe/Arena checks mean API/configuration preservation, not a new canonical chat or
end-to-end Arena trial. Short-lived local acceptance-token files were removed;
independent service credentials and all recovery materials remain protected.

Host/client swap, crash/core dumps, hibernation, browser decoder allocation/erasure,
worker cancellation limits and legacy A3 converter retention remain the approved
residual risks. No host security setting was changed; complete privacy is not claimed.

## Mac user handoff — services intentionally stay running

Open **https://lab-corvus.foxluma.com**. Complete legitimate **Lab FoxGate login**,
then the independent **Open WebUI login**. The generic FoxGate page title may say
Demo Access; the inspected Lab gateway routes this hostname to Lab WebUI. Use Lab
credentials, not a Demo realm, and do not provide passwords/tokens to the agent.

The available agent browser had no authenticated composer session. Browser
acceptance is **blocked pending user login**, not passed and not a deployment
rollback reason. No authentication bypass was used. Actual Mac microphone,
decode/resampling, editable insertion, no auto-send and manual Send remain the
user's acceptance steps; iPhone Safari is deferred and does not block Mac.

After login, refresh once if the old page is cached. Use the existing microphone
next to the composer, allow microphone access, speak a short Chinese sentence,
and finish with the native recording confirmation. Wait for text in the editable
composer; inspect/edit it and press Send yourself. Repeat with a short English
sentence; mixed language is optional and remains a quality-review item. Cancel a
recording once to check nothing is submitted. Do not mark STT_LAB_USER_ACCEPTED
until the user confirms real microphone and manual-send behavior.

No further engineering experiments follow this handoff. Keep the private STT
services and admission running for user use. Any subsequently discovered hard
security/privacy/resource/important-function failure still requires close admission
and the retained exact-owned-resource rollback, preserving the data volume.
Only this sanitized report and index are published to reports/web-validation.
