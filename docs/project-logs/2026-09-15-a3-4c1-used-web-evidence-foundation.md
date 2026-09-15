# A3.4c1 — Used Web Evidence Foundation

Date: 2026-09-15

Status:

**CHECKPOINT**

Project:

**Corvus — Persistent Personal AI on Consumer Hardware**

Stage:

**A3.4 — Web v1 / Read-Only Internet Grounding**

Substage:

**A3.4c1 — Used Web Evidence Foundation**

---

## 1. Purpose

A3.4c1 defines the persistence boundary between transient Web retrieval
and long-term Corvus evidence.

The central rule is:

**Web retrieval is ephemeral. Used evidence is persistent.**

Corvus does not permanently record every Web search, every search
result, every fetched page, or every intermediate retrieval operation.

Only external evidence that is actually selected for use in a model
answer is persisted.

---

## 2. Evidence Classes

Corvus distinguishes three different provenance classes.

### User Evidence

Information directly provided by the user.

Examples:

- typed messages;
- uploaded material;
- user-originated voice.

User evidence remains part of the canonical conversation evidence
system.

### External Evidence

Information obtained from an outside source and actually selected for
use in a Corvus answer.

Examples:

- a relevant excerpt from a public Web page;
- the URL from which that excerpt came;
- the page title associated with that excerpt.

External evidence is not user evidence.

It must never be silently promoted into user memory.

### Model Output

The assistant response produced from user context, memory, and external
evidence.

Model output is not itself proof that the underlying claim is true.

---

## 3. Persistence Policy

The following retrieval artifacts are ephemeral by default:

- Web search queries;
- raw search result lists;
- pages inspected but not used;
- complete fetched HTML;
- complete fetched page text;
- intermediate retrieval ranking.

The following information is persistent when it actually contributes
to an assistant answer:

- selected evidence excerpt;
- source URL;
- source title when available;
- excerpt content hash;
- linkage to the assistant message that used it;
- evidence ordering within that answer.

This provides answer provenance without turning Corvus into a browser
history archive.

---

## 4. Storage Model

A new table is introduced:

`web_evidence`

Each record belongs to an assistant message.

Important fields include:

- evidence ID;
- assistant message ID;
- ordinal;
- source URL;
- source title;
- excerpt;
- excerpt SHA-256;
- fetch/evidence timestamp.

The table is separate from `messages`.

This separation is intentional.

External Web evidence is not stored as user conversation evidence.

---

## 5. Assistant Linkage

Persistent Web evidence may only be attached to an assistant message.

It cannot be attached to a user message through the Web evidence API.

This creates a clear provenance relationship:

external source
→ selected excerpt
→ assistant answer.

The relation means:

"This assistant answer used this external evidence."

It does not mean:

"The user said this."

---

## 6. Retrieval Non-Persistence

A3.4c1 intentionally does not create persistent tables for:

- Web searches;
- search result history;
- fetch history.

Those operations remain runtime mechanisms.

If Corvus searches ten results, fetches four pages, and ultimately uses
two excerpts, only the two used excerpts need permanent evidence
records.

---

## 7. Why the Excerpt Is Persisted

Saving only a URL is insufficient for long-term provenance.

Web content may:

- change;
- disappear;
- move;
- be corrected;
- be replaced.

The relevant historical question is not merely:

"What URL did Corvus visit?"

It is:

"What external evidence did Corvus actually see and use when producing
this answer?"

Therefore the selected excerpt itself is persisted.

---

## 8. Relationship to Corvus Memory Architecture

A3.4c1 does not change the core architecture:

**Evidence Log → Working Context → Materialized Memory**

Instead, it introduces explicit provenance for external evidence.

Conceptually:

User Evidence
→ Working Context

External Web Evidence
→ Working Context

Model Output
→ conversation record.

External Web evidence is not automatically promoted into Materialized
Memory or accepted as permanent truth.

Any future promotion into structured knowledge requires an explicit
policy for authority, temporality, conflicts, and provenance.

---

## 9. Security Boundary

Every persisted Web evidence source URL must still pass the A3.4a Web
security policy.

Therefore External Evidence cannot use this persistence path to bypass:

- localhost blocking;
- private network blocking;
- link-local blocking;
- Web URL policy.

The A3.4a and A3.4b security boundaries remain authoritative.

---

## 10. Contract Validation

Validated contracts:

**WEB USED-EVIDENCE PERSISTENCE CONTRACT OK**

The selected excerpt can be persisted and loaded with its provenance.

**WEB RETRIEVAL NON-PERSISTENCE CONTRACT OK**

No persistent Web search, search-result, or fetch-history tables are
introduced.

**WEB USER-EVIDENCE SEPARATION CONTRACT OK**

Web evidence cannot be attached to a user message.

**WEB SOURCE SAFETY CONTRACT OK**

Blocked/private URLs cannot enter the External Evidence store.

A3.4a Web security regressions remain passing.

A3.4b safe public fetch regressions remain passing.

`git diff --check` passes.

---

## 11. Architecture Principle

The durable principle established here is:

**Store the evidence that mattered to the answer, not every retrieval
operation that happened along the way.**

Equivalent operational rule:

**Retrieval is temporary. Adopted evidence is durable.**

This keeps Corvus auditable without turning long-term memory into a
network activity log.

---

## 12. Next Step

The next Web layer can remain ephemeral while performing:

search query
→ search provider
→ normalized results
→ safe page fetch
→ text extraction
→ evidence selection.

Only after evidence is selected for the model context should it cross
the persistence boundary introduced by A3.4c1.

Status:

**A3.4c1 Used Web Evidence Foundation — CHECKPOINT**
