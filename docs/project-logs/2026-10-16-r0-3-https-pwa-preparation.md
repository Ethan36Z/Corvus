# R0.3 — Lab HTTPS and PWA compatibility preparation

Stage date: 2026-10-16; final validation/checkpoint completed 2026-10-17 local.
State: **PREPARED**, not **DEPLOYED** and not **REMOTE_ACCEPTED**.

## A. Starting Git baseline

Repository: `/home/ethan/srv/apps/corvus-lab`.
Branch: `lab/ow2e-console`.
Starting HEAD: `562433898f7f13a448c2b624bac24de305b38308`.
The only initial tracked modification was `deploy/lab/README.md`; untracked scope
was `deploy/lab/compose.https.yml`, `deploy/lab/https/`, and
`tests/test_lab_webui_https.py`. No unexpected changes were present.

The actual running Lab configuration was inspected independently of the base
Compose file. It uses, in order, `compose.webui.yml`, `compose.boot.yml`, and
`compose.arena-ui2.yml`. The active UI-2.1 image is
`sha256:8dea93c991ce80e1d1496783ee7badca025ec38be3fee666a682a679705980be`.
The persistent mount is `corvus-lab-open-webui-data:/app/backend/data`.

## B. Architecture decision

Preserve the existing non-streaming Corvus API/Pipe and Open WebUI v0.6.5
background-task/Socket.IO delivery. Task creation returns a task ID; the Pipe
waits for one complete Corvus response, verifies confirmed persistence, and
returns the reply for existing Socket delivery. Task acknowledgement is not
canonical persistence confirmation. No streaming rewrite, new asynchronous job
system, automatic retries, or change to canonical memory ownership is introduced.
Memory Arena UI-2 and the Hindsight lifecycle remain unchanged.

## C. Implemented HTTPS compatibility

`compose.https.yml` is a separate Lab-only override, appended after all three
active files for a later authorized remote deployment. It sets:

- `WEBUI_URL=https://lab-corvus.foxluma.com`
- `WEBUI_AUTH_COOKIE_SECURE=true`
- `WEBUI_SESSION_COOKIE_SECURE=true`
- Both supported SameSite settings to `lax`.

These variables were checked against pinned v0.6.5 source. Existing WebUI
authentication, signing secret, FoxGate's independent authentication realm,
volume and loopback binding are preserved. Browser API paths and Socket.IO
remain same-origin; the public URL corrects absolute links. Inherited startup
trusts forwarded headers from `*`; loopback and the gateway's fixed forwarding
fields remain the boundary, with local processes trusted. No proxy-trust
implementation is changed.

## D. PWA preparation and files

The Lab-only derivative corrects only the backend manifest handler. It reuses
Corvus's existing 192x192 and 512x512 PNGs, preserves the 180x180 Apple touch
icon, root start URL, Corvus name and standalone display, makes root scope
explicit, and serves `application/manifest+json`. No artwork or second frontend
is created. A hash guard rejects any unexpected base main.py before patching.

The derivative inherits the exact active UI-2.1 digest, frontend, authentication,
Arena behavior, task/socket code and dependencies. Shared branding patches,
locks and Production/Demo image recipes remain untouched. The original full-image
checker expects the old main.py; the derivative uses additional manifest checks
and must not be described as passing that original hash contract unchanged.

Files in this checkpoint:

- `deploy/lab/README.md`
- `deploy/lab/compose.https.yml`
- `deploy/lab/https/.dockerignore`
- `deploy/lab/https/Dockerfile`
- `deploy/lab/https/README.md`
- `deploy/lab/https/manifest.json`
- `deploy/lab/https/prepare_manifest.py`
- `tests/test_lab_webui_https.py`
- This checkpoint log.

## E. Final validation results

Cached dependencies/archive only; no live chat requests or canonical writes:

- HTTPS/PWA/task/socket tests: **7 passed**.
- Existing Open WebUI branding, Arena UI-1/UI-2 and Pipe regressions: **59 passed**.
- Lab FoxGate deployment contracts: **7 passed**.
- Four-file Compose configuration, in the documented order: **passed** using a
  non-secret interpolation placeholder and `/dev/null` environment file.
- Compose contracts verify only intended image/build/HTTPS settings change and
  preserve the Lab volume, authentication, loopback host/port and boot policy.
- Manifest contracts validate response MIME, scope/start URL, asset dimensions
  and Apple touch icon, and reject base-source drift.
- Read-only Docker inspection verified exact base/derivative identities,
  preserved base layers and unchanged startup/dependency environment.
- Git whitespace checks pass; staged changes are reviewed before commit.

Prepared image, built and checked offline during R0.3b, not rebuilt here:
`sha256:453f9f2c4cee37c5e0d158ed3fcbdfc1e099bc6ef55ab47a7cbcce8b7331df76`.
Require that identity rather than silently trusting its mutable tag.
The running Lab still uses the original UI-2.1 image and three-file Compose
configuration. At final validation its container ID is
`dae69ef59151f56c61cba2ec62bda66e68ed6389b3b7edf55052bcd22b954091`,
with start timestamp `2026-10-16T23:35:56.192350176Z`.

The Auth Go suite previously failed package setup because the offline cache
lacked `golang.org/x/crypto v0.41.0`; no Go tests executed and it is not passed.
No dependency download was attempted to complete that suite.

## F. Security semantic review

R0.3c verdict: **PASS_WITH_CONSTRAINTS**. No blocking fix required for checkpoint
and commit. This is not deployment authorization or public-access acceptance.

Accepted non-blocking test gaps remain documented: reconnection is simulated
bookkeeping and only checks some delivery to the new socket; missed final-result
recovery is untested. Icon lookup by basename does not fully validate URL shape,
manifest handler execution does not test route registration, and the new request
count assertion alone does not verify HTTP method/destination. Actual prepared
source was reviewed separately. Tests do not establish remote reliability.

## G. Accepted limitations

- Plain HTTP local browser authentication, including SSH-tunnel access, may stop
  working with Secure cookies. Do not weaken authentication for convenience or
  rely on browser-specific loopback exceptions. The original local configuration
  is retained, but simultaneous HTTP compatibility after HTTPS activation is
  not guaranteed.
- Cloudflare's default 125-second origin read timeout is not resolved by Nginx's
  600-second timeouts. Normal task/socket delivery needs live acceptance;
  silent SSE and non-streaming HTTP fallbacks remain exposed to that limit.
- The Pipe's 300-second HTTPX I/O timeout is not a whole-turn deadline.
  WebUI task lifetime, Socket liveness and generation duration are separate.
- Socket reconnection does not guarantee recovery of a missed final response.
  Task state is in memory, not a durable delivery/recovery mechanism.
- Browser loss, Pipe timeout or WebUI cancellation does not prove that canonical
  persistence failed. A server-side turn may finish afterward.
- No automatic retry of uncertain canonical turns is authorized. Repeating a
  request can persist another turn; inspect authoritative state before resending.
- iPhone PWA installation, standalone session behavior and remote HTTPS remain
  unverified. Both FoxGate and WebUI login/expiry/logout require live acceptance.

## H. Next deployment stage

**R0.4: Controlled local Lab FoxGate deployment and runtime security acceptance.**
Requires separate authorization. Recheck image identities, Compose ordering,
ports and unchanged secret/volume boundaries. Validate both authentication
layers, default-host rejection, unavailable-Auth failure closure, independent
realm sessions, cookies, redirects and Socket transport with authorized synthetic
inputs. Public routing, delayed remote delivery and iPhone acceptance remain
separate gates; no Cloudflare change is included in this checkpoint.

## I. Rollback and safety boundary

Keep the original UI-2.1 image and original three-file Compose stack available.
After a future HTTPS activation, remove only the HTTPS override and restore that
stack through a separately authorized recreation, retaining the existing Lab
volume and authentication secret. Apply the R0.2 Lab-only gateway/route rollback
boundary if those components have separately been deployed.

No running service, Production, Demo, Cloudflare route, credential, canonical
memory or Hindsight lifecycle was changed in this finalization. No image was
rebuilt. Only the reviewed R0.3 repository files and this log are committed;
no push or deployment is performed.
