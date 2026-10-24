# Corvus v1 — Release candidate readiness

Date: 2026-10-24 (America/Los_Angeles).
RC verdict: **RC_READY_WITH_LIMITATIONS**.
Recommendation: **GO for v1 release candidate (source), with the limitations below**.

This record integrates the accepted API v1 work into `integration/corvus-v1` and
gives the result of the final offline regression run. This is source integration only. It does
not deploy anything, publish a Production release, tag the code, or start a new development cycle. No service,
container, credential, private database, runtime memory or Cloudflare setting
was restarted, reconfigured or read for content.

## Version scope

Corvus v1 = the accepted v1 capabilities below, each within its own previously
defined acceptance scope. No new feature work happened at this stage.

| Capability | Source of record | Acceptance record |
| --- | --- | --- |
| Companion conversation, Evidence/RAG, H1 memory and admission | Lab and closure ancestry in baseline | `2026-10-11-h1-final-daily-use-acceptance.md` |
| Personality P0.3/P0.4 (opt-in profile 0.1.1) | 236b79b, dcc2e8a, b99a5d5 | `2026-10-22-personality-p0.4-lab-acceptance.md` |
| Web W1/W1.1/W2 and stage seal | 9331541 | `2026-10-23-web-stage-integration-seal.md` |
| Vision (single store, preview, resize) | multimodal closure 01797c5 | `2026-10-20-multimodal-v1-engineering-and-decisions.md` |
| STT, Kokoro TTS, half-duplex Voice Call | 75e3cf9, 0406e2d, f6d94ff…2bdd7ff | `2026-10-23-voice-v1-lab-seal.md` |
| Production foreground publisher | code byte-identical to main f240896/c315d0e | `2026-10-23-corvus-v1-pre-api-source-closeout.md` |
| **API v1** (stateless OpenAI-compatible text subset) | c2bc84f…ea1ea96 | `2026-10-24-corvus-api-v1-activation.md` (`API_3D_ACCEPTED`) |

## Integrated source

| Item | Value |
| --- | --- |
| Branch | `integration/corvus-v1` |
| Pre-API baseline (first parent) | `56a615e5a0b334bc05b87560148b6eaead62bcc6` |
| API feature tip (second parent) | `ea1ea9669ae8a32c48cefd47dcee9e2b96b806de` (`feature/api-v1`) |
| Integration merge | `ef6636c` — `git merge --no-ff feature/api-v1` |
| API implementation commit (manifest) | `c2bc84f7cc898ada10b23f5e23f526ad310d4952` |

Pre-merge state, checked against the freshly fetched origin: `integration/corvus-v1`
was at the baseline both locally and on origin (0/0 divergence).
`feature/api-v1` was the baseline plus four commits, with matching local and
origin tips. The merge was conflict-free. It adds 18 files (+2078 lines) and changes no
existing file. Its diff against the baseline is byte-identical to
`56a615e..feature/api-v1`. All changed paths are inside the API scope (`app/api_auth.py`,
`app/model_client.py`, `app/openai_api.py`, `deploy/lab/api-v1/`, API docs and
the three API tests). The companion, memory, personality, Web, Vision and Voice
source is therefore unchanged from the accepted baseline.

`main` (8b863ec) was deliberately not merged. This follows the pre-API closeout: its two personality
commits are patch-equivalent to integration commits, and its Production
publisher code is byte-identical here. Only the H1-7c-8/7c-9 log files remain
main-only. Lab's local `lab/ow2e-console` (4f8013a) is fully contained in the
baseline. It is 10 commits ahead of its origin branch, which was not pushed here.

## Validation

### Newly executed (this stage, 2026-10-24)

The run used the established API-1/pre-API bwrap harness with the integration tree mounted
read-only at the Lab path. Network was unshared, `/run`, `/etc/corvus-lab` and
`/home/ethan/srv/data` were replaced by empty tmpfs, the Lab venv was read-only,
and synthetic data and keys were used with mocked inference and embeddings
forbidden.

| Suite | Result |
| --- | --- |
| API v1: `test_openai_api.py` (contract, auth, rotation/revocation, isolation) | 17/17 passed |
| API v1: `test_model_client_api.py` (optional model transport) | 7/7 passed |
| API v1: `test_api_deployment.py` (preflight, unit, manifest, ingress) | 10/10 passed |
| Existing Python regressions: personality, memory Arena, Web MVP/source boundary/W2, attachments, STT/TTS, async retain/reconciliation, Open WebUI Pipe, foreground activity/publication, Production compatibility | 282 cases: 280 passed, 2 skipped (existing subprocess-only Pipe cases, blocked by the offline guard; not counted as passes) |
| Module-level assertion scripts: personality runtime, Vision runtime, Voice runtime, Voice API contract | 4/4 passed |
| Voice Call Node suite (`test_voice_call.mjs`) | 17/17 passed |

That is 24/24 suite runs with exit code 0 and no network or private-access violations
reported by the guard. The existing-regression counts are identical to the
pre-API closeout (282/280/2, 4 scripts, 17 Node). The merge changes no existing file, so this confirms
that the companion, memory, personality, Web, Vision and Voice pathways are unchanged.

Static and parity checks:

- `git diff --check 56a615e HEAD`: clean. All API Python files parse. All
  `deploy/lab/api-v1/*.json` files are valid.
- `source-manifest.json`: all 5 integrated app files match their SHA-256 hashes.
- The live API release `/opt/corvus-text-api/release/app/*` is byte-identical to
  the integrated files. The installed `corvus-text-api.service` is byte-identical to
  `deploy/lab/api-v1/corvus-text-api.service`.
- Secret-pattern scan of the merged diff: no hits. This scan is not a full security audit.

### Reused historical evidence (not repeated)

- Live API acceptance through the public edge, including off-host MacBook acceptance, key
  revocation and the official SDK: `2026-10-24-corvus-api-v1-activation.md`.
- Real-model API checks and the API-2 readiness run from the API stage records.
- Voice, Web, Vision, personality and memory user acceptance from their seals. This
  includes Vite/client/SSR build evidence from 45a70cf and the Voice seal.
- No live inference, browser build, fault injection or service operation was
  run to enlarge coverage.

## Current deployment state (read only, unchanged by this stage)

| Component | State |
| --- | --- |
| Production API `corvus-api` | active, enabled, `Restart=on-failure`; runs from the `main` checkout (8b863ec) |
| Demo API `corvus-demo-api` | active, enabled; daily 04:00 reset timer |
| Lab API `corvus-lab-api` | active, enabled, `Restart=no`; lab/ow2e-console 4f8013a + 28 preserved local changes |
| API v1 `corvus-text-api` | active, enabled, `Restart=no`; 127.0.0.1:18120 via Cloudflare `api-corvus` |
| Qwen llama.cpp, Open WebUI Lab, Hindsight, Kokoro, Whisper/STT, SearXNG, FoxGate | Docker, `unless-stopped`, running |
| Cloudflare Tunnel | active, enabled, `Restart=on-failure` |

Reboot audit (same day, read only): `REBOOT_READY_WITH_LIMITATIONS`.

The integration branch is a source RC. Production and Demo still run `main`, and Lab
runs its own worktree. Switching any deployment to this branch needs separate
authorization.

## Known limitations (preserved)

- API v1 is a documented **subset** of OpenAI Chat Completions. It is text-only,
  non-streaming, single model `corvus`, Bearer key, and has a restricted parameter set (`docs/api/v1.md`).
  It is not full OpenAI compatibility.
- API generation is **stateless** and isolated from private companion memory,
  personality and Hindsight. It cannot see any of them.
- All inference shares the existing **single Qwen slot**, so API, Lab, Production,
  Demo, Voice and Hindsight requests queue and wait on each other.
- Some startup paths have **not been through a full reboot**. API v1 was enabled
  after the last boot. The Lab Open WebUI/STT credential move to persistent
  `/etc` storage has been through a Docker daemon restart, but not a host reboot.
- Crash recovery is **deliberately disabled** (`Restart=no`) for `corvus-text-api`
  (documented design) and `corvus-lab-api`. A crash needs a manual start.
- Earlier quality limits remain: Voice Call needs manual confirm/send and has no VAD or
  streaming. The P0.2 personality quality BLOCK still applies, and Lab opt-in is not a quality release.
  Web/Vision limits are as recorded in their seals. There are retain-handoff gaps and no
  complete Hindsight disaster-recovery claim.
- Credentials, private backups, model/voice weights, images and Cloudflare
  account configuration are not restorable from GitHub source.

## Remaining operational risks

1. A crash of API v1 or the Lab API leaves that service down until someone starts it by hand.
2. The first full host reboot with API v1 and the moved STT credentials still needs to be watched.
3. Contention on the shared Qwen slot under concurrent API and companion use.
4. Production/Demo source is `main`, not this RC branch. Promotion is a separate step.

## Git and worktree preservation

- Only the `corvus-v1-integration` worktree was written. No reset, clean, stash,
  rebase, force-push, tag or GitHub Release was used.
- Every other worktree's HEAD and `git status --porcelain -uall` hash were recorded
  before and after this stage and were unchanged. This includes Lab (28 pending entries)
  and W1 (2 untracked drafts).
- Stale `/tmp` worktree registrations (prunable) were left as they were and not pruned.
- Mac-side working copies could not be inspected from this host. Only their pushed
  refs (seen on origin) are represented.
- Push target: `integration/corvus-v1` only, a normal fast-forward push.
