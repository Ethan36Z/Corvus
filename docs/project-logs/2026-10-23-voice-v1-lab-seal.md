# Voice V1 — Lab acceptance and engineering closeout

Date: 2026-10-23 (America/Los_Angeles).
Stage result: **VOICE_V1_LAB_ACCEPTED_WITH_CONSTRAINTS**.
Engineering closeout: **VOICE_V1_SEALED_LAB**.

Voice V1 development is closed for this Lab scope. The user explicitly confirmed
basic text chat, editable/manual STT dictation, Kokoro Read Aloud and half-duplex
Voice Call. This record combines that acceptance with read-only inspection of the
current deployment. It does not certify a Production release, comprehensive
voice quality, or end-to-end memory reliability. No new feature, test/build,
service operation, deployment, cleanup, push or merge was performed at closeout.

## Scope and implementation

Worktree: `/home/ethan/srv/apps/corvus-voice-v1`.
Branch: `feature/voice-v1-half-duplex`.
Integration parent: `93315415cf9efb541108e6f4fbcd3eb5967c9823`
(`integration/web-stage-seal`).
Application payload: `f6d94ffe48b2e07bd1adf0c5dc776850bb9c1980`.

The seven-file frontend overlay reuses native Open WebUI Call entry/recording,
existing WAV normalization and authenticated STT Bridge, native submitPrompt,
Corvus Pipe, existing personality/memory/Web behavior and Kokoro Read Aloud.
There is one chat runtime and no new scheduler. Ordinary Dictation remains
transcribe -> edit -> manual send. Call similarly requires review/confirmation
and explicit send for each turn, followed by the complete saved answer and speech.

The Call states include Listening, Transcribing, Review, Thinking, Synthesizing,
Speaking and visible Error/Unknown states. Recording is off during waiting and
playback. Implemented/offline-tested contracts include exactly one submission,
no automatic resend after timeout/unknown result, validated complete replies for
speech, media-only stop/hangup, and TTS replay without another chat submission.
The EventTarget-scoped UI correlation is not durable request idempotency or
browser-crash recovery. These implementation contracts are distinguished from
which cancellation details the user actually verified below.

## Commit chain and existing verification

| Commit | Contribution |
| --- | --- |
| `f6d94ffe48b2e07bd1adf0c5dc776850bb9c1980` | Opt-in half-duplex Call overlay, focused tests, offline implementation log |
| `b415ac958aa501c2d2bb33be57fed07c82a6411b` | Resource-blocked build evidence and Lab image-only rollout/rollback preparation |
| `45a70cfd294977f342ab4c9daa9d884bc8b9840b` | Successful full build and verified candidate evidence |
| This documentation commit | User-confirmed Lab acceptance, final limits and integration handoff; application payload unchanged |

Previously recorded checks are reused, not rerun: coordinator 17/17, native
Dictation 19/19, package contracts 9/9, five-component Svelte compilation/strict
TypeScript and fake-device two-turn Chrome checks. The later compatibility pass
covered 261 unittest cases (259 pass, two offline-subprocess skips), six assertion
scripts and the Vision frontend contract. Web W1/W2/Plan C boundaries,
Personality/P0.4, Pipe, STT/TTS, Arena and temporary-store memory checks were
covered offline. Mock/fake-device checks do not establish real acoustic quality,
live crash recovery or every Voice/Web/Arena combination.

The original 512 MiB heap cap was an explicit build-process flag. A later 2 GiB
attempt exhausted V8; the sequential 3 GiB old-space attempt passed the original
full Vite configuration with sourcemaps: SSR 1214 modules, client 4544 modules,
adapter-static completed, exit 0 in 114.10 seconds. The container peak was
4.25 GiB including charged cache, with at least 5.56 GiB host available RAM;
oom/oom_kill were zero. Existing locked dependencies/static assets were reused.
There was no build at this closeout.

## Candidate, deployment and rollback history

Candidate tag: `corvus-lab-webui:voice-v1-f6d94ff-candidate`.
Immutable image:
`sha256:5058ab1bdfd1112c38dda284f67c76717c0d6faf5eb425e59a0229f980c3ec6d`.
Rollback/base image:
`sha256:2427456fa33f5eccf8a854f9ad37f3af05f0cc443ae6348468f136a25a0745dc`.

Offline packaging replaced only `/app/build`: all 4751 frontend files matched
full build output, 349 application source maps and all seven overlay sources
matched, the enabled Call branch was verified, and 207 backend files plus
inherited runtime configuration matched the base. Voice is a build-time opt-in
for exact model `corvus_pipe` (`VITE_CORVUS_VOICE_CALL=true`); changing a container
environment variable cannot turn an already compiled frontend gate on or off.

The recovery package reached **BACKUP_READY** before activation: consistent
WebUI volume archive compared to then-current contents, two SQLite integrity
checks, configuration/Pipe/model snapshots, and all 28 dirty Lab files backed up
and hash-checked. STT bind sources were separately backed up and restore-tested
under manual root authorization; the exported `STT_BIND_RECEIPT_VERIFIED` receipt
was integrated without bypassing permissions or re-running root backup. The
failed zero-byte bind archive was explicitly excluded. Sensitive archives and
receipts stay outside Git in the private operator recovery directory:
`/home/ethan/.config/corvus-lab/voice-v1-activation-a9quxa91/`.
This is a historical verified recovery point, not a claim of a new backup today.

Controlled rollout replaced only Lab Open WebUI. An initial strict configuration
comparison caused a conservative rollback because Docker reordered mounts/env
and represented empty DNS defaults as null. Inspection confirmed equivalent
actual settings; only the temporary comparison was normalized. A later native
login smoke returned HTTP 400 and triggered a successful image-only rollback,
without restoring databases or deleting accepted messages. Read-only diagnosis
found the saved bootstrap identity absent in both pre-activation and current auth
records; the endpoint/JSON were correct and candidate/base auth code identical.
The existing Corvus administrator identity was different and active. No account,
password, signing secret or authentication policy was changed.

That automated smoke stopped at login: it did not perform chat, STT or TTS
requests. Its saved `BLOCKED_LOGIN_SMOKE_ROLLED_BACK` result is an earlier attempt,
not the current deployment state or a passing end-to-end smoke report. The user
subsequently completed actual Lab use and confirmed the four basic acceptance
items. Current read-only inspection corroborates the deployed candidate; this
closeout did not execute the intervening activation or reproduce the user's tests.

Image-only rollback remains documented in
`deploy/lab/voice-call/LAB_ACTIVATION.md` and `compose.rollback.json`. Retain current
mounts/secrets/data and restore the immutable old image through the same Lab
Compose project, under separate operation authorization. Do not use compose down,
remove volumes, or restore an old database for an ordinary image rollback: new
conversation records and accepted background operations must survive.

## Actual acceptance and explicitly unverified details

Source: the user's explicit final acceptance instruction in this session.

| Item | Live acceptance |
| --- | --- |
| Text chat | PASS — user confirmed |
| Ordinary STT Dictation | PASS — user confirmed editable transcript and manual send |
| Kokoro Read Aloud | PASS — user confirmed basic operation |
| Half-duplex Voice Call | PASS — user confirmed basic operation |
| Particular languages, accents, voices or acoustic conditions | Not separately confirmed; no per-language quality claim |
| Stop playback, hangup during generation, late completion and advanced cancellation/failure cases | Not separately confirmed live; prior offline contracts only |
| Reconnect, unknown-result recovery, long continuous sessions and duplicate prevention after browser/process failure | Not separately confirmed live |
| New Voice-specific Web/Arena A/B combinations and comprehensive retain/recovery behavior | Not a new live acceptance claim; prior compatibility evidence only |

The basic Call acceptance does not establish a specific round count, latency
percentile, supported-device matrix or uninterrupted long-call reliability.
No additional acceptance gate or development phase is opened by these limitations.

## Constraints carried forward

- Call requires manual transcript confirmation/editing and explicit submission.
- Speech begins after the complete answer is generated/saved; no true token
  streaming, speculative partial speech or full-duplex conversation is delivered.
- Qwen and Hindsight share inference resources. Existing serial contention and
  foreground waiting remain; no latency/preemption guarantee is made.
- The existing BackgroundTasks -> durable retain-intent handoff window and lack
  of automatic recovery/reconciliation remain unfixed. A process interruption
  can leave background submission absent despite canonical persistence. A
  successful foreground turn does not certify completed Hindsight retention.
- Lab basic acceptance is not a Production/Demo release or full memory-integrity
  acceptance. P0.2 BLOCK/personality-quality limits remain unchanged.

Reliability and Memory Integrity First. Latency Optimization Second. Original
message persistence, assistant commit ordering and background operation identity
were not redesigned. VAD, Call-only automatic submission and automatic turn
switching are optional later experience improvements; none is implemented or
committed as follow-up work here. Ordinary Dictation's editable/manual-send
behavior must remain distinct if those options are pursued later.

## Read-only closeout observation and Corvus v1 handoff

Observed 2026-10-23 20:10:48 PDT (2026-10-24 UTC). Lab WebUI is running and healthy
on the exact candidate image/tag above, host networking. Container:
`ff82a59a87eaa058394b8f8fc921acace748f3d6594236bc29ad4f61d440e2f4`.
Reported start: `2026-10-24T02:43:48.197744555Z`.
Compose sources are the existing
`/home/ethan/.config/corvus-lab/chat-recovery-runtime/recovery/candidate-compose.json`
plus this branch's `deploy/lab/voice-call/compose.candidate.json`.
The rollback/base image is still available.

Live Lab source remains `lab/ow2e-console` at
`4f8013af2c8e73774fcef91c2510e5808c1fd2c2` with **28 protected dirty files**.
Their tracked/untracked hashes, HEAD, status and index match the activation
baseline. Integration/main source snapshots, relevant service PIDs/environment
hashes/drop-ins and all non-WebUI container identities/configuration also match.
Production/main remains `8b863ec95b8c133951e166c8b60d6335b764f7db`.
No running configuration or service was modified during this documentation pass.

For Corvus v1 integration, use this Voice branch's small overlay and sealed
candidate/provenance relative to integration baseline `9331541`; preserve the
actual dirty Lab runtime as a separate integration input. Do not copy a whole
checkout over it, discard those 28 files, or assume live Lab equals the integration
branch. This frontend image does not deploy API STT refactor `688a8bb`. Keep the
existing API/STT Bridge/Whisper/Kokoro/Qwen/Hindsight and mounted STT protocol/
credentials consistent with the runtime manifest; do not package private volumes
or credentials into the integration commit. No merge/cherry-pick/push is performed
or implied here. Further integration/release operations require their own scope.

Historical implementation/build evidence is in the three earlier Voice V1 logs.
Final inspection evidence is local at `/tmp/corvus-voice-v1-seal/inspection.json`;
private backups/runtime logs remain outside Git. This documentation commit is the
final Voice V1 closeout commit; its SHA is reported in the delivery message.
