# W2.1 source-first Web MVP integration

Prepared integration only; no deployment or browser acceptance. The feature is
**off by default** (`CORVUS_WEB_MVP_ENABLED=FALSE`). Enabling it is a later,
Lab-only operator action. W2 is reused rather than replaced.

## Review of W2

No critical safety/data-integrity defect requiring a stop was found in the
reviewed, opt-in W2 scope. Its limits remain explicit: metadata adapters must
identify the *role* of a date/version; exact text witnesses do not prove that
role. Distinct URLs/bodies do not prove independent authorship. Empty structured
requirements do not establish semantic sufficiency. Those limits are handled
conservatively here rather than claiming a general verifier.

Default orchestration, model interface, evidence packing and persistence remain
compatible. The integration preserves the original `process_turn` positional
arguments and appends the new optional controls. No dependency was added.

## Outcomes

When the Lab flag is enabled and a text turn needs Web:

| Outcome | Behavior |
| --- | --- |
| `GROUNDED_ANSWER` | Explicit nontrivial coverage requirements pass W2, with no provider failure; existing context/model/packer produce the answer, followed by validated Markdown source links |
| `SOURCES_WITH_LIMITATIONS` | Fetched/extracted pages exist, but requirements are unknown, incomplete, mismatched or accompanied by partial provider failure; deterministic limitations and source links, no answer-model call |
| `SEARCH_FAILED` | Provider/intent/preparation failure, genuine empty discovery, or no verifiable page; deterministic honest failure, no answer-model call |

These presentation outcomes are exposed only after the canonical assistant
commit. Existing technical/persistence statuses are retained. A deterministic
reply reports `model=NOT_CALLED`, not a fictitious model success. API overall
status may consequently be `DEGRADED`, which is expected for this outcome.

Missing version/date metadata means *unverified*, not false. Only actual
fetched/extracted pages become links; unfetched discovery hits/snippets are
omitted. At most three candidates and two displayed distinct source URLs are
considered, with W2's 3,600-character selected-evidence budget. Ordinary unknown-
requirement fallback may stop after the first usable page; explicit unmet
requirements can continue within the three-page bound.

No new search pipeline, native WebUI search, query-rewrite model call, provider
fallback or automatic retry is introduced. Existing provider selection remains
configured by `CORVUS_WEB_PROVIDER`. Auto intent retains its existing behavior;
an intent exception in MVP mode becomes an honest failure rather than silently
falling through to a potentially fresh-fact model answer.

## Explicit requirements and trust

The existing API gains optional structured `web_requirements`, represented by
W2 `EvidenceRequirements`. For example, a trusted local caller can explicitly
require `required_text=["Connection.autocommit"]`. Version/date/source-count
requirements remain available. Fields constrain coverage; they are not a proof
that the model's entire answer is correct.

The caller cannot activate the server feature or supply trusted `SourceFacts`.
Those facts remain server-side adapter inputs. No general parser or real-site
version/date adapter is added. Consequently metadata-dependent questions without
such facts conservatively produce links and limitations. The installed Pipe
continues to send only the ordinary message/session/web-mode payload and does
not infer requirements from natural language. Normal WebUI Web queries therefore
use the source-first fallback. A broader automatic synthesis policy is deferred.

SearXNG has an optional raw-diagnostic callback before normalization. The MVP
captures selected engine failures without exposing raw backend messages.
Access-denied plus empty results is `PROVIDER_FAILED`, not genuine `NO_RESULTS`.
Partial failures with usable content remain visible as limitations. The default
adapter behavior is unchanged when no callback is supplied.

## Persistence and presentation

The existing canonical path still commits the user first. Grounded turns use
exact W2 evidence in the existing packer and commit final assistant text before
persisting that exact evidence set and performing derived dense sync. The final
canonical reply includes the presentation-filtered answer and source section,
so the text returned to WebUI matches the assistant record.

Deterministic link/failure replies take the same assistant-commit/dense-sync tail,
without model context, personal recall or generation. They report Web evidence
`NOT_USED`; no model-evidence provenance rows are invented for pages that only
supplied links. Links are present in the canonical assistant text. No schema,
Evidence Log ownership, Hindsight lifecycle or Arena change is made.

The simple Markdown footer is built only from validated final retrieval URLs
and source identities. Grounded reference IDs come from W2; invalid model refs
are not promoted into source citations. Model-generated link syntax/URLs are
removed or escaped; model text is rendered as conservative prose, which can
reduce rich code/Markdown formatting. This is presentation filtering, not
factual verification. Native cards/events and `[web_n]` numeric-inline mapping
are not required for this MVP.

The Pipe accepts deterministic fallbacks only with the same mapped session,
explicit fallback outcome, insufficient-evidence status, `model=NOT_CALLED`, a
positive assistant message ID, confirmed overall status and `persistence=NORMAL`.
All endpoint/auth/session/text-only/Arena guards remain. Presentation or transport
failure never resubmits a POST. An uncertain result must not be automatically
retried, even if no response reached the browser.

## Offline checks

Use the existing environment, with no dependency installation:

```sh
/path/to/existing/venv/bin/python -B tests/run_web_acceptance_offline.py test_web_mvp.py
/path/to/existing/venv/bin/python -B tests/run_web_acceptance_offline.py test_web_acceptance.py
```

The guarded driver denies network and private/deployed data access, redirects
writable paths before imports, stubs embedding-model loading, limits SQLite to
synthetic temporary data and bounds each module to 30 seconds. The inherited
fresh-subprocess Pipe test is explicitly skipped. The sandbox's existing ASGI
thread wakeup stall can require running the same guarded tests outside the
sandbox; no network/private-data guard is removed by doing so.

Tests cover all three outcomes, version/date rejection, exact multi-source
provenance, one canonical user/assistant pair, provider failure/empty distinction,
partial provider failure, presentation failure without retry, API requirement
forwarding, client activation/metadata rejection, metadata-only source links,
normal-chat compatibility, and inherited Pipe safety contracts. Generated text,
provider responses and storage calls are fixtures/stubs; no real model or chat
turn is submitted. Existing persistence tests use temporary synthetic SQLite.

## Exact deployment prerequisites — separate authorization required

1. Review the integration code and local commit chain, and verify actual Lab
   branch/runtime/installed Function before any mutation. The reviewed starting
   Lab commit was `975645963291ec992d64df0474a3ee9d0ba33dcd`. Stop on drift.
2. Obtain operator approval for a consistent protected Lab WebUI backup/export
   of the current Function and valves, Lab canonical-data recovery checkpoint,
   Lab code promotion, Function update and **Lab API-only** restart. Preserve
   existing credentials, signing secrets, volume, Function identity and session
   mapping. Do not delete or rewrite canonical turns for rollback.
3. Promote the reviewed W2 plus W2.1 local integration history to Lab only. Do not
   push code/main/Lab or alter Production/Demo. No deployment artifact/unit was
   changed by this stage; keep a code rollback point.
4. Update the existing **Lab** Function from the reviewed
   `deploy/open-webui/corvus_pipe.py` before enabling the new backend behavior.
   Preserve its installed ID and admin valves, especially the current Lab
   `INSTANCE_ID`, `CORVUS_CHAT_URL=http://127.0.0.1:18096/api/chat`, Web mode and
   timeout. Never use the source file's compatibility default production URL as
   a new Lab setting. The updated Pipe remains compatible with legacy model-OK
   responses. Do not create another Function/realm, enable native search or
   change WebUI image/volume/HTTPS configuration. Verify actual Function loading
   in the subsequent controlled stage; no WebUI restart is required by this
   source patch itself or authorized here.
5. In a **Lab API-only** environment override, set
   `CORVUS_WEB_MVP_ENABLED=TRUE`. The flag is read at process import, so restart
   only `corvus-lab-api.service` after code and Pipe are ready. Keep its existing
   `CORVUS_DATA_DIR`, model endpoint, provider setting and isolation unchanged.
   A later authorized operator may use a dedicated systemd drop-in; never edit
   shared/default Production or Demo settings. No restart is performed here.
6. Perform separately authorized local health/contract checks, then browser
   acceptance of saved-chat source fallback, failure, and any explicitly
   structured grounded case. Check remote HTTPS/Socket behavior independently.
   Do not invent live-provider success or submit canonical test chats without
   authorization. Avoid retrying uncertain turns.

Rollback: disable the Lab-only flag and restart only Lab API when authorized,
then restore the backed-up Lab Function/code if needed. Keep existing volumes,
secrets, canonical data and committed synthetic/user turns. Restoring the legacy
Pipe while MVP fallback responses remain enabled would reject them, so disable
the backend feature first. Production/Demo/FoxGate/Cloudflare are outside this
rollback boundary.
