# Memory Arena UI-2 offline validation

Date: 2026-10-16
Branch: `lab/ow2e-console`
Baseline: `680b626732360e3e2f731b535d3160c022e9dcb8`

## Purpose and behavior

UI-2 adds human RAG/Hindsight preference voting to the existing Memory Arena
panel. The only choices are **Prefer RAG** and **Prefer Hindsight**. Vote
controls are available only when the completed, votable Arena association is
present in authenticated Open WebUI saved chat history. Local or in-flight
Arena state does not establish eligibility.

The browser uses a dedicated authenticated Open WebUI vote Action. The Action
checks the saved message and user ownership, then forwards only `trial_id` and
`choice` to the fixed Lab Corvus vote endpoint. Corvus vote confirmation is
required before selected state changes. A failed vote leaves selection
unchanged. After confirmation, the Action persists only `corvus_arena.vote`
on the original saved assistant message; it does not rewrite the chat snapshot.

The read-only daily preferences API counts the latest actual vote event per
trial on the requested local calendar day. Its response contains the date,
RAG count, Hindsight count, and total votes. Missing votes do not count.

## Arena lifecycle and invariants

UI-2 does not change generation, retain, or canonical conversation lifecycle.
RAG remains the canonical answer. Hindsight remains a shadow candidate and is
not retained. Vote/evaluation data remains separate from canonical message
content except for the intended vote marker in saved Open WebUI message state.

## Offline validation

- Arena/backend and API contract tests: 34 passed, including the transformed
  Open WebUI Action tests.
- UI-2 frontend tests: 16/16 passed.
- UI-1 regression tests: 23/23 passed.
- Pinned Open WebUI UI-2 patch and lock verification: passed; 117 patched files
  verified and zero branding findings.
- Transformed Open WebUI Vite production build: passed.
- `svelte-check`: 4,948 upstream errors and 73 warnings. No new UI-2 diagnostic
  was identified in changed regions; the previously recorded UI-1 baseline was
  4,949 errors.
- `git diff --check`: passed.

## Status

Maturity: **VALIDATED_NOT_LIVE**. No live deployment or browser vote acceptance
has occurred. The next step is Lab live deployment followed by browser vote
acceptance.
