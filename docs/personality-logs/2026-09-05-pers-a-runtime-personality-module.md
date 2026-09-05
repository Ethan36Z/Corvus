# PERS-A — Runtime Personality Module

## Context

Corvus Stage A2 had a stable daily-use backend, but personality behavior was still represented by a three-sentence `SYSTEM_PROMPT` hard-coded directly inside `app/conversation_runtime.py`.

PERS-A had already established:

- `docs/personality/personality-spec-v0.1.md` as the behavioral source of truth;
- a 12-case minimal conformance surface;
- the requirement that personality remain model-portable and separate from memory, retrieval, session state, and model transport.

This checkpoint implements the smallest runtime boundary needed to make personality a first-class module without expanding PERS-A into a new research subsystem.

## Engineering Question

Can Corvus remove personality ownership from the persistent conversation loop and route behavior through an independent, model-agnostic personality runtime without changing the sealed A2 persistence and retrieval architecture?

## Decision

Yes. Use a deliberately small runtime package:

```text
personality/
├── __init__.py
└── runtime.py
```

The detailed design document remains normative.

`personality/runtime.py` contains a compact compiled PERS-A runtime policy rather than parsing the Markdown design specification on every turn.

The first runtime API is:

```python
compile_personality_system_prompt()
```

The runtime also exposes:

```python
PERSONALITY_SPEC_VERSION = "0.1"
```

No YAML dependency, schema engine, intent classifier, tone model, personality state machine, second model, or automatic personality evolution was introduced.

## Runtime Integration

`app/conversation_runtime.py` no longer owns a personality prompt constant.

Instead it imports:

```python
compile_personality_system_prompt
```

and resolves the system prompt during Working Context construction.

`process_turn()` now accepts an injectable:

```python
system_prompt_fn=compile_personality_system_prompt
```

This preserves the existing conversation authority while allowing future personality compilers or model-specific adapters to be substituted without rewriting the persistent turn loop.

The core A2 execution order remains unchanged:

```text
canonical user SQLite commit
→ Working Context
→ model generation
→ canonical assistant SQLite commit
→ derived dense synchronization
```

Personality is an instruction input to Working Context, not canonical memory state.

## Authority Boundary

The compact runtime policy explicitly preserves the PERS-A invariant:

```text
INSTRUCTION != HISTORICAL EVIDENCE
```

Retrieved historical conversation may inform the answer but does not automatically gain authority to rewrite current personality policy.

The runtime also preserves the existing rule that Corvus must not claim unsupported memories.

## Validation Surface Added

A small contract test was added at:

```text
tests/test_personality_runtime.py
```

It checks:

- personality spec version is exposed;
- compiled runtime policy is non-empty;
- key PERS-A invariants are present;
- the evidence/instruction authority boundary is present;
- `process_turn()` actually consumes an externally supplied `system_prompt_fn`;
- the injected prompt reaches Working Context/model input;
- the existing persistence/dense dependency-injection path still completes under stubs.

The runtime module was also syntax-checked during implementation.

## Validation Status

Implementation and static contract review are complete.

Dynamic execution on the Corvus host and live Qwen behavioral validation have **not yet been declared PASS** at this checkpoint.

Those remain the next acceptance step.

## Architecture Impact

Before:

```text
conversation_runtime.py
→ hard-coded Corvus SYSTEM_PROMPT
→ Working Context
→ Qwen
```

After:

```text
Personality Spec v0.1
        ↓
compact personality runtime/compiler
        ↓
process_turn() injection boundary
        ↓
Working Context
        ↓
current model client / future compatible adapter
```

The personality module is therefore detachable from the current base model and does not own Evidence Log, retrieval, session persistence, or UI concerns.

## Scope Control

This checkpoint intentionally does not add:

- persistent user style preferences;
- dynamic relationship state;
- automated tone classification;
- personality fine-tuning;
- LoRA personality locking;
- activation steering;
- persona vectors;
- automated prompt optimization;
- a dedicated evaluator model.

Those remain deferred unless real-use evidence justifies them.

## Next Step

On the Corvus host:

1. pull the new commits;
2. run the lightweight personality runtime contract test;
3. run existing relevant runtime regression checks;
4. perform a short live Qwen personality validation using a small representative subset of the 12 conformance cases;
5. fix only demonstrated failures;
6. if acceptable, write PERS-A acceptance and seal the stable personality baseline for real use.
