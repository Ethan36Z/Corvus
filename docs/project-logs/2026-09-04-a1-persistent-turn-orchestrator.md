# Stage A1 Checkpoint — Persistent Turn Orchestrator

## Context

Stage A1 now has independent Working Context and Model Client components.

The remaining per-turn integration requirement is to preserve canonical
conversation history while coordinating retrieval, generation, persistence,
and derived dense synchronization.

## What We Did

Added `app/conversation_runtime.py` with:

`process_turn(...)`

Normal ordering:

user SQLite commit
→ build Working Context
→ model generation
→ assistant SQLite commit
→ targeted dense synchronization

The runtime also exposes per-turn inspection state for:

- canonical message IDs;
- Recent Context IDs;
- Historical Evidence IDs;
- input tokens;
- retrieval status;
- model status;
- persistence status;
- dense status;
- errors.

Historical retrieval failure was also changed to degrade to recent/current
context rather than aborting the entire turn.

## Evidence / Results

Synthetic validation passed for:

- SQLite-first successful turn;
- assistant persistence after valid generation;
- dense sync only after canonical writes;
- model unavailable with user evidence preserved;
- no fake assistant after model failure;
- dense failure with both canonical messages preserved;
- retrieval failure with conversation continuing;
- assistant SQLite failure with assistant remaining non-canonical;
- no dense sync after assistant persistence failure.

Key failure semantics verified:

model failure
→ user remains canonical

retrieval failure
→ recent/current conversation remains usable

dense failure
→ canonical conversation remains intact

assistant persistence failure
→ generated text is not treated as canonical assistant evidence

## Decision

ADOPT the SQLite-first turn orchestrator for Stage A1.

Corvus preserves reality rather than forcing every user message into an
artificial successful user/assistant pair.

## Architecture Impact

A complete persistent turn can now be represented as:

SQLite Evidence Log
→ Working Context
→ local Qwen3.5-9B
→ SQLite Evidence Log
→ derived dense index

The remaining work is to expose this through the real conversation loop and
verify restart recovery with the actual persistent stores and model runtime.

## Next Step

Review and checkpoint this implementation, then connect it to the interactive
Persistent Conversation Loop with bounded startup dense recovery.
