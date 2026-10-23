# Voice V1 — isolated half-duplex Call implementation

Date: 2026-10-23. Result: **V1_IMPLEMENTED_OFFLINE**; no live activation.

Worktree: `/home/ethan/srv/apps/corvus-voice-v1`.
Branch: `feature/voice-v1-half-duplex`.
Parent baseline: `93315415cf9efb541108e6f4fbcd3eb5967c9823`.
No main/Production/Demo/Lab code, memory logic, Personality, Web, Vision, Arena,
model launch parameter, deployment or running image was modified. No push/merge.

## Delivered behavior

The native Open WebUI Call entry/container hosts a Corvus-only opt-in panel. It
reuses current VoiceRecording, real WAV normalization, authenticated private STT,
native submitPrompt, Corvus Pipe and Kokoro Read Aloud. No second chat backend or
new inference scheduler exists. The original Dictation stays editable/manual-send.

The loop provides Listening, Transcribing, Thinking and Speaking, plus review,
synthesis, error and unknown states. It supports recording/cancel, editable
confirmation, one send, confirmed complete answer, speech, stop and another turn.
The mic is off while waiting/playing. Corvus mode avoids legacy continuous capture,
optional emoji inference and browser TTS initialization. It is disabled before
microphone acquisition unless built with `VITE_CORVUS_VOICE_CALL=true`.

A stopped playback or hung-up call does not abort submitted chat or memory work.
TTS cancellation suppresses late audio; upstream admitted work may finish.
Unknown/timeout locks the Call turn instead of retrying. A late validated reply
is recorded by the original backend path and not played unexpectedly. The small
UI correlation map survives layout remount but is not a durable backend job ID.
Speech replay never resubmits chat. Complete saved replies are used, without
speculative/token speech or partial assistant persistence.

The frontend preparer checks five exact public source pins and creates seven
files in a fresh output directory. Current normalizer, Dictation composer handler,
STT protocol, Pipe and backend implementations are retained. The API client gains
only an optional TTS AbortSignal. Package preparation and enable/rollback details
are in `deploy/lab/voice-call/README.md`.

## Verification

- Call coordinator: **17/17** Node tests. Includes two turns, double send,
  review/edit, late/foreign events, timeout, unknown response, hanging up pending
  work, remount, TTS cancellation/failure/replay and stale callbacks.
- Existing native Dictation/browser contracts extended narrowly for Call events,
  opt-in entry and optional TTS cancellation: **19/19** Node tests. Editable/manual
  Dictation remains unchanged even with speechAutoSend=true.
- Source preparation/default-off/scope contracts: **9/9** Python unittest cases.
- **Five Svelte components compiled**, and coordinator **strict TypeScript passed**.
  The unchanged native video branch retains its pre-existing missing-captions
  compiler warning; the new Call panel has none.
- Real isolated headless Chrome mounted the **native CallOverlay** and native
  recorder/converter, using a fake device and synthetic WebM. Two confirmed sends
  and two simulated canonical replies completed; one was spoken, the second
  completed after hangup without speech. **chat abort calls=0**, edit preserved,
  all microphone tracks and audio object URLs released. No real model/TTS or
  human microphone/listening test was performed. Real-browser testing caught and
  fixed a Window timer binding error before closeout.
- Eight existing isolated backend suites: **96 unittest cases, 95 passed / one
  existing Pipe subprocess skip**, plus **four passing module-level assertion
  scripts** for voice runtime/API and TTS adapter/API.
- Memory suites specifically passed: async retain integration 18, ledger 27,
  reconciliation 26. They use temporary stores and mock transport. Initial runs
  of two suites were blocked by the pre-existing Web acceptance guard treating
  `file:///tmp/...?...` SQLite URIs as deployed databases. Re-running used only a
  temporary URI-aware copy of that guard inside the same bwrap network/private
  data isolation; the repository guard and memory code were not changed. Final
  guard logs reported no network/private-data access violations. This is not
  live crash/recovery proof.

Build dependencies came from the existing SHA-verified lock/cache: Svelte 4.2.19,
TypeScript 5.5.4 and esbuild 0.25.1. A full dependency restoration attempt hit its
isolated 1GB container memory cap (exit 137); it was removed automatically. To
protect the low-memory host, only 27 locked compiler packages were extracted
from that cache and the component/browser bundles were built. No dependencies
were upgraded/installed in active source. **Full production Vite/image build is
still a Lab acceptance prerequisite**, not claimed complete here.

Local evidence: `/tmp/corvus-voice-v1-build/focused-logs/`,
`focused-results.json`, `final-overlay/voice-v1-proof.json`, and
`regression-logs/` (the `uri-*` files contain final memory-suite results).
Those temporary files may be cleaned by the host. All fixtures and tokens in
frontend tests are synthetic. No deployed user/chat/credential data was read.

## Memory reliability and release boundary

Reliability and Memory Integrity First. Latency Optimization Second.

Canonical messages and existing assistant commit ordering are unchanged. The
original BackgroundTasks → durable retain-intent crash window and lack of
automatic reconciliation remain. Hindsight completion is not guaranteed by a
successful foreground turn, and failed/ambiguous background work must not be
reported as completed. No task identity was replaced, no accepted operation was
cancelled, and no retry/grace policy was altered. **End-to-end memory reliability
is not certified by this release. P0.2 BLOCK remains unchanged.**

Future automatic Call submission can reuse the separate transcribed/send methods;
it must not reactivate Dictation auto-send or bypass confirmed reply/persistence
checks. True token streaming, preemption, model-slot reclamation, memory-flow
reconstruction and performance guarantees are outside V1.

Lab acceptance requires a reviewed full pinned frontend build, protected current
Lab snapshot/rollback, exact Lab model binding, and separate activation approval.
Then verify actual login, Chinese/English microphone quality, editing, save-before-
speech, stop/hangup, repeated turns and existing text/STT/TTS/Web/memory behavior.
No destructive fault injection against live Lab is part of acceptance. Record
memory backlog/failure visibility and the existing gap explicitly.

## Protected-state observation

Final source hashes/status/index of the integration baseline, dirty Lab and main
match the V0 snapshot. Lab PID 828169 and Production PID 6052, their environments,
Docker daemon and all container identities/configuration match. Demo API changed
PID to 1006708 at 04:00:11 PDT. Read-only lifecycle evidence identifies the
**existing** corvus-demo-reset.timer trigger at 04:00:01 and successful reset
service completion at 04:00:18; this was not performed by the Voice workflow.
Demo source is unchanged. No Demo database content was read or changed by this
implementation. Kernel evidence confines the npm test OOM to its 1GB temporary
Docker memory cgroup; no service OOM/restart was attributed to that attempt.
