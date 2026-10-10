# Hindsight 0.10.1 intentional-defer patch

**Offline artifact; not deployed.** No registry reader, admission gate, model configuration, or new worker is included. Reflect remains deferred.

This patch is pinned to the exact installed `hindsight-api-slim` 0.10.1 source. `manifest.json` records SHA-256 hashes of all ten frozen input/dependency files, expected patched hashes, and the observed container/image/configuration fingerprints. It does not vendor upstream source. Version alone is insufficient: another build labeled 0.10.1 is rejected if any pinned file differs.

The source root is an isolated directory with `pyproject.toml` and `hindsight_api/`, corresponding to `/app/api`. Copy **only** the relative files listed in the manifest from the running container into two fresh offline directories (one pristine, one to patch). Create their parent directories locally, then use `docker cp hindsight-lab:/app/api/<relative-file> <offline-api-root>/<relative-file>`. Copying out does not edit the container. Confirm installed distribution metadata read-only with `docker exec hindsight-lab python -B -c 'from importlib.metadata import version; print(version("hindsight-api-slim"))'`.

With Python 3.11+ and Git, from the Corvus Lab repository:

```sh
python3 -B deploy/hindsight-patches/0.10.1/apply.py --root /tmp/offline-hindsight-api --check
python3 -B deploy/hindsight-patches/0.10.1/apply.py --root /tmp/offline-hindsight-api --apply
python3 -B deploy/hindsight-patches/0.10.1/apply.py --root /tmp/offline-hindsight-api --verify-patched
python3 -B deploy/hindsight-patches/0.10.1/test_control_flow.py --source /tmp/offline-hindsight-api --upstream-source /tmp/pristine-hindsight-api
```

Do not apply the diff directly. The helper validates distribution/version and **every** input hash before any application, runs `git apply --check`, applies once, and verifies every expected output hash. It rejects drift and repeated application. The unified diff uses zero context (`--unidiff-zero`); exact hash pinning supplies the stronger source guard and avoids trailing-space context records. `/app/api` in-place application is explicitly refused. Application is for an offline source/build workspace; a future image build and controlled rollout need separate authorization. An interrupted application fails subsequent hash verification; discard/recreate that offline copy rather than guessing its state.

Retain aggregation prioritizes any `DeferOperation` in completed results over ordinary sibling exceptions. The latest `exec_date` wins, with input order breaking ties; the same exception object is raised. Ordinary sibling errors are logged with tracebacks and must still be resolved on a later successful attempt. Partial successes never satisfy whole-retain completion. Split halves and document groups now settle before choosing an exception; ordinary error types stay unchanged, although propagation can wait for siblings.

The streaming producer raises defer before its end-of-stream sentinel. The driver cancels/drains its peer and gives completed defer results precedence. This prevents a final partial `facts_committed` checkpoint; previously committed chunks remain recoverable by existing chunk hashes. The engine's completed-sub-batch collection also recognizes defer before selecting an ordinary error. It does not change cancellation, store transaction semantics, operation IDs, or checkpoint formats.

Consolidation rethrows defer before failure metrics, outer retries, failed-batch results, or adaptive bisection. Already committed batches keep their stamps; the deferred batch remains unstamped and eligible. Existing worker routing and poller deferral already preserve the control signal, so no worker or LLM-wrapper/provider patch is needed.

Tests execute complete selected upstream functions and streaming/dispatch closures via AST, with fake prompts, SDK collaborators, LLM, storage, tracing and SQL boundaries. This avoids importing/initializing the service and requires no external Python packages or real inference. Both patched and pristine sources run the ordinary-error regression suite. Coverage includes parser failures, retry/bisection behavior, partial checkpoint recovery, worker pending scheduling, permit release, and application guards. This is focused offline control-flow validation, not a full upstream service/database suite or real-bank partial-commit acceptance. The latter remains necessary before admission rollout.
