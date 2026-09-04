# Stage A2 Checkpoint — Shared Runtime Config and Lifecycle

## Context

Stage A1 produced a working persistent conversation runtime, but several
daily-use settings and startup recovery behavior were still owned directly by
individual modules or the CLI.

Stage A2 needs the CLI and upcoming API service to share the same runtime
configuration and startup semantics.

## Research / Engineering Question

Can Corvus centralize runtime configuration and startup dense recovery without
changing the behavior validated in Stage A1?

## Starting Hypothesis

A small standard-library configuration module plus one shared lifecycle module
should be sufficient.

No new configuration framework or task system is justified for the current
single-machine local runtime.

## What We Did

Added:

`app/runtime_config.py`

It centralizes:

- model base URL;
- model timeout;
- token-count timeout;
- maximum generation tokens;
- dense recovery batch size;
- dense recovery maximum batches.

Defaults preserve the Stage A1 values.

Environment variables can override the defaults.

Positive integer configuration is validated at process startup.

Added:

`app/runtime_lifecycle.py`

It owns the bounded:

`recover_dense_tail()`

startup recovery operation.

Updated:

`app/model_client.py`

to consume shared runtime configuration.

Updated:

`app/chat_persistent.py`

to consume the shared recovery lifecycle instead of maintaining a private copy.

## Evidence / Results

Configuration validation passed:

`default_config_preserved=PASS`

`env_override=PASS`

`invalid_config_guard=PASS`

Model Client integration passed:

`shared_config_import=PASS`

`model_urls_valid=PASS`

`a1_defaults_preserved=PASS`

`model_client_env_override=PASS`

Shared recovery validation passed:

`shared_recovery_behavior=PASS`

`recovery_degradation=PASS`

CLI integration passed:

`cli_uses_shared_recovery=PASS`

Source review confirmed that the shared recovery implementation preserves the
A1 `OK`, `DEGRADED`, and `BOUNDED` semantics.

## Interpretation

This is a product-layer refactor, not a memory-architecture change.

The CLI and upcoming FastAPI service can now share one configuration source and
one startup recovery implementation.

## Decision

ADOPT the shared configuration and lifecycle modules.

Keep configuration deliberately small and standard-library based.

Do not add dotenv, pydantic-settings, queues, schedulers, or other infrastructure
without a concrete A2 requirement.

## Architecture Impact

The daily-use runtime now has reusable foundations:

runtime configuration
→ model client

runtime configuration
→ shared startup lifecycle
→ CLI / future API

A1 Evidence Recall and persistence semantics remain unchanged.

## Open Questions

The next question is how the FastAPI service should expose runtime health,
startup recovery state, chat turns, and minimal session information.

## Next Step

Checkpoint these changes, then add the FastAPI lifecycle and stable backend
health/status contract.
