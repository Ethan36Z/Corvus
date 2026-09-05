# PERS-A — Stable Personality Baseline Kickoff

## Context

Corvus Stage A2 has been sealed as a `PRODUCTION_CANDIDATE_DAILY_USE_BACKEND`.

The current runtime has only a minimal hard-coded system prompt describing Corvus as a persistent personal AI. That is sufficient for persistent-chat validation but is not yet an engineering-grade personality subsystem.

Personality work is intentionally separated from the long-term memory research track. Formal personality checkpoints will live under:

`docs/personality-logs/`

Formal personality specifications will live under:

`docs/personality/`

This avoids mixing personality engineering records with the existing memory/retrieval project logs and phase reports.

## Research / Engineering Question

What is the smallest stable, model-portable personality foundation that can make Corvus feel like the same long-term Personal AI across sessions, restarts, situations, and future model changes without turning personality into a major research program?

## Starting Hypothesis

Corvus should treat personality as a first-class modular behavioral subsystem rather than a large monolithic prompt.

The initial subsystem should separate:

- stable core identity;
- conversational / collaboration policy;
- voice and expression style;
- relationship boundaries;
- situational tone adaptation;
- later user-specific soft personalization.

The runtime prompt should be treated as a compiled representation of the personality specification, not as the personality source of truth.

## What We Did

Before implementation, we:

- audited the Stage A2 conversation runtime and Working Context boundary;
- confirmed that the current personality layer is only a small placeholder system prompt;
- reviewed current public work and frameworks covering model behavior specifications, constitutions, procedural memory, persistent persona objects, portable character/persona definitions, persona consistency evaluation, and long-dialogue personality drift;
- confirmed that a modular personality layer can be inserted without changing Corvus Evidence Log, retrieval, session backend, or UI layout;
- adopted the same rolling-development discipline used by the wider Corvus project.

## Evidence / Results

The current Corvus architecture already has a clean boundary:

`process_turn -> Working Context -> model client`

This allows personality policy to be resolved and compiled before Working Context assembly while keeping the underlying model replaceable.

The external landscape also supports several useful patterns:

- behavior specifications are more robust than lists of adjectives;
- stable identity should be separated from situational adaptation;
- persistent agent persona can be treated as a first-class state object;
- personality / behavioral policy can be understood as procedural memory;
- example dialogues are useful for voice calibration;
- multi-turn drift testing is necessary for long-lived persona consistency.

## Interpretation

Corvus should not make personality research a primary innovation track.

The goal is to reach a mature product-level interaction experience comparable in quality to strong general-purpose assistants for personality, tone, and conversational behavior, while keeping Corvus-specific innovation focused on persistent personal memory and long-term personalization on consumer hardware.

The personality track therefore follows:

`stable baseline -> real use -> measured problems -> smallest justified upgrade`

not:

`large personality research program -> eventual integration`

## Decision

Create a dedicated personality track with the following delivery stages:

### PERS-A — Stable Personality Baseline

Current stage.

Deliver the smallest stable personality foundation that is usable in daily conversation.

### PERS-B — Real-Use Refinement

Use real conversation traces to fix proven style and behavior problems.

### PERS-C — Persistent Personalization

Allow stable user-specific soft preferences and relationship style to persist without allowing automatic mutation of Core Personality.

### PERS-D — Advanced Personality

Deferred by default.

Activation steering, personality fine-tuning, LoRA personality, automated personality evolution, psychological state machines, or other advanced mechanisms will be considered only if real-use evidence proves that the simpler baseline is insufficient.

## Architecture Impact

Personality becomes a planned first-class Corvus subsystem, but no runtime code is changed at this checkpoint.

Target conceptual boundary:

`Personality Spec -> Personality Resolver -> Runtime Compiler / Model Adapter -> Working Context`

Core personality remains independent of the current base model.

Memory architecture remains unchanged.

## PERS-A Scope

PERS-A will define and validate only:

1. Core Personality invariants;
2. collaboration / response policy;
3. situational tone behavior;
4. voice and expression style;
5. relationship boundaries;
6. a compact versioned Personality Spec;
7. a minimal runtime compiler / adapter boundary;
8. a small conformance and multi-turn drift test set.

## Explicit Non-Goals

PERS-A will not introduce:

- personality fine-tuning;
- LoRA personality training;
- activation steering;
- automatic Core Personality learning;
- complex psychological state simulation;
- a separate personality model;
- a large custom personality benchmark;
- changes to Evidence Log, retrieval, session backend, or UI layout.

## Exit Condition

PERS-A is complete when Corvus can demonstrate a stable, natural, model-portable personality baseline that:

- remains recognizably the same across sessions and restarts;
- shifts register appropriately between casual, technical, serious, emotional, and celebratory contexts;
- does not confuse empathy with agreement;
- does not automatically turn ordinary sharing into advice;
- maintains stable relationship boundaries;
- preserves its core behavior under reasonable multi-turn pressure;
- can be applied to the current local model through a small runtime adapter;
- has a compact regression suite sufficient to catch obvious personality drift.

Once this condition is met, personality engineering pauses and Corvus returns to real use before PERS-B.

## Open Questions

- Which 5–8 Core Personality invariants make Corvus recognizably Corvus?
- Which behaviors belong to immutable core identity versus editable style?
- How much variation should be allowed while still counting as personality consistency?
- What is the smallest useful conformance suite for the local 9B runtime?

## Next Step

Define the PERS-A Core Personality invariants as observable behavioral contracts rather than adjective lists.
