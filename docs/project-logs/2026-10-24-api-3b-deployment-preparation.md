# API-3B — independent deployment preparation

Date: 2026-10-24 (America/Los_Angeles)
Status: **API_3B_STAGED_READY** — not installed, activated or published.

## Baseline and preservation

Worktree `/home/ethan/srv/apps/corvus-api-v1`, branch `feature/api-v1`, started
clean at approved API-1 `c2bc84f7cc898ada10b23f5e23f526ad310d4952`.
GitHub confirmed that feature SHA and integration
`56a615e5a0b334bc05b87560148b6eaead62bcc6` before preparation. No branch switch,
merge, shared-service restart or deployment. API-2 local SDK acceptance and API-3A
were read and reused. Lab's 28 pending paths, W1's two drafts, the integration
baseline and existing FoxGate work remain outside this change.

## Actual infrastructure verification

Read-only authenticated Cloudflare dashboard inspection establishes the remotely
managed Tunnel dashboard/account as the authoritative configuration source.
`ethan-home` is healthy with one desktop connector on cloudflared 2026.10.1 and
nine applications. Production/Lab/Demo Corvus hosts map to their existing
127.0.0.1 ports 8093/8100/8091. Their DNS records are proxied CNAMEs to that Tunnel;
no API hostname or wildcard DNS record exists. No Tunnel credentials were read.

The zone uses Free: 0 custom WAF rules, 0 rate-limit rules, 0 user-created managed
rules; separate settings show always-active Cloudflare managed/DDoS protection.
Bot Fight Mode, Precursor and Under Attack Mode are off; Browser Integrity Check
is on. Cache level Standard, browser TTL four hours; 0 cache rules, 0 response
cache rules, 0 Page Rules; Always Online off. Worker Routes shows no configured
routes. Access opens the Zero Trust welcome/onboarding screen, with no configured
application visible; no additional Access credential requirement was found.
No onboarding, account setting, route, policy or DNS mutation was performed.

These observations support Bearer-only service authentication without changing
browser FoxGate. They are not a policy export or a universal SDK compatibility
claim. The full Tunnel backing JSON/final catch-all, possible account-level
transforms/log capture and configuration revision need a fresh operator check
before any additive apply. API-3A's earlier unknown account-side settings are
partly resolved by this inspection; no speculative global security bypass is
required or prepared.

## Prepared files and operational choices

The deployment folder now contains:

- A separate `corvus-text-api.service`, dedicated UID, standard systemd minimal
  RootDirectory and readonly binds; no borrow of a running venv or private mounts.
- A small direct-process `serve.py` bootstrap: exact environment, private-path
  absence, five-file approved source manifest and existing safe auth-file checks
  before listener startup; no inference or shared process action.
- Hashes pin the five unchanged API/runtime dependencies to approved API-1. Only
  those five application files are exported into a fresh release. No second API,
  prompt builder, inference transport or memory implementation was introduced.
- Exact new-host regex ingress plus hostname-specific 404 fallback. Separate
  proposed fragments block plaintext HTTP for this hostname and bypass caching;
  neither is a complete Tunnel/ruleset configuration nor automatically applied.
- Reviewed installation, key lifecycle, graceful stop/rollback and off-host SDK
  acceptance instructions in `deploy/lab/api-v1/DEPLOYMENT.md`.

Uvicorn remains the main process so systemd signals reach its own graceful handler.
No auto restart or forced SIGKILL; infinite stop timeout preserves worker drain,
with a documented possible deactivating/host-shutdown wait. If completion is
unknown, close only the API route, revoke API keys and report incomplete drain;
never disrupt shared inference to claim cleanup. Actual source/dependencies are
readonly; digest directory is mounted as a directory so atomic key replacement
remains visible. No real credentials were generated or committed.

## Offline validation

**34 tests passed**: 10 deployment tests, the existing 17 API contract/security/
statelessness tests and 7 transport/legacy-caller tests. Tests used a readonly
source overlay and dependency mount in a minimal-root bwrap sandbox with its
network namespace isolated. No API listener, model/token-count call or live
fault injection. Coverage includes startup refusal, source integrity, private
path exclusion, explicit limits and graceful-run settings, exact route deny
cases, authentication/rotation, JSON verification, timeout/disconnect/worker
ownership and unchanged legacy client behavior.

`systemd-analyze verify` passed using the **unmodified unit** in a disposable
system root with target/executable fixtures. This verifies syntax/directives,
not live cgroup enforcement, dedicated UID provisioning or privileged mount
setup. Direct host validation cannot resolve an uninstalled `/opt/venv` binary;
no deployment was performed to manufacture a passing check. Kernel enforcement,
independent venv reproduction and actual PID mounts must be verified at the
separately authorized loopback activation gate. Existing API-1 broader Python and
Voice regression results are reused, not relabeled as newly executed.

Detailed sanitized observations, logs and preservation evidence are in
`/tmp/corvus-api3b-preparation-t3o3vqh5/`. Only preparation docs/configuration,
deployment bootstrap and focused tests belong in this commit; API-1 implementation
files and integration HEAD are unchanged. Diff and sensitive-value checks precede
explicit staging/feature-only commit and push.

## Activation prerequisites and limits

No persistent API unit/UID/release/key installation or hostname publication yet.
Fresh resource gate: >=2 GiB available RAM, cgroup headroom and no continuing
paging; do not stop shared services for capacity. Initial available RAM was
7.666 GiB with quiet memory PSI and zero swap paging in a short sample, while
swap free remained only 66.44 MiB; activation must recheck.

Separate authorization is still needed for new service/account/secret provisioning,
account-side route/DNS/HTTP-block/cache changes and at most two sequential remote
synthetic inference requests. Remote acceptance requires ordinary SDK settings
plus retry disablement, no Cookie or Cloudflare-specific credential. If Access
becomes required it adds a second credential pair; report contract impact rather
than overloading Authorization. Never embed the permanent operator key in public
client code. Cloudflare remains a plaintext-processing TLS trust boundary.

No streaming, strict JSON Schema, companion memory, replay deduplication or global
model fairness is added. Shared Qwen contention and the existing companion
BackgroundTasks -> durable retain-intent/automatic recovery gap remain. Local
API-2 acceptance and staged readiness do not certify remote deployment, Production
release or complete disaster recovery. Stop after preparation.
