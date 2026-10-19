# W2.1 — Source-first Web MVP integration

Date: **2026-10-18**

Verdict: **W2_1_MVP_INTEGRATION_READY**

The integration implements three observable outcomes: a grounded answer when explicit evidence requirements pass, fetched source links with limitations when coverage is uncertain, and an honest deterministic failure when retrieval cannot provide usable pages. Natural synthesis is not required for the source-first MVP. This is an offline integration checkpoint, not deployment, live provider validation or browser acceptance.

## A. Baseline, recovery and W2 review

- Running Lab checkout remained clean on `lab/ow2e-console` at `975645963291ec992d64df0474a3ee9d0ba33dcd`.
- Existing integration worktree/branch `integration/w2-web-mvp` was inspected after interruption. It was clean at `9b374cf2ef46ea08399b124e0c2a725d96c92a38`, the already completed W2 cherry-pick. The worktree was not recreated, the cherry-pick was not repeated, and no uncommitted work was discarded.
- Original reviewed W2 commit: `01dd02e1aa826d49bd628891641892f3450b698f`. Its implementation and complete [W2 report](2026-10-18-w2-evidence-acceptance-prototype.md) were reviewed.
- **W2.1 code commit:** `50a63850f83506724aaff4c2af4f50811d00d646` — `Integrate source-first Web MVP with honest fallbacks`.
- The code branch remains **local and unpushed**. The two integration commits above descend from the verified Lab baseline. A SHA reference in this report does not publish those objects or unpublished Lab history.
- Reporting branch baseline: `reports/web-validation` at `46f08f9d81957c76044c26d49f488eb85f958368`.

No critical safety or data-integrity defect requiring a stop was found in W2's stated, opt-in prototype scope. Its trust limitations remain important: a source-bound witness proves provenance, not the semantic role of an arbitrary date/version. Distinct source URLs/bodies do not establish independent authorship. Empty requirements do not prove semantic coverage. W2.1 therefore does not promote unknown ordinary queries into sufficient evidence.

Reference uniqueness, default behavior, exact evidence persistence, user/assistant ordering and existing Pipe identity mapping were inspected. Metadata assertions remain server-side; API clients cannot supply trusted source facts or activate the server feature. No general verifier/parser was added.

## B. Implementation and files

The W2 collector, existing discovery, Safe Fetch, trafilatura extraction, passage ranking and evidence packing are reused. No second pipeline, search engine, model, agent, framework, dependency or async subsystem was introduced.

Ten files changed in the W2.1 commit:

| File | Change |
| --- | --- |
| `app/web_mvp.py` | Progressive outcome preparation, sanitized provider handling, validated Markdown sources, conservative answer presentation |
| `app/conversation_runtime.py` | Opt-in MVP path; deterministic fallbacks reuse the existing canonical assistant/provenance/dense tail |
| `app/playground_api.py` | Optional typed requirements and additive source/outcome observability |
| `app/runtime_config.py` | Default-off `CORVUS_WEB_MVP_ENABLED` flag |
| `app/searxng_provider.py` | Optional raw diagnostics callback before normalization; preserved across adapter routing |
| `app/web_acceptance.py` | Bounded observed extracted pages retained for clearly labeled fallback links |
| `deploy/open-webui/corvus_pipe.py` | Accept only confirmed deterministic fallback replies without weakening session/persistence guards |
| `tests/test_web_mvp.py` | End-to-end offline runtime/API/presentation contracts and inherited Pipe contracts |
| `tests/run_web_acceptance_offline.py` | Apply the existing explicit subprocess-test skip to inherited MVP Pipe tests |
| `docs/prototypes/w2-1-web-mvp.md` | Behavior, trust boundaries, reproduction, exact deployment prerequisites and rollback |

The branch also inherits W2's six files, including its fixtures, evidence acceptance tests and optional orchestration hook. W2 was not rewritten. Much of the runtime line diff is indentation of the unchanged context/generation block under a condition; the persistence tail remains shared. Existing positional `process_turn` arguments are preserved; new controls are appended.

No persistence/schema, Hindsight, Arena, deployment unit, Compose, credential, FoxGate or Cloudflare file changed. No running checkout or installed Function was edited.

## C. Working MVP behavior

| Presentation outcome | Conditions and observable behavior |
| --- | --- |
| `GROUNDED_ANSWER` | Explicit nontrivial requirements pass W2 without provider errors. Existing Qwen interface/context/evidence packer generates the answer; validated Markdown source links are added before canonical assistant persistence. |
| `SOURCES_WITH_LIMITATIONS` | Actual fetched/extracted pages exist, but requirements are unknown, incomplete, mismatched or affected by partial provider failure. Deterministic limitations plus source links; no answer-model/context call. |
| `SEARCH_FAILED` | Provider/intent/preparation failure, genuine empty discovery, or no page that can be presented. Deterministic honest failure; no answer-model call or fabricated fresh facts. |

These are presentation outcomes, not replacements for technical statuses or canonical confirmation. The outcome field is exposed only after the assistant commit succeeds. A model/presentation/assistant-commit failure cannot masquerade as a completed grounded response.

Unknown open-ended requirements always remain `EVIDENCE_INSUFFICIENT`. Domain matching or source count alone is not promoted into factual coverage. Missing date/version metadata means unverified, not false. Specific version/date/distinct-source limitations are stated when known. Ordinary queries can still return useful fetched links.

The installed Pipe's request remains ordinary text/session/Web-mode only, so standard WebUI Web queries will ordinarily use this conservative source-first fallback. Optional structured API requirements permit explicitly known cases, for example literal API-symbol coverage. No automatic natural-language requirements interpretation or real-site publication/version adapter is supplied. Synthesis for arbitrary natural questions is intentionally deferred.

Limits remain three candidate pages, two accepted sources and 3,600 selected excerpt characters. At most two distinct fallback URLs are displayed. Explicit unmet requirements can continue after the first readable page. An ordinary fallback may stop at the first usable page. Only fetched/extracted final URLs become source links; unfetched hits and snippets are omitted rather than presented as verified content.

The current provider setting is preserved; no provider switch was deployed or made the new default. MVP uses the original query without a query-rewrite model call and restricts the existing provider plan to one attempt, with no added fallback/retry. Existing auto-intent behavior remains, but an intent exception becomes `SEARCH_FAILED` instead of silently obtaining an ungrounded fresh-fact answer.

## D. Failure honesty and source presentation

SearXNG engine diagnostics are captured before its normalizer drops them. Access denied plus an empty result becomes provider failure, while a genuinely empty discovery remains `NO_RESULTS`. Content accompanied by provider failure becomes `SOURCES_WITH_LIMITATIONS`, with the failure visible as a coverage limitation. Raw engine/backend error messages do not enter user-facing replies.

Markdown links come from validated final retrieval URLs and source identity, never model-generated URLs. Labels are fixed source labels, not unverified discovery titles. Grounded reference IDs come from the exact W2 evidence set. Unknown model citation IDs and link destinations are removed/replaced or escaped; model text is treated as conservative prose before adding the trusted source section. This reduces rich Markdown/code formatting and does not prove that every factual claim supports its citation.

The API exposes only minimal source URL/identity/refs/fetched-status metadata; no personal memory, evidence excerpt, internal service URL or raw provider error is added to this source list. The ordinary source section is sufficient for this MVP. Native source-card events, frontend redesign and automatic numeric inline-citation mapping remain deferred.

No browser acceptance is claimed. Offline string/provenance checks are not a complete browser Markdown-renderer security or interoperability test.

## E. Canonical persistence and ownership

The existing user-first path is retained. For grounded turns the exact W2 evidence set is supplied to the existing packer/model. Final presented assistant text, including the validated source section, is committed before that exact evidence set is persisted; derived dense sync stays last. No new Evidence Log owner or schema is introduced.

Deterministic source/failure replies take the same assistant-commit/dense-sync tail, skipping generation and model context. They report `model=NOT_CALLED` and Web evidence `NOT_USED`, not fictitious model success or invented evidence-provenance rows. Links remain in the canonical assistant text; no evidence set is claimed to have been supplied to a model that was not called.

A presentation failure before the assistant commit does not repeat the provider call, generation or canonical user write. A later browser/transport failure does not resubmit a POST. Confirmed assistant persistence failures/degradation still fail the existing Pipe guard. Uncertain turns must not be automatically retried.

The Pipe accepts deterministic fallbacks only when all of these hold: matching mapped session, recognized fallback outcome, insufficient-evidence status, `model=NOT_CALLED`, positive assistant message ID, confirmed overall status and `persistence=NORMAL`. Existing endpoint ownership, saved-chat/user identity, text-only, task suppression, Arena and no-retry guards remain. Arena explicitly uses Web off; attachments retain the legacy path.

Hindsight lifecycle code is unchanged. Existing shadow scheduling requires a model-OK result, so deterministic fallbacks do not trigger that path. No Hindsight bank was accessed or changed during tests.

## F. Offline validation

**Final results: 60 unittest methods passed, zero failed, one explicitly skipped; 19 existing assertion-based contract scripts passed.**

Breakdown:

- W2.1 runtime/presentation/API tests: **15 passed**.
- New fallback Pipe tests: **2 passed**.
- Inherited existing Pipe tests: **24 passed, one fresh-subprocess test skipped** under the network/subprocess-denying driver.
- W2 acceptance tests: **19 passed**.
- Existing module-level Web contract scripts: **19 passed**. These are script passes, not invented unittest counts.

The final MVP suite discovered 42 methods: 41 passed and one skipped. The separate W2/regression run passed 19 methods plus 19 script modules. No skipped test is reported as passed.

Coverage includes:

- complete grounded flow through the existing evidence packer and exact provenance persistence;
- source-only fallback without context/generation or false evidence-use claims;
- provider failure, genuine emptiness, and partial provider failure;
- old/wrong version and out-of-window/unverified dates;
- bounded continuation and globally unique refs across two sources;
- validated metadata-only links, unknown citation/link filtering, and omission of unfetched URLs;
- exactly one user/assistant pair, one provider call/generation where applicable, and no retry after presentation/persistence failure;
- optional API requirement forwarding and rejection/ignoring of client activation/trusted-metadata attempts;
- normal non-Web chat and existing default Web-path compatibility;
- Safe Fetch public-IP/DNS pinning, redirects, extraction/ranking, exact-source evidence, batch rollback, canonical ordering and working context;
- existing Pipe authentication/session/endpoint/no-retry boundaries and in-process stubbed API transport.

No live searches, page fetches, Qwen inference, deployed API/chat calls or browser sessions ran. Models/providers/storage calls in the new tests are fixtures/stubs. Existing storage regression scripts use synthetic SQLite only inside temporary isolated paths. Writable home/data/cache/temp paths are redirected before imports; network, subprocess, deployed-data and private-home access are guarded, and embedding construction is stubbed to fail. Final completed drivers reported no network/private-access violations. These are application-level controls, not OS-level containment proof.

One sandbox run hit the previously observed existing ASGI thread-wakeup timeout and exited at its 30-second bound. The same guarded suite passed outside the sandbox; network/private-data guards remained active. That incomplete attempt is not counted as a pass. No real operation had an uncertain live outcome.

Git whitespace checks, exact staged file/byte review and scope checks passed. Lab stayed clean at the expected baseline. No runtime or data migration validation is claimed.

## G. Known limitations

- Feature defaults off; it is not installed or activated. Live provider reliability and latency remain unverified.
- Ordinary WebUI requests lack explicit structured requirements and therefore use a source-first fallback. No broad automatic synthesis or universal semantic verification is promised.
- Metadata role identification remains a trusted server adapter boundary. Version/date-dependent grounded generation stays conservative without that adapter.
- Explicit literal requirements can be a weak proxy for real question coverage. Passing them does not prove all generated claims or citations are correct.
- Greedy selection, fixed quotas and lexical ranking can omit useful content. Source identity does not prove independent corroboration.
- Query rewriting is skipped in MVP mode; existing query/provider length and transport limits still apply. There is no newly claimed strict cap on provider-library or SearXNG server-internal HTTP work.
- Presentation filtering favors safe plain prose and validated links over rich formatting. Native citation cards and actual remote HTTPS/Socket rendering remain untested.
- One subprocess-only regression is skipped. No live chat, model, canonical persistence or browser acceptance was performed.

## H. Exact Lab deployment requirements — not performed

The detailed reviewed procedure is in local code documentation `docs/prototypes/w2-1-web-mvp.md`. A later controlled stage requires:

1. Separate operator approval and runtime-drift preflight. Verify the actual running Lab image, installed Function, admin valves, API unit/data isolation and current Lab Git baseline before any mutation.
2. Consistent protected backups/recovery checkpoints for Lab WebUI/installed Function and valves, Lab canonical data and code. Retain credentials, signing secrets, persistent volume and rollback artifacts; never print or regenerate them for this change.
3. Promote the reviewed local integration history to Lab only: reused W2 commit `9b374cf2ef46ea08399b124e0c2a725d96c92a38`, then W2.1 `50a63850f83506724aaff4c2af4f50811d00d646`. Do not repeat an already integrated commit or push Lab/main/code branches. Stop on drift.
4. Update the existing **Lab** Function from the reviewed Pipe source before enabling backend fallback responses. Preserve its installed ID, current `INSTANCE_ID`, Lab endpoint `http://127.0.0.1:18096/api/chat`, Web mode and timeouts. Never adopt the source file's production compatibility default for Lab. Do not enable native WebUI search or alter WebUI image, volume, HTTPS/PWA, authentication or session mapping. Verify actual Function loading in that stage.
5. Set `CORVUS_WEB_MVP_ENABLED=TRUE` in a **Lab API-only** environment override, then perform the separately authorized restart of **only** `corvus-lab-api.service`. The flag is read at import. Keep existing data/model/provider configuration and loopback binding. No WebUI recreation or shared-model/Hindsight/Production/Demo restart is required by this patch.
6. Run separately authorized local and browser acceptance for fallback, failure, and any explicitly structured grounded case; verify existing-service regression and remote rendering independently. No canonical test turn or retry of uncertain turns is authorized by this report.

Rollback must disable the Lab backend feature first and restart only Lab API when authorized, then restore the saved Function/code if needed. Restoring a legacy Pipe while deterministic backend replies remain enabled would reject those replies. Preserve volumes, secrets and canonical turns; rollback is not permission to delete new user/assistant records. FoxGate, Cloudflare, DNS, Production and Demo are outside the boundary.

## I. Publication and next step

Only this sanitized report and its relative-link index entry are committed/pushed on `reports/web-validation`. Code, fixtures, raw metrics and terminal transcripts are not published. The code branch remains local; Lab/main remain unpushed. No passwords, tokens/cookies, private conversations, personal memory, database contents or unnecessary sensitive host details are included.

Next step: semantic review of the integration commit and the paired API/Pipe deployment contract, followed by a separately approved controlled Lab activation/acceptance stage. No further general benchmark, prompt-tuning loop or new infrastructure is required before reviewing this working source-first MVP.
