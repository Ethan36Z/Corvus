# Stage A1 Checkpoint — Live Persistent Recall Validation

## Context

Stage A1 reached its first real end-to-end persistent conversation test using
the actual SQLite Evidence Log, A0 retrieval stack, pinned llama.cpp runtime,
and Qwen3.5-9B.

## What We Did

Session A stored a unique verification fact:

`cedar-lantern-5842`

The user message became canonical SQLite message `#26`.

The model request then failed with HTTP 500. The runtime correctly preserved
`#26`, created no assistant message, and performed no dense sync.

The process was fully exited.

A new process was then started with a different session:

`a1-live-session-b`

Startup dense recovery processed `#26`.

The new session asked a paraphrased question about the earlier verification
token.

## Live Bug Found

The first live request exposed a pinned Qwen3.5 chat-template constraint:

two consecutive `system` messages caused HTTP 500 with:

`No user query found in messages.`

Historical Evidence had originally been emitted as a second system message.

The Working Context builder was corrected to merge:

Corvus system instructions
+
Historical Evidence

into one system message.

Live token-count validation then passed with exactly one system message.

## Evidence / Results

Startup recovery:

`Dense recovery: OK (batches=1, indexed=1, progress=26)`

Session B inspection:

`recent=[]`

`history=[26, 2, 15, 16, 14]`

The model answered:

`Your verification token is **cedar-lantern-5842**.`

Canonical messages:

- `#26` — Session A user verification fact
- `#27` — Session B recall question
- `#28` — Session B correct assistant answer

Dense classification:

`current=[26, 27, 28]`

`missing=[]`

`stale=[]`

`source_missing=[]`

The durable dense recovery cursor remained at `26` because `#27/#28` were
inserted through foreground targeted sync rather than tail recovery.

## Decision

The core Stage A1 persistent recall path is validated:

canonical SQLite evidence
→ process exit
→ restart recovery
→ different session
→ A0 Historical Evidence Recall
→ local 9B grounded answer

The test also validates the intended failure rule:

model failure does not erase canonical user evidence.

## Architecture Impact

Corvus now demonstrates evidence-grounded long-term conversational recall
across both process and session boundaries.

Working Context serialization must preserve the pinned model's chat-template
requirements, including a single merged system message.

## Next Step

Review and checkpoint the final A1 runtime changes, then produce the Stage A1
report and maturity judgment before sealing the stage.
