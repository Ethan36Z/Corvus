# Corvus W1.1 — Experiment Control Repair

Experiment: **W1.1**

Date: **2026-10-18**

Related Lab baseline: `975645963291ec992d64df0474a3ee9d0ba33dcd`

> Public archive copy. Account-specific checkout paths are replaced with
> `<lab-checkout>` (or `$LAB_CHECKOUT` in the historical command). Local `/tmp`
> artifacts are referenced for provenance only and are not included in this
> archive. The baseline identifies the local experiment checkout; it may not
> resolve on GitHub because its commits were unpublished. Verdicts, measurements
> and acceptance boundaries are preserved.

**W1_1_READY_FOR_RESUME** — offline controls repaired; new explicit operator authorization is required before live execution. Strict SearXNG server-internal HTTP limits remain unenforceable through its query interface.

## A. Root cause

Verified branch `lab/ow2e-console`, HEAD `975645963291ec992d64df0474a3ee9d0ba33dcd`, clean worktree in `<lab-checkout>`.

Installed DDGS 9.16.0 defaults to `backend="auto"`. Grokipedia is an enabled text backend; auto/all explicitly includes it. W1's manually maintained discovery allowlist omitted this installed backend. Its request was blocked, but DDGS swallowed the guard exception and returned other results. The original harness checked the violation only after orchestration, allowing the official-page fetch before stopping.

This was a harness control defect, not evidence that Grokipedia is malicious or that Corvus Safe Fetch contacted an unsafe address. Grokipedia remains excluded.

## B. DDGS explicit backend options

Installed enabled registry, inspected offline:

- Text: brave, duckduckgo, google, grokipedia, mojeek, startpage, wikipedia, yahoo.
- News: bing, duckduckgo, yahoo.
- Bing and Yandex text engines are disabled; availability is category-specific.

DDGS supports single/comma-separated `backend` arguments. Existing Corvus `DDGSProvider` already accepts this setting. The repaired experiment selects **duckduckgo only** for text and news, validating registry membership first. Invalid names can cause DDGS to fall back to auto, so auto/all, unknown names, lists and Grokipedia are rejected before provider execution.

Discovery destinations are narrowed to exact HTTPS hosts `html.duckduckgo.com` and `duckduckgo.com`. News may obtain a token before requesting news.js: one backend is not one HTTP request.

Engine selection uses supported configuration. No installed package files or engine-selection internals were patched. Temporary request-boundary instrumentation remains only for destination checks, transport counting and manual redirects, and is restored on exit.

## C. SearXNG bounded query options

Read-only installed source inspection confirmed `/search?engines=...` selects engines. Combining it with `categories` can add category engines; query bangs/specific routing can override selection; invalid names can fall back to preferences/categories.

The repaired adapter requests exactly **google cse** for general discovery or **google news** for news. It removes categories/category_* parameters, disables the Corvus adapter bang, and rejects routing overrides, duplicate/unexpected parameters and unexpected endpoints. Language/time-range fields remain. Client redirects are blocked. Raw responding-engine names and unresponsive_engines are retained; an unselected reported engine latches a stop.

The saved W1 inventory marked both engines enabled. Local settings use defaults, with no local preferences-lock or outgoing timeout/retry override. No deployed API calls were made in W1.1. Availability/preferences need fresh verification in a later authorized preflight.

**Limit:** one selected engine can perform multiple preparation, redirect or retry requests. The existing client interface cannot strictly count, cap or cancel server-internal HTTP work. Response diagnostics are not a transport audit. No service configuration was changed.

## D. Harness safety repair

- Repaired: `/tmp/corvus-w1-run.py`.
- Preserved original: `/tmp/corvus-w1-run.before-w1-1.py`.
- Added controls: `/tmp/corvus_w1_controls.py`.
- Added offline tests: `/tmp/test_corvus_w1_controls.py`.
- Added cumulative JSON ledger: `/tmp/corvus-w1-1-state/ledger.json`.
- Validation/hashes: `/tmp/corvus-w1-1-validation.json`.

The first mandatory stop is sticky and persists across repaired-run restarts. SafetyStop sits outside ordinary Exception recovery; checks before/after providers and before candidate, actual HTTP and future Qwen admissions remain effective even when a mock library catches BaseException.

Actual transport admissions are serialized without holding the provider lock while DDGS waits on a worker. Fetch HTTP accounting occurs at the actual connection request. Redirect budgets are reserved before redirected dispatch. Counters persist before dispatch and are never refunded after uncertain outcomes. Ledger failure blocks dispatch; a process lock prevents concurrent runners; pending interrupted plans cannot automatically resubmit. Completed W1 case 1/DDGS is skipped.

Default runner execution is OFFLINE_NO_DISPATCH. No Phase-B inference implementation is enabled. Future Qwen use has an explicit guarded admission method, tested with mocks only.

Corvus Safe Fetch, public URL/IP restrictions and TLS validation remain unchanged. Future Phase-A execution establishes isolated data/cache paths before application imports and forbids SQLite connections/subprocesses.

## E. Offline validation

**15 tests passed, 0 failed.** Tests blocked socket connect/create_connection/getaddrinfo and forbade SQLite connections.

Covered: unexpected destination blocked before dispatch; swallowed stop cannot reach candidate fetch or later provider/HTTP/Qwen callbacks; allowed mock responses; explicit backend forwarding/installed text-news selection without searching; worker deadlock prevention; exact SearXNG engine-only selection; routing/duplicate/endpoint rejection; cumulative/per-plan/redirect/deadline budgets; loopback fetch rejection; historical accounting; persistence-before-dispatch and ledger failure; durable stops and interrupted-plan refusal; inert runner import/default mode.

No live search, Qwen inference, deployed API call or database write occurred. Offline mocks prove these control contracts, not live provider reliability or OS-level containment.

## F. Remaining limitations and preserved accounting

| Counter | W1 consumed, unchanged | Cumulative cap | Remaining |
|---|---:|---:|---:|
| Initial plans | 1 | 16 | 15 |
| Provider calls | 1 | 32 | 31 |
| Candidate fetches | 1 | 48 | 47 |
| DDGS HTTP dispatches | 10 | 128 harness cap | 118 |
| SearXNG search HTTP calls | 0 | 32 harness cap | 32 |
| Candidate-fetch HTTP dispatches | 1 | 96 harness cap | 95 |
| Redirect hops | 2 | 64 harness cap | 62 |
| Qwen turns | 0 | 8 | 8 |

Historical elapsed 4.342 seconds is retained against the cumulative 900-second envelope. Per-plan deadline: 45 seconds; DDGS per-plan HTTP cap: ten. DDGS redirects: two hops per chain; candidate redirects retain Corvus's three-hop bound and consume shared counters before redirected dispatch.

In-flight work cannot be recalled. A local stop cannot cancel already-started SearXNG server work; its internal HTTP counts remain outside client caps. No strict whole-system transport-cap claim is made.

Narrow backend selection changes the experiment: future results compare explicit configurations, not deployed DDGS auto versus default SearXNG fan-out. W1's original sample remains separate. Live availability, CAPTCHA/rate-limit behavior, answer synthesis and Phase-B persistence are unverified.

## G. Exact minimal live test proposal — NOT EXECUTED

After **new explicit operator authorization**, including acknowledgement of the SearXNG internal-transport limitation, run W0 case 2's frozen query sequentially:

1. DDGS backend=duckduckgo.
2. SearXNG engines=google cse, without categories/bangs.

Maximum: **2 new plans, 2 provider calls, 6 candidate fetches, 0 Qwen turns**. Cumulative upper bounds become 3/16 plans, 3/32 provider calls and 7/48 candidate fetches; transport/redirect/deadline caps remain. Stop on any latch; do not widen destinations or retry uncertain work automatically.

Proposed command, not executed:

```sh
env -i PATH=/usr/bin:/bin LANG=C.UTF-8 PYTHONDONTWRITEBYTECODE=1 "$LAB_CHECKOUT/.venv/bin/python" -B /tmp/corvus-w1-run.py --resume-authorized --case 2 --max-new-plans 2
```

If a strict cap on all SearXNG upstream traffic is required, do not use this shared-service arm; a separately designed containment/telemetry solution is necessary.

Existing W1 report/metrics were preserved. No repository source, deployed configuration, service, authentication, networking, Hindsight or Personality changes. Git remains clean; no commit or push.

Preceding live experiment: [W1 report](2026-10-18-w1-live-validation.md).
