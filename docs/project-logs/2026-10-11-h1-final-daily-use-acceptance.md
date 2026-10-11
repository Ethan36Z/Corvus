# H1 FINAL — Daily-use acceptance and seal

Date: 2026-10-11. Exit decision: **H1 SEALED**.

This log seals existing acceptance evidence and the completed terminal reconciliation.
No live experiment was repeated during documentation. Operational acceptance passes;
maturity is a provisional local daily-use candidate with accepted constraints.

## Baselines and evidence

Before documentation edits, Lab was clean on `lab/ow2e-console` at
`98693f616c9f1e29bca3f8c1df48498a526dd7e9`. Production was clean on `main` at
`c315d0e767e31fde3c82ba4dfb08659a268c267a`. Production remained at that baseline.

Existing version-controlled milestones include the
[architecture freeze](2026-10-09-h1-7a-provisional-hindsight-architecture-freeze.md),
[first real async retain](2026-10-10-h1-7d-2f-2-real-async-retain-acceptance.md),
[live foreground admission](2026-10-10-h1-7d-3c-live-foreground-admission-rollout.md)
and [bounded consolidation](2026-10-10-h1-7e-bounded-consolidation.md).
The final turn's saved request/response, canonical-row verification, submission,
deferred operation, status polls and terminal result are under `/tmp/corvus-h1-final/`.
The ledger itself supplies the durable reconciliation evidence. Full private runtime
snapshots and environment values are not copied into Git.

## Exactly one canonical Lab turn

One normal Lab `POST /api/chat`, with a fresh dedicated session, `web_mode:off`
and no attachment, used this exact synthetic content:

```text
H1 FINAL synthetic acceptance marker: the temporary test codename is Indigo Heron 482. This is test data, not a personal fact. Reply only with: Recorded.
```

- Session: `h1-final-indigo-heron-482-1791693165030420222`.
- User message ID: **15**; assistant message ID: **16**.
- HTTP **200**, one attempt, **1303.519 ms**; visible response **Recorded.**
- Canonical SQLite count/max ID **14 → 16**. The session contains exactly the
  two matching rows, and all earlier canonical row hashes were preserved.
- Actual Lab publisher activity was sampled during foreground generation; it
  returned to count zero after the reply. Model/persistence status was OK/NORMAL.

There was one chat only, no ambiguous-chat retry, no duplicate canonical turn,
and no direct acceptance-script retain POST. The normal post-response Corvus
lifecycle created its one logical async retain submission.

## Durable retain submission and BUSY deferral

Bank: `corvus-hindsight-lab-v1`.

Document: `corvus-lab:turn:15:16`.

Client/parent operation UUID: **`7a6c0763-ebb0-4280-8265-b323135ae5e8`**.

Executable child UUID: `9dffcf70-0946-40c4-a5d9-25067006ada0`.

Contract version: **1**. Payload fingerprint:
`9d1ede15b905ee6eea3373fee7d5c1707361639af8666cbb3f34527cb7a0cc89`.
The reconstructed async request matched the exact canonical content, source/session/
message metadata, timestamp and deterministic document ID. The real accepted outcome
validated `success:true`, `async:true`, bank, one item and the pre-recorded UUID.

The existing private ledger is
`/home/ethan/srv/data/corvus/lab/h1-shadow-recall.jsonl`. Its linked sequence is:

1. Line **11**: the final turn's shadow comparison, before retain intent.
2. Line **12**: `RETAIN_INTENT`, `2026-10-11T05:01:07.894231+00:00`.
3. Line **13**: `RETAIN_SUBMISSION_ACCEPTED`,
   `2026-10-11T05:01:07.934336+00:00`, same client UUID.
4. Line **14**: linked async-submission retain outcome.
5. Line **15**: `RETAIN_STATUS(completed)`,
   `2026-10-11T19:46:49.420811+00:00`, after explicit terminal reconciliation.

The code's file lock, append-safe write and file/directory fsync enforce comparison
before intent and durable intent before POST. UUIDs and fingerprints are durable
operational metadata, not canonical evidence. Async acceptance is not retain completion.

A separate safe process used the **real** Lab tracker/registry publisher as logical
`lab-h1-final-acceptance` to hold host BUSY across the reply and initial background
attempt. Its identity was `661802-61140744-6b9764d1a4504c38a01ec819b7440fd6`.
This was a controlled scheduling seam, not a second chat or a claim that foreground
model generation itself lasted for the defer interval. Lab/Production publisher
identities and the expected Hindsight set `lab,production` were preserved.

At `2026-10-11T05:01:08.494015682Z`, the worker logged the same child deferred for
**foreground admission: BUSY**. It was **pending**, with
`next_retry_at=2026-10-11T05:01:38.492399+00:00`, retry count **0** and null error.
No memory-provider slot dispatch occurred while BUSY after the foreground reply;
the earlier foreground inference was the authorized chat itself. Deferral did not
fabricate completed/failed state, new facts, replacement operations or retries.

The controlled publisher finished at `2026-10-11T05:01:09.119718+00:00` and released
busy ownership. The unchanged **30-second idle/recovery grace** applied. The same
worker child resumed naturally; its only memory model slot dispatch was task **7152**
at `2026-10-11T05:02:09.257967231Z`, about **60.138 seconds after finish**, beyond grace.
Recorded observation reached terminal completion approximately **63.746 seconds**
after finish, within the bounded acceptance window.

Parent and child completed at `2026-10-11T05:02:11.006406+00:00`. Retry counts stayed
**0 → 0**. The child payload hash before/after was identical:
`83c0de1ffb737a6868b2ba248c3606fea8006054ebc82f25a8fca3f03e4fcfa7`.
The parent/child pair is native fan-out of one logical submission, not two retain
submissions or a replacement client UUID.

Retain extracted zero facts and tracked the document. Bank counts changed
**9 → 10 documents**, **9 → 9 memories**. Naturally queued consolidation
`869d8d12-c2d4-42ff-9d36-ae02c30c210b` completed with zero processed; it was not manually
triggered and is distinct from retain completion. Operations changed **13 → 16**:
one parent, one child and that automatic consolidation, all completed/error-free.

## Missing terminal reconciliation completed without repeating acceptance

Remote transport interruptions happened after the live acceptance had succeeded.
Read-only inspection found the server completed but the Corvus intent still unresolved;
the persisted events then stopped at accepted submission. No acceptance was repeated.

The separately authorized recovery queried the existing UUID, then invoked
`hindsight_shadow.reconcile_async_retain(max_operations=1, deadline_seconds=10)`
for the sole unresolved intent. A status-only transport allowed exactly one GET
inside reconciliation, with zero retries and no POST/replay path. The result was
**COMPLETED**, `outcome_durable:true`; the real ledger appended line 15 above.

A newly constructed `RetainLedger` recovered the target's
`terminal_status:completed`, `last_hindsight_status:completed`, and `unresolved:false`.
Unresolved intents changed **1 → 0**; both recorded logical operations are terminal.
The file contains **15 lines**, two intents, two accepted events and two status events.
Final SHA256 is `5f2cc8ba78b8ae3a42559ba4bd9ab359a2af79b0c5e0c8e4b2b87bc96784c46c`.
No new UUID, chat, retain submission, replay, inference, consolidation or restart
occurred during terminal reconciliation. Automatic reconciliation remains disabled.

## Existing bounded-consolidation acceptance satisfies the final check

The sealed H1.7e replay is the final frozen bounds evidence; no additional replay
was required or performed. It used real failed trace
`454bf090-99eb-4f9f-8171-4a47b4a5672e`, one source fact and three observations, through
the installed consolidator/provider, without applying returned operations or changing
bank/canonical data.

- Context **8192**, completion cap **1024**, safety margin **256**.
- Exact final rendered input **4131**; reservation **4131 + 1024 + 256 = 5411 ≤ 8192**.
- Actual provider request: `max_tokens=1024`, `reasoning_effort=none`,
  `chat_template_kwargs.enable_thinking=false`, consolidation scopes only.
- Response: **4131 prompt + 161 completion = 4292 tokens**, finish_reason **stop**,
  **4321.221 ms**, schema/source-ID validation **PASS**, one UPDATE, no CREATE/DELETE.
- Real consolidator returned normally, failed=false, **no OutputTooLong**, zero retry.
- Batch size one; oversized indivisible input defers before send without blind
  fact truncation or failed-fact marking. At least 512 completion tokens must fit.
- Exact serving-model template/tokenizer counting and the final foreground-admission
  recheck preserve the per-attempt context invariant and foreground priority.

Existing validation recorded 69 focused patch tests, ten pristine ordinary-error
regressions and seven runtime-preservation tests. They were not rerun for this
strict documentation task. A successful bounded response is not a guarantee of
complete semantic quality or a total multi-batch-job latency bound.

## Final read-only health, isolation and seal

Immediately before documentation edits, checks verified:

- Lab API **OK**, PID **13671**, async retain enabled.
- Hindsight **healthy**, version **0.10.1**, all guarded patched/dependency hashes valid.
  Container `271da9e5744daf97b14005294dc384fb139054daae310ec095b4fe391006c1b9`, PID **517830**;
  image `sha256:36a59577d7bdabe7525a114f8baa9bd26bac195df99e1999c807a3301be284f8`.
- Registry bind remains readonly. Both expected publishers are live/healthy,
  host aggregate trustworthy **IDLE**, active count **0**.
- Production API **OK**, PID **2831871**. Its repository, runtime/unit/environment,
  private SQLite/dense state and host deployment fingerprints match before-state.
  Production received no test turn or Lab memory writes.
- `:8095` **OK**, PID **2867**, unchanged image/container/start/configuration,
  one idle inference slot and 8192 context. :8106/:8107 identities also unchanged.
- Bank **10 documents / 9 memories**; all **16** operations completed, with **0**
  pending/processing operations. Canonical Lab messages/max ID **16**; no duplicate turn.
- Corvus unresolved retain intents **0**, verified by the real read-only reducer.
  Tail dense progress **12** is independent bookkeeping; direct turn indexing can
  create current rows ahead of it. No cursor repair or bootstrap was run for sealing.

No live request was repeated to seal H1. This task changes only the Phase Report
and this log; it changes no code, service/container configuration, registry state,
bank, Production data or model runtime. No restart, Reflect, reboot or push occurred.
Document/link/evidence consistency checks and `git diff --check` passed before sealing.

Accepted limitations:

1. No preemption when foreground arrives after memory inference has begun; no
   perfect arbitration or zero-wait guarantee.
2. Oversized indivisible consolidation may stay durably deferred and need operator
   attention; repeated foreground use can starve memory work.
3. Reflect remains deferred.
4. Retained documents do not necessarily yield semantic facts. COMPLETED means
   processing/storage succeeded, not semantic correctness or completed consolidation.
5. H1 does not establish universal semantic superiority over alternative memory
   architectures. Evidence is fixture-specific and natural history remains small.

**H1 exit decision: SEALED.** Canonical SQLite/Corvus context ownership is preserved,
Lab durable async retain and foreground-safe durable deferral are accepted, and
consolidation generation is bounded. Maturity is a provisional local daily-use
candidate with these constraints, not whole-system production certification.
Rollback recipes/images/containers and durable UUID/fingerprint/status history remain
available; recovery requires explicit observation, not fresh replacement submissions.
The [Phase Report](../phase-reports/h1-hindsight-integration.md) is the phase-level record.
