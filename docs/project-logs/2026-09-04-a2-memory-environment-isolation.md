# A2 — Memory Environment Isolation

## Context

During the first real daily-use test of the Corvus Memory Playground,
synthetic benchmark memory unexpectedly appeared in a normal personal
conversation.

The user told Corvus:

> I like to drink soda.

Corvus replied that its records instead indicated that the user's
benchmark drink was jasmine tea.

Investigation of the canonical SQLite Evidence Log found:

- message #8
- session: `p1-rag-benchmark`
- content: `For the Corvus benchmark, my test drink is jasmine tea.`

The first real Playground session later contained:

- #40 — real user Playground message
- #41 — normal assistant reply
- #42 — `I like to drink soda.`
- #43 — assistant reply contaminated by the old jasmine-tea benchmark evidence

Git history traced the synthetic fixture to:

`c389f5b Add Phase 1 RAG benchmark`

The incident showed that historical development benchmarks and the
daily-use Corvus runtime had been sharing the same persistent memory
environment.

## Research/Engineering Question

How should Corvus prevent synthetic benchmarks, experiments, and test
fixtures from contaminating the canonical personal Evidence Log while
still exercising the real production retrieval architecture?

## Starting Hypothesis

Filtering benchmark session names, fixture strings, or known message IDs
would treat symptoms rather than the architectural cause.

The correct boundary should be the entire memory environment:

- canonical SQLite Evidence Log
- derived LanceDB dense index

Both should belong atomically to one data root.

Synthetic evaluation should therefore run in a separate temporary
environment instead of inside the daily-use personal memory world.

## What We Did

### 1. Centralized the memory environment

Added:

`memory/config.py`

Corvus now resolves its persistent memory root through:

`CORVUS_DATA_DIR`

The normal production default remains:

`<project-root>/data`

Both persistent resources are resolved from the same root:

- SQLite: `corvus.db`
- LanceDB: `corvus-retrieval.lancedb`

`memory/store.py` and `memory/dense_index.py` were updated to use this
centralized configuration.

### 2. Added isolated benchmark execution

Added:

`benchmarks/run_isolated.py`

The launcher:

1. creates a temporary directory,
2. sets `CORVUS_DATA_DIR` to that directory,
3. launches the benchmark in a fresh child process,
4. destroys the temporary environment after execution.

The fresh process ensures storage paths are resolved after the
environment has been configured.

Added:

`benchmarks/isolated_env.py`

This provides a shared fail-closed safety check for new memory-touching
benchmarks and refuses execution against the normal production data
directory.

### 3. Added an A0 production-path smoke benchmark

Added:

`benchmarks/run_a0_retrieval_smoke.py`

Unlike historical P1 prototype runners, this benchmark exercises the
current A0 production retrieval path:

SQLite canonical Evidence Log
→ SQLite FTS5 / BM25 sparse retrieval
+ persistent LanceDB dense retrieval
→ RRF hybrid fusion
→ canonical SQLite hydration

Synthetic fixtures are created only inside the isolated temporary
memory environment.

### 4. Archived the contaminated development environment

Before cleanup, the A2 backend was stopped so the persistent state was
no longer changing.

The old `data/` memory environment was archived to:

`/home/ethan/srv/backups/corvus/pre-clean-20260904T155634`

The SQLite SHA256 checksum was:

`fdb4b909c597cc7d38e068c21bdf4c49b3cfdd1fbe600b7aadde3a21edf1639a`

The original and archived SQLite databases had identical checksums.

The contaminated development world therefore remains available as a
forensic snapshot rather than being silently rewritten.

### 5. Created a clean production memory environment

The previous development memory world was replaced with a fresh
production `data/` environment.

Initialization verification showed:

- `MESSAGE_COUNT: 0`
- `JASMINE_COUNT: 0`
- dense table exists
- dense rows: 0

This established a clean boundary between historical development data
and future personal daily-use evidence.

## Evidence/Results

### Environment isolation regression

A temporary `CORVUS_DATA_DIR` correctly redirected both SQLite and
LanceDB away from production.

The isolated benchmark launcher left the production SQLite database
unchanged.

### A0 production retrieval smoke

The new production-path smoke benchmark passed all three cases:

- semantic case — PASS, rank 1
- exact identifier case — PASS, rank 1
- hybrid case — PASS, rank 1

Final result:

`A0_PRODUCTION_RETRIEVAL_SMOKE: PASS`

Production safety result:

`PRODUCTION_DB_UNTOUCHED: PASS`

Benchmark exit code:

`0`

### Daily-use cross-session regression

After the clean production environment was created, the user told
Corvus in one Playground session:

`I like to drink soda.`

A new session then asked:

`Which beverage did I tell you I like?`

Corvus correctly answered that the user had said they like:

`soda`

The original statement was not part of the new session's local chat
history, demonstrating persistent cross-session recall.

The previous jasmine-tea benchmark evidence did not reappear.

Result:

**Cross-session persistent recall regression: PASS**

## Interpretation

The jasmine-tea incident was a memory-environment boundary defect, not a
failure of hybrid retrieval.

A0 retrieval correctly retrieved evidence that genuinely existed in its
canonical Evidence Log.

The architectural mistake was allowing synthetic benchmark evidence to
share that canonical Evidence Log with a daily-use personal assistant.

The new environment boundary fixes that problem while allowing
benchmarks to continue exercising the real production retrieval code.

## Decision

Corvus adopts the following engineering rule:

**Production personal memory and synthetic evaluation memory must use
separate memory environments.**

A memory environment contains at least:

- canonical SQLite Evidence Log
- derived LanceDB dense index

Both must resolve from the same `CORVUS_DATA_DIR`.

Synthetic benchmarks must not depend on filtering by:

- session prefix,
- fixture text,
- known message IDs,
- benchmark-specific cleanup after execution.

Isolation occurs before synthetic evidence is written.

Historical P1 benchmark runners remain valid historical research
records, but they are not the acceptance path for the current production
retrieval architecture.

## Architecture Impact

Before:

development / benchmark / daily-use runtime
→ shared SQLite Evidence Log
→ shared LanceDB dense index

After:

daily-use Corvus
→ production `CORVUS_DATA_DIR`
→ personal SQLite Evidence Log
→ personal LanceDB dense index

synthetic benchmark
→ temporary isolated `CORVUS_DATA_DIR`
→ temporary SQLite Evidence Log
→ temporary LanceDB dense index
→ automatic cleanup after execution

The existing A0/A1/A2 architecture remains intact.

No new memory semantics or retrieval algorithm was introduced.

## Open Questions

No additional architecture work is required for this incident before
continuing the current Corvus roadmap.

Possible future work, only if later justified:

- pytest integration using temporary directories,
- broader benchmark lifecycle tooling,
- migration tooling for mature production installations.

These are intentionally deferred.

The verbose response style observed during the soda regression is also
outside the scope of this memory-isolation fix.

## Next Step

Perform final repository validation:

- inspect Git diff and status,
- run relevant Python compile checks,
- confirm the Playground frontend still builds,
- commit the environment-isolation implementation and this project log,
- push the stable checkpoint.

After that, stop work on this incident and return to the existing
Corvus roadmap.
