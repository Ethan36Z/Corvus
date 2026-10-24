# API-3B: independent API deployment preparation

**STAGED ONLY. Nothing here installs, starts or publishes a service automatically.**
Implementation: `c2bc84f7cc898ada10b23f5e23f526ad310d4952`.
Client: `https://api-corvus.foxluma.com/v1`, Bearer API key, model `corvus`.
Companion routes, personality and private memory are not part of this API.

## Prepared boundary

`corvus-text-api.service` is a new unit, never the existing Production
`corvus-api.service`. It runs Uvicorn directly as a dedicated unprivileged account.
Standard systemd RootDirectory/bind mounts reproduce API-2's minimal filesystem
without an additional wrapper supervisor. The root contains only system libraries,
an independent venv, five pinned API source files, deployment checks and a readonly
key directory. No private storage, host home, Lab configuration, companion packages,
shared registry, Docker socket or host environment file is mounted.

`serve.py` checks the explicit environment, absent private paths and pinned source
hashes before importing the API; it validates the digest file with the existing
auth checker. Failure exits without a listener or provider call. No model health
probe, real client key or generation is needed at startup. `/usr` supplies trusted
system libraries, not a claim of isolation from all localhost services after an
arbitrary code compromise. Do not add private bind mounts to repair startup.

One ASGI worker, eight server connections, backlog eight, one actual inference
worker; existing six attempts/minute, 128 KiB/5-second body, 4096 input/1024 output
tokens and 90-second API deadline remain unchanged. API-only address space/cgroup
limits are 512 MiB; swap pressure must be checked separately. No access/body logs,
core dumps, proxy-header trust, shared foreground publication or auto restart.
Systemd lifecycle status is available; stdout/stderr are discarded deliberately.

## Authoritative infrastructure snapshot (2026-10-24, read only)

Cloudflare dashboard, rather than a guessed local YAML, is the configuration source.
Tunnel `ethan-home` has one healthy `ethan-desktop` connector, cloudflared 2026.10.1,
and nine published applications. Corvus routes are:

| Order | Hostname | Origin |
| --- | --- | --- |
| 7 | corvus.foxluma.com | http://127.0.0.1:8093 |
| 8 | demo-corvus.foxluma.com | http://127.0.0.1:8091 |
| 9 | lab-corvus.foxluma.com | http://127.0.0.1:8100 |

DNS shows those proxied CNAMEs to the same Tunnel and no API hostname/wildcard.
The zone uses the Free plan. Security rules show 0 custom, 0 rate rules, and no
user-created managed rules; Security Settings separately show always-active
Cloudflare managed protection/DDoS. Bot Fight Mode, Precursor and Under Attack
Mode are off; Browser Integrity Check is on. Access opens the Zero Trust welcome/
onboarding screen; no configured Access application was visible. Do not onboard
Access or change existing policies for this rollout. Dashboard counts are a
snapshot, not proof of all account-level exceptions; repeat the narrow review
before applying changes. See the API-3B engineering log for cache/rules findings.

## Operator installation — requires separate authorization

These are reviewed preparation instructions, **not executed by API-3B**. Choose a
reviewed immutable API-3B commit for `DEPLOY_SHA`; do not deploy a mutable worktree
or borrow/modify the Lab venv. Stop if any target already exists: review its owner
and release before proceeding. Do not replace another service's files.

1. Fresh gate: approved source/dependency versions; source and ingress diff review;
   no other operator editing the Tunnel; all current services healthy; port 18120
   free; >=2 GiB available RAM plus cgroup headroom; quiet PSI and no continuing
   paging. Near-full allocated swap alone is not a utilization measurement. Do
   not stop any Corvus service to create headroom.
2. Save existing account-side routing/DNS/rules privately with revision/time.
   Snapshot only metadata for shared services/source; never copy private databases
   into this service or into Git. Confirm an API-host 404 rollback can be applied
   without restarting the shared connector or modifying browser gateways.
3. Create only the new account, root/release and independent venv. Example commands
   below assume a fresh install, reviewed repository and approved dependency access:

```sh
REPO=/home/ethan/srv/apps/corvus-api-v1
DEPLOY_SHA=REPLACE_WITH_REVIEWED_API3B_COMMIT
# Verify these targets do not already exist before provisioning.
sudo useradd --system --user-group --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin corvus-text-api
sudo install -d -o root -g root -m 0755 /opt/corvus-text-api/release /opt/corvus-text-api/root
# Export just the reviewed allowlist. No .git, tests, memories, runtime env or DB.
git -C "$REPO" archive "$DEPLOY_SHA" app/openai_api.py app/api_auth.py app/model_client.py app/foreground_activity.py app/runtime_config.py deploy/lab/api-v1 | sudo tar --extract --no-same-owner --directory=/opt/corvus-text-api/release
printf '%s\n' "$DEPLOY_SHA" | sudo tee /opt/corvus-text-api/release/DEPLOYMENT_COMMIT >/dev/null
sudo chown -R root:root /opt/corvus-text-api/release
sudo chmod -R go-w /opt/corvus-text-api/release
sudo python3 -m venv --copies /opt/corvus-text-api/venv
sudo /opt/corvus-text-api/venv/bin/python -m pip install -r /opt/corvus-text-api/release/deploy/lab/api-v1/requirements.txt
# Root skeleton only; these paths contain no host data.
sudo install -d -o root -g root -m 0755 /opt/corvus-text-api/root/usr /opt/corvus-text-api/root/etc /opt/corvus-text-api/root/opt/corvus/app /opt/corvus-text-api/root/opt/deployment /opt/corvus-text-api/root/opt/venv /opt/corvus-text-api/root/run/corvus-api-keys /opt/corvus-text-api/root/tmp
sudo ln -s usr/bin /opt/corvus-text-api/root/bin
sudo ln -s usr/lib /opt/corvus-text-api/root/lib
sudo ln -s usr/lib64 /opt/corvus-text-api/root/lib64
sudo install -d -o root -g root -m 0755 /var/lib/corvus-text-api
sudo install -d -o corvus-text-api -g corvus-text-api -m 0700 /var/lib/corvus-text-api/keys
```

4. Follow [existing credential provisioning](../../../docs/api/v1.md#authentication-provisioning-and-revocation).
   Generate the raw key only into an operator-private client file; never print it
   or place it in shell arguments. Install only its digest allowlist as
   `/var/lib/corvus-text-api/keys/keys.sha256`, owner/group `corvus-text-api`, 0600.
   All ancestors must be protected from untrusted writes. For rotation, install a
   new 0600 owned file in that same private directory and atomically rename it;
   never edit the live file in place or replace the mounted directory. Overlap
   old+new, migrate clients, then remove old; retain unrelated keys. Revoking one
   of several keys produces 401 for that key. Empty/missing/malformed keysets fail
   closed with 503. An already-authorized request may finish.
5. Validate dependency imports and the minimal root offline first. On the target,
   inspect the installed unit with `systemd-analyze verify`, then install the new
   unit only. Actual root mount enforcement and dedicated UID checks must be
   confirmed during separately authorized loopback acceptance:

```sh
sudo install -o root -g root -m 0644 /opt/corvus-text-api/release/deploy/lab/api-v1/corvus-text-api.service /etc/systemd/system/corvus-text-api.service
sudo systemctl daemon-reload
sudo systemctl start corvus-text-api.service
systemctl show corvus-text-api.service -p MainPID -p ActiveState -p SubState
ss -ltn 'sport = :18120'
```

`daemon-reload` reloads unit metadata; it is not a shared-service restart. Do not
use `enable --now` before acceptance. Verify the actual PID's UID, loopback bind,
mounts/private paths, readonly key directory and source hashes; use protected
local models/schema GETs without printing credentials. If these checks fail,
stop before hostname publication. Do not relax sandboxing on the fly.
Only after approved acceptance may `systemctl enable corvus-text-api.service`
make this independent service persistent. No other unit is enabled/restarted.

## Exact Cloudflare proposal — separate authorization

`ingress-additions.json` is a **fragment**, never a complete configuration PUT.
Add both entries to the remotely managed Tunnel before its final catch-all and
before any wider rule matching the new hostname; preserve every existing rule and
its relative order. The API hostname catch-all is mandatory, even if a global
catch-all currently returns 404. Inspect the actual catch-all/export before apply:
the dashboard's nine application rows do not expose its full backing JSON.

- Exact hostname + `^/v1/(models|chat/completions)$` -> HTTP 127.0.0.1:18120.
- Same hostname, all other paths -> `http_status:404`.
- The API enforces GET models / POST completions; unsupported methods fail. No
  prefix rewrite, redirect, alternate upstream, automatic POST retry or failover.
- Add only the proxied API CNAME to the existing Tunnel. Do not publish 18120,
  8095, companion APIs or private paths through a LAN/public bind.
- `edge-rule-additions.json` also stages a hostname-only HTTP block (`not ssl`);
  add it without changing existing HTTPS/browser policy. Plain HTTP never reaches
  the API; clients must start with HTTPS and never transmit keys to HTTP.
- Add a cache rule matching `http.host eq "api-corvus.foxluma.com"`, action bypass
  cache, after any conflicting cache rules (last applicable cache setting wins). Retain API `no-store`.
- Retain WAF/DDoS protection, existing FoxGate and browser host policies. Do not
  globally disable Browser Integrity Check or create a broad WAF Skip. If genuine
  SDK requests are blocked, record the Ray ID/product and stop for a narrowly
  reviewed remedy. No API key values belong in Cloudflare expressions.
- Ensure no Worker/Transform replaces Authorization, rewrites paths or captures
  bodies/credentials; do not collect auth headers/Cookies in custom logs.

Bearer-only is suitable for this bounded personal service: at least 32 random
bytes, independently revocable keys, verified HTTPS and app-side limits. Key
possession grants generation, not private-memory access. Keep permanent operator
keys in an application backend; public JS/distributed binaries cannot conceal
one. CORS stays disabled. If account policy later requires Cloudflare Access,
its client-id/client-secret headers add a second credential pair and violate the
three-setting-only contract; its single Authorization JSON option conflicts with
Corvus Bearer. Report that decision rather than silently changing the client.

Cloudflare terminates public TLS and can see plaintext keys/prompts; the encrypted
Tunnel then connects to loopback HTTP. This is not end-to-end TLS past Cloudflare.
Do not alter shared connector launch flags or restart it; verify live remote
configuration propagation and stop if it cannot be safely achieved.

## Minimal remote acceptance — not run during preparation

From a genuine off-host backend, with no Cookie/extra Cloudflare headers:

- Valid certificate/hostname, HTTPS Base URL ending `/v1`; no redirect/challenge.
- GET models: missing/invalid/revoked key -> 401 JSON; valid key -> 200 alias corvus.
  Rotate one key atomically and verify another still works, with API PID unchanged.
- Root, `/api/chat`, `/openapi.json`, `/docs`, `/health`, `/metrics`, tokenize/admin,
  extra/trailing paths and encoded/path-normalization variants fail closed; none
  reaches another service. Other methods do not invoke inference.
- No authenticated response/error cache hits; no auth/body/query logging. Old
  browser hosts retain their auth behavior; current services remain healthy.
- At most two sequential real SDK completions: developer-instructed text <=64
  output tokens, JSON object <=96. Official Python SDK `max_retries=0`, timeout
  about 110 seconds, verified TLS, `stream=False`. Check real envelope, usage,
  finish_reason and valid complete object; record only synthetic output/metrics.
  Stop after any failure or unknown outcome; no manual retry. Do not deliberately
  stall the shared slot. Reuse existing mocked timeout/disconnect/busy tests.

The 90-second API budget sits below Cloudflare's documented 125-second read limit,
not a latency guarantee. Default SDK retries must be disabled. There is no
end-to-end exactly-once or replay-deduplication guarantee, and client timeout does
not prove shared model work stopped. Existing single-slot contention remains.

## Shutdown and rollback

1. Close the API hostname at the edge first: replace only its allow entry with a
   hostname 404; preserve every old entry. Confirm remote fail-closed behavior.
2. Atomically revoke its dedicated keys. Do not modify browser/STT/model secrets.
3. Gracefully stop only the new unit:

```sh
sudo systemctl stop --no-block corvus-text-api.service
systemctl show corvus-text-api.service -p MainPID -p ActiveState -p SubState
ss -ltn 'sport = :18120'
```

SIGTERM reaches Uvicorn directly. `TimeoutStopSec=infinity` and `SendSIGKILL=no`
allow its actual executor thread to settle rather than manufacture successful
cancellation. A stuck worker can leave the unit deactivating; report incomplete
drain and keep ingress closed/keys revoked. Do not force-kill or automatically
restart it, and never disrupt shared Qwen to finish cleanup. Infinite drain may
also delay host shutdown; this conservative tradeoff needs operator awareness.

4. After confirmed exit/port release, disable only this unit if enabled. Remove
   only the new hostname/DNS/host-scoped rules as appropriate; cached DNS alone is
   not a kill switch. Retain its pinned release and private metadata for recovery.
   Never restore an old whole-Tunnel export over unrelated later edits.

No memory rollback or shared-service restart is involved. Source/dependency
reproduction, systemd mount enforcement, new-host TLS and off-host SDK behavior
still require authorized installation/activation. Preparation is not remote
acceptance, Production release, or certification of the old companion
BackgroundTasks -> durable retain-intent recovery gap.

References: [systemd filesystem isolation](https://www.freedesktop.org/software/systemd/man/255/systemd.exec.html), [graceful stop semantics](https://www.freedesktop.org/software/systemd/man/255/systemd.service.html), [Tunnel matching](https://developers.cloudflare.com/tunnel/features/locally-managed-tunnels/configuration-file/), [cache rules](https://developers.cloudflare.com/cache/how-to/cache-rules/create-api/), [Access service credentials](https://developers.cloudflare.com/cloudflare-one/access-controls/service-credentials/service-tokens/).
