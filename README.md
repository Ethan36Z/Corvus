# Corvus

### Persistent Personal AI on Consumer Hardware

Corvus is a self-hosted personal AI system designed to remain useful across long periods of interaction while running on fixed consumer hardware.

The project explores a simple question:

> **How far can a local 9B model be pushed through better system architecture instead of simply increasing model size?**

Corvus combines persistent conversation history, hybrid memory retrieval, context construction, a model-portable personality layer, multimodal vision, and production-style deployment around a local Qwen model running on an RTX 2080 Ti with 11 GB of VRAM.

The goal is not to build the largest model.

The goal is to build a personal AI that can **remember, continue, adapt, and remain usable over time**.

---

## Live Demo

**Demo:**  
https://demo-corvus.foxluma.com/

**Username:** `demo`  
**Password:** `0321`

The public demo is isolated from the private Corvus deployment and uses a separate canonical memory store.

Demo conversations are periodically reset to a clean baseline.

---

## At a Glance

Corvus currently supports:

- persistent multi-session conversation
- restart-safe conversation continuity
- SQLite canonical Evidence Log
- bounded recent conversation context
- hybrid long-term Evidence Recall
- BM25 / FTS5 sparse retrieval
- multilingual dense retrieval
- Reciprocal Rank Fusion
- persistent LanceDB dense index
- incremental dense indexing and crash recovery
- inspectable retrieved evidence
- model-portable personality runtime
- personality conformance testing
- PNG / JPEG image understanding
- canonical attachment provenance
- React / TypeScript web UI
- mobile-friendly web interaction
- FastAPI backend
- local `llama.cpp` inference
- isolated Private and Demo deployments
- authenticated remote access through FoxLuma

Current base model:

```text
Qwen3.5-9B-Q5_K_M.gguf
```

Reference hardware:

```text
GPU: NVIDIA RTX 2080 Ti — 11 GB VRAM
CPU: AMD Ryzen 7 3700X
RAM: 32 GB
OS: Linux Mint 22.3
```

---

# Why Corvus Exists

Most improvements in AI capability are associated with larger models and larger compute budgets.

Corvus explores another direction:

```text
Fixed Local Model
        +
Persistent Evidence
        +
Selective Recall
        +
Context Construction
        +
Stable Personality
        +
Background / System Orchestration
        =
A More Capable Personal AI System
```

The project is intentionally constrained to consumer hardware.

That constraint forces architectural questions that become less visible when compute is effectively unlimited:

- What should be remembered?
- What should be retrieved?
- What should enter the active prompt?
- What should remain canonical evidence?
- What can be rebuilt?
- When is model intelligence worth spending?
- How can personality remain stable across model changes?
- How much complexity is actually justified by real use?

---

# Current Architecture

The current daily-use conversation path is:

```text
User
 │
 ▼
FastAPI / Conversation Runtime
 │
 ├── Canonical user message → SQLite
 │
 ├── Recent Conversation Context
 │
 ├── Hybrid Historical Evidence Recall
 │      │
 │      ├── FTS5 / BM25
 │      │
 │      └── GTE multilingual embeddings
 │              ↓
 │           LanceDB
 │              ↓
 │        exact vector search
 │
 │      sparse + dense
 │            ↓
 │            RRF
 │            ↓
 │     canonical SQLite hydration
 │
 ├── Personality Runtime
 │
 ├── Optional Vision Input
 │
 ▼
Working Context
 │
 ▼
llama.cpp
 │
 ▼
Qwen3.5-9B
 │
 ▼
Assistant Response
 │
 ├── Canonical SQLite persistence
 │
 └── Incremental dense-index synchronization
```

A derived-index failure must never cause canonical conversation loss.

SQLite is written first.

---

# Memory Architecture

Corvus separates memory into three concepts:

```text
Evidence Log
    ↓
Working Context
    ↓
Materialized Memory
```

## 1. Evidence Log

The Evidence Log is the canonical source of truth.

Current implementation:

```text
SQLite messages
```

Raw conversation experience is preserved before derived interpretation.

Corvus does not use a KEEP / DROP gate to decide whether the original experience deserves to exist.

---

## 2. Working Context

Working Context is the small, active context constructed for the current model call.

It can contain:

- recent conversation
- relevant historical evidence
- current task context
- personality policy
- multimodal input
- future structured memory

Working Context is deliberately bounded and rebuildable.

---

## 3. Materialized Memory

Materialized Memory represents derived understanding such as:

- assertions
- temporal validity
- provenance
- authority
- supersession
- relations
- current-world projections

Structured-memory foundations already exist in the repository, but the current daily-use path deliberately relies primarily on **Evidence Recall**.

Derived knowledge is not allowed to silently replace canonical evidence.

This keeps Corvus able to answer:

> **What did the user actually say?**

even if a later interpretation is wrong.

---

# Hybrid Evidence Recall

The productionized Evidence Recall path is:

```text
                  SQLite Evidence Log
                         │
                 ┌───────┴───────┐
                 │               │
                 ▼               ▼
           FTS5 / BM25      GTE multilingual
             sparse            dense
                                   │
                                   ▼
                                LanceDB
                                   │
                              exact search
                 │               │
                 └───────┬───────┘
                         ▼
                        RRF
                         ▼
                SQLite hydration
                         ▼
                  Working Context
```

Dense embeddings use:

```text
Alibaba-NLP/gte-multilingual-base
dimension = 768
```

The dense index is persistent and incrementally synchronized.

Corvus distinguishes canonical data from derived search infrastructure:

```text
SQLite = truth
LanceDB = rebuildable retrieval state
```

---

# Persistent Conversation

Stage A1 turned the retrieval system into a complete persistent conversation loop.

The runtime guarantees:

```text
user message
→ canonical SQLite commit
→ recent context
→ historical recall
→ Working Context
→ local model
→ assistant response
→ canonical SQLite commit
→ derived index sync
```

Conversation state survives process restarts.

A later session can paraphrase a fact from an earlier session and retrieve the original evidence through the hybrid recall path.

---

# Daily-Use Backend

Stage A2 converted the persistent runtime into an inspectable HTTP service suitable for daily use.

The backend supports:

- persistent HTTP chat
- service and model health reporting
- startup dense-index recovery
- session listing
- session resume
- canonical transcript reload
- historical memory inspection
- restart-and-continue conversation behavior

Stage A2 maturity:

```text
PRODUCTION_CANDIDATE_DAILY_USE_BACKEND
```

This maturity applies to the single-user Corvus backend, not to a general multi-user SaaS product.

---

# Personality System

Corvus treats personality as an engineering subsystem rather than a long list of adjectives inside one prompt.

The personality architecture is:

```text
Personality Specification
        ↓
Personality Resolver / Compiler
        ↓
Compact Runtime Policy
        ↓
Working Context
        ↓
Model Adapter
        ↓
Base Model
```

The personality layer is deliberately separate from:

- memory storage
- retrieval
- session management
- UI
- model transport

This means changing the base model should not require redefining who Corvus is.

The current **PERS-A** personality baseline is sealed.

Its core behavioral principles include:

- **Truth Before Approval**
- **Care Without Taking Over**
- **Respect for User Agency**
- **Independent Judgment, Open Revision**
- **Grounded Relationship Continuity**
- **Stable Identity, Adaptive Expression**
- **Proportionate, Non-Performative Presence**

PERS-A also has runtime contract tests and behavioral conformance tests covering cases such as:

- truth vs. approval
- empathy without agreement
- casual conversation without unwanted advice
- technical directness
- uncertainty calibration
- low-mood interaction
- tone switching
- relationship continuity
- personality drift
- historical evidence attempting to override current instructions

The design goal is:

> **A recognizable Corvus across sessions and compatible model changes.**

---

# Vision v1

Corvus A3 added image perception without creating a separate multimodal conversation system.

Current flow:

```text
Image selected
      ↓
Attachment upload
      ↓
Canonical attachment identity
      ↓
User message persisted
      ↓
Attachment linked to message
      ↓
Transient multimodal model input
      ↓
Existing Corvus conversation runtime
      ↓
Assistant response
```

Vision v1 currently supports:

- one image per turn
- PNG
- JPEG
- text + image interaction
- local browser preview
- canonical attachment metadata
- Private deployment
- Demo deployment
- real Qwen vision inference

Model-facing image size is currently limited to 16 MiB.

Images remain associated with canonical conversation messages, while raw image bytes are managed separately from permanent conversational evidence.

The architectural rule is:

> **Evidence first. Perception second.**

Vision is currently a perception channel, not a separate memory architecture.

---

# Web Interface

Corvus includes a React + TypeScript interface built with Vite.

The UI supports:

- persistent sessions
- session switching
- conversation history
- memory inspection
- responsive mobile layout
- image upload and preview
- canonical image rendering after reload

The same backend contract is intended to support future native clients.

A native iPhone / iPad client is planned but is not yet implemented.

---

# Deployment

Corvus currently runs in two isolated environments:

```text
Private Corvus
Demo Corvus
```

They share:

- source code
- architecture
- local model runtime

They do **not** share:

- authentication realms
- canonical SQLite history
- LanceDB retrieval indexes
- persistent user data

Public Demo architecture:

```text
Internet
   ↓
Cloudflare HTTPS
   ↓
Cloudflare Tunnel
   ↓
FoxGate
   ↓
Corvus Web
   ↓
Corvus FastAPI
   ↓
Local llama.cpp
   ↓
Qwen3.5-9B
```

The local model endpoint and database services are not directly exposed to the public Internet.

The Demo environment is automatically returned to a clean baseline on a scheduled reset, with explicit safeguards preventing the reset process from targeting Private Corvus data.

---

# Engineering Philosophy

Corvus follows several rules.

### Always maintain a working Corvus

Research should upgrade the product, not postpone its existence.

```text
Working Corvus
→ use it
→ observe failures
→ identify the highest-value gap
→ add the smallest justified capability
→ validate
→ Working Corvus+
```

### Architecture is guilty until benchmarked

Complexity is not automatically an improvement.

Do not add:

- rerankers
- ANN indexes
- extra models
- gates
- background workers
- summarization layers
- multi-agent systems

simply because they appear in an architecture diagram.

Add them when a measured problem requires them.

### Store all experience. Spend intelligence selectively.

Canonical evidence is cheap to preserve.

Model reasoning is expensive.

Corvus separates the two.

### Freeze the goal, not the implementation

Long-term capabilities may remain stable while implementation choices change as technology improves.

---

# Current Project Status

| Area | Status |
|---|---|
| Local Qwen runtime | ✅ Working |
| Persistent Evidence Log | ✅ Working |
| Hybrid Evidence Recall | ✅ A0 sealed |
| Persistent conversation loop | ✅ A1 sealed |
| Daily-use backend | ✅ A2 complete |
| Web UI | ✅ Deployed |
| Mobile-responsive web UI | ✅ Deployed |
| Personality baseline | ✅ PERS-A sealed |
| Private remote deployment | ✅ Deployed |
| Recruiter Demo deployment | ✅ Deployed |
| Vision v1 | ✅ Complete |
| Native iOS / iPadOS client | ⏳ Planned |
| Voice interaction | ⏳ Planned |
| Knowledge Recall integration | 🧪 Existing foundation / intentionally deferred |
| Background consolidation | 🧪 Evidence-driven future work |
| Adaptive recall | 🧪 Future |
| Multi-agent | 🧪 Long-term / conditional |

---

# Repository Structure

```text
app/
    conversation runtime, API, model integration, vision

memory/
    canonical storage, sparse retrieval, dense retrieval,
    hybrid recall, temporal and structured-memory foundations

personality/
    personality runtime and compiler

playground/
    React / TypeScript web interface

tests/
    runtime and contract validation

benchmarks/
    retrieval, memory, and experimental benchmarks

docs/
    architecture records
    phase reports
    project logs
    personality specifications
    deployment logs
    roadmaps

deploy/
    production deployment configuration and systemd assets

compose.corvus.yml
compose.corvus.demo.yml
```

---

# Key Design Documents

For deeper engineering context:

- [`docs/roadmaps/corvus-capability-and-delivery-roadmap-v2.md`](docs/roadmaps/corvus-capability-and-delivery-roadmap-v2.md)
- [`docs/phase-reports/phase-a0-retrieval-productionization.md`](docs/phase-reports/phase-a0-retrieval-productionization.md)
- [`docs/phase-reports/stage-a1-persistent-conversation-loop.md`](docs/phase-reports/stage-a1-persistent-conversation-loop.md)
- [`docs/phase-reports/stage-a2-daily-use-baseline.md`](docs/phase-reports/stage-a2-daily-use-baseline.md)
- [`docs/personality/personality-spec-v0.1.md`](docs/personality/personality-spec-v0.1.md)
- [`docs/project-logs/2026-09-08-a3-vision-v1-web-interaction.md`](docs/project-logs/2026-09-08-a3-vision-v1-web-interaction.md)
- [`docs/deployment-logs/2026-09-05-foxluma-deployment-security-baseline.md`](docs/deployment-logs/2026-09-05-foxluma-deployment-security-baseline.md)

---

# Near-Term Direction

The next phase of Corvus is intentionally driven by real daily use rather than architecture for its own sake.

Current areas of interest include:

- native mobile access
- voice interaction
- longer-term personality evaluation
- real-world memory failure logging
- background cognition during idle compute
- selective structured-memory integration when Evidence Recall is insufficient

The project will continue to prefer measured user-facing value over architectural complexity.

---

# Project Goal

Corvus is ultimately trying to answer:

> **Can a modest local model become a genuinely useful long-term personal AI when the system around the model is designed carefully enough?**

The experiment is ongoing.

But Corvus is no longer only an experiment.

It is already a working persistent personal AI running on consumer hardware.
