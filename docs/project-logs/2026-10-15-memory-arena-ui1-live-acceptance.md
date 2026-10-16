# Memory Arena UI-1 — Live Acceptance

**Date:** 2026-10-15
**Verdict:** `MEMORY_ARENA_UI1_LIVE_ACCEPTED`

## Goal and scope

UI-1 adds an opt-in, read-only Hindsight comparison panel to the existing
Lab Open WebUI chat. It does not change Corvus Arena backend behavior, H1,
RAG, canonical memory, or Production. Voting is explicitly deferred to UI-2.

The UI is based on Open WebUI v0.6.5, pinned to upstream commit
`07d8460126a686de9a99e2662d06106e22c3f6b6`. A session-local **Memory A/B**
toggle defaults OFF and is not persisted. Only the narrow boolean
`corvus_arena` request metadata is passed to the Pipe. An opted-in turn sends
one `POST /api/arena/chat`; the Pipe returns `main.reply` through the normal
message path and emits one `corvus:arena:v1` event associated with the
canonical assistant message. The event stores a read-only Hindsight candidate
panel with evidence and timing in normal Open WebUI chat history. It does not
enter Corvus canonical memory.

## Persistence and association

All Chat-owned full-history saves use one serialized writer. If the Arena
event arrives before completion, it attaches locally and does not persist a
full-history snapshot. Normal completion saves the completed reply and Arena
field together. An event arriving after completion saves through the same
writer. This prevents a placeholder snapshot from replacing the server
completion. Save as Copy and assistant content edits remove the Arena
association; ratings preserve it. The separate trial record is unchanged.

Accepted limitations: navigating away or refreshing before completion/save
may lose the panel; there is no cross-tab save coordination.

## Verification and live evidence

- Tests: 55 Python and 23 frontend tests passed; Svelte/TypeScript checks,
  production Vite build, overlay verification, and image verification passed.
- Lab image: `corvus-open-webui:0.6.5-arena-ui1.2`,
  `sha256:ae941e36d670a5462edb9566617a027e3c15467c4601af0ad8c43a74822c2cf7`.
- Browser smoke for **“你好，Corvus”** passed, including refresh persistence.
  The persisted panel references trial
  `f0b4e44b-3eca-4cd4-8bb3-79aa5cfbf5f1` and shows a completed candidate.
- Backend smoke found exactly one canonical user/assistant pair (IDs 19/20),
  one Arena trial, no vote, and one normal H1 comparison/retain lifecycle.
  H1 recorded one retain intent and one accepted submission for that pair.
  The shadow reply happened to be byte-identical to the canonical reply; no
  separate shadow row or shadow persistence path was found.
- Dense sync reported `OK` for the canonical turn and the canonical path
  synchronizes only IDs 19/20. Direct Lance row enumeration timed out; this
  was non-blocking because the turn result and sync call path were verified.
- Production image, container, Pipe, and configuration remained unchanged.

UI-1 is accepted for Lab. UI-2 voting remains future work; no vote was cast
for the smoke trial.
