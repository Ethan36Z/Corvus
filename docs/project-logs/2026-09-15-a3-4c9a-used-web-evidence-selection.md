# A3.4c9a — Used Web Evidence Selection Foundation

Date: 2026-09-15

## Status

CHECKPOINT READY

This checkpoint adds a deterministic, CPU-only selection layer that
converts ranked Web passage candidates into the exact External Evidence
excerpts that may later be shown to the model.

The selector performs no networking, persistence, embeddings, model
inference, or GPU work.

---

## Input

A3.4c8 provides ranked Web passage candidates.

Each candidate preserves:

- passage ID
- character start
- character end
- exact passage text
- lexical ranking score
- matched query terms

---

## Flow

    ranked Web passages
        ->
    verify exact extracted-page source slice
        ->
    remove heavily overlapping candidates
        ->
    apply evidence-item budget
        ->
    apply total-character budget
        ->
    UsedWebEvidence

---

## Default Budget

Maximum used-evidence items:

    3

Maximum combined evidence characters:

    3600

Maximum overlap ratio:

    0.50

These values are conservative baseline parameters rather than permanent
architecture constants.

---

## Exact Evidence Contract

Every selected excerpt must exactly match its original extracted-page
character range.

The selector rejects a candidate if:

    page.text[start_char:end_char].strip()

does not equal:

    passage.text

This preserves provenance and prevents rewritten or generated text from
silently becoming External Evidence.

---

## Provenance

Each UsedWebEvidence record keeps:

- result ID
- provider
- source URL
- source title
- passage ID
- source character range
- exact excerpt
- lexical score
- matched terms
- exact-phrase-match flag

Source URL is revalidated through the existing Corvus Web security
boundary.

---

## Evidence-Set Contract Correction

The first contract incorrectly required the highest-ranked individual
excerpt to contain both:

    Zstandard

and:

    compression.zstd

Diagnostic output showed that the relevant information legitimately
spanned two selected passages:

- the highest-ranked passage contained the strongest Zstandard
  compression explanation
- the second-ranked passage contained the exact compression.zstd string

The selector correctly retained both.

The contract was corrected to validate coverage across the complete
Used Web Evidence set rather than forcing all relevant facts into the
single top-ranked excerpt.

No ranking or selection behavior was changed to satisfy the test.

---

## Contracts

Passed:

    WEB USED-EVIDENCE EXACT-SLICE CONTRACT OK
    WEB USED-EVIDENCE BUDGET CONTRACT OK
    WEB USED-EVIDENCE OVERLAP CONTRACT OK
    WEB USED-EVIDENCE SOURCE-PROVENANCE CONTRACT OK
    WEB USED-EVIDENCE NO-MODEL BOUNDARY CONTRACT OK

Regression:

    WEB PASSAGE CONSTRUCTION CONTRACT OK
    WEB PASSAGE MULTILINGUAL TOKEN CONTRACT OK
    WEB PASSAGE BM25 RANKING CONTRACT OK
    WEB PASSAGE POSITIVE-SELECTION CONTRACT OK
    WEB PASSAGE CPU-ONLY BOUNDARY CONTRACT OK

    WEB EXTRACTION HTML CONTRACT OK
    WEB EXTRACTION TEXT CONTRACT OK
    WEB EXTRACTION SIZE BOUNDARY CONTRACT OK
    WEB EXTRACTION EMPTY CONTRACT OK
    WEB EXTRACTION NO-NETWORK BOUNDARY CONTRACT OK

Boundary:

    CPU_ONLY_PURE_SELECTION_BOUNDARY=PASS

Result:

    A3_4C9A_USED_WEB_EVIDENCE_SELECTION=PASS

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
    ranked_count = 65
    used_evidence_count = 3
    used_evidence_total_chars = 3266

The selected evidence set contained:

    Zstandard

and:

    compression.zstd

Every selected excerpt was verified against the exact extracted-page
source slice.

Acceptance:

    USED_EVIDENCE_EXACT_SOURCE_SLICE=PASS
    USED_EVIDENCE_BUDGET=PASS
    USED_EVIDENCE_ZSTANDARD_COVERAGE=PASS
    USED_EVIDENCE_COMPRESSION_ZSTD_COVERAGE=PASS
    A3_4C9A_LIVE_USED_EVIDENCE_ACCEPTANCE=PASS

---

## Compute Boundary

Current Web narrowing path:

    raw Web content
        -> CPU extraction
        -> CPU passage construction
        -> CPU lexical ranking
        -> CPU used-evidence selection

No GPU work is required before the final evidence set is ready.

In the live acceptance:

    536237 raw characters
        ->
    3266 used-evidence characters

Only the final small evidence set needs to be considered for model
context.

---

## Architecture Boundary

Current pipeline:

    search discovery
        ->
    SearchResult ID
        ->
    Safe Public Fetch
        ->
    bounded extraction
        ->
    passage construction
        ->
    lexical candidate ranking
        ->
    exact Used Web Evidence selection

Still not implemented:

- Web evidence prompt formatting
- prompt / Working Context integration
- assistant answer generation from Web evidence
- persistence of the exact evidence actually used
- answer citations
- normal chat Web orchestration

---

## Principle

    Store the evidence that mattered to the answer,
    not every retrieval operation that happened
    along the way.

UsedWebEvidence is intended to become the shared object between:

    model prompt input

and:

    persistent Web evidence provenance

so that the evidence stored after an answer is the same evidence the
model actually saw.

---

## Maturity

Used Web Evidence selection:

    LIVE VALIDATED FOUNDATION

GPU requirement:

    NONE

Prompt integration:

    NOT YET IMPLEMENTED

Evidence persistence integration:

    NOT YET IMPLEMENTED

---

## Next

Next work should connect the exact UsedWebEvidence set to a bounded,
explicit prompt representation without changing the evidence text.

The same evidence set should later be persisted against the resulting
assistant message.

---

## Checkpoint

A3.4c9a Used Web Evidence Selection Foundation:

    PASS
