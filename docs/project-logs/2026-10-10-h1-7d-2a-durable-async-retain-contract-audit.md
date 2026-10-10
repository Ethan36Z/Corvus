# H1.7d-2a — Durable async retain contract audit

Date: 2026-10-10

Audit verdict: **PASS WITH CONSTRAINTS**. This document seals the completed
read-only contract audit; it does not implement async retain or admission.

Verified repository baselines:

- Lab: `lab/ow2e-console` at `eac145cf28c1c1c8c1174748650aa6e42ed51697`, clean.
- Production: `main` at `c315d0e767e31fde3c82ba4dfb08659a268c267a`, clean.

Both foreground publishers were healthy and idle, with trustworthy aggregate
`IDLE` and active count zero. The shared `:8095` endpoint was healthy. Hindsight
remained unchanged and disconnected from the foreground registry. Installed
Hindsight is **0.10.1**, with source under `/app/api/hindsight_api`.

## Current Corvus retain path

Canonical conversation persistence precedes Hindsight shadow work.
`app/playground_api.py::post_chat` schedules
`app/hindsight_shadow.py::run_shadow_recall` after a confirmed persisted reply.
Shadow recall runs, then the comparison observation is durably appended through
`append_observation`, including file and directory fsync. Only a successful
comparison append permits `retain_completed_turn` to submit retain.

The current request is synchronous (`async:false`) to:

```text
POST http://127.0.0.1:8888/v1/default/banks/corvus-hindsight-lab-v1/memories
```

The deterministic document ID is
`corvus-lab:turn:{user_id}:{assistant_id}`. `_load_retain_item` reads the canonical
user/assistant rows, constructs `User:\n…\n\nAssistant:\n…`, uses the assistant
creation timestamp normalized to UTC, and includes source, session and message-ID
metadata. No context field is supplied.

There are **zero retries**. An HTTP timeout can leave write completion ambiguous;
the current outcome explicitly records that uncertainty. An OK outcome requires
HTTP success and the expected response bank, `success:true`, `async:false` and
`items_count:1`. Outcomes are appended to the shadow JSONL; append failures are
logged. This synchronous response does not wait for consolidation.

## Installed async retain contract and durability point

Use the same endpoint, with the preserved item and a client-supplied UUID:

```text
{"items": [item], "async": true, "operation_id": "<client-supplied UUID>"}
```

Here `item` is the preserved retain item object described above.
`api/http.py::RetainRequest` at line 1288
defines the contract and validates the UUID. `api_retain` at line 9529 routes
async requests to `engine/memory_engine.py::submit_async_retain` at line 21773.
The existing single-item request satisfies the single-strategy requirement for
a supplied operation ID.

Async success returns `success`, `bank_id`, `items_count`, `async:true` and the
parent `operation_id`. The API can return multiple `operation_ids` for mixed
strategy groups; that is not needed for the current per-turn submission.

The submission atomically persists the parent operation and executable child
payloads in one transaction (`memory_engine.py:21947–22029`) before acknowledging
success. The parent is a status aggregator; children carry the executable retain
payloads. Extraction/storage run in durable workers, not in the submission's
synchronous retain path. Workers can begin after commit, even before the client
receives the acknowledgment. Consolidation is queued separately afterward.

## Operation status and completion meaning

The status API is:

```text
GET /v1/default/banks/{bank}/operations/{operation_id}
```

`api/http.py::OperationStatusResponse` at line 4472 and
`api_get_operation_status` at line 7885 define the actual states:

- `pending`
- `processing`
- `completed`
- `failed`
- `cancelled`
- `not_found`

**DEFERRED is not a separate enum.** Deliberate deferral parks work as `pending`
with `next_retry_at`. A future retry timestamp alone does not distinguish an
intentional defer from a scheduled retry.

The API exposes timestamps, error information, retry count, next retry time,
progress and child operation IDs/statuses. Parent status may remain pending
while children run or are deferred; child status requests expose their timing.
`result_metadata` is internal and is not a stable application contract.

COMPLETED means retain processing/storage completed successfully. It does **not**
prove semantic memory quality, nonzero extracted facts, or consolidation success
or completion. The retain worker path is
`memory_engine.py::_handle_batch_retain` at line 3303; terminal worker status is
handled by `worker/poller.py::_mark_completed` at line 857.

The status GET can repair parent status bookkeeping
(`memory_engine.py::get_operation_status` at line 20649). It was not called during
this read-only audit; its source was inspected instead.

## Idempotency and duplicate submissions

Deterministic `document_id` is document/upsert identity, **not submission
identity**. Identical chunks can be skipped and changed content can replace
existing facts, but repeated submissions with different operation IDs can create
additional async operations. Document identity alone is not an exactly-once
submission guarantee.

The client-supplied `operation_id` is the required async submission identity.
Replay using the **same UUID** returns the original operation and creates no
replacement work while that operation exists. The parent primary key also
handles concurrent replay. A UUID owned by a different bank/operation type
returns HTTP 409.

`memory_engine.py::_resolve_retain_replay` at line 21744 does **not** compare
payload equality for the same bank/type. Corvus must retain the exact contract
version and payload fingerprint associated with the UUID, detect mismatches and
not silently replay changed data. Current operation retention is disabled;
deletion or future pruning would remove this server-side replay authority.

## Crash-window conclusions

- **A — comparison fsync, crash before submission:** retain work does not exist
  yet. Canonical evidence and the comparison survive; Corvus reconciliation must
  create/recover the durable intent and submit it before memory work can occur.
- **B — accepted submission, crash before recording ACK:** safe recovery requires
  a **pre-recorded** client UUID and lookup/replay using that same UUID. A lost
  server-generated ID can otherwise lead to duplicate submissions.
- **C — persisted operation, Hindsight restart before processing:** the operation
  remains durable and claimable.
- **D — partial worker processing, crash:** uncommitted state rolls back;
  committed checkpoints/chunks can resume under the existing recovery policy.
  Processing recovery has bounded retry allowances; it is not unlimited.
- **E — proper foreground DeferOperation:** work can remain pending without
  consuming retries. Repeated foreground use can still starve completion.
- **F — ambiguous HTTP timeout:** reconcile/replay the **same UUID and same
  payload**. Never mint a new UUID solely because acknowledgment is missing.

The SQL retain path uses matching content/chunk hashes and operation checkpoints
for recovery (`engine/retain/orchestrator.py:2371,3259`). Partial-commit and
deferred resumption must be tested before claiming duplicate-free daily use.

## Minimal Corvus durable state and persistence design

Persist at minimum:

- Corvus user and assistant message IDs.
- Session and Hindsight bank.
- Deterministic document ID.
- Client operation UUID generated **before POST**.
- Contract version and payload fingerprint.
- Submission state and terminal retain status.

This is **derived operational metadata, not canonical evidence**. Canonical
conversation content remains in Corvus SQLite.

Extend the existing fsynced Hindsight shadow JSONL into a small durable retain
intent/outcome ledger. Do not introduce another database, queue or infrastructure
framework. Use linked append-only events with the existing locking/fsync
guarantees and a stable client UUID, recoverable for each qualified turn.

Required ordering:

1. Canonical Corvus persistence.
2. Shadow recall.
3. Comparison append/fsync.
4. Durable retain-intent append/fsync, including stable operation UUID.
5. Async retain POST.
6. Durable submission/outcome update by append-only event.
7. Bounded reconciliation of unresolved intents.

A comparison without an intent is a recoverable gap; reconciliation must persist
the intent before attempting submission. An intent without an acknowledgment is
ambiguous, not proof that submission failed. Reconstructed payloads must match
the recorded contract/fingerprint. Legacy synchronous or ambiguous outcomes need
explicit handling rather than blind resubmission.

## Bounded reconciliation

A bounded startup/periodic scan over durable records should:

- Recover comparison-qualified turns lacking an intent.
- Submit recorded-but-never-submitted intents using their existing UUID.
- Lookup/reconcile ambiguous submissions and safely replay the same request.
- Observe pending, processing and parked/deferred children without duplicating
  their work.
- Durably record completed retain status.
- Surface failed/cancelled work.
- Use existing explicit Hindsight operation retry APIs under a bounded policy
  for failed work, rather than minting new retain submissions.

Re-submitting an existing failed UUID only resolves the original operation; it
does not restart it. The existing retry API requeues eligible failed/cancelled
children and revives their parent without resetting live or completed children.
Missing/pruned operation records require deliberate reconciliation; `not_found`
alone must not erase recorded terminal completion or authorize replacement work.

## Foreground admission prerequisites and architecture ordering

Hindsight worker infrastructure can durably defer work without retry consumption.
`memory_engine.py::execute_task` at line 4052 already passes `DeferOperation`
through; `worker/poller.py::_defer_operation` at line 1032 parks the operation.

However, installed extraction failure aggregation
(`engine/retain/fact_extraction.py:2636`) can convert control exceptions such as
`DeferOperation` into `RuntimeError`. Before foreground admission is enabled,
intentional deferral must propagate through extraction/streaming handlers,
operation identity/checkpoints must survive, and deferred partial-commit
resumption must be tested. A naive gate is not sufficient.

Architecture ordering:

1. Durable Corvus retain intent/outcome ledger.
2. Async retain submission and bounded reconciliation.
3. Hindsight DeferOperation passthrough.
4. Standalone foreground-registry reader.
5. Per-attempt admission gate.
6. Bounded consolidation.
7. Daily-use acceptance.

The read-only registry mount and controlled Hindsight rollout remain deployment
prerequisites from H1.7d-1. Reflect remains deferred. This document does not
authorize unbounded consolidation or change the trusted provisional models.

Likely future changes are Lab shadow-retain submission, a small reconciliation
helper/lifecycle hook and focused retain tests, plus Hindsight
extraction/orchestrator/wrapper integration. This sealing task changes only this
log: no implementation, retain submission, inference, bank mutation, runtime or
registry change, service/container restart, or push is performed.
