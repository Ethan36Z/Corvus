# H1 — Hindsight integration

Sealed: 2026-10-11. Exit decision: **H1 SEALED**.

Maturity: **provisional local daily-use candidate with accepted constraints**.
The Lab memory lifecycle is operationally validated. This is not a general
semantic-quality certification or a deployment of Hindsight memory writing to
Production Corvus.

## Goal and starting architecture

H1 evaluated Hindsight as derived historical-memory intelligence without giving
it ownership of conversation evidence, recent context, or foreground reasoning.
The starting architecture used Corvus SQLite as the canonical Evidence Log,
Corvus-owned Recent Conversation Context, and Corvus hybrid historical recall
with a rebuildable LanceDB index. Qwen3.5-9B generated foreground replies.

H1.1's ownership audit established that **historical retrieval is the provider
seam**. H1.2 extracted `memory/historical_memory.py::recall` while preserving
canonical message IDs, working-context budgets, recent-context ownership and
persistence. H1.3 added post-response Hindsight shadow recall rather than silently
switching active retrieval. H1.4 added shadow retain. The ownership decisions and
early-stage findings are summarized in the
[architecture freeze](../project-logs/2026-10-09-h1-7a-provisional-hindsight-architecture-freeze.md)
and [shadow-retain record](../project-logs/2026-10-07-h1-4a-2-shadow-retain.md).

Active historical retrieval remains Corvus hybrid recall. Hindsight Recall is
shadow-only in this sealed Lab lifecycle. H1 does not declare a universal winner
between Hindsight, Corvus RAG, or other memory architectures; natural daily-use
history is still too small for that conclusion.

## Recall, retain, Reflect and paired observability

The completed canonical turn precedes all shadow work. Shadow recall records
Hindsight results/status/latency alongside the same turn's Corvus historical IDs,
recent IDs, retrieval latency and error/status information. H1.5 paired
observability makes the two paths inspectable without changing the visible reply
or treating Hindsight source UUIDs as canonical Corvus message IDs.

The comparison is appended and fsynced before retain. Retain reads the canonical
user/assistant rows and preserves combined `User:` / `Assistant:` content,
assistant UTC timestamp, source/session/message metadata and deterministic
`corvus-lab:turn:{user_id}:{assistant_id}` document identity. The initial
synchronous path used `async:false`, zero retries and explicit ambiguous-write
reporting on timeout. Retain completion did not wait for queued consolidation.

[Reflect's contract audit](../project-logs/2026-10-07-h1-4b-reflect-decision.md)
corrected the maintenance hypothesis: Reflect is optional memory-grounded
reasoning, not a necessary post-retain maintenance step. Normal maintenance is
retain extraction/storage followed by built-in consolidation. **Reflect remains
deferred**, with no per-turn, periodic or idle Reflect hook.

## Observed failure, contention and model selection

The [real consolidation failure](../project-logs/2026-10-07-h1-6a-consolidation-output-too-long.md)
was context/output exhaustion, not demonstrated semantic incapability. The
original 9B call used **4129 input + 4063 output = 8192 tokens**, ended with
`finish_reason=length` and raised OutputTooLongError before schema validation,
after approximately 64 seconds. The later direct CPU rendering counted 4038;
counts depend on the actual provider/template. Canonical evidence and retained
facts survived. `CONSOLIDATION_MAX_TOKENS=512` was a retrieval budget and did not
limit generated output.

The [contention audit](../project-logs/2026-10-07-h1-6b-foreground-background-contention.md)
found that post-response work can overlap a later foreground request. Corvus and
Hindsight share the Qwen3.5-9B llama.cpp server at :8095, with one 8192-token
inference slot. Hindsight's global LLM concurrency is one; Corvus foreground is
outside that semaphore. Asynchronous execution alone does not give foreground
priority or separate model capacity.

The [isolation audit](../project-logs/2026-10-08-h1-6b-2-memory-model-isolation.md)
confirmed native operation-specific provider/model/base-URL/API-key routing for
retain, consolidation and Reflect. Moving consolidation alone would leave
extraction on the shared server. Another full 9B GPU copy did not fit the audited
free VRAM. Isolation was technically available, but required quality evidence.

Three isolated CPU trials supplied narrow evidence:

- [Qwen3-1.7B Q8_0 consolidation](../project-logs/2026-10-08-h1-6c-cpu-consolidation-capability-trial.md):
  one real fixture was USABLE, with a grounded UPDATE, valid schema/source IDs,
  189 output tokens and approximately 68.9 seconds elapsed. Conflict handling
  and general consolidation quality were not established; actions were not applied.
- [Qwen3-1.7B retain](../project-logs/2026-10-08-h1-6d-cpu-retain-extraction-capability-trial.md):
  UNUSABLE on a real fixture despite valid schema. It substituted October 8 for
  the October 7 event date, invented user participation and omitted Corvus.
- [Gemma 4 E2B IT Q4_K_M retain](../project-logs/2026-10-09-h1-6e-gemma-retain-extraction-capability-trial.md):
  UNUSABLE on the same fixture despite being installed Hindsight 0.10.1's local
  llama.cpp default. Date handling improved, but invented participation,
  incorrect assistant-experience classification and missing entity/occurrence
  detail still made retention unsafe.

The existing Qwen3.5-9B retain path had a successful real baseline. H1.7a froze
Qwen3.5-9B for foreground, retain and consolidation; neither small model was
adopted as a memory writer. Model hunting stopped: no size escalation merely to
find a smaller writer. Reopen selection only for a concrete need exposed by real
use. Schema-valid output and an upstream default are not sufficient safety evidence.

## Host-wide foreground signal and admission

The [scheduling audit](../project-logs/2026-10-09-h1-7b-foreground-safe-memory-scheduling-audit.md)
identified existing Hindsight durable async operations, restart recovery,
reconciliation and DeferOperation. No Redis, Celery, daemon or new queue framework
was needed. Admission cannot preempt an already-running memory inference.

H1.7c added a thread-safe local tracker around foreground `process_turn`
generation, with overlapping counts and `finally` cleanup, then a host-local
registry at `/run/corvus-foreground/`. Lab and Production share the model but
retain isolated data roots. Both now publish through independently restartable
process identities. The directory is ethan:ethan 0700, files 0600, boot-created
by tmpfiles; service restarts do not delete peer lock inodes.

[Registry failure semantics](../project-logs/2026-10-09-h1-7c-6-foreground-fail-open-background-fail-closed.md)
use kernel lifetime/health/busy locks, PID/start/UUID identity and monotonic finish
history. Crashes release ownership; stale records cannot prove live health.
Foreground remains usable on publication failure; missing/degraded/untrustworthy
expected publishers make background state UNKNOWN. Lock descriptors have
fork/exec protections. Metadata contains activity/identity only, not conversations.
The Hindsight consumer independently requires **lab,production** even though the
Lab publisher's originally deployed reader expectation remains Lab-only.

## Durable async retain and recovery

The [async contract audit](../project-logs/2026-10-10-h1-7d-2a-durable-async-retain-contract-audit.md)
established that document identity is not submission identity. Corvus now records
a client UUID **before POST** and verifies the exact payload fingerprint on replay.
The existing private shadow JSONL is an append-only derived operational ledger;
file locking plus file/directory fsync precede reported durable success.

The enabled Lab ordering is:

```text
canonical user/assistant persistence and foreground reply
→ Hindsight shadow recall
→ comparison append/fsync
→ RETAIN_INTENT append/fsync (UUID, provenance, contract fingerprint)
→ async:true POST
→ durable submission outcome
→ durable Hindsight worker processing
→ explicit bounded status reconciliation
→ RETAIN_STATUS(completed/failed/cancelled)
```

Comparison or intent durability failure prevents submission. Acceptance validates
the returned UUID, bank, async flag and item count; it means durable submission,
not completed extraction. Ambiguous transport remains unresolved, with no inline
retry or replacement UUID. Server-side parent/child payloads are persisted
atomically before acknowledgement; consolidation is queued separately.

The [reconciliation primitive](../project-logs/2026-10-10-h1-7d-2d-async-retain-reconciliation.md)
queries stable UUIDs, skips terminal work, bounds unresolved selection and records
status append-only. It performs no automatic replay. A not-found operation can
become replay-needed only after exact payload/fingerprint validation. Reconciliation
is explicit/manual; no startup timer or periodic worker was enabled. Durability
begins at the fsynced intent: a crash before intent creation still requires checking
the comparison/canonical gap, not an assumed automatic repair guarantee.

The async feature is default-off in code and **enabled only in Lab**. Its synchronous
path remains available as rollback. The [first real async acceptance](../project-logs/2026-10-10-h1-7d-2f-2-real-async-retain-acceptance.md)
proved canonical turn → one intent → accepted submission → real worker completion
→ durable terminal reconciliation without duplicate work.

## Patched Hindsight runtime and bounded consolidation

The version/hash-guarded Hindsight **0.10.1** patch preserves intentional
[DeferOperation control flow](../project-logs/2026-10-10-h1-7d-3a-hindsight-defer-operation-patch.md)
through extraction aggregation/streaming and consolidation. Deferral does not
become RuntimeError, retry/bisection, failed-fact marking or false completion.
Ordinary errors retain their behavior; committed checkpoints remain recoverable.

A [standalone read-only reader and per-attempt gate](../project-logs/2026-10-10-h1-7d-3b-foreground-admission-gate.md)
consume the same registry protocol without Corvus imports or a network API.
`engine/llm_wrapper.py::_attempt_permits` checks after operation/global permits,
immediately before every upstream attempt. Only trustworthy IDLE beyond the
**30-second completion/recovery grace** admits work. BUSY/UNKNOWN/grace raises
DeferOperation, releases permits, and returns durable work to pending with
next_retry_at and no retry consumption. Reflect is still not invoked.

The [live rollout](../project-logs/2026-10-10-h1-7d-3c-live-foreground-admission-rollout.md)
used a reproducible derived image, readonly registry mount and preserved runtime
settings/data volumes. The first startup harness timed out at the same 30 seconds
required by grace; automatic rollback restored the exact original. The authorized
retry used a 75-second observation horizon, unchanged 30-second grace, and proved
one real BUSY/defer/grace/same-UUID completion. Readonly access was verified with
EROFS, not only Docker configuration.

[Bounded consolidation](../project-logs/2026-10-10-h1-7e-bounded-consolidation.md)
then added an independent **1024-token completion cap**, **256-token safety margin**
and **8192 context limit**, with batch size one and reasoning/thinking disabled
only for consolidation scopes. The final wrapped request is rendered/tokenized
using the serving llama.cpp `/apply-template` and `/tokenize` APIs. Each attempt
must satisfy `input + allowed_completion + 256 <= 8192`, with at least 512 useful
completion tokens; otherwise it durably defers without truncating provenance or
marking facts failed. Foreground admission is rechecked after counting, before send.

The existing frozen failure fixture reserved **4131 + 1024 + 256 = 5411 tokens**.
Its actual request used `max_tokens=1024`; response usage was 4131 prompt/161 output,
finish_reason stop, schema/source IDs PASS, one UPDATE, no OutputTooLong, and normal
return in approximately 4.32 seconds. No returned operations or bank changes were
applied. This recorded replay satisfies the final bounds requirement; it was not
repeated for sealing. The deployed image passed 69 focused patch tests, ten
pristine ordinary-error regressions and seven runtime-preservation tests.

## Final acceptance and exit decision

The [final daily-use acceptance](../project-logs/2026-10-11-h1-final-daily-use-acceptance.md)
records one normal synthetic Lab turn, canonical IDs **15/16**, document
`corvus-lab:turn:15:16` and client UUID
`7a6c0763-ebb0-4280-8265-b323135ae5e8`. It proved async acceptance, actual Lab activity,
controlled BUSY deferral before memory inference, unchanged retry count and payload,
same-operation resumption after grace and successful completion. Terminal
reconciliation subsequently appended `RETAIN_STATUS(completed)`; reopening recovered
terminal completion and **zero unresolved intents**. No second turn, replay or
replacement UUID was needed after remote transport interruptions.

Final read-only seal checks found Lab, Hindsight, Production and :8095 healthy,
both publishers healthy/idle, no pending/processing bank operations, and Production
code/runtime/private state unchanged. SQLite holds 16 messages; the Lab bank holds
10 documents/9 memories. The final synthetic document yielded zero extracted facts;
COMPLETED certifies processing/storage, not a required semantic fact count.

## Reversibility, limitations and maturity

SQLite evidence and canonical IDs remain authoritative. LanceDB and Hindsight are
derived/rebuildable, not a new source of truth; regenerated semantic output need
not be byte-identical. The active Corvus retrieval path remains available. Async
retain can be disabled through a controlled Lab-only rollback; that does not
cancel already accepted Hindsight work, whose recorded UUIDs still need observation.

Guarded patch/image recipes and retained stopped containers preserve rollback to
prior admission-enabled or original runtimes with the same data/cache volumes.
Automatic rollback was exercised. Private inspect snapshots stay outside Git;
retain them securely before temporary-artifact cleanup. Never remove shared lock
inodes or persistent volumes as a rollback shortcut. Status reconciliation and
operator-visible failure handling remain necessary; there is no claim of automatic
exactly-once recovery for every crash window.

Accepted limitations:

1. Foreground arrival after a memory inference begins cannot preempt it. Admission
   narrows the race; it does not guarantee zero foreground waiting.
2. Oversized indivisible consolidation inputs may remain durably deferred and need
   operator attention. Bounds are per attempt, not a total-job latency guarantee;
   continuous foreground use can starve background work.
3. Reflect remains deferred.
4. Retained documents need not yield semantic facts, and schema/status success is
   not a universal semantic-safety guarantee.
5. H1 does not establish Hindsight's universal semantic superiority over other
   memory architectures.

**H1 SEALED:** the single-host Lab integration is a provisional daily-use candidate
with explicit constraints, operational provenance, durable deferred work and bounded
consolidation. Model research stops; future changes should address observed daily-use
failures rather than expand the architecture speculatively. Production participated
only as a foreground publisher and remained isolated from this Lab memory exercise.
