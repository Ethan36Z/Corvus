# Demo Corvus Clean Public Baseline

Date: 2026-09-07

## Context

Demo Corvus had passed local isolation, FoxGate authentication, public HTTPS acceptance, and real browser recruiter-path acceptance.

The Demo Evidence Log still contained two messages created solely for the earlier Private/Demo isolation test.

Those test messages were useful engineering evidence but were not appropriate as recruiter-facing product content.

## Decision

Reset Demo canonical and derived memory to a clean zero-message baseline before final deployment sealing.

Private Corvus data was not modified.

## Procedure

The Demo API was stopped before resetting runtime data.

Only this directory was recreated:

/home/ethan/srv/data/corvus/demo

The Demo SQLite schema was initialized from the current Corvus code.

The Demo LanceDB derived index was initialized from the empty canonical Evidence Log.

The Demo API was then restarted.

## Acceptance

Demo SQLite integrity: OK

Demo messages after reset: 0

Demo API: healthy

Demo Web: healthy

Public Demo unauthenticated access: HTTP 401

Private messages before reset: 52

Private messages after reset: 52

Therefore the recruiter-facing Demo now starts from a clean canonical-memory baseline while Private Corvus remains unchanged.

## Status

DEMO_CLEAN_BASELINE_PASSED

## Next Step

Verify the clean state through the real browser recruiter path, then perform full-host reboot recovery acceptance before sealing Demo Corvus deployment.
