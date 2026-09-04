# Stage A2 Checkpoint — Final Daily-Use Backend Acceptance

## Context

Stage A2 had reached a functional HTTP backend with health, persistent chat,
retrieved-memory inspection, and minimal session resume.

The final acceptance needed to validate actual repeated daily-use behavior
across multiple turns and a backend restart.

## Research / Engineering Question

Can the A2 backend sustain a real multi-turn conversation, restart cleanly,
recover canonical session state, and continue the same conversation without
losing memory or persistence guarantees?

## What We Did

Ran an end-to-end HTTP acceptance using a dedicated session.

The test covered:

- FastAPI startup;
- runtime health;
- first persistent chat turn;
- second turn using Recent Conversation Context;
- backend shutdown;
- backend restart;
- dense recovery;
- canonical session reload;
- continued conversation after restart.

## Acceptance Bug Found

The first acceptance attempt exposed a real multi-turn bug.

The second turn persisted the user message to canonical SQLite but failed
before Working Context construction completed.

Evidence showed:

- user `#31`;
- assistant `#32`;
- failed-turn user `#33`.

The SQLite-first persistence guarantee therefore behaved correctly.

The root cause was in Recent Context token budgeting.

While scanning conversation history backward, the runtime temporarily formed
an assistant-only candidate and sent it to the model-native token counter.

Qwen's chat template rejected that shape with HTTP 500.

A minimal reproduction confirmed:

`assistant_only_rejected=PASS`

`valid_conversation_counted=PASS`

## Fix

Updated `build_recent_context()` so model-native token counting only receives a
valid recent chat shape beginning with a user message.

The change preserves:

- newest-history preference;
- chronological final ordering;
- existing token budgets;
- existing A1 persistence semantics.

Regression checks passed:

`assistant_partial_shape_not_counted=PASS`

`complete_recent_turn_preserved=PASS`

`live_recent_context_31_32=PASS`

`recent_context_starts_with_user=PASS`

`qwen_token_count_regression=PASS`

## Final Acceptance Results

A fresh session used marker:

`silver-fox-8427`

First persistent turn passed:

`first_persistent_turn=PASS`

Second same-session turn recalled the marker and used canonical recent context:

`same_session_recent_context=PASS`

`second_persistent_turn=PASS`

The first backend process stopped successfully.

After restart:

`backend_restart=PASS`

`restart_dense_recovery=PASS`

Recovery progress reached canonical message `#37`.

The session API restored:

`[34, 35, 36, 37]`

Validation passed:

`session_resume_after_restart=PASS`

`canonical_transcript_preserved=PASS`

A third turn after restart again recalled:

`silver-fox-8427`

Validation passed:

`continued_chat_after_restart=PASS`

`persistent_recent_context_after_restart=PASS`

Final acceptance:

`daily_use_http_loop=PASS`

`restart_resume_continue=PASS`

`recent_context_bug_fixed=PASS`

`a2_backend_acceptance=PASS`

## Interpretation

The A2 backend now supports the minimum daily-use lifecycle required by the
existing Corvus UI:

HTTP chat
→ canonical persistence
→ recent context
→ historical Evidence Recall
→ model response
→ derived dense sync
→ restart
→ canonical session resume
→ continued conversation.

## Fresh Landscape Check

Current FastAPI guidance still recommends lifespan-based startup and shutdown.

Current llama.cpp continues to expose a health surface and an OpenAI-compatible
chat API.

For future orchestrated deployment, separate liveness and readiness endpoints
may be useful, but this is not required for the local A2 daily-use baseline.

No external framework currently justifies replacing the existing A2 service
architecture.

## Decision

ACCEPT the A2 backend daily-use baseline.

Keep the current architecture.

DEFER deployment-oriented liveness/readiness separation until deployment
requirements justify it.

## Next Step

Write the Stage A2 Phase Report, assign the final maturity judgment, review the
complete diff, commit and push.

Then pause at:

A2 backend ready for UI integration.
