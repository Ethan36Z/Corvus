# Corvus API v1 activation (API-3D) — 2026-10-24

**Verdict: `API_3D_REMOTE_PENDING`.** Live and verified end to end through the
public Cloudflare edge from the origin host. Not yet verified from a separate
off-host client (the only other device was offline), so the unit is **not enabled**.

Endpoint `https://api-corvus.foxluma.com/v1`, model `corvus`, Bearer key,
text-only, non-streaming, stateless. Release pinned to `3dd7619` (implementation
`c2bc84f`); procedure per `deploy/lab/api-v1/DEPLOYMENT.md`.

## Deployed state

- `corvus-text-api.service`: active, **disabled** (no start at boot), Restart=no.
  Dedicated system user `corvus-text-api`, CapEff 0, NoNewPrivs, seccomp on,
  RootDirectory minimal root; `/usr`, app, venv and key directory mounted
  read-only; no home, `/srv`, Lab, private memory or Docker paths visible.
- Listens on `127.0.0.1:18120` only. Five app files match the source manifest.
- Independent venv in `/opt/corvus-text-api/venv` (pinned requirements, PyPI).
- Key store `/var/lib/corvus-text-api/keys/keys.sha256` (digest only, owner
  service user, 0600, dir 0700). One active key; operator copy kept privately
  outside Git. No key appears in this log, Cloudflare or shell arguments.

## Cloudflare changes (host-scoped only)

Applied in this order, each verified after the change:

1. WAF custom rule: `(http.host eq "api-corvus.foxluma.com" and not ssl)` → block.
2. Cache rule: same host → bypass cache.
3. Tunnel config v12 → v13: two entries inserted before the catch-all
   (exact host + `^/v1/(models|chat/completions)$` → `http://127.0.0.1:18120`;
   same host otherwise → `http_status:404`). The 9 existing routes and the
   catch-all were checked as byte-identical. The connector applied v13 live with no restart.
4. Proxied CNAME `api-corvus` → the existing Tunnel (publication switch).

There were no other Cloudflare changes. Access is not enabled, and BIC/managed/DDoS
protection is unchanged.

## Acceptance evidence (through the public edge, from the origin host)

- TLS valid (`*.foxluma.com` universal certificate), HTTP/2. Plain HTTP → 403.
- `GET /v1/models`: no key / invalid key → 401 JSON; valid → 200 `["corvus"]`.
- `POST /v1/chat/completions` without a valid key → 401.
- `/`, `/v1`, trailing slashes, `/openapi.json`, `/docs`, `/health`, `/metrics`,
  `/api/*`, other `/v1/*`, `//` and `./`/`../` variants → edge 404 (never reach
  the API). Wrong methods → 405. Query string → 400.
- Every response: `cf-cache-status: DYNAMIC`, `cache-control: no-store`.
- Revocation: atomically removed a second test key → 401 at once; the primary
  key still returned 200; service PID unchanged (no restart).
- Official OpenAI Python SDK 2.26.0, `max_retries=0`, `timeout=110`, `stream=False`.
  Two sequential calls, both `finish_reason=stop`, no retries:
  - Text: 35+10 tokens, 0.4 s.
  - `json_object`: 46+20 tokens, 0.6 s, valid JSON.

## Resource impact and preservation

- API process RSS about 45 MB, 2 tasks. Host about 6.7 GiB available, memory PSI 0.
- Production, Lab, Demo, Qwen and cloudflared: same PIDs, NRestarts 0, health OK.
  The existing browser hosts still return 401 (FoxGate). No shared service was restarted.

## Remaining limitations

- **Off-host client acceptance pending.** Then run
  `sudo systemctl enable corvus-text-api.service`. Until then a reboot leaves the
  API down (edge returns an error and fails closed).
- TLS ends at Cloudflare. Requests share the single Qwen slot. No replay
  deduplication. Browser Integrity Check is unchanged; record a Ray ID if a client is challenged.

## Rollback

1. Tunnel: replace the API allow entry with a host 404, or remove both API
   entries. Re-read the live config first; never re-PUT an old export.
2. Revoke: atomically install an empty/new digest file (empty → 503).
3. `sudo systemctl stop --no-block corvus-text-api.service`; confirm the exit and
   that port 18120 is free. Never force-kill it.
4. Remove the `api-corvus` DNS record and the two host-scoped rules. Disable the unit if enabled.
