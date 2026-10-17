# R0.5b — Controlled local Lab HTTPS/PWA activation

Date: 2026-10-17 local. Branch: `lab/ow2e-console`.
Starting HEAD: `279688ed393a2376f079c03abec0ce39f91b5ff8`.
Verdict: **LAB_HTTPS_PREPARED_FOR_PUBLICATION**.
Public routing: **REMOTE_NOT_CONFIGURED** by this stage; remote HTTPS browser
authentication, Socket delivery and PWA installation are not accepted.

## Authorization and starting state

The operator authorized a protected Lab WebUI backup and recreation of only
Lab Open WebUI. Preflight confirmed a clean worktree, the reviewed image pins,
healthy existing services, the original three-file Compose stack, and persistent
volume `corvus-lab-open-webui-data` at `/app/backend/data`.

Before:

- Image: `sha256:8dea93c991ce80e1d1496783ee7badca025ec38be3fee666a682a679705980be`.
- Container: `dae69ef59151f56c61cba2ec62bda66e68ed6389b3b7edf55052bcd22b954091`.
- Compose ordering: webui, boot, arena-ui2.

Both images were already cached. The HTTPS image retains the exact original
UI-2.1 base layers. No image was built, pulled or upgraded in this stage.

## Protected backup evidence

Archive:
`/home/ethan/srv/backups/corvus-lab/r0-5b-20261017T075739Z/lab-webui-data.tar`.

- Full persistent WebUI volume snapshot, including existing authentication and
  user data; no private records or credential values were printed or inspected.
- Only Lab WebUI was briefly paused during export. An isolated helper mounted
  the volume read-only, with networking disabled and Docker logging disabled,
  and streamed archive bytes directly into the protected host file.
- Lab WebUI was unpaused in a finally block before archive validation/recreation.
- Backup parent/directory: mode 0700. Archive: mode 0600, UID/GID 1000:1000.
- Archive size: **241,776,640 bytes**, containing **39 regular files** and
  **241,625,882 logical file bytes**.
- Free space before export: **540,382,633,984 bytes**; required headroom passed.
- SHA-256:
  `91e5651179d6ec3b251285bc9d7804e383d074825d1209c94cb361e8f336e895`.
- Every regular archive member was fully read for validation; entry paths were
  checked for absolute paths/traversal. SQLite and any WAL were copied into a
  protected temporary directory for validation, not opened for writes in the
  source volume. SQLite `PRAGMA integrity_check` returned `ok`.
- User/auth/chat/function/model counts matched the source. The checksum was
  verified again immediately before activation.
- Non-secret evidence is retained in `backup-evidence.json` beside the archive.

The existing protected `/home/ethan/.config/corvus-lab/webui.env` was retained
unchanged and remains required for recovery; it is separate from this volume
archive. Before recreation, the merged deployment's signing-secret value was
compared internally with the running container and found equal; neither value
nor a key fingerprint was emitted or stored in checkpoint evidence.

## Activation

Only `open-webui` in project `corvus-lab-open-webui` was recreated using this
exact ordering:

```sh
docker compose -p corvus-lab-open-webui \
  --env-file /home/ethan/.config/corvus-lab/webui.env \
  -f deploy/lab/compose.webui.yml \
  -f deploy/lab/compose.boot.yml \
  -f deploy/lab/compose.arena-ui2.yml \
  -f deploy/lab/compose.https.yml \
  up -d --no-deps --no-build --pull never --wait --wait-timeout 180 open-webui
```

After:

- Image: `sha256:453f9f2c4cee37c5e0d158ed3fcbdfc1e099bc6ef55ab47a7cbcce8b7331df76`.
- Container: `6e8f593f65ef2ebad7d5410214f6f172fd2de39d25b222f10c2e644e64dcc7a4`.
- Start timestamp: `2026-10-17T08:00:07.279866651Z`.
- Volume: the original `corvus-lab-open-webui-data`, unchanged attachment.
- Health: healthy. Runtime Compose labels confirm the four-file order above.

The separate HTTPS override now supplies the public WEBUI_URL, both Secure
cookie settings and SameSite=Lax. Host networking remains loopback-bound to
127.0.0.1:3003; no port mapping was introduced. The existing signing secret,
authentication, database and backend connections were retained.

## Local acceptance

All **21 recorded local acceptance checks passed**, plus the final opaque
database byte-fingerprint comparison:

| Check | Result |
| --- | --- |
| Correct derivative image / original volume | Passed |
| Public WEBUI_URL and both Secure/SameSite settings | Passed |
| `/manifest.json` | 200; exact prepared manifest; application/manifest+json |
| 192x192 / 512x512 / Apple touch icons | 200; exact existing Corvus asset hashes |
| Entire UI-2 frontend and Arena markers | Unchanged fingerprint |
| User/auth/chat/function/model counts | Unchanged |
| Active Pipe content/configuration fingerprint | Unchanged |
| Unknown Host at Lab gateway | 404 |
| Unauthenticated gateway root/API/manifest | 401 |
| External internal-verify request | 404 |
| Direct WebUI session endpoint without WebUI authentication | Denied (401/403) |
| Lab WebUI and Lab API health | 200 |
| Production API and Demo API health | 200 |
| Lab Auth health | 200 |
| Lab/Demo/Private gateways without credentials | 401 |
| All other tracked container/service identities and start times | Unchanged |
| Fingerprinted canonical/derived records outside WebUI | Unchanged |
| TCP listening-address inventory | Unchanged |
| WebUI container health | Healthy |

The live WebUI SQLite file is byte-identical to `webui.db` inside the validated
backup. This supplements volume, table-count and Pipe checks without querying
private conversation content or credential fields.

The PWA and asset requests used the direct loopback WebUI endpoint. Separate
gateway requests confirmed those paths remain protected. No user or FoxGate
login was performed in this stage and no passwords/session tokens were read.
Cookie checks establish configured runtime flags, not actual HTTPS browser
cookie issuance or transport. No browser HTTP-cookie exception was relied upon.

## Existing-service and data boundaries

Lab FoxGate, existing Demo/Private FoxGate, Production/Demo frontends, Hindsight
and Qwen containers were neither restarted nor recreated. Their IDs, image IDs,
start times, mounts and running states matched the pre-activation snapshot.
Lab API, Production API and cloudflared systemd PID/start/state metadata also
matched. Relevant service health responses stayed as expected.

Opaque before/after fingerprints covered existing Lab/Private/Demo canonical
database files and available WALs, plus available H1 observation/Arena JSONL
files. They matched. No real or synthetic chat turn, model request, canonical
write, Hindsight operation, credential change, new listener, Tunnel/DNS/ingress
change, Git commit or push was performed. Broader volume contents outside the
specified checks are not claimed as exhaustively audited.

There was a brief Lab WebUI pause for backup and one WebUI recreation. Browser
downtime was not measured. No other service was interrupted. No rollback was
needed because activation and local acceptance succeeded.

## Rollback and backup recovery

Keep the original cached image and original three-file stack available. Ordinary
configuration rollback preserves the existing volume and uses:

```sh
docker compose -p corvus-lab-open-webui \
  --env-file /home/ethan/.config/corvus-lab/webui.env \
  -f deploy/lab/compose.webui.yml \
  -f deploy/lab/compose.boot.yml \
  -f deploy/lab/compose.arena-ui2.yml \
  up -d --no-deps --no-build --pull never --wait --wait-timeout 180 open-webui
```

Then verify the original image, original volume, WebUI health, FoxGate protection,
Pipe and existing-service health. Do not delete the volume or change secrets.

For recovery from confirmed volume corruption, first verify the archive SHA-256
above, preserve the current volume for review, and stop only Lab WebUI during a
separately controlled recovery window. Restore the archived `data/` contents
with that prefix removed into the exact Lab WebUI volume, preserving file modes
and ownership. Validate SQLite on a protected recovered copy, retain the same
private environment file, then recreate the original three-file deployment and
verify functionality. Do not extract into Corvus canonical data or other realms.
No archive restore was performed, and a full restore rehearsal is not claimed.

## Remaining public acceptance

No Cloudflare route, DNS record, Tunnel service or Dashboard state was changed.
Recheck current Dashboard/DNS conflicts, Tunnel identity, edge certificate,
HTTPS redirection, caching and WebSocket settings before any later publication.
The only proposed public origin remains Lab FoxGate at http://127.0.0.1:8100.

External dual login, Secure-cookie issuance, logout/expiry, authenticated Socket
delivery, reconnect/missed-result behavior and iPhone/PWA installation remain
unverified. Plain HTTP SSH-tunnel authentication may be unreliable now that
Secure cookies are enabled; do not weaken authentication for convenience.
Cloudflare's default 125-second origin read timeout is not resolved by local
checks or Nginx's longer timeout. Do not automatically retry uncertain turns.
Reverse-direction Demo/Private-session rejection by Lab remains NOT_VERIFIED.

Deployment execution ended with this checkpoint uncommitted at the starting
baseline. Separately authorized finalization commits only this log after
accuracy, secret-safety, staged-diff and whitespace review. No runtime or public
routing changes, credential/memory changes, or Git push occur during finalization.
