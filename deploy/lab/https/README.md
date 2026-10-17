# R0.3b — Lab HTTPS sessions and PWA preparation

Status: **PREPARED_NOT_DEPLOYED**. Neither DEPLOYED nor REMOTE_ACCEPTED.
Baseline: `562433898f7f13a448c2b624bac24de305b38308`, branch `lab/ow2e-console`.

## Verified baseline and architecture

The running Lab container was inspected rather than inferred from the base file.
It uses `corvus-open-webui:0.6.5-arena-ui2.1`, image ID
`sha256:8dea93c991ce80e1d1496783ee7badca025ec38be3fee666a682a679705980be`.
Its Compose labels name `compose.webui.yml`, `compose.boot.yml`, and
`compose.arena-ui2.yml`, in that order. The base file alone names an older image;
the UI-2 override's historical "not deployed" comment is not runtime evidence.
The data volume is `corvus-lab-open-webui-data`; host networking remains bound
by the application to `127.0.0.1:3003`.

R0.3a verified the active database Pipe content against the repository SHA-256
`cc5299b32fedb0f10ee2a37c7466121049a2837c09dc0ec0c7d6f8bd157ec890`.
Its Lab endpoint is `http://127.0.0.1:18096/api/chat`, timeout 300 seconds,
web mode off. No Pipe, canonical SQLite, Hindsight lifecycle, Arena code, or
authentication secret is changed by this preparation.

Adopt the existing v0.6.5 background task and Socket.IO response delivery.
Do not introduce new SSE generation or a new job system. The Lab API remains
non-streaming and owns canonical persistence. The Pipe returns only a complete
confirmed reply; Open WebUI is a separate authenticated presentation/storage layer.

## Prepared HTTPS configuration

Append `deploy/lab/compose.https.yml` **after all three active Compose files**
only for a later authorized remote deployment. It changes only the Lab image,
its build recipe, and these supported v0.6.5 settings:

| Setting | Prepared value |
| --- | --- |
| WEBUI_URL | https://lab-corvus.foxluma.com |
| WEBUI_AUTH_COOKIE_SECURE | true |
| WEBUI_SESSION_COOKIE_SECURE | true |
| WEBUI_AUTH_COOKIE_SAME_SITE | lax |
| WEBUI_SESSION_COOKIE_SAME_SITE | lax |

`WEBUI_URL` is an environment-backed persistent setting; this installation has
`ENABLE_PERSISTENT_CONFIG=false`. It supplies absolute OpenSearch/notification
links, not the browser API base URL. Production frontend API paths are relative;
Socket.IO uses the page origin at `/ws/socket.io`. No external asset origin is
introduced. Ordinary login navigation is relative; OAuth callbacks, if enabled
later, also need correct request scheme/host and provider configuration.

The WebUI `token` cookie remains host-only and HttpOnly. The frontend also uses
the returned JWT in local storage and Authorization headers; Secure-cookie flags
do not remove that behavior. `oui-session` is the OAuth middleware session cookie
when OAuth is configured. SameSite=Lax is sufficient for this same-origin setup.
The existing default JWT lifetime policy is unchanged.

Startup inherits upstream `--forwarded-allow-ips '*'`. The app is loopback-only;
the R0.2 gateway supplies fixed Host, X-Forwarded-Host, HTTPS scheme and port 443,
replaces forwarding IP fields, and clears common conflicting fields. Local
processes remain trusted. A `FORWARDED_ALLOW_IPS` environment setting alone
would not narrow this explicit startup argument; no proxy-trust change is made.

FoxGate's independent host-only session cookie and WebUI's `token` cookie do
not replace each other. Keep both logins and their independent secrets. API
requests after FoxGate expiry receive denial, and socket reconnection requires
FoxGate authentication again. Reauthenticate through a normal page navigation;
never automatically resend an uncertain chat POST.

## Lab-only PWA correction

The active backend `/manifest.json` advertises only 500x500 icons, despite the
existing Corvus 192x192 and 512x512 PNGs. The prepared derivative reuses those
assets, retains the Corvus name, root start URL and standalone display, makes
root scope explicit, and serves `application/manifest+json`. Existing root scope
was implicit; making it explicit does not expand it.

The shell already references `/manifest.json` with `crossorigin=use-credentials`
and the existing 180x180 Apple touch icon. No artwork or frontend rebuild is
needed. No maskable claim is added to the reused icons. No service worker or
offline cache is introduced. Installation and standalone cookie behavior still
require browser/device acceptance through authenticated HTTPS.

The Dockerfile derives from the exact cached UI-2.1 digest. Its script rejects
any unexpected backend main.py hash and replaces only `get_manifest_json`,
retaining the route decorator and other source. All frontend, task/socket,
authentication, Arena and dependency files are inherited. Shared branding
patches, locks and Production/Demo image recipes are unchanged. The original
UI-2 image checker still expects the original main.py hash; use the new manifest
contract as an additional derivative check, not as a claim that the original
whole-image hash contract passes unchanged on the derivative.

Offline build, with the pinned base already cached (no deployment):

```sh
DOCKER_BUILDKIT=0 docker build --network none --pull=false \
  --tag corvus-open-webui:0.6.5-arena-ui2.1-https-r03b \
  --file deploy/lab/https/Dockerfile deploy/lab/https
```

The build context is explicitly allowlisted to this Dockerfile, patch script
and manifest. It contains no runtime data, credentials, Pipe or other repo files.

## Offline configuration and regression checks

Use a non-secret placeholder solely for Compose interpolation. Do not print the
rendered real secret or read the private env file for offline validation.

```sh
CORVUS_LAB_WEBUI_SECRET_KEY=OFFLINE_VALIDATION_PLACEHOLDER \
docker compose --env-file /dev/null \
  -f deploy/lab/compose.webui.yml \
  -f deploy/lab/compose.boot.yml \
  -f deploy/lab/compose.arena-ui2.yml \
  -f deploy/lab/compose.https.yml config --quiet

CORVUS_OW2D_ARCHIVE=/tmp/corvus-arena-ui1/upstream.tar.gz \
.venv/bin/python -B -m unittest discover -s tests -p 'test_lab_webui_https.py' -v

CORVUS_OW2D_ARCHIVE=/tmp/corvus-arena-ui1/upstream.tar.gz \
.venv/bin/python -B -m unittest discover -s tests -p 'test_open_webui*.py' -v
git diff --check
```

The new tests checksum-verify and patch the cached upstream archive. They execute
complete selected pinned function bodies with mocked HTTP/socket/database I/O,
without starting Open WebUI or contacting live Corvus. A deterministic event
gate delays the real Pipe's mocked HTTP response while the returned task remains
registered. Tests check one POST, task/message identity, final socket events,
disconnect/reconnect bookkeeping, and rejection of unconfirmed persistence.
A source contract also checks that socket setup/reconnect handlers contain no
chat submission. No concurrency or Socket implementation is modified.

These are regression checks, not remote transport reliability or a real
125-second delay test. Reconnection is simulated bookkeeping, not a browser
network test. The earlier FoxGate Go suite never executed because its offline
module cache lacked `golang.org/x/crypto v0.41.0`; it is not reported as passed
and no dependency downloads are required by this stage.

### Validation evidence — 2026-10-16

- Seven new HTTPS/PWA/task/socket contracts passed.
- All 59 existing branding, UI-1/UI-2 and Pipe regressions passed with the cached
  archive. The first sandboxed runner stalled at its in-process ASGI boundary
  test and was terminated; the complete rerun outside the sandbox passed.
- All seven existing Lab FoxGate deployment contracts passed.
- The four-file merged Compose configuration passed validation using only the
  placeholder secret. No private environment file was loaded.
- The network-disabled cached build succeeded. Local derivative image ID:
  `sha256:453f9f2c4cee37c5e0d158ed3fcbdfc1e099bc6ef55ab47a7cbcce8b7331df76`.
  Require that identity for this reviewed build before any future recreation;
  do not silently trust a moved tag.
- A transient read-only, unprivileged, network-disabled container with no data
  mounts executed only the manifest handler and checked its MIME, icon assets,
  and unchanged hashes of the function adapter, middleware, socket, tasks and
  auth router. It did not start the WebUI server. Patched main.py SHA-256:
  `f541f307960d0598e54d3cbfe72e7896d09687666c60f483343337fcbdcde9e2`.
- Final inspection confirmed the running container still uses the original
  UI-2.1 image, three-file Compose stack and original Lab data volume.
- Git whitespace checks passed. Changes remain unstaged for semantic review.

## Local HTTP and timeout contract

The original three-file local configuration remains unchanged and usable at
`http://127.0.0.1:3003`. Do not append the HTTPS override for ordinary local use.
Its public URL and Secure cookies are intended for the external HTTPS origin;
do not rely on browser-specific loopback Secure-cookie exceptions. A new public
origin has its own browser cookie/local-storage state and requires login.

The request stages are distinct:

1. Browser chat HTTP POST includes saved chat/message IDs, `stream=true` and its
   Socket.IO ID. With these metadata, WebUI returns `{status, task_id}` and
   consumes the Pipe generator in an existing in-memory background task.
2. The Pipe makes one non-streaming Corvus POST. Its 300-second HTTPX I/O timeout
   and 5-second connect timeout are not a whole-turn deadline.
3. Corvus retrieves context, generates, and commits canonical evidence. Current
   API defaults include model socket timeout 60 seconds and token-count timeout
   30 seconds per operation; multiple operations can extend total turn duration.
4. After a confirmed response, WebUI emits the final result through Socket.IO.
   Engine.IO's inspected defaults are 25-second pings and 20-second ping timeout.
   A task ID acknowledges task creation, not confirmed canonical persistence.
5. A request without the normal task/socket metadata may fall back to SSE;
   the existing Pipe emits no reply data while waiting. `stream=false` also
   waits for the complete Pipe result in the HTTP request.

First HTTP response latency, first reply latency, read/idle timeout and total
generation duration are different measurements. Nginx's 600-second application
timeouts do not override Cloudflare's default 125-second origin read timeout.
The task/socket path is a reason to validate the existing transport first,
not evidence that Cloudflare timeout acceptance is complete. Silent fallback
HTTP responses remain exposed to that limit.

Socket loss does not cancel the background task. A Corvus synchronous turn can
finish after browser loss, Pipe timeout or explicit WebUI task cancellation.
The user message is committed before generation; an assistant reply is committed
after generation. Neither disconnect nor an error proves that persistence failed.
There is no Corvus request idempotency key or automatic retry. Repeating a request
can create a second canonical turn. Check the authoritative result before any
manual resend. WebUI task state is in memory, not a durable recovery system.

## Required later live acceptance and rollback

No service start/restart/recreation, credential generation, Cloudflare change,
canonical write, commit or push is authorized by this preparation.

After separate authorization, verify image identity, merged configuration and
unchanged data volume/secret; provision only the separately reviewed FoxGate
realm. Exercise both login layers, Secure/HttpOnly/SameSite cookies, deep links,
authenticated manifest/icons, absence of mixed content, and WebSocket upgrade.
With explicitly authorized synthetic inputs, verify task ID arrives before a
delayed reply, socket heartbeats/delivery beyond 125 seconds, reconnect without
resubmission, expiry/relogin, cancellation and uncertain-outcome reconciliation.
Test fallback timeout behavior separately. Test mobile installation and standalone
relaunch, including separate browser/standalone credentials where applicable.
Keep Corvus API, Hindsight, model server and WebUI origin off public interfaces.

Rollback after a future deployment removes only this HTTPS override and restores
the original three-file UI-2.1 configuration through a separately authorized
recreation. Preserve the existing Lab volume and secret. Follow the R0.2 boundary
for any separately published Lab route/gateway; do not alter Production/Demo,
canonical memory, Hindsight banks or the shared model service.
