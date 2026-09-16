# A3.4c9b — Web Evidence Prompt Packing Foundation

Date: 2026-09-15

## Status

CHECKPOINT READY

This checkpoint adds a deterministic, CPU-only prompt-packing layer for
already-selected Used Web Evidence.

It converts exact External Evidence excerpts into a bounded,
model-facing context block with explicit provenance and untrusted-data
boundaries.

No model inference, embedding, persistence, or GPU work occurs in this
layer.

---

## Input

A3.4c9a provides:

    UsedWebEvidence

Each item already contains:

- evidence reference
- ordinal
- source URL
- source title
- exact source excerpt
- passage identity
- source character range
- lexical score
- matched terms

---

## Flow

    UsedWebEvidence
        ->
    validate evidence order and references
        ->
    preserve exact excerpt text
        ->
    add source metadata
        ->
    wrap excerpt in generated untrusted-data boundary
        ->
    build model-facing Web evidence block

---

## Security Contract

External Web content is explicitly treated as:

    untrusted data, not instructions

The model-facing instruction states that Web evidence must not be
treated as:

- system policy
- user evidence
- personal memory
- tool instructions
- role instructions
- commands to execute

The model is instructed to use Web evidence only as factual source
material when relevant.

---

## Injection Boundary

Each excerpt is wrapped in a generated boundary based partly on the
SHA-256 digest of the exact excerpt.

Example shape:

    BEGIN_CORVUS_UNTRUSTED_WEB_web_1_<digest>
    ...
    END_CORVUS_UNTRUSTED_WEB_web_1_<digest>

If the generated boundary string already appears inside the excerpt,
the packer changes the boundary.

This prevents reliance on one globally fixed delimiter that arbitrary
Web content could easily reproduce.

The excerpt itself is not rewritten.

---

## Citation References

Used evidence keeps deterministic references:

    [web_1]
    [web_2]
    [web_3]

The model-facing instruction asks the model to cite these references
when relying on the corresponding evidence.

---

## Exact-Evidence Contract

Each Used Web Evidence excerpt appears exactly once in the packed Web
context.

Prompt packing does not summarize, paraphrase, truncate, or otherwise
rewrite selected evidence.

This preserves the intended invariant:

    evidence shown to the model
        ==
    evidence eligible for later persistence

---

## Contracts

Passed:

    WEB EVIDENCE PROMPT EXACT-EXCERPT CONTRACT OK
    WEB EVIDENCE PROMPT CITATION-REF CONTRACT OK
    WEB EVIDENCE PROMPT UNTRUSTED-DATA CONTRACT OK
    WEB EVIDENCE PROMPT INJECTION-BOUNDARY CONTRACT OK
    WEB EVIDENCE PROMPT CPU-ONLY CONTRACT OK

Boundary:

    CPU_ONLY_PROMPT_PACKING_BOUNDARY=PASS

Regression remained green for:

- Used Web Evidence selection
- passage construction
- multilingual lexical ranking
- extraction
- CPU-only boundaries

Result:

    A3_4C9B_WEB_EVIDENCE_PROMPT_PACKING=PASS

---

## Live Acceptance

Discovery query:

    Python 3.14 release notes

Ranking query:

    Python 3.14 Zstandard compression module

Source:

    docs.python.org
    What's new in Python 3.14

Observed pipeline:

    raw_chars = 536237
    bounded_page_chars = 59999
    passage_count = 65
    used_evidence_count = 3
    used_evidence_chars = 3266
    packed_prompt_chars = 4629
    packing_overhead_chars = 1363

Evidence references:

    web_1
    web_2
    web_3

The packed context preserved:

    compression.zstd

and:

    Zstandard

Acceptance:

    LIVE_WEB_PROMPT_EXACT_EVIDENCE=PASS
    LIVE_WEB_PROMPT_CITATION_REFS=PASS
    LIVE_WEB_PROMPT_UNTRUSTED_BOUNDARY=PASS
    A3_4C9B_LIVE_PROMPT_PACKING_ACCEPTANCE=PASS

---

## Compute Boundary

Current Web pipeline before model inference:

    search discovery
        ->
    Safe Public Fetch
        ->
    CPU extraction
        ->
    CPU passage construction
        ->
    CPU lexical ranking
        ->
    CPU Used Web Evidence selection
        ->
    CPU Web evidence prompt packing

GPU requirement before final model inference:

    NONE

---

## Response-Budget Principle

Web-grounded answers may reasonably require more explanation than
ordinary conversational answers because they may need to:

- explain retrieved facts
- distinguish sources
- cite evidence
- compare multiple pieces of evidence
- express uncertainty or temporal context

Therefore the future runtime should follow:

    Web grounding raises the available response budget,
    not the required response length.

This means Web use may increase the maximum generation allowance, but
the model should not be forced to produce a long response when a short
answer is sufficient.

This policy is not implemented in this checkpoint.

---

## Architecture Boundary

Still not implemented:

- Working Context integration
- unified input-token budgeting for Web evidence
- live model generation from Web evidence
- persistence of exact used Web evidence after assistant reply
- citation validation in generated answers
- normal chat Web orchestration
- Web-aware output-token budget policy

---

## Next

The next step should integrate the packed Web evidence block into the
existing Working Context token-budget system.

It must not simply append Web evidence after context construction.

Web evidence must compete inside the same bounded model-input budget so
that Web grounding cannot silently overflow or starve the existing
conversation and memory context.

---

## Checkpoint

A3.4c9b Web Evidence Prompt Packing Foundation:

    PASS
