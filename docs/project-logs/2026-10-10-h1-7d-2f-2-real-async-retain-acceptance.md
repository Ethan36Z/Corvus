# H1.7d-2f-2 — One real Lab async-retain acceptance turn

Date: 2026-10-10

Verdict: **PASS** for the first real durable async-retain lifecycle. One canonical
Lab turn produced one durable client retain intent, an accepted async operation,
successful worker processing, and an explicitly reconciled terminal ledger state.
Production remained untouched. No application or deployment code change was needed.

## Before state

Read-only preflight at `2026-10-10T22:30:13.737698+00:00`, repeated immediately
before the single chat submission, verified:

- Lab: clean `lab/ow2e-console` at
  `9e0dff39611496583bcc7b33d511fd8d773092ef`.
- Production: clean `main` at `c315d0e767e31fde3c82ba4dfb08659a268c267a`.
- Lab PID **13671**, runtime/unit async-retain flag **true**; Production PID
  **2831871**. Both APIs were healthy.
- Both foreground publishers held their live/health locks and were idle.
  The explicit `lab,production` aggregate was trustworthy **IDLE**, count zero.
- `:8095` healthy/idle, model container process PID **2867**.
- Hindsight healthy, process PID **2884**, container
  `336680f1d0a7a4dfb531f818976e969b6e1c7e55861fec4b605401df295a8bfe`.
  Image/configuration/start identity matched the sealed enablement baseline;
  the foreground registry remained unmounted and absent inside Hindsight.
- Target bank: `corvus-hindsight-lab-v1`; **7 documents / 7 memories**.
- Lab canonical SQLite: **12 messages**, maximum ID **12**. Dense readiness:
  all 12 rows current, progress **12**, caught up.
- Private shadow/retain ledger: **5 lines**, **0 intents**, **0 logical retain
  operations**, **0 unresolved intents**, verified using the real ledger reducer.
- Hindsight's read-only operation listing contained 7 existing operations and
  no pending/processing work.

## Exactly one normal Lab turn

One `POST http://127.0.0.1:18096/api/chat` used a fresh session and `web_mode:off`
through the normal API/conversation runtime. No attachments were supplied.
The user content was exactly:

```text
H1.7d-2f-2 acceptance marker: the temporary test codename is Silver Raven 271. Reply only with: Recorded.
```

This is synthetic acceptance data, not a personal fact. It remains in the Lab
evidence log and derived Hindsight state; no cleanup/deletion was performed.

- Session: `h1-7d-2f-2-silver-raven-271-20261010T223019551148Z`.
- Chat attempt began: `2026-10-10T22:31:08.843297+00:00`.
- HTTP **200**, elapsed **4042.283 ms**, visible reply **`Recorded.`**.
- User message ID **13**; assistant message ID **14**.
- Foreground model, persistence, retrieval, dense indexing, inspection and
  overall response statuses: **OK** / persistence **NORMAL**.
- Canonical count **12 -> 14**, maximum ID **14**. The fresh session contains
  exactly these two rows; their content matches the request/response. All previous
  canonical message hashes remain unchanged. No duplicate turn exists.
- Foreground activity returned to **IDLE** and published a completion watermark.

The client used zero HTTP retries, no redirects, and a fsynced exclusive-create
one-use guard before POST. An ambiguous outcome would have stopped without another
submission. The real response was unambiguous and successful.

## Durable ledger and actual async proof

Document ID: **`corvus-lab:turn:13:14`**.

Stable client operation UUID: **`d6afe2e0-e019-4f4e-8bc1-6c218ff08498`**.

Contract version: **1**. Canonical payload fingerprint:
`d33ef03d2b1e92e853aeb530304159ba22996c53b30fc825ce9ef3b84daa8fc6`.
Rebuilding the exact item from canonical rows and verifying it with
`async_retain.build_async_request` reproduced the recorded contract/fingerprint.

The real append-only sequence in
`/home/ethan/srv/data/corvus/lab/h1-shadow-recall.jsonl` was:

1. Line **6**: shadow comparison, `2026-10-10T22:31:13.604113+00:00`;
   shadow recall **OK**.
2. Line **7**: `RETAIN_INTENT`, `2026-10-10T22:31:13.614202+00:00`.
3. Line **8**: `RETAIN_SUBMISSION_ACCEPTED`,
   `2026-10-10T22:31:13.644327+00:00`, same UUID.
4. Line **9**: linked `retain_outcome`, mode **`async_submission`**, status
   **ACCEPTED**, HTTP **200**, `outcome_durable:true`,
   `acceptance_unknown:false`, same document/operation/source linkage.
5. Line **10**: explicit reconciliation's `RETAIN_STATUS`, status **completed**,
   `2026-10-10T22:31:42.169985+00:00`.

The live code enforces canonical persistence before shadow work, comparison
append/fsync before intent creation, and intent append/fsync before HTTP POST.
The shared `durable_jsonl.append_jsonl` locks the append and completes file and
directory fsync before returning success. Reopened ledger state recovered the
same UUID and fingerprint. No ambiguous/failed submission or replacement UUID
was recorded.

This proof is not based only on the enabled flag: the real ACCEPTED outcome can
only be produced after `_validate_ack` verifies `success:true`, **`async:true`**,
the expected bank, `items_count:1`, and the returned UUID equal to the durable
intent UUID. The raw ACK was not separately captured. Independently, Hindsight
exposed that exact UUID as a real **`batch_retain` parent** with `is_parent:true`,
one item, this deterministic document ID, and one executable worker child.

Child UUID: `755b1dbf-b9ef-4e46-b00d-374d1d44f1ea`. Its preserved task payload
contains the exact `User:\n…\n\nAssistant:\nRecorded.` content, bank, document ID,
source/session/message metadata and event date
`2026-10-10T22:31:12+00:00`. Its result metadata links back to the same parent
UUID, reports facts committed and zero extraction errors. The native child is
part of the one logical retain submission, not a replacement client operation.

## Bounded worker observation and explicit reconciliation

Four real status GETs targeted the recorded parent UUID, with two-second sleeps
between nonterminal observations and a 180-second maximum observation window:

- Elapsed **2.839 ms**: parent **pending**, child **processing**.
- **2006.893 ms**: parent **pending**, child **processing**.
- **4009.705 ms**: parent **pending**, child **processing**.
- **6013.197 ms**: parent **completed**, child **completed**.

Server parent creation: `2026-10-10T22:31:13.639974+00:00`.
Server parent completion: `2026-10-10T22:31:19.008283+00:00`.
Parent/child retry counts **0**; no operation error.

Only after terminal completion, one explicit invocation of
`hindsight_shadow.reconcile_async_retain(max_operations=1, deadline_seconds=10)`
queried the real status API. The sole unresolved intent was the target UUID.
It returned **COMPLETED**, HTTP **200**, `outcome_durable:true`, then persisted
the terminal status through the existing ledger primitive.

A newly constructed `RetainLedger` recovered `submission_state:ACCEPTED`,
`terminal_status:completed`, `last_hindsight_status:completed`, and
`unresolved:false`. `select_unresolved` returned no work. No retry/replay or new
client UUID was generated; automatic startup/periodic reconciliation remains off.

COMPLETED establishes successful retain processing/storage. It does not establish
semantic extraction quality, a required fact count, or consolidation completion.

## Result inspection and isolation

Read-only final acceptance at `2026-10-10T22:32:46.622330+00:00` passed:

- Bank **7 -> 8 documents**, **7 -> 9 memories**. No particular memory count was
  required for acceptance. The stored document preserved its original text and
  exact metadata: source `corvus-lab`, the session above, user `13`, assistant `14`.
- Ledger **5 -> 10 lines**, exactly **1 intent / 1 logical retain operation**,
  terminal completed and **0 unresolved**. Final SHA-256:
  `8a4506e2b05fbd2e1bb1f114726216ca39b034d96b678e4d162fc7052f57244f`.
- The operation-list delta contains exactly the expected parent and child plus
  one naturally queued consolidation:
  `b7a4837d-1179-41c1-8033-214e0f788f94`, observed **completed**. Consolidation
  was not manually triggered, and retain completion was assessed separately.
- New dense rows **13/14** are **CURRENT** according to the real read-only
  classifier. The tail progress cursor remains **12**: direct turn indexing
  legitimately writes current rows ahead of that cursor. No cursor repair,
  bootstrap, or extra embedding was initiated by the acceptance inspection.
- Both foreground publishers remain live/healthy/idle; host aggregate **IDLE**,
  count zero. Publisher identities and lock inodes are unchanged.
- Production PID/invocation/environment/unit, repository HEAD/worktree, canonical
  table/database hashes and private dense files are identical to before-state.
  Production received no acceptance turn.
- Lab PID/invocation/environment/unit are unchanged. `:8095` remains healthy and
  was idle at final inspection. Model container/process/config/start identity is
  unchanged; slot task state changed naturally from the authorized test work.
- Hindsight container/image/process/configuration/start identity and volumes are
  unchanged; registry access remains disconnected. The CPU test endpoint
  containers are also unchanged. No service/container restart occurred.

There was **one Lab chat, one client async retain submission, zero retries/replays,
and no second chat**. No Production/Hindsight source or configuration changes,
registry configuration changes, manual consolidation, Reflect, reboot, or push
were performed. The synthetic test data was not modified or deleted afterward.

Validation comprised the real guarded acceptance, exact canonical/ledger/request
checks, bounded status observation, durable reconciliation/reopen, document/worker
provenance inspection, read-only isolation comparisons and `git diff --check`.
Evidence helpers and raw responses are under `/tmp/corvus-h17d-2f-2/`; this commit
contains only this project log. This is one lifecycle acceptance, not a broader
memory-quality or scheduling/preemption result.

Next step: **H1.7d-3 — preserve DeferOperation through Hindsight retain/consolidation
paths**.
