# API-1 — Minimal stateless text API

Date: 2026-10-24 (America/Los_Angeles)
Status: **API_1_IMPLEMENTED_OFFLINE** — awaiting review; not deployed/activated.

## Baseline and scope

Isolated worktree `/home/ethan/srv/apps/corvus-api-v1`, branch `feature/api-v1`,
created directly from approved integration commit
`56a615e5a0b334bc05b87560148b6eaead62bcc6`. API-0's actual source and audit were
reviewed first. No occupied checkout was switched and no existing work was reset,
cleaned or overwritten. No integration merge or deployment is part of API-1.

Standalone `app.openai_api:app` exposes Bearer-protected `/v1/models` and
`/v1/chat/completions`, plus a protected OpenAPI document. Default disabled;
no interactive documentation or private /api routes. Caller messages are the
entire context; no default personality, conversation runtime, canonical startup,
Evidence Log, private recall/database access or Hindsight retention.

The existing model client gains an optional bounded transport preserving native
response envelopes. Original source bytes for all legacy functions remain
unchanged. Same Non-Thinking/template payload is counted then generated, with
at most one generation POST and no retry. No second model/conversation runtime,
application dependency, new scheduler, authentication database or test framework.

## Contract and safeguards

- Text only, model corvus, n=1, stream=false; bounded sampling/token/stop settings.
  Leading developer/system messages are explicitly normalized into one system
  prefix; remaining user/assistant turns alternate and end in user.
- Genuine upstream id/created/model/content/finish_reason/usage; whitespace is
  preserved. Complete JSON objects are parsed/verified, including duplicate and
  finite-number checks. No strict JSON Schema or streaming claim.
- Independent digest-file keys, checked on every request for immediate next-check
  revocation/rotation. Owned 0700 directory/0600 singly linked regular file,
  checked FD-based opens, no final symlinks, special files or stale key cache.
  No actual credentials were generated, loaded or committed.
- Authentication before body buffering; 128 KiB bodies, 4096 rendered input tokens,
  output 512 default/1024 maximum; six attempts/minute, one real inference worker,
  no API queue. Body and response deadlines, bounded backend replies, explicit
  safe errors, no raw request/provider values or private key logging.
- Fixed literal loopback backend; no proxy/redirect forwarding or arbitrary URL,
  media/tool/backend-control passthrough. Existing shared model config unchanged.
- Existing foreground tracker with distinct optional api publisher; old readers
  already count it. No existing expected-peer or Hindsight policy changes.
- Actual concurrent-future completion owns admission release. Async wrapper/request
  cancellation, client disconnect or deadline cannot release a still-running
  thread or automatically resubmit. Shutdown preserves active tracker ownership.

See `docs/api/v1.md` for exact schemas/subset, errors, sample client request,
credential provisioning/rotation and operational boundaries. Config/dependency
samples are documentation only and are not installed or automatically sourced.

## Verification

All testing used synthetic keys/data and mocked inference, in the existing bwrap
isolation pattern: network namespace disabled, source/venv readonly, live data,
/run and protected STT configuration hidden. No live inference, token-count POST,
service fault injection, build, database or deployment operation occurred.

- New focused tests: **24/24 passed** (7 optional model-transport tests and
  17 API contract/security/isolation tests, with parameterized subcases).
- Existing relevant regressions: **282 unittest cases, 280 passed + 2 existing
  subprocess-only skips**, four module-level assertion scripts passed.
- Existing Voice Call Node suite: **17/17 passed**.
- Coverage: key revocation/rotation/file safety, authenticated models/schema,
  supported/unsupported roles/parameters, JSON/truncation, malformed/oversized
  and chunked bodies, safe failures, rate windows, busy ownership, deadline,
  disconnect, request cancellation, optional publisher compatibility and legacy
  model-client behavior. A fresh subprocess blocks memory/personality/runtime
  imports, SQLite and live sockets on success/failure/timeout paths.
- The initial disconnect-monitor cleanup could absorb cancellation inside the
  underlying disconnect check and wait indefinitely. The focused test exposed it;
  an explicit stop event now terminates that observer. Resource ownership is
  independently attached to the actual worker, not that observer or asyncio task.
- Final review covers only the new API source, additive client seam, tests and
  documentation. Explicit staging and diff/security checks precede the commit.
  No complete Vite rebuild or full architecture/personality experiment was needed.

Detailed logs and generated schema are under `/tmp/corvus-api1-results/` on the
implementation host. Those are synthetic test artifacts, not production evidence.

## Remaining limits and rollout boundary

This is a tested offline wire-contract implementation, not live Qwen JSON/API
acceptance. No streaming, strict JSON Schema, multimodal/tool support, or full
companion-memory API; existing companion routes remain intact. The STT API refactor
in integration remains undeployed, as before. Shared Qwen single-slot inference
can queue behind other callers; API admission limits only this process, requiring
one ASGI worker/instance. No global fairness, preemption or latency gain is claimed.

A socket read started before the response deadline can settle later; retain the
API slot/foreground ownership until then. Closing HTTP cannot prove remote model
execution stopped. Existing upstream logs/process/GPU buffers are not a secure
memory-erasure guarantee. BackgroundTasks-to-durable-retain-intent recovery gaps,
P0.2 quality BLOCK and old Hindsight recovery snapshot limits are unchanged.

Remote HTTPS ingress remains unavailable: existing FoxGate browser-cookie auth
cannot be bypassed by this API key. A future narrow TLS route, dedicated loopback
service/sandbox, credential provisioning, live synthetic/SDK smoke and rollback
need separate review/authorization. API-only rollback must not restart shared
Corvus services or touch private data.

The intended publication is only `feature/api-v1` via normal non-force Push.
Final commit SHA, GitHub/local SHA agreement and unchanged-running-state guard
are recorded in the delivery report; integration/corvus-v1 is not merged.
