# A3.4c8 — Passage Construction & Lexical Ranking Foundation

Date: 2026-09-15

## Status

CHECKPOINT READY

This checkpoint adds an in-memory, CPU-only passage construction and
lexical relevance-ranking layer after bounded Web page extraction.

The purpose of this layer is candidate generation, not final evidence
selection.

---

## Input

A3.4c7 provides:

    ExtractedWebPage

with a maximum readable-text size of:

    60000 characters

---

## Flow

    ExtractedWebPage
        ->
    bounded passages
        ->
    multilingual lexical features
        ->
    in-memory BM25 ranking
        ->
    top candidate passages

This layer performs no:

- networking
- database writes
- model inference
- GPU work
- Web evidence persistence

---

## Passage Construction

Default target passage size:

    1200 characters

Default overlap:

    200 characters

Passage construction prefers natural boundaries where available.

Each passage records:

- passage ID
- ordinal
- start character
- end character
- exact passage text

Passage text remains derived from the extracted page rather than being
generated or rewritten.

---

## Boundary Bug Found During Development

The first contract run exposed a passage-boundary bug.

The helper responsible for finding a natural passage ending used the
global default target size instead of the actual target_chars argument.

For tests using a smaller custom passage size, this caused hard splitting
at the maximum boundary and separated:

    compression.

from:

    compression.zstd

The contract correctly failed.

The helper was changed to receive and use the active target_chars value.

After the fix:

    A3_4C8_PASSAGE_BOUNDARY_FIX=PASS

This was caught before staging or commit.

---

## Multilingual Lexical Features

English-style terms use Unicode-aware lexical matching with lightweight
stopword filtering.

Chinese Han sequences retain the full sequence and additionally emit
character bigrams.

Example:

    洛杉矶

produces useful lexical signals including:

    洛杉矶
    洛杉
    杉矶

This provides a zero-dependency baseline for Chinese lexical candidate
generation.

---

## Ranking

Ranking uses an in-memory BM25-style score.

Signals include:

- query-term frequency
- inverse document frequency
- passage-length normalization
- exact-query phrase bonus

Ranking is deterministic.

Only positive-score candidates are returned by the selection helper.

Default:

    top_k = 5

---

## Contracts

Passed:

    WEB PASSAGE CONSTRUCTION CONTRACT OK
    WEB PASSAGE MULTILINGUAL TOKEN CONTRACT OK
    WEB PASSAGE BM25 RANKING CONTRACT OK
    WEB PASSAGE POSITIVE-SELECTION CONTRACT OK
    WEB PASSAGE CPU-ONLY BOUNDARY CONTRACT OK

Result:

    A3_4C8_PASSAGE_BOUNDARY_FIX=PASS

---

## Live Acceptance

Discovery query:

    Python 3.14 release notes

Ranking query:

    Python 3.14 Zstandard compression module

Selected source:

    What's new in Python 3.14
    docs.python.org

Observed pipeline:

    raw_chars = 536237
    extracted_chars_before_bound = 119137
    bounded_extracted_chars = 59999
    passage_count = 65
    selected_count = 5
    top_5_total_chars = 5634

Top-ranked passage:

    passage_23
    score = 13.460328

Matched terms:

    3.14
    compression
    module
    python
    zstandard

The top passage contained the exact relevant documentation:

    compression.zstd

and described Python's Zstandard compression support.

Acceptance:

    TOP_PASSAGE_ZSTANDARD=PASS
    TOP_PASSAGE_COMPRESSION_ZSTD=PASS
    LIVE_WEB_PASSAGE_RANKING=PASS
    A3_4C8_LIVE_ACCEPTANCE=PASS

---

## Observed Limitation

Lower-ranked candidates demonstrated the expected limitation of lexical
ranking:

A passage can receive a positive score because it shares important query
terms even when its surrounding meaning is only partially relevant.

Therefore this layer is intentionally classified as:

    lexical candidate generation

and not:

    final evidence selection

This is useful behavior for the architecture because inexpensive CPU
processing can first reduce a large page to a small candidate set before
more expensive semantic or model-based judgment is considered.

---

## Architecture Boundary

Current flow:

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

Still not implemented:

- final evidence selection
- exact used-evidence persistence
- prompt integration
- answer citations
- normal chat Web orchestration

---

## Compute Boundary

Current passage construction and ranking are CPU-only.

No GPU inference is required.

This continues the Corvus efficiency principle:

    Spend cheap deterministic compute first.
    Spend model compute only where it adds value.

---

## Maturity

Page extraction:

    LIVE VALIDATED FOUNDATION

Passage construction:

    LIVE VALIDATED FOUNDATION

Lexical candidate ranking:

    LIVE VALIDATED FOUNDATION

Final evidence selection:

    NOT YET IMPLEMENTED

---

## Next

Next work should transform:

    ranked candidate passages
        ->
    final used External Evidence

The next stage should decide how to improve precision without making
large-model inference the default cost for every Web lookup.

---

## Checkpoint

A3.4c8 Passage Construction & Lexical Ranking Foundation:

    PASS
