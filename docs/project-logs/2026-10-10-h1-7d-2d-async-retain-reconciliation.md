# H1.7d-2d — Async retain operation reconciliation primitive

Date: 2026-10-10

Verdict: **PASS** for the offline bounded reconciliation primitive. Reconciliation
is not wired into startup, periodic tasks or live `post_chat`. Live retain remains
`async:false`; no real Hindsight request, retain replay or inference was performed.

Verified starting baselines: Lab `lab/ow2e-console` at
`78ddbd8789673ed156deca3cd64d01899922daf7`, clean; Production `main` at
`c315d0e767e31fde3c82ba4dfb08659a268c267a`, clean. Production remains unchanged.

## Status contract

`app/retain_reconciliation.py::get_operation_status` implements exactly one GET:

```text
GET /v1/default/banks/{bank}/operations/{recorded_operation_id}
```

The Hindsight 0.10.1 contract, established in H1.7d-2a and inspected in the saved
installed source (`api/http.py::OperationStatusResponse`, `ChildOperationStatus`,
`OperationProgress`, `api_get_operation_status`, and
`engine/memory_engine.py::get_operation_status`), requires `operation_id` and
`status`. Actual states are `pending`, `processing`, `completed`, `failed`,
`cancelled`, and `not_found`. Intentional deferral is parked `pending` with a
future `next_retry_at`, not a separate state.

The helper verifies the returned UUID and, when supplied, bank and retain
operation type. It captures optional `error_message`, `retry_count`,
`next_retry_at`, `created_at`, `updated_at`, `completed_at`, `progress`, and child
operation IDs/statuses, including child batch/count/error metadata. Missing or
null optional fields are tolerated. Child states are diagnostic and never
override the parent state. Timestamp strings are preserved in the observation;
the existing ledger normalizes the scheduling timestamp to aware UTC.

Only supported status metadata is retained. Raw task payloads and unstable
`result_metadata` are discarded. Strict JSON parsing rejects duplicate keys and
non-finite values using the existing durable-JSONL parsing helpers. Malformed
responses or mismatched identity cannot establish completion.

HTTP 404 is `STATUS_ERROR`, not `REPLAY_NEEDED`: the installed API returns a
successful JSON `status:not_found` for a missing UUID. HTTP errors and invalid
API responses are surfaced as `STATUS_ERROR`; transport timeouts/connection
uncertainty are `STATUS_AMBIGUOUS`. Neither overwrites the last valid ledger
observation or fabricates a server state.

The default transport has `retries=0`, ignores environment proxies and does not
follow redirects. Each GET has a configurable positive deadline, default 10
seconds and maximum 60 seconds. A captured response survives client-cleanup
failure. Durable status appends occur outside the HTTP deadline. There are no
automatic retries, retain POSTs or operation-retry calls.

Although this client only issues GET, the installed Hindsight status endpoint
can repair parent operation bookkeeping. No real GET was sent here; future
deployment must account for that server-side behavior.

## Ledger observations and state mapping

The existing `RETAIN_STATUS` event gains an optional `observation` object;
previous records remain readable without it. A pure shared normalizer verifies
supported metadata, and event validation requires the embedded identity/status,
retry information and error to agree with the event. `record_status` continues
to use the existing append/flock/file-and-directory-fsync mechanism. No records
are rewritten or migrated. `RetainState.status_observation` exposes the latest
captured metadata after reopening.

`reconcile_operation` reconstructs the durable intent before any GET. It returns
a typed `ReconciliationResult` with stable UUID, captured observation, error,
HTTP status and local outcome-durability flag:

- `PENDING` and `PROCESSING`: unresolved; existence can establish acceptance
  even if no HTTP acknowledgment was recorded.
- `COMPLETED`: terminal retain processing/storage completion. This does not
  establish semantic quality, nonzero facts or consolidation completion.
- `FAILED` and `CANCELLED`: terminal retain states with server error preserved.
  No operation retry or replacement submission is attempted.
- `REPLAY_NEEDED`: a validated JSON `not_found` observation, unresolved, with
  exact replay material verified as described below.
- `STATUS_AMBIGUOUS`: status could not be observed through the transport.
- `STATUS_ERROR`: invalid client/API/ledger state, durability failure or
  unreconstructable replay payload; operator-visible and not actionable replay.

A status append/fsync failure returns `STATUS_ERROR` with
`outcome_durable:false`, rather than claiming durable completion. Duplicate
status observations reduce to one logical operation. A malformed or truncated
ledger tail rejects the entire reconstruction, never a trusted partial result.
The original terminal-state rules remain: `not_found` does not erase completion;
contradictory pending/failed observations after completion are rejected.

## Crash recovery and replay safety

Intent-only, submission-ambiguous and submission-accepted operations all query
the **existing recorded UUID first**. Intent-only state cannot distinguish a
crash before POST from a crash after POST before outcome fsync. An existing
server operation is observed normally in either case. The reconciler never
generates a UUID or assumes lack of a local ACK means the POST did not occur.

Before returning actionable `REPLAY_NEEDED`, it reads the canonical source
messages through the existing retain-item builder and reuses
`async_retain.build_async_request` to verify contract version, document ID and
the recorded canonical payload fingerprint. It does not guess content,
timestamps, context or metadata. Missing source material, changed content/date,
or unsupported contract produces `STATUS_ERROR` with
`REPLAY_PAYLOAD_UNRECOVERABLE`; the valid `not_found` observation is still
durably recorded and remains unresolved.

The ledger is checked again after reconstruction so a concurrently recorded
terminal outcome is not reported as replay-needed. Future replay must still use
the existing replay helper, which rechecks intent, terminal state and fingerprint
before sending the same UUID/payload. `REPLAY_NEEDED` is permission to consider a
later exact replay, not a replay performed by this primitive. Hindsight operation
deletion/pruning and changed canonical source require deliberate reconciliation;
this task does not authorize replacement identities.

## Bounded scan

`select_unresolved` is pure. It selects only nonterminal intents, ordered by
original intent timestamp as an absolute instant, then UUID for ties.
`reconcile_unresolved` performs one finite sequential pass over at most
`max_operations` selected intents (default 10). The limit must be a nonnegative
integer; zero performs no GET. Terminal operations are skipped, including those
that become terminal before their individual lookup. One status error is
returned for inspection and does not prevent other selected operations from
being checked.

There is no sleep, unbounded polling loop, worker, timer or background task.
The operation limit bounds visits and HTTP attempts, not JSONL history size:
the existing ledger reader/append validator still reads the complete history.
Untrustworthy scan input raises before any HTTP instead of silently treating it
as an empty ledger. This primitive does not recover comparison records lacking
an intent, schedule failed-operation retries, or reconcile canonical data.

## Verification

All status HTTP responses used `httpx.MockTransport`. Canonical SQLite and ledger
files were temporary; no real Hindsight or model request was made.

- Focused `test_retain_reconciliation.py`: **26 tests passed**, covering every
  state, pre-submit/accepted/ambiguous recovery, optional metadata, stable UUIDs,
  exact replay verification, bounded deterministic selection, terminal skips,
  status/API/transport errors, zero retries/replays, reopen/duplicate events,
  malformed tails/JSON, fsync failure and concurrent completion preservation.
- Existing async submission suite: **25 tests passed**.
- Existing ledger suite: **27 tests passed**, including legacy compatibility and
  concurrent append durability.
- Existing Hindsight shadow/synchronous-retain suite: **25 tests passed**.
- Historical-memory suite: **5 tests passed**.
- Vision, voice, web and personality runtime assertion scripts: **all four
  passed** using their fake generation paths.
- AST parsing and in-memory compilation of the changed Python files, plus
  `git diff --check`: **PASS**.

Canonical SQLite bytes remained unchanged during lookup/replay verification.
Live `post_chat`, lifespan/startup and synchronous retain code are unchanged.
No live intent generation, status reconciliation, feature enablement, service
restart, bank mutation, registry change, Hindsight modification or Production
change occurred.

Next step: integrate durable intent + async submission + bounded reconciliation
behind a disabled feature flag before switching live retain.
