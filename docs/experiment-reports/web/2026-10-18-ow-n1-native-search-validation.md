# OW-N1 — Open WebUI 0.6.5 native search validation

Date: **2026-10-18**

Verdict: **OW_N1_BLOCKED_WITH_REASON**

**Decision:** do not activate native search in Lab. Native 0.6.5 supplies search, page loading, inline context, model dispatch and source cards, but this experiment did not establish a safe functional public-egress boundary. Live execution stopped at mandatory preflight. There were **zero public searches, zero fetched public pages and zero Qwen calls**. Native answer quality and superiority to W2.1 remain unmeasured.

Offline inspection and twelve deterministic checks also found concrete citation, retry, budgeting and failure-transparency issues. A network/filesystem sandbox was demonstrated with inert negative tests; it deliberately has no external connectivity. The missing piece is a constrained bridge for public retrieval and exact SearXNG/Qwen operations, not the availability of namespace isolation itself. No large security architecture was built to finish this experiment.

## A. Existing native search capability

### Baseline and source provenance

- Lab branch `lab/ow2e-console`, HEAD `975645963291ec992d64df0474a3ee9d0ba33dcd`, clean at admission.
- Report branch `reports/web-validation`, starting HEAD `897d839f88c746daef6966ac4b001a03005a916e`, clean at admission.
- Running Lab image: `corvus-open-webui:0.6.5-arena-ui2.1-https-r03b`, reported healthy by Docker. Existing SearXNG and Qwen containers were running; Qwen was reported healthy. No new service-level HTTP health request or inference was made. SearXNG search availability was not freshly established.
- Cached source `package.json` declares **0.6.5**. Its LICENSE contains the BSD three-clause terms. No upgrade or newer-version code was introduced.
- Five inspected backend files were hashed both in the cached source and, using read-only `sha256sum`, in the running WebUI container. All five matched exactly. No installed Function database, conversation database, credentials or environment values were read.

| Matched file under `backend/open_webui/` | SHA256 |
| --- | --- |
| `retrieval/web/utils.py` | `3620119a18a642c667f16cbd3619252b8839f42b885e057f9c5054bbfb8dcde4` |
| `retrieval/web/searxng.py` | `51fcaf149e9895b6959c13dc521e5d0c38ea9abf46dea489213980b2674a2b51` |
| `retrieval/utils.py` | `e3dece36dc30eaf864653894b152e93e539a9a000070f977e3655718d4f031da` |
| `routers/retrieval.py` | `95bc6cb94bffbc9a21dfeeb83fba6ab096b95f5d870be6ef0cb7d7466777c0d4` |
| `utils/middleware.py` | `a2e66ce5d02a1f8350e09bbb486a6323f7e6506392b6b18d5ca19b250fefd138` |

These hashes establish the inspected backend relationship, not byte identity of every installed frontend asset or complete runtime configuration. The cached LICENSE SHA256 is `6c4b8d8034b9a5795643e1771716689a22638a7d6779d422136a008ecfaf3951`.

### Existing flow

1. `utils/middleware.py::process_chat_payload` consumes the `web_search` feature and calls `chat_web_search_handler`.
2. That handler asks `generate_queries` for discovery queries, emits search status events and loops over the generated queries. It does not itself enforce this experiment's two-query ceiling. If query generation raises, it falls back to the user text; an empty query list ends search.
3. `routers/retrieval.py::search_web` selects the configured provider. Its SearXNG adapter sends JSON search requests, sorts returned results by score and normalizes links/titles/snippets.
4. `process_web_search` passes result links to `get_web_loader`, then awaits `loader.aload()`. The default `SafeWebBaseLoader` uses aiohttp and BeautifulSoup text extraction, rather than Corvus's trafilatura/passage selector.
5. With `BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL=True`, fetched documents return inline. Otherwise each nonempty page is stored in a hashed vector collection through `save_docs_to_vector_db`.
6. The middleware turns inline documents into `web_search` files. `chat_completion_files_handler` still attempts retrieval-query generation before `get_sources_from_files`; inline `docs` then bypass vector retrieval and embedding execution in that function.
7. The RAG formatter wraps document text in `<source id="n">` tags and adds the configured RAG instruction through the existing message helper. Standard model dispatch supports an OpenAI-compatible backend. A model marked as a Pipe instead dispatches through its Function.
8. Sources are emitted as source events. The pinned `Citations.svelte` groups document/metadata pairs by metadata source URL, offers source cards and a details modal. This is an existing presentation contract, not proof that any model claim is supported.

**Budget implication:** a normal successful native turn can include discovery-query generation, retrieval-query generation and final answer generation. Thus two ordinary end-to-end turns could require more than the authorized two Qwen completions. A future bounded harness must freeze both helper-query outputs offline or otherwise account for and refuse excess model calls. It must also enforce page/context/elapsed limits and disable automatic retries. No call was spent resolving this issue here.

## B. Security preflight result

**Functional live preflight: BLOCKED.** The native loader's application URL check is insufficient as the only SSRF boundary, and no reviewed restricted-egress bridge was established for this experiment.

Observed source findings:

- `validate_url` resolves the initial hostname and rejects addresses classified as private by its validators when local fetching is disabled. The source itself warns that this remains vulnerable to DNS rebinding.
- The later aiohttp request does not pin that checked DNS answer. The inspected `_fetch` method does not revalidate redirect targets or disable automatic redirects by default. Initial-host checks therefore do not establish every actual destination.
- `_fetch` defaults to **three connection attempts** with backoff. Its normal request path supplies no explicit per-page timeout in the inspected method; full response text is read without an experiment-specific byte/context cap there. Caller/session defaults are not the requested hard experiment bounds.
- `WEB_SEARCH_TRUST_ENV=False` avoids that configured trust in proxy environment variables, but does not establish network isolation. A domain allowlist or disabled local-fetch setting alone would also be insufficient.
- The current Lab WebUI runs with host networking. Reusing it for this experiment would violate isolation and the prohibition on enabling native search in the existing Lab. An ordinary Docker bridge also does not, by itself, establish public-only egress.

No unsafe URL was sent to a deployed service or public network to demonstrate these defects. Redirect and DNS findings are source/control-flow observations, supplemented by inert mocked transport checks; they are not a live exploit or a complete SSRF regression suite.

## C. Isolation boundaries and offline validation

### Demonstrated OS boundary

An ephemeral Bubblewrap process used a fresh user/network/mount namespace, cleared environment, read-only system executables/libraries, private proc/dev, and temporary `/tmp` and `/data`. The expanded check mounted only its reviewed synthetic check script in addition to system files. It had no home directory containing host data, no host `/etc` or `/run`, no Docker socket and no Lab or preserved experiment-data mounts. Temporary synthetic data was writable. No full WebUI application was started.

Observed: only the namespace's loopback interface existed, and the IPv4 route table had no routes. Thirteen inert connection checks all failed: IPv4 loopback, all three RFC1918 ranges, link-local, shared-address space, unspecified, multicast and documentation addresses; IPv6 loopback, unique-local, link-local and documentation addresses. Most nonlocal checks returned `ENETUNREACH`; loopback/unspecified returned `ECONNREFUSED`; the unscoped IPv6 link-local check returned `EINVAL`. These results are reported as observed, not as equivalent individual firewall rules.

This no-egress namespace prevents the fetcher from reaching host services even if URL validation is bypassed or DNS/redirect behavior changes. It also prevents real public fetching and access to shared SearXNG/Qwen. No suitable existing constrained broker was located in the inspected deployment files/temporary controls. No virtual interface, firewall rule, daemon, container or service configuration was added to create one.

The command sandbox initially denied Bubblewrap's network setup. The same inert test succeeded with approved elevated command execution. This was a test-run permission issue, not permission to use host networking for Web retrieval.

### Twelve focused checks

The separate offline driver extracted selected function bodies from the pinned source using AST, removed decorators/type annotations and supplied inert dependency stubs. It never imported the WebUI application or initialized storage. Network connection/DNS operations and database-file opens were denied by an audit hook. No such operation was attempted. No package was installed.

| Check | Observed result |
| --- | --- |
| Version and BSD license text | Passed |
| Bypass search returns inline documents without vector saves | Passed; zero save calls |
| Non-bypass control reaches vector-save stub | Passed; two synthetic saves |
| Inline document path avoids embedding/vector-query stubs | Passed |
| Two bypassed pages reproduce duplicate inline citation IDs | Passed reproduction of defect |
| SearXNG engine failure diagnostics disappear during normalization | Passed reproduction of defect |
| Normal URL engine selector survives; adapter omits explicit timeout | Passed observation |
| Legacy `<query>` URL form strips all query parameters | Passed reproduction |
| Fetch forwards no default redirect restriction or DNS pin | Passed mocked/control-flow observation |
| Default connection failure causes three attempts | Passed with inert failures and stubbed sleep |
| Initial validation and later connection resolve separately | Passed source-structure observation |
| Rejected URLs are silently omitted by URL filter | Passed with inert validator stub |

**Final: 12 passed, zero failed/errors; zero attempted network/database operations.** An initial driver run had four missing-dependency-stub errors, with no live effects. Its output was preserved; after supplying the dependency-injection stub, the complete run passed. These are selected-function tests, not full installed-dependency, browser, authentication or deployment acceptance.

Temporary scripts and outputs remain outside the repository. Historical W1 ledgers/artifacts were not modified or reset. Only this sanitized report and index entry are published.

## D. Actual search results

| Authorized question | Search queries used | Public pages fetched | Outcome |
| --- | ---: | ---: | --- |
| Explain three Python 3.14 release-note changes naturally in Chinese | 0 | 0 | NOT RUN — mandatory isolation preflight incomplete |
| Summarize a recent official NASA release with publication date | 0 | 0 | NOT RUN — same blocker |

No source relevance, publication date, extraction quality or native retrieval-success measurement exists for these questions. Earlier W1/W2 results were not relabeled as native-search results. No retry or budget expansion occurred.

The inert SearXNG fixture returned HTTP-success semantics with no results and an engine `Access denied` diagnostic. Native normalization returned `[]` and discarded that diagnostic. This is an offline failure-transparency finding, not a new observation of the live provider.

## E. Actual Qwen answers

**None: zero calls out of two authorized.** There are no generated answers, token counts, answer-quality scores, unsupported-claim counts or naturalness measurements for OW-N1. No deployed chat endpoint, Corvus Pipe, personal memory or Hindsight was used.

The OpenAI-compatible dispatch path makes use of the existing Qwen endpoint technically plausible. Actual native search-plus-Qwen interoperability, answer usefulness and Chinese/English quality remain unverified. Prior single-source Qwen experiments established neither this path nor reliable multi-source synthesis.

## F. Source/citation behavior

**Existing useful feature:** inline fetched documents retain source URLs/titles and reach the native source-card schema without needing a second frontend. Multiple page texts can be included in one context, unlike Corvus v1's first-usable-page selection. No semantic sufficiency, version/date acceptance or accurate claim attribution follows automatically.

**Reproduced correctness defect:** native bypassed Web documents contain `source`, title and optional description/language metadata, but no `file_id`. The RAG context formatter uses `doc_meta.get("file_id")` as its citation-number key. Executing that exact formatter loop with two distinct synthetic native-bypass pages produced two `<source id="1">` tags and no ID 2. The source-card component separately groups by URL; two visible cards do not fix ambiguous model-context citation numbering. This is a deterministic backend defect in the inspected path; browser impact was not exercised.

**Trust limitation:** the loader records the original requested path as metadata source. The inspected async path does not establish that this is the validated final redirect destination. Source cards display provenance supplied to them; they do not verify final URL safety, article authority, publication date or factual support.

The pinned default RAG instruction asks for concise inline citations and same-language answers. It also permits answering from the model's own understanding when the context lacks an answer. That policy is not a guarantee of evidence-only current facts. Failure/insufficiency needs explicit presentation rather than reliance on citation appearance.

## G. Latency and resource usage

| Resource | Authorized maximum | Actual new usage |
| --- | ---: | ---: |
| Public search queries | 2 | 0 |
| Public page fetches | 10 | 0 |
| Local Qwen completions | 2 | 0 |

Search, extraction, generation and end-to-end latency: **not measured**. Prompt/completion tokens and context size: **not measured**. No statistical reliability, percentile, throughput or performance comparison is claimed. Offline mocked attempts are not counted as live provider requests or page fetches. SearXNG server-internal fan-out was not exercised or measured.

## H. Memory and data separation

Observed function behavior: enabling the bypass avoids `save_docs_to_vector_db` in `process_web_search`; inline `docs` also avoid vector lookup and embedding invocation in `get_sources_from_files`. The non-bypass control confirms the test could detect vector saves. This establishes the selected Web-document path, not every application write.

The full native application can still initialize a configured database/cache and persist chat messages, source events and other metadata. Source inspection shows `DATA_DIR`-derived uploads/cache/vector paths, a default SQLite URL, persistent configuration loading and chat-response writes. A bypass environment variable alone does not make the app stateless or prevent saved configuration from taking precedence.

A future full-app experiment must set all data/database/cache/home locations before any storage-initializing import, mount no deployed volumes or credentials, and use only synthetic users/chats. An isolated direct-Qwen model can keep retrieval separate from Corvus canonical memory, but it does not exercise Corvus canonical persistence.

This experiment imported no WebUI/Corvus storage modules, read no conversation/memory databases, and performed no chat or model requests. No installed Function, service, volume, credential, Hindsight/Arena lifecycle, authentication or networking configuration was changed. No claim is made about unrelated concurrent service activity or a database checksum audit.

## I. Open WebUI versus Corvus W2.1

| Dimension | Native 0.6.5 findings | W2.1 established position |
| --- | --- | --- |
| Search/read/answer UI | Existing integrated flow and source cards; live usefulness unmeasured | Existing Pipe plus simple trusted Markdown sources |
| Multi-page context | Supported inline; citation-ID defect reproduced | Bounded three candidates/two accepted sources with unique refs |
| Fetch security | Initial DNS/private check insufficient; functional OS-isolated egress not ready | Reuses Corvus public-IP pinning and Safe Fetch redirect restrictions; offline regression evidence, not universal safety proof |
| Evidence sufficiency | No demonstrated question/version/date acceptance gate | Explicit typed requirements; ordinary queries conservatively use limited-source fallback |
| Provider failure | HTTP-success engine failure can normalize to empty; handler emits errors but can continue completion | Explicit failure/limited-source outcomes and diagnostic handling |
| Grounded natural answer | Native pipeline untested here; citations do not verify claims | Natural synthesis remains limited; source-first MVP is the working baseline |
| Persistence | Separate temporary WebUI storage possible; bypass does not stop chat writes | Existing canonical owner and exact used-evidence ordering retained |
| Current readiness | Not accepted for activation | Local offline integration ready; not deployed or browser-accepted |

Relevant prior evidence: [W1.2b](2026-10-18-w1-2b-provider-comparison.md) found a readable old official Python page insufficient despite `READY`, while SearXNG supplied more relevant evidence for one question. [W1.3](2026-10-18-w1-3-retrieval-architecture-decision.md) found no complete-question sufficient evidence across its six plans, including hidden Google News failure. Native search reusing SearXNG does not by itself eliminate those provider/relevance risks. [W2.1](2026-10-18-w2-1-web-mvp-integration.md) documents 60 passed tests, one skip and 19 passed contract scripts, with ordinary-query fallback and no live/browser acceptance.

**Adoption judgment:** there is no evidence here to replace W2.1 with native retrieval, and also no measured basis to declare native answer quality worse. Reuse native source presentation where useful; retain W2.1 as the current reviewed source-first integration candidate pending its own deployment authorization. Do not enable both discovery pipelines.

## J. Exact next integration step

The smallest prerequisite for a native live decision is **one focused isolated security/compatibility harness stage**, not another provider benchmark or prompt-tuning loop:

1. Keep the tested no-network/no-private-mount worker. Supply reviewed narrow operations across that boundary: public-page fetching through existing Corvus Safe Fetch with DNS pinning, redirect validation and byte/deadline/call limits; a fixed SearXNG search operation with bounded query/engine input; and an exact local Qwen completion operation with persisted-before-dispatch budget admission. Do not provide a generic internal HTTP or CONNECT proxy. Existing components should perform the actual search/extraction/context/model work; the bridge is a security boundary, not a new search framework. No such bridge was implemented here.
2. Disable native transport retries for the experiment; preserve raw SearXNG failure diagnostics. Freeze helper query generation offline so the original two final completions remain the entire model budget. Bound candidate count, extracted/context text and elapsed time before dispatch.
3. Add the smallest source-identity adapter: derive stable, unique citation keys from validated fetched-source identity and verify agreement with native URL-grouped cards. Test redirect provenance and two-page numbering offline before enabling live access.
4. Only after those boundaries pass inert negative tests, run the two originally specified questions in temporary WebUI storage and record actual answers. This report does not authorize deployment or claim the absent native live validation is complete.

**Estimated effort, not a measurement:** one focused security/identity harness implementation-and-review stage followed by one bounded live acceptance stage. A safe deployment estimate cannot be given before the bridge is reviewed. If that boundary becomes a broad refactor, defer native retrieval and use the existing W2.1 path rather than building a new infrastructure project for this experiment.

For the current Corvus Pipe, native retrieved context cannot simply be forwarded as ordinary user text or activated by deleting guards. The checked-in Pipe explicitly rejects WebUI feature/files/tools input; function dispatch and retained metadata preserve that boundary. A future native integration requires a small typed, authenticated evidence/source envelope, one retrieval owner, exact used-evidence provenance and existing user-first/assistant persistence ordering. Its scope is larger than merely enabling an admin toggle. No installed-Pipe compatibility or ownership acceptance is claimed here.

Privacy review: only this authored report and its relative-link index row are publication candidates. They contain public source hashes, synthetic observations and prior sanitized report references; no credentials, tokens/cookies, private conversations, personal memory, database contents or raw terminal/metrics dump. Lab/source code branches remain unchanged and unpushed. Public publication is restricted to `reports/web-validation` without force push.
