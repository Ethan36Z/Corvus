# H1.7d-2c — Durable async retain submission primitive

Date: 2026-10-10

Verdict: **PASS** for the offline submission primitive. No live retain switch,
operation-status reconciliation, Hindsight admission, or deployment is included.

Verified starting baselines: Lab `lab/ow2e-console` at
`992bd18dd421e799500af6ce061348b8fb04a0ce`, clean; Production `main` at
`c315d0e767e31fde3c82ba4dfb08659a268c267a`, clean. Production is unchanged.

## Request and ordering contract

`app/async_retain.py::submit_async_retain` reuses
`app/hindsight_shadow.py::_load_retain_item`, rather than duplicating the
successful synchronous payload construction. The canonical SQLite read is
read-only. Content remains `User:\n…\n\nAssistant:\n…`, document identity remains
`corvus-lab:turn:{user_id}:{assistant_id}`, timestamp remains the assistant's
creation time normalized to UTC, and metadata preserves source, session and
both message IDs. No context field is introduced.

The Hindsight 0.10.1 contract is:

```text
POST /v1/default/banks/{bank}/memories
{"items": [exact_retain_item], "async": true, "operation_id": "<client UUID>"}
```

Request material is validated and fingerprinted before generating the UUID.
The helper retains an owned JSON copy of the item, generates or accepts the
stable client UUID, then records `RETAIN_INTENT` through the existing
`RetainLedger` and `durable_jsonl` append/flock/file-and-directory-fsync machinery.
Only after successful durable recording and read-back verification may it POST.
Intent append, fsync, damaged-history or conflicting-UUID failure produces
`INTENT_DURABILITY_FAILED` and prevents HTTP entirely. Invalid canonical material
or client configuration produces `FAILED_TO_SUBMIT` before intent creation.

The ledger path remains explicit and caller-supplied, suitable for the existing
private `h1-shadow-recall.jsonl`; no new runtime file or live intent is created.
The future integration must still enforce the broader ordering:

```text
canonical persistence -> shadow recall -> comparison append/fsync
-> intent append/fsync -> async POST -> outcome append/fsync
```

This primitive enforces intent-before-POST. It does not itself run recall or
claim that a preceding comparison has been recorded; that remains the future
caller's responsibility.

## Identity and replay

Contract version 1 retains the existing SHA-256 fingerprint of canonical JSON:
bank, contract version, `async:true`, and every item field. Sorted keys, compact
separators, UTF-8 and rejection of non-finite/non-JSON values make it deterministic.
UUID, ledger event times and transport timing are excluded. Omitted fields and
explicit nulls remain distinct.

`build_async_request` verifies the document ID, contract version and fingerprint.
`replay_async_retain` loads an existing trustworthy durable intent, rebuilds its
item from canonical message IDs/session, and refuses HTTP if the content, date,
context, metadata, bank or contract differs. It never generates a replacement
UUID. Missing canonical rows or malformed ledger tails also prevent submission.
Known terminal operations require status/retry reconciliation rather than a new
submission. Explicit replay of a nonterminal accepted or ambiguous intent uses
the same UUID and payload; duplicate outcomes reconstruct one logical operation.

Hindsight's audited server-side UUID replay protection depends on the operation
still existing and does not compare payload equality itself. A replay refusal
must be surfaced for reconciliation; this helper does not repair changed data or
mint a new identity. A caller must use the replay API for an unresolved intent,
rather than calling fresh submission without its existing UUID.

## Submission outcomes

`SubmissionResult` distinguishes `ACCEPTED`, `AMBIGUOUS`, `REJECTED`,
`FAILED_TO_SUBMIT`, and `INTENT_DURABILITY_FAILED`, including operation UUID,
sanitized error, HTTP status, remote-acceptance uncertainty, local outcome
durability and any ledger failure class.

- `ACCEPTED` requires a successful HTTP response and `success:true`, `async:true`,
  the expected bank, integer `items_count:1`, and the same operation UUID. Any
  optional `operation_ids` list must match the single requested parent. It appends
  and fsyncs `RETAIN_SUBMISSION_ACCEPTED`. Acceptance means durable async
  submission only, not extraction completion, facts, quality or consolidation.
- Timeout, read/write connection loss and other post-attempt uncertainty append
  `RETAIN_SUBMISSION_AMBIGUOUS`, preserving the UUID. HTTP 408, server errors and
  redirects are treated conservatively as ambiguous; redirects are not followed.
- A malformed or mismatched successful acknowledgment is `REJECTED` as proof of
  acceptance, with `acceptance_unknown:true`. Its ledger event is ambiguous:
  the remote operation may already exist. It must not authorize replacement work.
- Definitive API client-error responses other than 408 record `REJECTED` with
  status/error. Known connection-establishment/pool failures and replay/client
  precondition failures record `FAILED_TO_SUBMIT`. Neither implies terminal
  retain failure or permits a replacement UUID.

One small event, `RETAIN_SUBMISSION_FAILED`, extends the ledger with failure kind,
sanitized error and optional HTTP status. These events remain unresolved and do
not erase known acceptance or terminal status. A later valid acceptance clears
obsolete rejection metadata. Existing intents, outcomes and legacy shadow lines
remain readable; malformed/truncated history is still rejected in full.

Each caller invocation attempts at most one HTTP POST. The default transport has
`retries=0`, ignores environment proxies and disables redirects. The configurable
HTTP deadline defaults to 10 seconds and must be positive and at most 60 seconds.
Injected test transports must likewise not implement retries. There is no automatic
resubmission. Client cancellation after an attempt records ambiguity and propagates.

Outcome fsync is outside the HTTP deadline: slow durable recording cannot turn a
known rejection into transport uncertainty. A fully validated ACK is retained even
if client cleanup fails. If outcome append/fsync fails, the result explicitly
reports `outcome_durable:false` and the ledger error class; the pre-send intent
survives for reconciliation, and there is no second POST. Raw response bodies,
payload content and exception details are not copied into error events.

## Verification

All HTTP behavior used `httpx.MockTransport`; SQLite and JSONL fixtures were
temporary. No real Hindsight request or model inference was sent.

- `test_async_retain.py`: **25 tests passed**, covering fsync-before-POST,
  intent failure preventing HTTP, exact synchronous-item parity, accepted and
  ambiguous reopen, invalid acknowledgments, definitive rejection, transport
  ambiguity and pre-send failure, deadlines/cancellation, zero retries, stable
  replay, changed payload refusal, duplicate outcomes, damaged tails, outcome
  fsync failure, cleanup failure and terminal-operation refusal.
- `test_retain_ledger.py`: **27 tests passed**, including concurrent appenders,
  deterministic fingerprints, legacy compatibility and malformed-tail safety.
- Existing `test_hindsight_*.py`: **25 tests passed**, including the live
  synchronous contract, comparison-before-retain ordering and reply isolation.
- `test_historical_memory.py`: **5 tests passed**.
- Vision, voice, web and personality conversation/runtime assertion scripts:
  **all four passed**, using existing fake generation paths.
- AST parsing and in-memory compilation of the helper, ledger and focused tests:
  **PASS**. `git diff --check`: **PASS**.

The synchronous/async parity test confirms canonical SQLite bytes are unchanged.
The existing `post_chat`, shadow-recall scheduling and `retain_completed_turn`
files are unchanged: **live retain remains `async:false`**, with no live ledger
wiring, startup reconciliation, runtime configuration or service restart. Hindsight,
Production, banks, foreground registry and model endpoints were not modified.

Next step: implement bounded operation-status reconciliation before switching
live retain.
