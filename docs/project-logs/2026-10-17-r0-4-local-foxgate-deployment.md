# R0.4 — Controlled local Lab FoxGate deployment

Date: 2026-10-17 local. Branch: `lab/ow2e-console`.
Git baseline: `0f9094cde3cedd7731c06e8c23354195338cf82b`.
Final verdict: **LOCAL_DEPLOYED_WITH_CONSTRAINTS**.

## State and authorization

- **LOCAL_DEPLOYED**: dedicated Lab Gateway and Auth are running and healthy.
- **LOCAL_AUTH_ACCEPTED** for the executed local checks below; the full
  bidirectional realm-isolation matrix remains incomplete as explicitly allowed
  by the operator. Reverse-direction sessions are **NOT_VERIFIED**.
- **REMOTE_NOT_CONFIGURED**: no Cloudflare/DNS/public ingress configuration was
  changed. Actual HTTPS browser authentication and mobile/PWA installation are
  not accepted by these local HTTP tests.

Read-only preflight confirmed the expected clean Git baseline, cached image
pins, healthy existing Lab/Production services, no existing `foxgate-lab`
containers, absent Lab runtime/secret directories, and free ports 8100/8101.
The initial Demo probe used an unconfigured hostname and returned 404; inspection
identified `demo-corvus.foxluma.com`, whose unauthenticated response is 401.
The operator then explicitly approved Phases 2–5, forbidding use of existing
Demo/Private signing keys and permitting reverse-direction checks to remain
unverified. Only the new Lab Auth interruption was authorized.

## Deployed configuration and credentials

Runtime configuration: `/home/ethan/srv/infrastructure/lab-access`.
The committed R0.2 Compose and both Nginx configuration files were copied with
exclusive creation, validated, and compared byte-for-byte after deployment.
Compose project: `foxgate-lab`, containing only `auth` and `gateway`.

| Component | Listener / origin | Image |
| --- | --- | --- |
| Lab gateway | 127.0.0.1:8100 | nginx@sha256:a8b39bd9cf0f83869a2162827a0caf6137ddf759d50a171451b335cecc87d236 |
| Lab Auth | 127.0.0.1:8101 | foxgate-auth@sha256:2d7745847cb4f5875496830082bd9bcd5bbc5aa1d0c8733e18a07646d4772523 |
| Existing Lab WebUI | 127.0.0.1:3003 | unchanged UI-2.1 image |

Only Host `lab-corvus.foxluma.com` selects the Lab application virtual host.
Both new containers use host networking, UID/GID 1000:1000, read-only roots and
bind mounts, dropped ALL capabilities, and restart policy `unless-stopped`.
The dedicated runtime and nginx directories are mode 0700.

Fresh random Lab-only password and 32-byte HMAC material were generated locally.
Host Blowfish bcrypt support produced a cost-12 hash; the actual Auth service
accepted it through a real local login. No existing realm signing key or
credential was read or used to create test sessions.

The mode-0700 Lab secret directory is
`/home/ethan/srv/shared/secrets/lab-access`, owned by UID/GID 1000:1000.
It contains mode-0600, UID/GID 1000:1000 files:

- `gated.htpasswd`
- `session-hmac.key`
- `operator-login.json` — retained for operator retrieval and secure storage;
  it has not been automatically deleted. Never print, log, or commit its password.

All paths were exclusively created; no existing material was overwritten.
No credential or cookie values are included in this log. Session cookies were
held only in temporary process memory, not persisted in repository artifacts.

## Validation and acceptance observations

The seven existing deployment contracts passed. Compose config validation and
network-disabled, read-only Nginx syntax validation of the copied runtime files
passed before activation. Only the dedicated project was started with
`up -d --no-build --pull never --wait`; no image was built or downloaded.

All **25 recorded local acceptance checks passed**:

| Check | Observed result |
| --- | --- |
| Unknown Host | 404 |
| Unauthenticated WebUI API request | 401 |
| HTML navigation without session | 302 to relative Lab login path |
| Lab login page | 200 |
| Real Lab credential login | 303 and session issuance |
| Cookie header | Secure, HttpOnly, SameSite=Lax, Path=/, no Domain |
| Lab-session request to upstream `/health` | 200 |
| Lab session without WebUI login at `/api/v1/auths/` | 403; separate WebUI authentication retained |
| Lab session sent to Demo gateway | 401 |
| Lab session sent to Private gateway | 401 |
| External request to internal verify endpoint, with and without query | 404 |
| Unauthenticated WebSocket upgrade request | 401 |
| Auth stopped: valid-session API request | 500, fail-closed |
| Auth stopped: valid-session HTML request | 500, fail-closed |
| Auth restored | Authenticated upstream `/health` returns 200 again |
| Lab listeners | Only 127.0.0.1:8100 and 127.0.0.1:8101 |
| Other listeners | Unchanged from baseline |
| Existing container identities, start times, images, mounts and running states | Unchanged |
| Fingerprinted persistent database files | Unchanged |
| Six existing Demo/Private gateway configuration files | Unchanged |
| Existing environment health | Expected responses retained |
| Three Lab secret-file permission checks | 0600, UID/GID 1000:1000 |

The new Lab Auth was stopped only for the bounded fail-closed test and restarted
in a finally block. Both `foxgate-lab-auth-1` and `foxgate-lab-gateway-1` were
confirmed healthy after restoration. No acceptance failure occurred and no
deployment rollback was necessary.

Secure cookies were explicitly supplied in synthetic Cookie request headers
over loopback HTTP to test authorization. Header-level flag verification is
separate from browser transport behavior: Secure was not disabled, browser HTTP
exceptions were not used, and no actual HTTPS browser login is claimed.

## Existing environment and data regression

Final local health responses:

- Production API `127.0.0.1:8096/api/health`: 200.
- Demo gateway on 8091, Host `demo-corvus.foxluma.com`: 401 without credentials.
- Private gateway on 8093, Host `corvus.foxluma.com`: 401 without credentials.
- Lab WebUI `127.0.0.1:3003/health`: 200.
- Lab API `127.0.0.1:18096/api/health`: 200.

The original Lab WebUI, Demo/Private Auth/gateways, Production/Demo frontends,
Hindsight Lab and Qwen container identities, images, start times, mount
configuration and running state remained unchanged. The Lab WebUI still uses
`sha256:8dea93c991ce80e1d1496783ee7badca025ec38be3fee666a682a679705980be`;
the HTTPS override was not activated.

Before/after SHA-256 and size fingerprints matched for the Lab, Private and Demo
canonical `corvus.db` files and Lab WebUI `webui.db`. No corresponding WAL files
were present in those snapshots. These checks cover the named files, not every
file in every persistent volume. Fingerprinting exposed no conversation content.
No chat turn, WebUI user login, canonical write, Hindsight operation, or model
generation was submitted. Only public/static health/authentication endpoints
were exercised. Existing Docker access logs may naturally record these probes.

## Remaining constraints

- Valid authorized Demo/Private sessions were unavailable. Their rejection by
  the Lab gateway is **NOT_VERIFIED**; no existing keys or sessions were accessed
  or manufactured to fill that gap.
- HTTPS browser authentication: **NOT_VERIFIED**.
- Authenticated WebSocket delivery: **NOT_VERIFIED**. An unauthenticated upgrade
  denial does not prove authenticated WebSocket reliability or missed-result recovery.
- Mobile/PWA installation: **NOT_VERIFIED**.
- Public hostname access, SSE delivery and Cloudflare timeout behavior remain
  unverified.
- R0.3 URL/cookie/PWA preparation remains undeployed. Existing local WebUI
  authentication/settings were deliberately preserved.
- Cloudflare's default 125-second origin read timeout is not resolved by these
  checks. Do not automatically retry an uncertain canonical turn.
- The earlier offline Auth Go suite never executed because its module cache was
  incomplete; the successful live bcrypt login is not a substitute for that suite.

## Rollback and handoff

If rollback is later required, stop only the dedicated Lab project:

```sh
docker compose -p foxgate-lab \
  -f /home/ethan/srv/infrastructure/lab-access/compose.yaml \
  stop gateway auth
```

Retain Lab configuration and secrets, particularly `operator-login.json`, for
operator retrieval/review. Do not remove volumes, keys, canonical data, existing
realms or the Tunnel. No existing service belongs to this rollback boundary.

Deployment execution ended with this log uncommitted at the baseline HEAD.
The separately authorized final checkpoint commits only this log. Finalization
reran all seven FoxGate deployment tests successfully, checked Git whitespace,
reviewed staged content for secret safety, and verified directory/file permissions
using metadata only. Both dedicated Lab containers remain running and healthy.
No new runtime acceptance tests or service mutations were performed during
finalization. Runtime state remains **LOCAL_DEPLOYED_WITH_CONSTRAINTS** and
**REMOTE_NOT_CONFIGURED**.

No Git push, Cloudflare/DNS/public ingress change, HTTPS override activation,
credential modification, canonical memory write, or existing-service restart
was performed during finalization.
