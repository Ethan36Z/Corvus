# R0.2 — Dedicated Lab FoxGate V2 preparation

Date: 2026-10-16. Branch: `lab/ow2e-console`.
Baseline: `7f389f183d01b6c1ad5e542b53a0132ee3cf1a0e`.

## State and architecture decision

**PREPARED**: dedicated deployment templates and offline contracts are ready
for a separately authorized controlled local deployment and acceptance stage.
**DEPLOYED: no. REMOTE_ACCEPTED: no.** Committing this preparation does not
authorize deployment or public routing.

Reuse the existing FoxGate V2 Auth implementation from `1009bba` and cached
pinned Auth/Nginx images. The external Auth checkout at
`/home/ethan/srv/infrastructure/demo-access` has HEAD
`a8aea8661ef140bf588c6663b82f6de98bd95043`; its Auth source has no differences
from `1009bba`. No FoxGate application source is changed or copied here.
Image identity inspection matched both configured pins; independent
binary-to-source provenance was not established.

The separate Compose project is `foxgate-lab`, with future runtime directory
`/home/ethan/srv/infrastructure/lab-access`. Proposed routing:

```text
HTTPS lab-corvus.foxluma.com
  -> future existing Tunnel route
  -> 127.0.0.1:8100 dedicated Lab gateway
       -> 127.0.0.1:8101 dedicated Lab Auth
       -> 127.0.0.1:3003 existing Lab WebUI
```

Host networking uses explicit loopback listeners, no published ports, and
read-only containers/mounts with dropped capabilities. Unknown hosts return
404. Application requests, including WebSocket handshakes, require Auth;
the verification location is internal. Fixed public forwarding fields preserve
application Authorization/Cookie headers. Local processes remain trusted.
The semantic review observed no listeners on 8100/8101; recheck before deployment.

## Credential and key isolation

Only Auth mounts these independent Lab paths:

- `/home/ethan/srv/shared/secrets/lab-access/gated.htpasswd`
- `/home/ethan/srv/shared/secrets/lab-access/session-hmac.key`

No Lab secrets have been created. Independent key material is a provisioning
requirement, not an established runtime fact. Never reuse Demo/Private secrets.
Missing bind sources fail instead of being created. The documented provisioning
subshell stops when the realm directory already exists; it must not overwrite
an existing realm. Use host UID/GID 1000:1000, directory mode 0700 and file mode
0600. No secret contents are included in this checkpoint.

Reviewed Auth source sets host-only Secure, HttpOnly, SameSite=Lax session
cookies with the supplied secure-cookie setting. WebUI retains its separate
authentication requirement. Runtime cookie and cross-realm tests remain pending.

## Files created

- `deploy/lab/foxgate/README.md`
- `deploy/lab/foxgate/compose.yaml`
- `deploy/lab/foxgate/nginx/nginx.conf`
- `deploy/lab/foxgate/nginx/gated-locations.conf`
- `tests/test_lab_foxgate_deployment.py`
- This checkpoint log.

The interrupted preparation was recovered and preserved. Finalization hardens
only the existing seven static tests and adds this log. Tests reject permissive
`satisfy any`, require exact secret/config mounts and environment mappings,
loopback bindings, the expected location set and auth directive, and the minimal
unknown-host rejection block. Comments cannot satisfy directive checks. These
are small static contracts, not a general Nginx parser or proof of runtime safety.

## Validation evidence and review

- Deployment contracts: `python3 -B -m unittest discover -s tests -p
  'test_lab_foxgate_deployment.py' -v` — all seven passed after hardening.
- `docker compose -f deploy/lab/foxgate/compose.yaml config --quiet` — passed.
- Pinned cached Nginx `nginx -t` — passed with `--network none`, read-only
  root/configuration, unprivileged UID/GID, no secrets and temporary `/tmp`.
  No gateway listener was started.
- `git diff --check` — passed; staged content is reviewed before commit.
- Prior Auth Go attempt failed during package setup because the offline cache
  lacked `golang.org/x/crypto v0.41.0`. **No Go tests executed; suite not passed.**
  No dependency downloads or environment changes were made to complete it.
- Independent semantic review: **PASS_WITH_CONSTRAINTS**, permitting only a
  separately authorized controlled local deployment/validation stage.

## Known limitations and next stage

Runtime Auth outage rejection, external verification denial, authenticated
WebSocket/SSE behavior, actual cookies, redirects, downstream proxy trust and
cross-realm session rejection remain unverified. The gateway healthcheck proves
only unauthenticated rejection, not successful login or WebUI readiness. Login
throttling shares the loopback peer key among Tunnel clients. Static tests do
not establish deployed behavior.

Public access also needs WebUI public URL/secure-cookie review and verified
Tunnel identity/HTTPS routing. Nginx's 600-second application timeouts and
disabled response buffering do not resolve Cloudflare's default 125-second
proxy read timeout. Slow non-streaming requests may complete durably after
browser timeout; do not automatically retry them. Resolve this contract before
public chat acceptance. Public/mobile/PWA acceptance remains separate.

Next: obtain separate authorization, recheck ports/images/configuration,
provision fresh Lab-only secrets, deploy only this project, and run controlled
local security acceptance. Any later public route requires separate authorization
and remote acceptance. No deployment, restart, Cloudflare change, secret
generation, Production/Demo modification or canonical memory modification was
performed during preparation/finalization. Only repository artifacts are committed;
no push is authorized.

## Rollback boundary

After a future deployment, remove only a subsequently added Lab public route
first, then stop only `gateway` and `auth` in Compose project `foxgate-lab`.
Retain Lab configuration and secrets for review. Do not remove volumes or
canonical data, stop Lab WebUI/API, alter the existing Tunnel, or touch
Production/Demo. Any later WebUI setting change needs its own rollback record.
