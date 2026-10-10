# H1.7d-2e — Feature-flagged durable async retain integration

Date: 2026-10-10

Verdict: **PASS** for the default-off Lab integration. This task does not enable
async retain in a running service or deploy Hindsight admission.

Verified starting baselines: Lab `lab/ow2e-console` at
`381892d6d60532ff7b73a3d41bd6d55268d651eb`, clean; Production `main` at
`c315d0e767e31fde3c82ba4dfb08659a268c267a`, clean. Production is untouched.

## Feature flag and default behavior

`app/runtime_config.py::HINDSIGHT_ASYNC_RETAIN_ENABLED` reads:

```text
CORVUS_HINDSIGHT_ASYNC_RETAIN_ENABLED
```

The default is **false**. Values `true` and `false` are case-insensitive and
whitespace-trimmed, using the existing choice-environment configuration helper;
invalid values raise a configuration error. Configuration is read at process
import, matching existing Corvus settings. No deployment file, systemd unit,
environment source or running-process setting was changed.

With the flag unset/false, `run_shadow_recall` still calls the existing
`retain_completed_turn` synchronous helper. Its `async:false` payload, canonical
item construction, response checks, timeout and zero-retry behavior are unchanged.
No ledger intent or async operation-status request is generated. The shared Lab
eligibility predicate preserves the original project/data/database checks.

Read-only inspection confirmed `corvus-lab-api.service` is active, PID `2705518`,
with this flag **UNSET** in its process environment. No service was restarted.
**The running Lab continues to use `async:false`.**

## Enabled ordering and submission semantics

The switch occurs in `app/hindsight_shadow.py::run_shadow_recall`, after the
comparison append has succeeded. The existing scheduling seam still captures a
confirmed canonically persisted turn and starts shadow work only after the
user-visible response is transmitted. `post_chat` and lifespan/startup are not
modified.

Enabled ordering is:

```text
canonical user/assistant persistence
-> shadow recall
-> comparison append + file/directory fsync
-> construct the exact canonical retain item and fingerprint
-> stable client UUID + RETAIN_INTENT append/fsync
-> one async:true retain POST
-> durable submission outcome append/fsync
-> linked shadow retain_outcome append/fsync
```

`_submit_durable_retain` reuses `async_retain.submit_async_retain` and
`RetainLedger(DATA_DIR / LOG_NAME)`, the existing private `h1-shadow-recall.jsonl`.
Lazy imports preserve the disabled path's independence from the async helpers
and avoid the shared retain-item builder's import cycle. No payload or durability
machinery is duplicated. The async path is protected by the same Lab-only
project/data/database eligibility checks as synchronous retain.

The item remains `User:\n…\n\nAssistant:\n…`, with
`corvus-lab:turn:{user_id}:{assistant_id}`, assistant creation time normalized to
UTC, and unchanged source/session/message-ID metadata. No context field is added.
The request changes only submission mode and the pre-recorded client UUID:

```text
POST /v1/default/banks/corvus-hindsight-lab-v1/memories
{"items": [exact_item], "async": true, "operation_id": "<durable client UUID>"}
```

Comparison append/fsync failure prevents intent creation and retain submission.
Intent append/fsync failure prevents the HTTP POST. The primitive verifies the
recorded fingerprint and identity before sending. There are no inline retries,
replacement UUIDs, status polls or waits for extraction/consolidation.

Linked shadow outcomes retain the existing document ID/error/elapsed fields and
add `mode:async_submission`, stable operation UUID, local outcome durability,
remote-acceptance uncertainty, HTTP status and ledger error class:

- `ACCEPTED`: validated durable async submission acknowledgment, not retain
  completion. The ledger remains unresolved until a terminal status observation.
- `AMBIGUOUS`: remote completion of submission is uncertain; preserve the UUID
  and leave it for explicit reconciliation.
- `REJECTED` / `FAILED_TO_SUBMIT`: operational failure, no replacement operation
  and no inline retry. An invalid success ACK can be rejected while the remote
  operation remains ambiguous, as defined by the submission primitive.
- `INTENT_DURABILITY_FAILED`: no retain request is sent.

The helper logs successful durable acceptance at INFO and operational/durability
failures at WARNING with sanitized errors and source linkage. Every log explicitly
states that completion has not been observed. An outcome fsync failure is exposed
through `outcome_durable:false` and the ledger error class; it does not erase the
stable durable intent or claim extraction success. Existing linked-outcome append
failure handling remains isolated from the already-produced foreground reply.

## Passive reconciliation seam

`app/hindsight_shadow.py::reconcile_async_retain` is one explicit async callable,
with `max_operations` (default 10), optional injected HTTP transport, and bounded
status deadline. It delegates to the existing `reconcile_unresolved` primitive
using the same private ledger and API origin.

Disabled returns an empty tuple before importing reconciliation, reading the
ledger or contacting Hindsight. Enabled requires Lab eligibility and processes
at most N unresolved intents, oldest first, skipping terminal work. It exposes
the existing typed results, fingerprint-verified `REPLAY_NEEDED`, and errors.
Malformed history and invalid bounds surface to the caller. No retain replay is
performed by this entry point.

Nothing automatically calls it: there is no startup hook, timer, thread, worker,
background reconciliation task or network endpoint. It is suitable for a later
explicit startup/manual integration; tests invoke it with fake status responses.
Turning the feature off does not cancel operations already accepted by Hindsight;
their durable identities remain available for subsequent reconciliation.

## Verification

All HTTP used `httpx.MockTransport`; ASGI calls stayed in-process, model generation
was fake, and SQLite/JSONL fixtures were temporary. No real Hindsight call or
operation-status query, model inference or bank mutation occurred.

- Focused `test_async_retain_integration.py`: **18 tests passed**, covering flag
  parsing/default-off behavior, unchanged synchronous contract, comparison and
  intent fsync ordering, exact provenance, accepted/ambiguous/rejected/pre-send
  failure outcomes, no inline retry/replacement, durability failures, duplicate
  ledger events, Lab guards, passive bounded reconciliation, disabled startup,
  and explicit status observation of the submitted UUID.
- The ASGI test blocks a fake async submission and proves the complete reply body
  was already sent. Releasing the ACK finishes the background sequence without
  polling extraction or consolidation completion.
- Existing async submission suite: **25 tests passed**.
- Existing reconciliation suite: **26 tests passed**.
- Existing retain-ledger suite: **27 tests passed**.
- Existing, unmodified Hindsight shadow/synchronous-retain suites:
  **25 tests passed**.
- Historical-memory suite: **5 tests passed**; vision, voice, web and personality
  runtime assertion scripts: **all four passed**.
- AST parsing/in-memory compilation of all five changed Python files and
  `git diff --check`: **PASS**.

The enabled ordering test confirms canonical SQLite bytes are unchanged during
background processing. Production, Hindsight, foreground registry, model endpoints,
service/environment configuration and running retain mode remain unchanged.
No push was performed. Foreground admission and automatic gap recovery/replay
are separate work, not introduced by this flag.

Next step: controlled Lab-only enablement and one real async-retain acceptance test.
