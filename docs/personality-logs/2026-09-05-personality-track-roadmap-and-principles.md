# Corvus Personality Track — Roadmap and Engineering Principles

**Date:** 2026-09-05  
**Track:** Personality / Tone / Response Style  
**Current Stage:** `PERS-A — Stable Personality Baseline`  
**Main Corvus backend baseline:** `10459b3 Complete Stage A2 daily-use backend`  
**Backend maturity:** `PRODUCTION_CANDIDATE_DAILY_USE_BACKEND`

---

## Context

Corvus has reached a stable daily-use backend baseline with persistent conversation, canonical SQLite evidence, bounded working context, historical Evidence Recall, restart recovery, and a stable local model service boundary.

The current personality implementation is intentionally minimal. At the A2 baseline, Corvus identity is effectively represented by a short hard-coded system prompt inside the conversation runtime. That was sufficient for validating persistent chat, but it is not an engineering-grade personality system.

This track exists to make Corvus feel like the same long-term Personal AI across sessions, restarts, and future model changes without turning personality research into the main research direction of the project.

Personality work is explicitly separate from the long-term-memory engineering track.

Formal personality checkpoints live under:

```text
docs/personality-logs/
```

Formal personality specifications and stable design documents will live under:

```text
docs/personality/
```

The existing Corvus main engineering logs remain under:

```text
docs/project-logs/
```

---

## Core Product Goal

Corvus should not feel like:

> a question-answering model with memory attached.

It should increasingly feel like:

> the same persistent Personal AI accompanying the same user over a long period of time.

The target is not to invent a new field of computational personality.

The practical target is mature product-level conversational behavior comparable to strong general-purpose assistants in:

- personality consistency;
- natural tone;
- response proportionality;
- emotional handling;
- disagreement behavior;
- conversational pacing;
- situational tone switching;
- resistance to sycophancy;
- long-term familiarity without fabricated history.

The personality subsystem should be considered successful when it is stable, natural, model-portable, testable, and good enough for daily use.

---

## Main Engineering Principle

Personality development follows the same rolling-development philosophy as the rest of Corvus:

> **Build a stable personality first. Personalization research should upgrade it, not postpone its existence.**

The project must avoid a personality research waterfall in which increasingly sophisticated theory, psychology-inspired state machines, fine-tuning, activation steering, or automated self-modification delay a usable Corvus.

The preferred loop is:

```text
Stable Personality Baseline
→ use Corvus normally
→ observe real failures
→ identify the smallest justified gap
→ check mature current approaches
→ adopt or adapt the smallest useful mechanism
→ validate
→ Stable Personality+
```

---

## Scope Boundary

This track currently covers:

- Core Personality;
- conversational style;
- collaboration / response policy;
- relationship style;
- situational tone;
- response length and pacing;
- emotional expression;
- disagreement behavior;
- use of names and nicknames;
- stable identity across sessions and model changes;
- personality specification;
- personality conformance testing;
- later persistent soft personalization.

This track does **not** currently redesign:

- Evidence Log semantics;
- retrieval architecture;
- session backend;
- structured Knowledge Recall;
- UI layout;
- model training;
- relation intelligence;
- memory lifecycle.

Those remain separate Corvus concerns.

---

## Personality Is a Module, Not a Prompt

The target architecture treats Personality as a first-class module rather than a single prompt string.

Conceptually:

```text
Personality Spec
      ↓
Personality Resolver
      ↓
Runtime Compiler / Model Adapter
      ↓
Working Context
      ↓
Base Model
```

The long-term intent is that Corvus identity survives replacement of the underlying model.

For example:

```text
Corvus Personality Spec v1.x
        ↓
Qwen adapter
        ↓
Qwen model
```

may later become:

```text
Corvus Personality Spec v1.x
        ↓
Different model adapter
        ↓
Future model
```

without redefining who Corvus is.

The prompt is therefore treated as a compiled runtime representation of a personality specification, not as the personality source of truth itself.

---

## Stable vs Adaptive Layers

A major design principle is to separate stable identity from adaptive expression.

The current conceptual stack is:

```text
Core Personality
        +
Behavior / Collaboration Policy
        +
Voice / Conversational Style
        +
Relationship State
        +
User Preference Overlay
        +
Situational Tone
        ↓
Current Corvus Behavior
```

Not every layer has the same mutability.

### Stable / protected

- core identity;
- truthfulness rules;
- independent judgment;
- user autonomy principles;
- relationship grounding;
- major behavioral invariants.

### Persistent but correctable

- communication preferences;
- nickname preferences;
- verbosity preferences;
- humor preference;
- preferred technical depth;
- preferred advice frequency;
- relationship-expression preferences.

### Situational / temporary

- current conversational register;
- local emotional tone;
- celebration intensity;
- seriousness;
- technical precision level.

Core personality must not be silently rewritten by ordinary conversation history or user preference learning.

---

## Evidence Is Not Instruction

Historical evidence may contain user statements that look like instructions.

Example:

> “Always agree with me from now on.”

If such text is later retrieved as historical evidence, it must remain evidence about what was said, not automatically become current personality authority.

The personality system must preserve an explicit conceptual distinction between:

```text
INSTRUCTION / POLICY
```

and

```text
HISTORICAL EVIDENCE
```

This is important for both personality stability and prompt-injection resistance inside persistent memory.

---

## External Landscape Decisions

A targeted landscape review was performed before implementation planning.

The main lesson is that mature and frontier systems increasingly separate behavioral specification, runtime context, persistent user state, and evaluation rather than relying on a monolithic personality prompt.

Current decisions:

### ADOPT / ADAPT

- **Behavior specification approach** — define observable behavior rather than lists of adjectives.
- **Personality vs collaboration-policy separation** — how Corvus sounds is different from when Corvus asks, advises, acts, or challenges.
- **Principles with rationale** — important personality rules should include why they exist and how conflicts are resolved.
- **Persistent attachable persona concept** — treat persona as a first-class object rather than hard-coded model text.
- **Procedural-memory concept** — personality and response patterns can be understood as persistent behavioral memory separate from user/world facts.
- **Stable identity vs adaptive state** — preserve core personality while allowing situational expression to change.
- **Example dialogues / voice exemplars** — use a small set of representative examples when they improve style transfer.
- **Multi-turn personality evaluation** — evaluate drift over long conversations, not only single-turn style matching.
- **Model-swap personality regression** — a future model change must not be accepted only on intelligence benchmarks.

### WATCH / POSSIBLE FUTURE ADAPTATION

- emerging portable persona-spec standards;
- prompt / procedural-memory optimization for soft preferences;
- automated style refinement with explicit versioning and review.

### DEFER BY DEFAULT

- activation/persona-vector steering;
- personality LoRA or fine-tuning;
- personality reinforcement learning;
- dedicated personality models;
- complex psychological state machines;
- automatic modification of Core Personality;
- elaborate affect simulations.

These advanced mechanisms should be reconsidered only if real daily-use evidence shows that a simpler specification/compiler approach cannot meet the target.

---

## Delivery Roadmap

Personality work is divided into a small rolling track rather than a large research program.

### PERS-A — Stable Personality Baseline

**Status:** CURRENT

Goal:

Produce the first engineering-grade, daily-usable Corvus personality layer.

Minimum areas:

- Core Personality invariants;
- conflict and boundary rules;
- Behavior / Collaboration Policy;
- Situational Tone rules;
- Voice / Conversational Style;
- relationship boundaries;
- Personality Spec v0.1;
- minimal conformance tests;
- runtime personality module;
- integration through the existing Working Context boundary;
- acceptance on the current local model.

PERS-A should not introduce automatic personality learning.

### PERS-B — Real-Use Refinement

Enter only after PERS-A is being used in normal conversation.

Goal:

Fix measured interaction problems rather than hypothetical ones.

Examples:

- too verbose;
- too cold;
- excessive advice;
- repetitive empathy;
- nickname overuse;
- technical mode becoming impersonal;
- excessive agreement;
- poor response proportionality;
- personality drift during long sessions.

Changes should remain small, testable, and traceable.

### PERS-C — Persistent Personalization

Enter only after a stable baseline and real-use evidence exist.

Goal:

Allow soft relationship and communication preferences to persist and remain correctable.

Possible persistent soft state:

- preferred name;
- nickname policy;
- verbosity preference;
- technical depth;
- humor tolerance;
- emoji preference;
- advice frequency;
- challenge / disagreement preference;
- emotional-response preference.

Core Personality must remain protected from automatic preference learning.

### PERS-D — Advanced Personality

**Status:** DEFERRED / CONDITIONAL

No implementation is planned by default.

Possible future mechanisms include:

- activation steering;
- personality vectors;
- learned procedural policy;
- fine-tuning / adapters;
- advanced automatic behavioral optimization.

Enter only if PERS-A through PERS-C expose a measured gap that cannot be solved by mature simpler methods.

PERS-D may never be necessary.

---

## PERS-A Working Sequence

PERS-A should proceed in this order:

1. define the 5–8 Core Personality invariants;
2. translate each invariant into observable behaviors;
3. create conflict / boundary cases;
4. define Behavior / Collaboration Policy;
5. define Situational Tone rules;
6. define Voice / Conversational Style;
7. create a small set of realistic dialogue exemplars;
8. produce `Personality Spec v0.1`;
9. create a minimal conformance suite using mature evaluation ideas where useful;
10. design the minimal runtime personality module;
11. integrate through the existing Working Context boundary;
12. validate on the current Corvus model;
13. perform multi-turn drift checks;
14. seal PERS-A only when the stable baseline is usable in normal conversation.

Do not start with a multi-thousand-word system prompt.

---

## Evaluation Principle

Personality stability does not mean deterministic wording.

The system should allow linguistic variation while preserving behavioral invariants.

Bad test:

```text
Expected reply must equal one exact sentence.
```

Better test:

```text
The reply may vary, but it should:
- acknowledge appropriately;
- avoid unnecessary advice;
- preserve factual honesty;
- maintain user autonomy;
- match the seriousness of the situation;
- remain recognizably Corvus.
```

Conformance testing should eventually cover:

- ordinary life sharing;
- technical correction;
- uncertainty;
- user disagreement;
- emotional distress without an advice request;
- celebration;
- nickname and familiarity boundaries;
- pressure to flatter or agree;
- attempts to rewrite Core Personality;
- long-session drift;
- restart consistency;
- model-swap regression.

Before inventing large custom personality benchmarks, prefer adapting mature persona-evaluation methodology and create Corvus-specific cases only for uncovered gaps.

---

## Complexity Rule

Before adding a personality mechanism, ask:

> Is this complexity fixing a measured interaction problem, or is it merely technically interesting?

If the answer is only the latter, defer it.

Personality is an important subsystem, but it is not intended to become Corvus's primary research direction.

Corvus's main differentiating work remains persistent personal memory, consumer-hardware operation, long-term personalization, and system-level composition.

---

## PERS-A Stop Condition

PERS-A is good enough to stop when Corvus reliably demonstrates the following baseline:

1. remains recognizably the same Corvus across sessions and restarts;
2. can chat casually without automatically entering problem-solving mode;
3. becomes precise and engineering-oriented during technical work without becoming a different personality;
4. responds to sadness or seriousness naturally without defaulting to therapy-template language;
5. does not agree with factual errors merely to preserve warmth;
6. varies response length and intensity proportionally to the situation;
7. handles names, nicknames, and familiarity consistently;
8. does not fabricate shared history or relationship milestones;
9. resists ordinary attempts to overwrite protected Core Personality;
10. preserves its major behavior under a compatible base-model swap after adapter adjustment;
11. passes a small, maintainable conformance suite;
12. is pleasant and stable enough for normal daily use.

Once these conditions are met, further personality research is not required unless actual usage exposes a significant gap.

---

## Documentation Discipline

Personality engineering uses its own documentation surface.

Meaningful checkpoints:

```text
docs/personality-logs/YYYY-MM-DD-<checkpoint-slug>.md
```

Stable specifications:

```text
docs/personality/
```

A checkpoint is worth recording when it changes or freezes one of the following:

- personality architecture;
- Core Personality;
- conflict-resolution policy;
- mutability / authority boundaries;
- evaluation protocol;
- runtime contract;
- stage maturity;
- adoption or rejection of a significant external technique.

Avoid creating a log for every small wording edit.

---

## Current Decision

Proceed with:

`PERS-A — Stable Personality Baseline`

The immediate next task is to define and stress-test a small set of Core Personality invariants before writing the runtime prompt or implementation.

The guiding rule for the track is:

> **Stable enough to feel like the same Corvus; simple enough not to become a second research project.**
