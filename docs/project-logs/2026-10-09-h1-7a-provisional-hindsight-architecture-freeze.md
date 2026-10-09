# H1.7a — Provisional Hindsight architecture decision and freeze

Date: 2026-10-09

Baseline: `lab/ow2e-console` at `1be9b6b6e716c22dff732dfb167fba9d6e1f4ae4`

Decision: **Freeze the provisional daily-use architecture around canonical
Corvus SQLite evidence, Corvus-owned recent context, Hindsight derived memory
intelligence, and Qwen3.5-9B for foreground chat, retain extraction, and
consolidation.** Reflect remains deferred, and small-model research stops.

This is an architecture decision, not a deployment or implementation. Keeping
the 9B consolidation model is a provisional model choice, not a declaration
that the current consolidation lifecycle is reliable for daily use. Foreground
safety and bounded consolidation behavior are the next engineering gate.
The active historical-provider choice remains provisional; this freeze does
not switch active retrieval from Corvus RAG to Hindsight.

The expected branch and HEAD and a clean worktree were verified before creating
this document. No runtime audit or inference experiment was repeated.

## 1. Evidence summary

H1.1–H1.5 established the ownership boundaries and working integration:

- **Corvus SQLite remains the canonical Evidence Log.** Canonical conversation
  persistence and Corvus message identifiers remain authoritative.
- **Recent Conversation Context remains Corvus-owned.** Historical retrieval
  is the provider seam; a memory backend does not take over the recent context
  builder or the canonical conversation lifecycle.
- **LanceDB is derived and rebuildable.** Hindsight is derived memory
  intelligence, not canonical truth or a replacement for SQLite.
- Shadow recall/retain plumbing works. The completed canonical turn precedes
  the shadow flow; shadow recall and its durable comparison record precede
  retain. See [H1.4a shadow retain](2026-10-07-h1-4a-2-shadow-retain.md).
- **Reflect is optional memory-grounded reasoning, not memory maintenance.**
  Retain-time consolidation supplies the maintenance path; explicit Reflect
  is deferred from the normal lifecycle. See
  [H1.4b Reflect decision](2026-10-07-h1-4b-reflect-decision.md).
- Natural daily-use history remains too small to establish a final historical
  retrieval quality winner between Hindsight and Corvus RAG.

H1.6 established the operational constraints and model evidence:

- Corvus foreground and Hindsight extraction, consolidation, and Reflect
  currently resolve to the **same Qwen3.5-9B llama.cpp process** unless
  operation-level routing is changed. The server has **one inference slot**.
  Long background generation can queue foreground conversation behind it;
  post-response execution does not guarantee future foreground priority.
  Configuration and matching-build source establish this contention mechanism;
  actual overlap latency was not live-tested. See
  [H1.6b contention audit](2026-10-07-h1-6b-foreground-background-contention.md).
- Hindsight supports **native per-operation model/provider/base-URL isolation**
  for extraction, consolidation, and Reflect. Its global LLM semaphore is
  currently **1**, and Corvus foreground is outside that semaphore. Routing
  capability alone does not establish quality or foreground safety. See
  [H1.6b-2 isolation audit](2026-10-08-h1-6b-2-memory-model-isolation.md).
- The real 9B consolidation failure was **OutputTooLong/context-budget
  exhaustion**: **4129 input + 4063 output tokens = 8192**. It was rejected on
  `finish_reason=length` before structured-response validation, and the
  discarded output was not preserved. This does **not** demonstrate semantic
  incapability. Canonical evidence and the extracted fact remained intact.
  See [H1.6a failure audit](2026-10-07-h1-6a-consolidation-output-too-long.md).
- **Qwen3-1.7B CPU consolidation was USABLE on one real fixture**: one grounded
  UPDATE, valid schema/source IDs, and no generated operations applied.
  General consolidation quality, conflict handling, and production readiness
  remain unestablished. This is promising research evidence only. See
  [H1.6c consolidation trial](2026-10-08-h1-6c-cpu-consolidation-capability-trial.md).
- **Qwen3-1.7B retain extraction was UNUSABLE on one real fixture**, with
  temporal, entity, and source-attribution errors. See
  [H1.6d extraction trial](2026-10-08-h1-6d-cpu-retain-extraction-capability-trial.md).
- **Gemma 4 E2B retain extraction was UNUSABLE on the same fixture**, despite
  being installed Hindsight 0.10.1's built-in `llamacpp` local default. It
  preserved the date but invented participation, misclassified the external
  event as assistant experience, and omitted Corvus. See
  [H1.6e Gemma trial](2026-10-09-h1-6e-gemma-retain-extraction-capability-trial.md).
- The **existing Qwen3.5-9B retain path has a successful real baseline** for
  that fixture. **No small model has enough evidence to become a production
  memory writer.** Single-fixture successes or failures do not establish
  universal capability or incapability.

## 2. Adopt decisions

These are the provisional daily-use architecture choices:

- **Canonical truth: Corvus SQLite Evidence Log.** Preserve original evidence
  and canonical identifiers; derived observations cannot replace them.
- **Recent context: Corvus-owned.** Continue composing recent conversation
  from Corvus's canonical evidence and existing context responsibilities.
- **Historical memory intelligence: Hindsight derived state.** Keep historical
  retrieval behind the provider seam, with provenance back to canonical
  evidence and a reversible active-provider choice. LanceDB remains a
  derived/rebuildable retrieval index.
- **Foreground chat: Qwen3.5-9B.** Corvus retains responsibility for foreground
  reasoning and the final response.
- **Retain extraction: Qwen3.5-9B.** Preserve the successful real baseline as
  the provisional memory-writing model; neither tested small model replaces it.
- **Consolidation: Qwen3.5-9B as the trusted provisional model.** Do not replace
  it based on one small-model success. Long-running memory work must ultimately
  be admitted/scheduled so it does not block foreground conversation. Address
  bounded generation/context handling for the observed OutputTooLong failure
  before considering active daily-use consolidation reliable.
- **Product direction: move from laboratory optimization to daily use.**
  Preserve reversibility through SQLite and fix real observed failures rather
  than speculative ones. Foreground responsiveness and faithful memory writing
  take precedence over finding the smallest model.

Adopting these decisions does not enable new routing, change the active
provider, or certify the current shared single-slot lifecycle as daily-use safe.

## 3. Defer decisions

- **Reflect: DEFERRED.** It is optional memory-grounded reasoning and is not
  part of the normal retain lifecycle. Do not add per-turn, periodic, or idle
  Reflect as memory maintenance.
- **Final provider-quality verdict: DEFERRED.** Do not force a claim that
  “Hindsight beats Corvus RAG.” Accumulate natural daily-use history before
  making a final quality judgment; the active-provider decision may remain
  provisional in the meantime.
- **Production small-model consolidation adoption: DEFERRED.** Preserve the
  Qwen3-1.7B result as research evidence, not a production decision or an
  instruction to run further model trials now.
- **Scheduling and consolidation implementation: outside this freeze.** This
  document states the required outcome, not a scheduler, queue design,
  preemption mechanism, endpoint deployment, or configuration remedy.

## 4. Explicitly rejected or not-adopted options

- **Do not adopt Qwen3-1.7B or Gemma 4 E2B for retain extraction** on current
  evidence. Both produced unsafe memory records on the tested fixture.
- **Do not adopt Qwen3-1.7B for production consolidation** from its one USABLE
  result. Production memory writing needs more evidence than that trial.
- **Do not treat schema validity or an upstream local default as retention
  safety.** Fact, date, entity, participant, classification, and provenance
  fidelity remain necessary.
- **Do not replace canonical SQLite truth with Hindsight or LanceDB**, or move
  Recent Conversation Context ownership into the historical memory provider.
- **Do not use Reflect as a maintenance hook**, declare a final provider-quality
  winner from sparse history, or interpret the 9B OutputTooLong failure as proof
  that the 9B model cannot consolidate correctly.
- **Do not resume model hunting or scale trials to 3B/4B/7B/20B merely to find
  a smaller retain/consolidation model.** Research stops under the rule below.

## 5. Known risks

- **Foreground/background contention:** retain extraction and consolidation
  still share the single-slot 9B server with foreground generation. A successful
  previous reply does not establish that the next turn avoids background work.
  Production can share inference contention even when canonical data is isolated.
- **Unbounded consolidation:** the observed context/output exhaustion is
  unresolved. Admission/scheduling alone does not fix it; conversely, a token
  limit alone does not guarantee faithful, complete consolidation.
- **Partial derived state and observability:** successful retain or a completed
  worker status does not prove successful consolidation. The failed fact in
  H1.6a remained recallable but excluded from automatic consolidation until
  explicit recovery; accumulated failures could reduce observation coverage.
- **Serialization:** Hindsight's global semaphore can remain a throughput
  constraint even with endpoint isolation, and it does not reserve foreground
  capacity. Moving consolidation alone would leave extraction sharing the
  foreground server.
- **Limited quality evidence:** the 9B retain baseline and small-model trials
  are narrow. Neither the provisional 9B choice nor the Hindsight backend is
  a claim of general correctness, final retrieval superiority, or production
  readiness.

## 6. Reversibility and fallback

Preserve canonical SQLite evidence independently of memory-provider success.
Recent context remains available through Corvus even when historical memory
is degraded. Keep canonical provenance available for checking generated facts
and for later authorized replay or rebuilding of derived state.

The historical-provider seam preserves a return to the existing Corvus
historical retrieval/RAG path without migrating canonical truth. LanceDB remains
rebuildable from canonical evidence; Hindsight remains derived and replaceable.
Rebuilding derived semantic memory is not a promise of byte-identical output.

If daily-use memory writing or responsiveness is unsafe, the provisional
architecture must permit returning to the existing canonical-evidence-backed
Corvus path and withholding unsafe derived writes. This is the fallback
principle, not a new automatic mechanism implemented here. No bank recovery,
replay, provider switch, or configuration change is performed by this freeze.

## 7. Research stop rule

**Stop small-model model hunting now.** Do not escalate to 3B, 4B, 7B, or 20B,
run additional model comparisons, or revisit the two failed retain candidates
merely to optimize model size. Preserve the existing results as evidence.

**Reopen model selection only if real daily-use evidence exposes a concrete
need.** That evidence must identify an observed limitation to address; a desire
for a smaller model, an upstream default, or a promising single laboratory
fixture is insufficient. The current observed engineering needs are foreground
contention and bounded consolidation, not another model search.

This freeze enables progress toward real use while preserving reversibility.
It does not waive the safety work needed before active daily-use consolidation
is considered reliable.

## 8. Exact next engineering objective

> Make the provisional Hindsight architecture safe for daily use, beginning with
> foreground-safe background memory scheduling and bounded consolidation behavior.

The next engineering task must address that objective while preserving the
canonical/derived boundaries and provisional model choices above. This freeze
does not design or implement the scheduler or prescribe a specific consolidation
remedy. Implementation and validation belong to the next task.

This commit changes only this architecture log. No application code, Hindsight
configuration, inference, download, bank mutation, service restart, `:8106` or
`:8107` stop/start, host reboot/shutdown, or push was performed.
