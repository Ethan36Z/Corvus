# H1.6a — Real Hindsight consolidation OutputTooLong failure

Date: 2026-10-07

Baseline: `lab/ow2e-console` at `89e27528cc9d854ef940152723c50cb7707d786b`

Audit verdict: **PASS WITH CONSTRAINTS**. This records the read-only audit;
no remedy, recovery, configuration change, or contention experiment was applied.

## Incident

A real H1.5b Lab turn returned HTTP 200 in **3346.113 ms**. Hindsight shadow
recall succeeded in **161.514 ms**, and retain/extraction succeeded in
**5361.834 ms**. Subsequent automatic consolidation failed with
`OutputTooLongError` after **64082 ms**. No retry or Reflect occurred.

Canonical turn IDs: user `11`, assistant `12`; derived document:
`corvus-lab:turn:11:12`. Consolidation operation:
`b11bcd7c-9c99-494c-a792-cea3bfa5fa14`; failed world fact:
`e48a7eec-a27f-4214-86e9-1c5e87b644d3`.

The model call ran from `2026-10-08T00:29:46.960908Z` to
`2026-10-08T00:30:51.043094Z` (October 7 locally). Evidence came from the real
Hindsight 0.10.1 installed source/configuration, Hindsight and llama.cpp logs,
stored model trace, read-only bank APIs, Corvus shadow JSONL, and canonical SQLite.

## Root cause

The shared llama.cpp model (`Qwen_Qwen3.5-9B-Q5_K_M.gguf`, alias `corvus`)
exhausted its configured **8192-token context**: **4129 input tokens + 4063
generated output tokens = 8192**. llama.cpp logged `truncated=1`. The Hindsight
OpenAI-compatible provider adapter rejected `finish_reason=length` with
`OutputTooLongError` before JSON parsing or structured-response validation.
This was output exhaustion during generation, not a large-bank input problem
or timeout; the input fitted, and the provider HTTP timeout was 180 seconds.

The batch already contained only one new fact. It retrieved three observations
and their supporting facts; total bank size was not the direct cause. The
recorded system prompt contained 11742 characters and the user message 2111,
despite the retained turn containing only 161 characters. Fixed instructions
and the structured create/update/delete schema add substantial overhead, while
generation length remains model-driven. No explicit consolidation completion
budget was configured.

The discarded output was not saved, so prolonged reasoning, repetition, or
excessive JSON cannot be distinguished. Consolidation reasoning effort was
unset; evaluating `none` is a candidate, not a proven fix.

## Post-failure state

The outcome is **partial-but-valid derived state**. Canonical Corvus SQLite
rows remain intact. The retained document and extracted world fact remain
valid, and the fact remains eligible for ordinary recall with retain-time links
intact. The fact did not complete consolidation; no observation update, merge,
or deletion occurred for it. No corruption or inconsistent canonical state
was found in the inspected evidence.

The bank remained at 7 documents, 4 world facts, 3 observations, and 23 persisted
links. No pending operation remained. The worker operation was marked
`completed` with retry count zero, while the fact carried
`consolidation_failed_at` and bank statistics reported one failed consolidation.
Operation completion alone therefore does not establish consolidation success.

Failed facts are excluded from subsequent automatic consolidation, including
maintenance reconciliation. Explicit recovery/requeue would be required to
make this fact eligible again. The supported bank-wide
`POST /v1/default/banks/{bank_id}/consolidation/recover` clears failure markers
for a subsequent run; it was not executed.

## Quality implication

Narrow exact-fact recall remains usable. This failed consolidation should not
be interpreted as a recall failure. The existing library observation still
covers the answer, but gained no additional evidence from this fact. Accumulated
failures could bias long-term observation coverage, evidence aggregation,
duplicate handling, and update quality. H1.5 long-term provider-quality
conclusions remain premature.

## Candidate remedies — NOT adopted

In increasing intervention order:

1. Observe recurrence under authorized natural use.
2. Evaluate consolidation `reasoning_effort=none` using the supported setting.
3. Evaluate an explicit consolidation completion/output budget.
4. Reduce supported observation/source-fact budgets if later evidence supports it.
5. Evaluate a dedicated consolidation model or larger compatible context.
6. Modify the upstream consolidation prompt only as a last resort.

Increasing output budget alone cannot exceed the 8192-token context; a smaller
budget could merely truncate sooner. Idle scheduling would address resource
contention, not this OutputTooLong root cause. No remedy was applied from a
single incident.

## Failure-isolation evidence

The user-visible reply, canonical persistence, and active Corvus RAG were
unaffected by this incident. Lab remained healthy; Production remained active
with unchanged PID/start time. No retry storm or Reflect occurred. Corvus's
derived JSONL records retain success, while the later consolidation failure is
observable through Hindsight logs, traces, and failed-consolidation statistics.

## Remaining H1.6 question

The shared llama.cpp server currently exposes **one inference slot**. The failed
consolidation occupied that shared model for approximately **64 seconds**.

Current evidence proves the previous reply does not wait for consolidation,
but **does not prove that a new foreground Corvus turn arriving during
consolidation receives priority or avoids queueing behind it**. Foreground versus
background contention is the next H1.6 target; no contention experiment has
been started.
