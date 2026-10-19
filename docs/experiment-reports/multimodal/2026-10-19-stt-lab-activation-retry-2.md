# STT Lab activation — Retry 2

Date: 2026-10-19.

Verdict: **STT_LAB_ROLLED_BACK**

The credential repair worked in the deployed topology: authenticated native
Chinese and English transcription each returned HTTP 200 and passed public
phrase keyword checks. Mixed-language transcription also returned HTTP 200 and
nonempty text, but failed the acceptance script's expected-word condition.
Admission was immediately closed and scoped rollback completed. **Lab is restored,
healthy and STT-disabled. No further activation or blind retry occurred.**

This is not ACTIVE_PARTIAL: the candidate was rolled back after the acceptance
check failed. The observed mixed-language result does not establish a transport
failure or prove that Whisper cannot transcribe mixed speech. The transcript was
not retained, so recognition error versus an overly narrow test criterion remains
unresolved. Neither the previous HTTP 503 permission failure nor an HTTP 502
occurred on the three synthetic transcription requests.

## Baseline and continuity

Read the complete [first activation/rollback](2026-10-19-stt-lab-activation.md),
[credential repair](2026-10-19-stt-credential-repair.md) and
[R7 preflight/checklist](2026-10-19-stt-r7-lab-preflight.md). Retry 2 used local
repair commit **`6a2a5eb1bab2c4c107dc34b60e2919071795bec1`** and existing R1–R7
code, model, successful frontend and wired images. No frontend/backend rebuild,
new engine, converter, UI or architecture was introduced; no downloads occurred.

A new retry-specific operational runner used the repaired three-variable mount
configuration. The old shared-secret activation runner was not used. No new
repository implementation changes were necessary; **no new code commit** was
created. The existing local repair commit remains the implementation baseline,
unpushed. Operational evidence and protected recovery material remain outside Git.

## Fresh preflight and protected backup

Fresh runtime inspection was compared with the latest credential-repair/post-
rollback snapshot, not the old pre-R7 ID. Starting Lab container was
`f030903208454567919b79c43bb09347bcdbd0eec101cefd877c4d919037c361`, healthy on
its original WebUI image. Environment values, existing data-volume mounts, host
networking and five-file Compose configuration matched the retained baseline.
Authentication, HTTPS-related settings, TTS, Pipe and Arena/Memory A-B were
preserved. No unexpected material drift was found.

Exact retained image IDs were verified locally. Existing model identity matched
487,601,967 bytes and its previously reviewed SHA-256. Port 18106 was free; no
conflicting STT service containers or named networks existed. Host had 9,647,960
KiB available RAM, 16 CPUs and load averages 0.24/0.24/0.21.

The prior protected backup manifest verified. Because WebUI had continued running,
a fresh consistent backup was made before runtime changes. Only Lab WebUI was
paused, for **1.851 seconds**, while its sole-writer data volume was archived
read-only. The 242,073,600-byte archive passed member/path/link/content-length and
hash verification; paused metadata stayed consistent. Copied WebUI and Chroma
SQLite databases passed integrity checks without querying private conversations.
Directory/file modes were 0700/0600. Original image, container configuration,
merged configuration, private environment and all five Compose files were retained
privately. Existing backups and canonical data were not overwritten or deleted.

## Repaired credential verification before deployment

The existing independent STT credential and separate consumer files were reused
without rotation or permission broadening: WebUI owner UID/GID 0/0, bridge owner
10001/10001, files mode 0400, consumer directories 0700 under a protected parent.
No credential values or credential hashes are published.

The public WebUI-only protocol artifact was checked against its pinned generator:
its only semantic change is the fixed expected credential owner from UID 10001
to UID 0. The bridge keeps the existing UID-10001 validator. Both exact candidate
images were tested before Lab recreation with actual UIDs, dropped capabilities,
read-only mounts, no-new-privileges and mocked upstreams only.

Fresh isolated tests passed CLOSED and OPEN admission, native synthetic auth,
actual cross-container service authentication/dispatch, incorrect authentication,
and missing/opposite-owner unreadable credential failures. Bridge compared its
assigned credential with the original privately under UID 10001; successful
WebUI-to-bridge HMAC authentication confirmed equality across consumers. Six
isolated cases passed; helper containers were identity-checked and removed.
No Lab network, host port, model or live Whisper was used by these checks.

Retry 2 used `CORVUS_STT_WEBUI_SECRET_FILE`,
`CORVUS_STT_BRIDGE_SECRET_FILE` and `CORVUS_STT_WEBUI_PROTOCOL_FILE`, retaining
fixed container paths, read-only mounts and missing-source creation rejection.
No consumer UID or capability was changed. New admission control began CLOSED.

## Actual installation identities and security

| Role | Exact image ID |
| --- | --- |
| Original/restored Lab WebUI | `sha256:72252f095805fa8aebb6ed17e7fb44c3746e9d2a289ec3ff395769aad0c44e3b` |
| Wired WebUI | `sha256:88330ac2e1aa941386d8d2aaff5640f77d7343557969b74452798a6968bc60de` |
| Wired bridge | `sha256:5d3cd6aff2db1a9712ce98669942d093858640298e9c04903f3cee3b510dc6b2` |
| Pinned independent Whisper | `sha256:caf0cd77c922e9c53f10a9bc17c2f74cc2295d12e7b0f96b630fb3b3c55a0026` |

New owned containers, subsequently removed:

- `corvus-whisper-dictation`:
  `d737ab79a9943b74770afce52d64d417d46a3e029731c700b72cc7ca74e22baa`.
- `corvus-stt-bridge`:
  `32ef4b2838bc67b10c4b3ba9335b12d86c4b506456f32cbc0cf7fe0991a2de0c`.

Only the new engine/bridge and two owned networks were created. Actual owner,
project/service labels, image IDs and exact network membership were verified.
Engine was healthy, internal-backend-only, no host port, no `--convert`, one
read-only existing model-file mount and read-only root. Its actual cgroups were
`memory.max=1140850688`, `memory.swap.max=0`, `memory.swap.current=0`,
`cpu.max=800000 100000` (eight CPU quota / 1,088 MiB).

Bridge used only 127.0.0.1:18106 ingress and the fixed private engine target, one
worker and existing one-request admission, no legacy fallback. Actual settings
included read-only root/credential mounts, UID 10001, all capabilities dropped,
no-new-privileges, bounded PIDs, 256 MiB/equal memory-plus-swap and one CPU.
Its cgroups were `memory.max=268435456`, `memory.swap.max=0`, current swap 0,
`cpu.max=100000 100000`. Both new containers had Docker logging `none` and empty
log paths. Immutable image commands retain discarded output/no access logs.

Owned networks, subsequently removed after exact-ID/ownership/empty checks:

- Internal backend `corvus-stt-dictation-private`:
  `1afecb1181cdd40b71eaadb440bfd7e7e51fd4b93ea9403ae39ab5c8e991fc79`.
- Bridge ingress `corvus-stt-dictation-ingress`:
  `fc8670e79e3e9fcfbbc758c2ea2e6175e537b2bda293f05b764da6d35609dcbe`.

Only Lab WebUI was recreated, first with repaired mounts/STT permission false,
then with permission true after baseline checks, always with admission CLOSED.
Actual strict WebUI credential read passed under UID 0/capabilities dropped.
Before opening admission, native auth, synthetic TTS HTTP 200/WAV/no-store, Pipe
model availability and exact Pipe/Arena technical configuration checks passed;
original environment matched before the STT-permission transition.

Final attempted wired WebUI container was
`e566e016c3c81528820b276071edbfffee5a69edf34ef36e1aa343b8b0b1926b`.
The earlier closed-permission wiring stage was
`f9edc10b2640e3b6bd45bf906344025a87c9822fac66745527fb9e5e4e7bae5c`.
No unrelated service was recreated or restarted.

## Synthetic STT observations and acceptance boundary

The same public synthetic finite mono PCM16/16 kHz WAV fixtures were reused from
the first attempt; no private or real microphone recording was used. Three
requests were made, one per fixture, with no retries. Transcripts were evaluated
in memory and were not logged or retained as report artifacts.

| Fixture | Audio duration | Native HTTP | End-to-end latency | Engine CPU time | Result |
| --- | --- | --- | --- | --- | --- |
| Chinese | 3.807 s | 200 | 4.360 s | 32.960 CPU-s | Nonempty, 17 characters; Chinese keyword check passed; no-store observed |
| English | 3.302 s | 200 | 4.122 s | 32.232 CPU-s | Nonempty, 50 characters; English keyword check passed; no-store observed |
| Mixed | 2.570 s | 200 | 4.399 s | 33.225 CPU-s | Nonempty bounded text, but expected-word check failed; immediate rollback |

These are authenticated native-route wall times and engine cgroup CPU deltas,
not isolated decoder-only timing or a language accuracy benchmark. Chinese used
an any-match check for simplified/traditional weather/test words. English required
`test` plus one of `hello`, `dictation`, `public`. Mixed required `你好` or
`Hello`/`hello` plus `test`, `voice` or `public`. That last condition can reject
an otherwise meaningful all-Chinese rendering; the retained metadata cannot tell
whether this happened. It is therefore an **unresolved acceptance/recognition
boundary**, not a verified model or language-support defect. No criterion was
weakened after failure and the request was not retried.

Peak observed engine cgroup memory across startup/requests was **860,913,664
bytes (821.031 MiB)**, below its 1,088 MiB limit. Peak bridge memory was
**54,489,088 bytes (51.965 MiB)**, below 256 MiB. Container swap remained zero in
all sampled metrics. About 33 engine CPU-seconds in roughly 4.1–4.4 wall seconds
shows substantial use of the eight-CPU quota; it is not a contention/QoS guarantee.
Bridge CPU deltas were small (Chinese 0.052 CPU-s, English 0.034 CPU-s).

After mixed acceptance failed, invalid/oversized/duration live rejection,
provider failure/timeout, live cancellation/admission recovery and mounted-page
composer/manual-send acceptance were **not run**. Their earlier offline evidence
is reused only as historical evidence, not relabeled fresh live acceptance.
Native unauthenticated rejection was checked before opening and after rollback;
correct actual native JWT/service authentication was exercised by all three live
requests. Invalid bridge authentication was freshly tested in isolation, not on
the deployed OPEN bridge. Synchronous worker termination was not observed/claimed.

## Privacy, browser and preservation evidence

The deployed engine omitted conversion and retained the pinned in-memory WAV
reader; no C++ change or server converter was introduced. Read-only engine/bridge
roots and absence of writable audio/data mounts constrain new conversion/cache
files. Docker logging was disabled as inspected above; source paths retain no
content logging and fixed routing/no legacy fallback. This does not establish
all possible system-level privacy properties or unexecuted failure behavior.

A metadata-only before/after inventory of WebUI audio-cache/uploads remained
unchanged: both directories had zero files. No historical audio content was opened
or inspected. No dictation attachment, artifact, transcript, canonical chat or
Hindsight submission was made. These observations cover the three synthetic
requests, not exhaustive storage/log/fault acceptance.

The available Chrome browser reached the target URL's **FoxGate Demo Access**
login gate rather than an authenticated mounted WebUI composer. No credentials
were entered and no microphone/private recording was used. Browser normalization,
editable-composer insertion, speechAutoSend suppression and manual-send control
acceptance are pending. The external access gate is not evidence of a Lab STT
route failure. Mac Safari and iPhone Safari remain **PENDING**, with no target-
device claim. No chat message was sent to demonstrate transcription.

## Executed rollback and verified final state

Admission was closed immediately on the mixed assertion failure. Only Lab WebUI
was restored from the fresh protected original configuration/image, with native
STT permission false and the same existing data volume. Original environment,
mounts and host networking match exactly after normalized comparison. No database
reset, canonical restore, volume deletion, model/image removal or prune occurred.

Only verified owned bridge/engine IDs were stopped/removed. Only their two owned
empty networks were removed by recorded exact ID after checks. Final inspection
confirmed those containers/networks absent. No uncertainty required broader cleanup.

**Current restored Lab WebUI:**
`4ecd0ddf7100f5e0543a5437f863c3d0b62b98229b2b8f158576b9adbe872d8d`,
healthy on the original `72252f095805...` image listed above. STT permission is
false and the retry admission marker is closed. Protected recovery/configuration,
original and repaired credentials, local images and prior backups remain retained.
The short-lived local acceptance-token file was removed after checks.

Post-rollback checks passed local health 200, unauthenticated audio rejection 403,
voice listing, public synthetic TTS HTTP 200/finite WAV/no-store, Pipe model
availability and exact technical Pipe/settings/Arena fingerprint preservation.
This is configuration/API preservation, not a fresh end-to-end Arena/chat exercise.
Legacy A3 and Kokoro retained exact ID/image/start metadata:

- A3: `51448dd0de959645e3a11433d5c58444e8b6c0dd2bed37d59dcf26ec4585edc5`,
  existing pinned Whisper image above; unchanged start.
- Kokoro: `72c8931661a11883f1dbb484933c61358ec7056a252208b8b95f315a2e8a3958`,
  image `sha256:94d19bad32ccb34df77cccc2f5c9bc4ebd1a225878be2522d27b16edc5ae3c44`;
  unchanged start. Only authorized public synthetic TTS requests were made.

Active Lab and implementation worktrees remain clean. Nine earlier STT worktrees
retain recorded HEAD/status/draft hashes, including uncommitted O_TMPFILE work.
Production, Demo, legacy A3, Qwen, Hindsight and Kokoro configuration/restarts were
untouched. No implementation branch was pushed.

## Smallest next action

Review the public mixed-language fixture and semantic acceptance rule offline
before another activation. Do not infer a mixed-language engine defect from a
keyword mismatch alone. A future authorized check should judge the public
synthetic response ephemerally against the spoken fixture, recording only verdict
and metrics, and distinguish meaningful translation/rendering from lost content.
No architecture change or new engine is justified by this evidence.

Any further activation requires separate authorization, retained repaired mounts,
fresh drift/recovery checks, then remaining live bounds/fault/cancellation/privacy
and authenticated native composer/manual-send/device acceptance. Do not continue
from a failed gate as ACTIVE_PARTIAL or silently relax the acceptance contract.

Host/client swap, core/crash dumps, hibernation, browser decoder allocation/
erasure, worker cancellation limitations and legacy A3 converter retention remain
unresolved risks. No host security settings changed; complete privacy is not
claimed. Only this sanitized report and the multimodal index are published to
`reports/web-validation`. Stop after rollback reporting; no realtime voice work.
