# H1.7d-3a — Hindsight DeferOperation control-flow patch

Date: 2026-10-10. Offline patch and tests only; **NOT DEPLOYED**.

## Baseline and frozen source

Lab began clean on `lab/ow2e-console` at `311046e4eee4b5101997816b4ed93bdef23facfc`; Production remained clean on `main` at `c315d0e767e31fde3c82ba4dfb08659a268c267a`. The real async-retain acceptance log exists. Lab async retain remains enabled; its one intent is terminal completed and there are no unresolved intents. Lab/Production APIs, :8095 and Hindsight are healthy; both registry publishers are healthy/idle and the host aggregate is trustworthy IDLE.

Installed distribution `hindsight-api-slim` and package/project version identify Hindsight **0.10.1**. Only ten required files were copied read-only from `/app/api` in `hindsight-lab` into `/tmp/corvus-h17d-3a/upstream/`; edits and tests used a separate `patched/` copy. The package source files match the previously captured installed-source audit copy. The exact current source SHA-256 values, relative to `/app/api`, are:

- `pyproject.toml`: `4e73d3aae4711cb95639a2b3cfbe93ccf3a411b2ab3d4ad8924b7abc279930ec`
- `hindsight_api/__init__.py`: `bcc7731940bd700adbfcc094677c648fa21c9853634ceccf5ec3ac79310355b9`
- `hindsight_api/engine/llm_wrapper.py`: `f8a69115e51ce85ef004e22129bff98902fb5fe369f8c101a93f8fcbab12d0e4`
- `hindsight_api/engine/providers/openai_compatible_llm.py`: `7c6aad58263b6b4134a7a67c2c5c289d22d106c90532f15a321fc28f6b05abae`
- `hindsight_api/engine/retain/fact_extraction.py`: `4a3f52813d8621e5df89f004cc0380af10a6f80654fc022ec1aaa113ac55dd24`
- `hindsight_api/engine/retain/orchestrator.py`: `53f32c20acaa8c2c09a9b1a1c1f73adb5549ce00b2922bb64cc1d0f6ac2b2988`
- `hindsight_api/engine/consolidation/consolidator.py`: `7cb6b7a70705b82a2ab31815d9d98613bba5e238e2995969e6746a002aa6ad6b`
- `hindsight_api/worker/poller.py`: `6eb7b8a733fbe6dfd9fd51c41c219f306d45d7b2a95cc59cbbf4c58a733a9bd9`
- `hindsight_api/worker/exceptions.py`: `15f54dfbb6774199c94863993104d2cbecc2f98c7fe075948193b7bec61f078d`
- `hindsight_api/engine/memory_engine.py`: `b6f2af3868d283946079ec5c2a87b44379dfc37c0101f383ea192bc07e220949`

Container image: `sha256:b4d3b76f363aa40cf348450e7f8f52a50653008731b99824b14623a196182e73`; container ID: `336680f1d0a7a4dfb531f818976e969b6e1c7e55861fec4b605401df295a8bfe`. The versioned manifest also records container start/process and configuration/mount fingerprints, plus every patched output hash.

## Original problem and patch

`engine/retain/fact_extraction.py::extract_facts_from_text` wrapped aggregated `DeferOperation` exceptions in `RuntimeError`. Content aggregation, recursively split chunks, streaming and engine sub-batch collection could choose an ordinary sibling error before a defer. Streaming could signal end-of-input and let its consumer write a final checkpoint before propagating producer errors. `engine/consolidation/consolidator.py::_consolidate_batch_with_llm` classified defer as an ordinary batch error, counted failures, retried, returned a failed batch, and admitted adaptive bisection/failed-fact stamping.

The version-pinned diff changes four files:

- `engine/retain/fact_extraction.py`: small `_raise_if_deferred` helper; checks in `_extract_facts_with_auto_split`, `extract_facts_from_text`, and `extract_facts_from_contents`.
- `engine/retain/orchestrator.py`: `retain_batch` document-group aggregation; `_streaming_retain_batch` producer and pipeline drain. The producer detects defer before sending the final sentinel.
- `engine/memory_engine.py`: `_run_retain_execution` completed-sub-batch collection and final aggregate checks. Existing `_execute_task` control routing remains unchanged.
- `engine/consolidation/consolidator.py`: explicit `except DeferOperation: raise` before ordinary failure handling in `_consolidate_batch_with_llm`.

Control-flow invariant: a future per-attempt gate raises intentional defer → retain/consolidation raises the original exception → engine control routing → poller `_execute_task_inner` / `_defer_all` / `_defer_operation` → persisted pending work and `next_retry_at`, without normal retry consumption or false terminal completion/failure.

## Retain, consolidation, and compatibility

Any defer among completed aggregated extraction results takes precedence. Choose the original exception with the latest `exec_date`; input order breaks ties. Ordinary sibling errors are logged with tracebacks, not silently discarded or treated as successful extraction. They can surface again on a later attempt; eventual completion still requires all remaining extraction to succeed. Split halves and document groups settle before classification, so ordinary-error propagation can wait for siblings. This is the explicit concurrency rule; cancellation semantics are not broadened.

Streaming defer stops the final sentinel/final checkpoint and drains/cancels its pipeline peer. Already committed chunk checkpoints are preserved; existing recovery skips those chunks and resumes the remainder. Consolidation defer exits before failure metrics/retries/bisection/fact-failure stamping. Prior successful batch stamps remain committed; deferred/remaining facts stay eligible. Neither path mints new operations or replaces payloads. Existing checkpoint/storage semantics are reused.

Ordinary retain model errors, malformed response/fact handling, consolidation transport retries, schema/JSON/output-limit fail-fast behavior, authorization propagation, and adaptive bisection/failed-singleton handling retain their existing behavior. The wrapper `_attempt_permits`, `LLMProvider.call`, and OpenAI-compatible provider already release permits and rethrow the same control exception without provider retries; they are unchanged. Generic diagnostic tracing remains upstream behavior. No registry gate or Reflect functionality was added.

Worker deferral remains upstream: status becomes `pending`; `next_retry_at` equals `DeferOperation.exec_date`; worker/claim fields are cleared; retry count, error field, operation identity and executable payload are not changed by deferral. No terminal-success/failure metric is emitted for proper defer.

## Validation and reproducibility

Artifact: `deploy/hindsight-patches/0.10.1/` contains the unified diff, ten-file upstream/patched hash manifest, guarded offline apply/verify helper, README, and focused source-driven test harness. All hashes and version are checked before writes; application refuses unexpected inputs, drift, and duplicate application. No upstream source tree is vendored.

Command used:

```sh
python3 -B deploy/hindsight-patches/0.10.1/test_control_flow.py --source /tmp/corvus-h17d-3a/patched --upstream-source /tmp/corvus-h17d-3a/upstream
```

**27 focused checks PASS**, including 10 ordinary-error regressions; the same **10 regressions PASS on pristine upstream**. Tests execute selected complete installed functions/closures with fake LLM/storage/SQL/SDK/tracing boundaries. They prove same-object defer through real extraction/consolidation → engine → poller, pending scheduling without retry consumption, permit release with zero HTTP calls, defer precedence with sibling errors, no bisection/failure on defer, actual ordinary bisection, previously committed batch preservation, chunk-hash recovery without duplicated successful chunks, no false terminal state, and version/hash application guards. Syntax compilation of all nine pinned Python files and `git diff --check` pass.

This is focused offline validation, not a complete upstream service/database integration suite. Real-bank partial-commit/idempotent resumption remains a later controlled acceptance requirement before admission enablement.

Final read-only checks confirm all ten live source hashes, service/container identities and configuration, canonical Lab evidence, Production private state, retain ledger, registry contents and host unit/tmpfiles files unchanged. Lab PID 13671 and Production PID 2831871 remain unchanged; Hindsight PID 2884/image/config/mount fingerprints remain unchanged. Bank counts remain 8 documents / 9 memories. No real retain, consolidation, Reflect, model request, bank mutation, service/container restart, registry mount, or runtime configuration change occurred. Hindsight remains disconnected; foreground admission is not enabled. Production is untouched.

## Next step

Implement a standalone read-only foreground registry reader and per-attempt admission gate against this patched Hindsight source, still offline before any controlled deployment. Preserve durable async retain, test deferred partial-commit resumption, and keep Reflect deferred.

Verdict: PASS for the offline, pinned control-flow patch; not deployed or claimed production-ready.
