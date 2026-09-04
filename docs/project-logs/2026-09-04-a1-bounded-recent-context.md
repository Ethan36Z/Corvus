# Stage A1 Checkpoint — Bounded Recent Context

## Context

Stage A1 needs Recent Conversation Context to come from persistent SQLite
history rather than the prototype process-local `messages[]` list.

This is not a separate short-term memory store. It is a bounded read view over
the canonical Evidence Log.

## Engineering Question

How should the runtime load recent messages from the current session after the
current user message has already been committed?

## What We Did

Added to `memory/store.py`:

`load_recent_messages(session_id, limit=64, before_message_id=None)`

Behavior:

- reads only one session;
- returns the newest bounded tail;
- returns results in chronological order;
- optionally excludes the current and newer messages through
  `before_message_id`;
- returns canonical message IDs and metadata.

The storage layer performs only bounded message retrieval.

Token-budget trimming remains a runtime concern and will use llama.cpp
model-native token counting.

## Evidence / Results

Validation passed:

- `python -m py_compile memory/store.py`
- chronological ordering: PASS
- invalid `limit=0` guard: PASS
- `git diff --check`: PASS

Observed test session returned message IDs:

`[24, 25]`

with:

`chronological=True`

## Decision

ADOPT the new bounded recent-message read interface for Stage A1.

Keep SQLite as canonical conversation history.

Do not place tokenizer or Working Context policy inside `memory/store.py`.

## Architecture Impact

Stage A1 can now follow:

user SQLite commit
→ load prior current-session messages with `before_message_id=user_message_id`
→ token-budget Recent Conversation Context
→ Historical Evidence Recall
→ model generation

This naturally prevents the current user message from being duplicated in the
recent-context tail.

## Next Step

Review the A1 checkpoint diff, explicitly stage only the intended A1 files,
commit, and push before continuing the persistent conversation loop.
