# Dedicated Lab FoxGate realm — R0.2

Status: **PREPARED_NOT_DEPLOYED**. Baseline: `7f389f183d01b6c1ad5e542b53a0132ee3cf1a0e`.
This bundle adds deployment templates only. It does not change Open WebUI,
Corvus Pipe/API, Memory Arena, Hindsight, Qwen, or existing FoxGate instances.

## Proposed deployment

```text
https://lab-corvus.foxluma.com
  -> existing Cloudflare Tunnel (future published route)
  -> http://127.0.0.1:8100  FoxGate Lab gateway
       -> 127.0.0.1:8101  FoxGate Lab Auth (auth_request)
       -> 127.0.0.1:3003  existing authenticated Lab Open WebUI
            -> 127.0.0.1:18096  existing Lab Corvus API
```

Runtime directory: `/home/ethan/srv/infrastructure/lab-access`.
Compose project: `foxgate-lab`, containing only `auth` and `gateway`.
Both use host networking with explicit loopback listeners. There are no public
port mappings, application data mounts, builds, or FoxGate source copies.

The templates follow `/home/ethan/srv/infrastructure/private-access`, reusing
the unchanged FoxGate V2 Auth image from commit `1009bba` and the existing
pinned Nginx 1.28 image. Auth source is maintained separately in
`/home/ethan/srv/infrastructure/demo-access/auth` (repository HEAD inspected:
`a8aea8661ef140bf588c6663b82f6de98bd95043`). Both image digests are pinned in
Compose; `pull_policy: never` requires those images already in the local cache.

## Authentication and secret provisioning — later authorized stage only

Lab uses these new host files, mounted read-only into Auth only:

- `/home/ethan/srv/shared/secrets/lab-access/gated.htpasswd`
- `/home/ethan/srv/shared/secrets/lab-access/session-hmac.key`

Create a new single-user bcrypt credential and a fresh independent random HMAC
key. Never copy Private/Demo files, keys, hashes, or credentials. Do not store
either file in this checkout or runtime deployment directory. The existing
Auth implementation enforces signed sessions and safe relative redirects;
with `FOXGATE_COOKIE_SECURE=true` it issues Secure, HttpOnly, host-only,
SameSite=Lax cookies. It sets no cookie Domain. Its fixed cookie name is safe
on separate hostnames; the independent HMAC key also rejects other realms'
tokens. Open WebUI still requires its own login.

Provision as host UID/GID 1000:1000, with a mode-0700 secret directory and
mode-0600 files. Using host `htpasswd` and `openssl`, a later operator may run
the following with the chosen Lab username (replace `LAB_USERNAME` first):

```sh
(
set -eu
umask 077
# Intentionally fail if the realm directory already exists. Review partial
# provisioning manually rather than overwriting any existing realm material.
mkdir -m 0700 /home/ethan/srv/shared/secrets/lab-access
# Prompt for the password; do not supply it in command arguments or shell history.
htpasswd -cB /home/ethan/srv/shared/secrets/lab-access/gated.htpasswd LAB_USERNAME
openssl rand -out /home/ethan/srv/shared/secrets/lab-access/session-hmac.key 32
chmod 0600 /home/ethan/srv/shared/secrets/lab-access/gated.htpasswd /home/ethan/srv/shared/secrets/lab-access/session-hmac.key
)
```

The subshell stops on any failure. Verify ownership
and permissions with `stat`, without displaying contents. The bind mounts use
`create_host_path: false`; missing secrets must fail rather than create directories.
No secret values are provided or generated in R0.2.

## Proxy contract and unresolved blockers

Only `lab-corvus.foxluma.com` is routed. Unknown hosts return 404. Every application
path uses `auth_request`; Auth errors fail closed. HTML navigation goes through
the existing Auth safe-redirect handler. Other unauthenticated requests return
401. The internal verify path is inaccessible externally. Application paths and
queries are preserved; only the FoxGate login/logout/redirect endpoints map to
Auth handlers. Authorization and Cookie are passed to Open WebUI unchanged.

The public route must use HTTPS; its future origin is plain HTTP over loopback.
The gateway sets a fixed public Host, HTTPS scheme, and port 443 rather than
trusting supplied forwarding fields. It replaces X-Forwarded-For and X-Real-IP
with the actual loopback peer, clears Forwarded and common prefix/scheme hints,
and performs no client-IP restoration. Login throttling therefore conservatively
shares a limit across Tunnel clients. It is not a trusted-client-IP deployment.

HTTP/1.1 and WebSocket Upgrade headers are forwarded, response buffering and
proxy caching are disabled for SSE, request bodies are limited to 10 MB, and
application read/send timeouts are 600 seconds. Auth uses five-second upstream
timeouts. Gateway retries are disabled, including for non-idempotent requests.
Unavailable Auth cannot authorize a request; unavailable WebUI returns an error
with no alternate origin. No Cloudflare route should point directly at port 3003
or 18096.

**Remote access is not ready for acceptance.** Longer Nginx timeouts and disabled
buffering do not solve Cloudflare's default 125-second proxy read timeout.
The current non-streaming Corvus Pipe may wait up to 300 seconds, and Open WebUI
awaits it before the first SSE event. A timed-out browser request may still have
completed durably in Corvus; do not automatically retry it. Later work must
resolve this timeout contract before public chat acceptance. See
[Cloudflare error 524](https://developers.cloudflare.com/support/troubleshooting/http-status-codes/cloudflare-5xx-errors/error-524/).

The current Lab WebUI also has a loopback `WEBUI_URL` and unset secure-cookie
flags. A later stage must review its public URL and HTTPS cookie settings,
while retaining `WEBUI_AUTH=true` and its existing secret. R0.2 does not change
these settings. Public DNS/Tunnel mapping, mobile/PWA behavior, WebSocket/SSE
delivery and the 10 MB body limit require later remote acceptance. The exact
existing Tunnel control-plane configuration/name still needs verification.

## Offline validation

```sh
python3 -B -m unittest discover -s tests -p 'test_lab_foxgate_deployment.py' -v
docker compose -f deploy/lab/foxgate/compose.yaml config --quiet
```

Nginx syntax can be checked without starting a gateway or binding any listener:

```sh
docker run --rm --pull never --network none --read-only --user 1000:1000 \
  --cap-drop ALL --security-opt no-new-privileges:true \
  --tmpfs /tmp:size=16m,mode=1777 \
  --mount type=bind,src=/home/ethan/srv/apps/corvus-lab/deploy/lab/foxgate/nginx/nginx.conf,dst=/etc/nginx/nginx.conf,readonly \
  --mount type=bind,src=/home/ethan/srv/apps/corvus-lab/deploy/lab/foxgate/nginx/gated-locations.conf,dst=/etc/nginx/foxgate/gated-locations.conf,readonly \
  --entrypoint /usr/sbin/nginx \
  nginx:1.28-alpine@sha256:a8b39bd9cf0f83869a2162827a0caf6137ddf759d50a171451b335cecc87d236 -t
```

This is a transient syntax-check process with no network and no secret mounts.
Static tests verify the default-host 404 branch and auth gate; live HTTP behavior
is deliberately deferred. Existing FoxGate Go tests may be run from a scratch
copy with a cached toolchain/module cache and network disabled; no downloads or
changes to the FoxGate checkout are required.

### Resumed validation — 2026-10-16

Recovered and reviewed all four bundle files and
`tests/test_lab_foxgate_deployment.py`; the interrupted implementation was
preserved. The seven deployment contract tests pass, Compose configuration
validation passes, and the pinned Nginx image passes `nginx -t` again with
networking disabled, a read-only root/configuration, and no secret mounts.

The existing Auth suite was attempted with the pinned Go 1.24 image, networking
disabled, read-only source/root, `GOPROXY=off`, `GOSUMDB=off`, and temporary
in-memory caches. Both packages failed during setup because
`golang.org/x/crypto v0.41.0` was unavailable in that cache. **No Go tests ran;
the Auth suite is not recorded as passing.** A later offline rerun needs a
verified prepopulated module cache. No dependencies were downloaded and the
external Auth checkout was not modified.

These checks establish preparation only. Runtime routing, unavailable-Auth
behavior, independent-secret/session rejection, and public access remain
unverified until a separately authorized deployment and acceptance stage.
No deployment, service restart, Cloudflare change, secret generation, canonical
memory modification, commit, or push was performed.

## Deployment procedure — future authorized stage only

1. Recheck the reviewed commit/diff, image identities, and that ports 8100/8101
   remain free. Resolve the WebUI URL/cookie and Cloudflare timeout blockers.
2. Create `/home/ethan/srv/infrastructure/lab-access/nginx` and copy only
   `compose.yaml`, `nginx/nginx.conf`, and `nginx/gated-locations.conf` from this
   bundle, preserving their relative layout. Provision independent secrets as
   described above. Do not change existing Private/Demo deployment directories.
3. Validate the copied configuration and local image cache:

   ```sh
   docker image inspect foxgate-auth@sha256:2d7745847cb4f5875496830082bd9bcd5bbc5aa1d0c8733e18a07646d4772523 --format '{{.Id}}'
   docker image inspect nginx:1.28-alpine@sha256:a8b39bd9cf0f83869a2162827a0caf6137ddf759d50a171451b335cecc87d236 --format '{{.Id}}'
   docker compose -p foxgate-lab -f /home/ethan/srv/infrastructure/lab-access/compose.yaml config --quiet
   ```

   Require image IDs to match the pinned digests above. Repeat the network-free
   Nginx syntax command using the copied runtime paths.
4. When separately authorized, start only the new project:

   ```sh
   docker compose -p foxgate-lab -f /home/ethan/srv/infrastructure/lab-access/compose.yaml up -d --no-build --pull never --wait auth gateway
   ```

5. Verify loopback binding, default-host 404, Lab host API 401, HTML login redirect,
   auth-unavailable fail-closed behavior, correct cookie flags and rejection of
   other realm sessions, with authorized synthetic acceptance only. Verify the
   existing Lab/Production/Demo services and routes remain healthy.
6. In a later Cloudflare stage, verify the intended existing Tunnel identity and
   add only the `lab-corvus.foxluma.com` published route/DNS mapping with origin
   `http://127.0.0.1:8100`. Preserve existing route entries. Require public HTTPS,
   downstream WebUI login, WebSocket/SSE, mobile/PWA and timeout acceptance before
   declaring remote access accepted. Do not send private test conversations.

## Rollback — future authorized stage only

If the future public route has been added, remove only that Lab route/DNS entry
first. Then stop only the dedicated gateway/auth services:

```sh
docker compose -p foxgate-lab -f /home/ethan/srv/infrastructure/lab-access/compose.yaml stop gateway auth
```

Retain secrets/configuration for review. Do not remove volumes, canonical data,
or the existing Tunnel. Do not stop Lab Open WebUI/API or any Private/Demo service.
Any later WebUI environment change needs its own recorded rollback, outside R0.2.
