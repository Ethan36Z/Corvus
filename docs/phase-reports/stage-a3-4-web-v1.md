# Stage A3.4 — Web v1

## Status

Stage A3.4 Web v1 is complete.

Status:

`SEALED`

Proposed maturity:

`PRODUCTION_CANDIDATE_READ_ONLY_WEB`

This maturity applies to the current single-user Corvus Web retrieval
capability.

It does not claim general-purpose browser automation, transactional Web
access, or unrestricted autonomous browsing.

The explicit Web v1 stop condition is:

`Corvus can retrieve current public Web information through a bounded,
read-only, provenance-preserving pipeline and use that evidence in the
existing conversation runtime.`

No further Web feature expansion is required before moving to the next
delivery stage.

---

## Context

Corvus entered Stage A3.4 with a stable persistent conversation runtime,
local model inference, Evidence Recall, multimodal attachment support,
vision, Voice v1, remote deployment, and a daily-use Web UI.

The missing capability was current external information.

The goal of Web v1 was not to build a browser agent.

The goal was narrower:

user question
→ current public Web discovery
→ safe fetch
→ text extraction
→ exact evidence selection
→ Working Context
→ local Qwen
→ canonical assistant response
→ exact Web provenance persistence

The Web capability had to remain subordinate to the existing Corvus
conversation architecture.

---

## Stage Question

Can Corvus safely read current public Web information, inject only bounded
evidence into the existing conversation runtime, preserve exact provenance,
and remain compatible with the canonical SQLite-first design?

The answer at seal time is:

`YES`

---

## Core Product Boundary

Web v1 is:

`READ THE WEB`

Web v1 is not:

`ACT ON THE WEB`

The current capability does not perform:

- login;
- form submission;
- purchases;
- messages;
- account actions;
- POST-based external actions;
- deletion;
- GitHub mutation;
- arbitrary shell execution;
- filesystem mutation;
- localhost browsing;
- LAN browsing;
- metadata-service access;
- autonomous open-ended browser loops.

The Web pipeline remains information retrieval only.

---

## Architecture

The sealed Web v1 pipeline is:

User request
→ canonical SQLite user commit
→ ephemeral Search Query Rewrite
→ Search Provider
→ normalized SearchResult
→ public-URL security validation
→ Safe Fetch
→ text extraction
→ passage construction
→ evidence selection
→ UsedWebEvidence
→ Working Context Web evidence block
→ existing local Qwen runtime
→ canonical assistant commit
→ exact Web evidence persistence
→ derived dense synchronization

Canonical user text is never replaced by the rewritten search query.

The rewritten query is ephemeral derived state used only for discovery.

---

## Existing-First / No-New-Wheel Decision

A fresh prior-art audit was performed before expanding the retrieval stack.

The final composition follows:

`Reuse engines. Own product.`

Corvus reuses mature components where appropriate and retains only the
boundaries that are product-specific.

Reused components include:

- DDGS for default Web discovery;
- SearXNG as an optional self-hosted discovery provider;
- Trafilatura for document text extraction;
- the existing Corvus local Qwen runtime for query rewrite and answering.

Corvus owns:

- provider normalization;
- URL policy;
- SSRF / private-network protection;
- DNS validation;
- pinned-IP fetch transport;
- redirect revalidation;
- response-size bounds;
- evidence selection;
- Working Context integration;
- exact evidence persistence;
- provenance linkage;
- canonical SQLite ordering;
- failure semantics.

No new search engine, custom source-authority scorer, external browsing agent,
or custom reranking framework was introduced.

---

## Search Providers

Web v1 supports two discovery providers.

Default:

`DDGS`

Optional:

`SearXNG`

Provider selection is controlled by runtime configuration.

Provider output is always treated as untrusted discovery data.

Search results do not bypass Corvus security boundaries.

A result must pass Corvus URL validation and Safe Fetch before its content can
become model-visible evidence.

---

## Search Query Rewrite

A relevance regression showed that conversational user wording could cause
DDGS to rank a documentation mirror ahead of the official source even though
the official source was present in the result set.

Changing DDGS backend did not solve this reliably.

A prior-art review rejected adding a custom source scorer or reranker before
the actual gap was established.

The successful minimal solution was:

natural-language user request
→ existing local Qwen
→ concise search-only query
→ DDGS

Example regression:

Original:

`According to the current Python 3.14 documentation, what is the
compression.zstd module? Use current Web evidence.`

Rewrite:

`Python 3.14 documentation compression.zstd module`

The rewrite was deterministic in the pilot and moved the official
`docs.python.org` page to result rank 1.

The rewrite adapter is discovery-only.

The original user text remains canonical and continues into final model
context.

Rewrite failure degrades to:

`FALLBACK_ORIGINAL`

Therefore query rewrite does not become a new single point of failure.

Checkpoint:

`56f3b3b Add Web search query rewrite adapter`

---

## Safe Fetch Boundary

Discovery does not grant fetch authority.

Safe Fetch independently validates every external URL.

The boundary includes:

- scheme validation;
- public-host validation;
- DNS resolution;
- rejection of private, loopback, link-local, reserved, and metadata targets;
- numeric-IP transport to reduce DNS rebinding exposure;
- original-host TLS SNI and certificate validation;
- original Host header preservation;
- redirect revalidation;
- textual-content enforcement;
- bounded response reads;
- read-only request behavior.

Redirect targets are revalidated before follow-up.

No provider is allowed to fetch arbitrary user URLs outside this boundary.

---

## Large Public Pages

The original Safe Fetch ceiling was 2 MiB.

The live Python documentation regression showed that valid public
documentation pages can exceed that bound.

Web v1 therefore raised the hard response ceiling to:

`8 MiB`

The extraction layer remains bounded separately.

The extraction output cap remains:

`60,000 characters`

Partial or silently truncated HTML is not accepted as a successful document.

The change retained fail-closed response-size behavior.

Checkpoint:

`9239359 Expand bounded Web fetch capacity`

Live validation successfully fetched and extracted the official Python
documentation page.

---

## Extraction

HTML/text extraction uses Trafilatura.

Extraction remains downstream of Safe Fetch.

The extractor performs no independent networking.

This preserves the security authority boundary:

Search Provider
→ Safe Fetch
→ Extraction

not:

Search Provider / Extractor
→ independent network access

---

## Used Web Evidence

Only selected exact excerpts become model-visible Web evidence.

Each UsedWebEvidence record contains provenance including:

- evidence reference;
- ordinal;
- source URL;
- source title;
- passage identity;
- character offsets;
- excerpt;
- relevance metadata.

The model-facing evidence block explicitly marks external Web content as
untrusted data rather than instructions.

Evidence references use stable current-turn labels:

`[web_1]`
`[web_2]`
`[web_3]`

The final model is instructed to cite those references when relying on the
corresponding excerpt.

---

## Working Context Integration

Web evidence enters the existing Working Context.

Web mode does not create a separate conversation engine.

The runtime remains:

existing conversation runtime
+ optional current-turn Web evidence

Historical user evidence and current external Web evidence remain distinct.

Web evidence is not treated as personal memory.

---

## Canonical Ordering

The sealed runtime preserves:

SQLite first.

For a Web turn:

1. canonical user message is committed;
2. query rewrite is derived;
3. Web grounding runs;
4. evidence is packed;
5. final model inference runs;
6. canonical assistant message is committed;
7. exactly the Used Web Evidence supplied to the successful model call is
   persisted;
8. derived dense state is synchronized.

Web discovery failure cannot erase the canonical user turn.

Web evidence persistence failure cannot erase an already committed assistant
turn.

---

## Exact Provenance Persistence

The `web_evidence` table persists the evidence actually supplied to the
successful final model call.

Each row stores:

- evidence id;
- assistant message id;
- ordinal;
- source URL;
- source title;
- exact excerpt;
- excerpt SHA256;
- fetched timestamp.

Web evidence may attach only to an assistant message.

Batch persistence is atomic.

Evidence ordinals are contiguous and zero-based.

The persisted SHA256 is calculated from the exact excerpt text.

---

## Schema Lifecycle

A production regression exposed an important lifecycle gap:

new additive tables existed in code but older deployed databases were not
automatically upgraded at API startup.

The initial Private database required a one-time manual `init_db()` call.

The final Web v1 design removed that operational dependency.

API startup now performs:

`init_db()`
→ `recover_dense_tail()`
→ serve

Schema ensure is:

- additive;
- idempotent;
- SQLite-first.

Canonical schema failure is fatal to API startup.

Dense recovery remains derived state and may retain its existing degraded
semantics.

This boundary intentionally does not introduce a general migration framework.

The rule going forward is:

`CREATE IF NOT EXISTS` additive schema may use startup ensure.

The first rename, destructive schema change, column transformation, or
data migration must trigger a fresh migration-tooling decision.

Checkpoint:

`b7e9826 Ensure database schema at API startup`

---

## Private / Demo Deployment Validation

Startup schema ensure was validated against both deployed instances.

Private:

- service: active;
- API port: 8096;
- database integrity: OK;
- canonical messages preserved;
- `web_evidence` present.

Demo:

- service: active;
- API port: 8098;
- database integrity: OK;
- canonical messages preserved;
- `web_evidence` absent before restart;
- `web_evidence` automatically present after restart.

This demonstrated a real additive upgrade of an older deployed database.

The initial immediate post-restart health probe failed because systemd
`Type=simple` reports the process active before FastAPI lifespan startup is
complete.

This was diagnosed as a readiness race, not an application failure.

Subsequent bounded readiness validation showed both services healthy.

---

## Full Live Provenance Regression

The final live regression used the Private API and the query:

`According to the current Python 3.14 documentation, what is the
compression.zstd module? Use current Web evidence.`

Observed runtime result:

- Web grounding: `READY`;
- selected result: `result_1`;
- evidence status: `PERSISTED`;
- evidence refs: `web_1`, `web_2`, `web_3`;
- persisted evidence count: `3`;
- overall runtime status: `OK`.

The selected source was:

`https://docs.python.org/3/library/compression.zstd.html`

All three persisted evidence excerpts came from the official Python
documentation host:

`docs.python.org`

The regression verified:

`LIVE WEB API RESPONSE: PASS`

`LIVE WEB EVIDENCE REF USAGE: PASS`

`CANONICAL USER MESSAGE EXACT: PASS`

`CANONICAL ASSISTANT MESSAGE EXACT: PASS`

`EXACT WEB EVIDENCE LINKAGE: PASS`

`EXACT WEB EVIDENCE SHA256: PASS`

`OFFICIAL SOURCE PROVENANCE: PASS`

`LIVE SESSION CANONICAL PAIR: PASS`

`FULL_LIVE_WEB_PROVENANCE_REGRESSION: PASS`

The final session contained exactly one canonical user message and one
canonical assistant message.

---

## Failure Semantics

Web v1 intentionally fails closed where correctness or security requires it.

Examples:

- invalid URL → reject;
- private or local network target → reject;
- unsafe redirect → reject;
- oversized response → reject;
- unsupported content → reject;
- no usable evidence → do not produce an ungrounded Web answer;
- canonical schema failure → API startup fails;
- query rewrite failure → fall back to original user query;
- dense recovery failure → preserve canonical conversation state;
- Web provenance persistence failure after assistant commit → preserve
  canonical assistant evidence and report degradation.

---

## Known Boundaries

Web v1 deliberately does not solve every future Web problem.

Known boundaries include:

- DDGS may experience transient provider-side no-result failures;
- query rewrite improves retrieval but is not a universal authority resolver;
- the current orchestration is optimized for a bounded current-turn evidence
  path, not deep autonomous research;
- Web v1 does not perform browser interaction;
- Web v1 does not execute Web actions;
- Web v1 does not log in to websites;
- Web v1 does not use external Web content as system instructions;
- Web v1 does not convert Web pages into long-term personal memory by default;
- Web v1 does not introduce a general schema migration framework.

- inline Web citation markers in assistant text are model-generated and therefore best-effort; persisted `web_evidence` provenance is the authoritative record;

These are intentional scope boundaries, not seal blockers.

---


## Auto Web Intent Gate

Web v1 now uses `web_mode=auto` as the product-facing default.

The explicit modes remain available:

- `off` forces Web access off;
- `on` forces Web grounding on;
- `auto` lets the Corvus conversation runtime decide once for the turn.

The Auto Web decision is owned by the backend conversation runtime rather
than by the Playground UI. This keeps the policy shared across Web, Voice,
and future native clients.

The decision path is:

`explicit/high-confidence deterministic signal`
`→ otherwise one-shot Qwen classification`
`→ WEB or NO_WEB`
`→ latch the result for the turn`

The classifier does not own a recursive tool loop.

One user turn receives at most one Web-intent decision and at most one
bounded Web-grounding phase. Existing Web discovery and fetch attempt bounds
remain authoritative after the decision.

Classifier output is accepted only when it is exactly:

`WEB`

or:

`NO_WEB`

Invalid classifier output or classifier failure fails closed to `NO_WEB`.

A structured-output pilot was not adopted because the deployed llama.cpp
runtime accepted the request but returned the raw token `WEB` rather than
schema-constrained JSON. The binary router therefore uses strict token
validation instead of adding JSON-schema dependency to this narrow decision.

### Frozen Web-Intent Regression

A frozen 24-case bilingual mini benchmark was used to validate the final
gate without expanding Web routing into a separate research project.

Final result:

- 24 / 24 cases correct;
- 13 / 24 handled by deterministic high-confidence routing;
- 11 / 24 required one model fallback call;
- average total gate latency across the full set: approximately 104 ms.

The benchmark included:

- explicit Web requests;
- current weather, news, prices, scores, versions, and officials;
- current documentation requests;
- recent external-claim verification;
- stable general knowledge;
- conversation-memory questions;
- translation;
- creative and emotional conversation;
- explicit no-Web instructions;
- temporal words that do not actually require current Web information.

The frozen benchmark is an engineering regression set, not a new continuing
research program.

### Playground Product Integration

The Playground does not require a permanent Web toggle.

When the client omits `web_mode`, the API default is `auto`.

This gives the product flow:

`normal user message`
`→ backend Auto Web Intent Gate`
`→ optional bounded Web grounding`
`→ existing Corvus conversation runtime`

The existing explicit `on` and `off` modes remain available for testing,
debugging, privacy-sensitive use, and future client controls.

### Browser Auto-Web Acceptance

A real Private Playground turn asked:

`corvus，现在帮我查一下 Ontario, California 接下来 7 天的天气。`

The Playground required no Web button or explicit `web_mode`.

The resulting assistant message had persisted Web provenance from:

`https://www.theweathernetwork.com/en/city/us/california/ontario/7-days?_guid_iss_=1`

The acceptance verified:

- the browser request reached the new Auto-Web runtime;
- current external weather evidence was retrieved;
- one exact Web-evidence record was attached to the assistant message;
- the persisted evidence ordinal was valid;
- the persisted excerpt SHA256 matched a fresh hash of the stored excerpt;
- the canonical user and assistant messages remained intact.

Result:

`BROWSER_AUTO_WEB_PROVENANCE: PASS`

The separate Private live API acceptance also verified both product-default
branches:

- default `auto` + current documentation request → `WEB` → `READY`
  grounding → persisted evidence;
- default `auto` + ordinary creative request → `NO_WEB` → no Web grounding.

---

## Security Principle

The Web subsystem follows:

`Discovery is not authority.`

A search provider may suggest a URL.

Only Corvus may decide whether that URL is safe to fetch.

External content is always untrusted.

---

## Architecture Principle

The final Stage A3.4 architecture follows:

`Reuse engines. Own product.`

and:

`Store canonical experience first.`

and:

`Derived systems may fail without destroying canonical evidence.`

---

## Seal Decision

Stage A3.4 Web v1 satisfies its intended product goal.

Corvus can now:

- automatically decide whether a turn needs current public Web information;
- preserve explicit `on` / `off` Web controls while defaulting product traffic to `auto`;
- search current public Web information;
- rewrite conversational questions into retrieval-oriented search queries;
- use DDGS by default;
- use SearXNG optionally;
- safely fetch public resources;
- extract bounded text;
- select exact evidence;
- inject evidence into the existing conversation runtime;
- cite current-turn Web references;
- persist exact evidence after successful model use;
- verify evidence integrity by SHA256;
- survive query-rewrite degradation;
- automatically ensure additive schema on startup;
- operate in both Private and Demo deployments.

No additional Web subsystem is required before continuing the A3 delivery
roadmap.

Stage A3.4 Web v1 is therefore:

`SEALED`

Next delivery target:

`Realtime Voice`
