# Private Corvus API — systemd Hardening

Date: 2026-09-06

## Context

Corvus deployment work began from a functioning Stage A2 daily-use backend.

Before hardening, the FastAPI runtime was started manually inside tmux and
listened on:

`0.0.0.0:8096`

That was acceptable for development but not for the intended FoxLuma security
boundary.

A verified canonical-data backup was created before changing the runtime.

Backup:

`/home/ethan/srv/backups/corvus/20260906-080519`

The SQLite backup passed:

`PRAGMA integrity_check = ok`

and contained 40 canonical messages.

## Engineering Question

Can the current Private Corvus API be moved from a temporary tmux process to a
reboot-safe system service while preserving:

- existing canonical data;
- retrieval recovery;
- model connectivity;
- API health;
- the current Stage A2 behavior;

and while restricting direct network exposure to the local host?

## Starting Hypothesis

The application itself does not need architectural modification.

A systemd service should be sufficient if it:

- runs as user `ethan`;
- uses the existing Corvus virtual environment;
- explicitly selects the existing Corvus data directory;
- connects to the existing loopback-only llama.cpp endpoint;
- binds Uvicorn only to `127.0.0.1:8096`;
- restarts on process failure;
- starts automatically during host boot.

## What We Did

Created:

`/etc/systemd/system/corvus-api.service`

The service runs:

`app.playground_api:app`

using:

`/home/ethan/srv/apps/small-vram-companion/.venv/bin/uvicorn`

The runtime explicitly uses:

`CORVUS_DATA_DIR=/home/ethan/srv/apps/small-vram-companion/data`

and the local model endpoint:

`http://127.0.0.1:8095`

The previous `corvus-api` tmux session was stopped.

The systemd service was started and enabled.

The verified live unit was also copied into the repository at:

`deploy/systemd/corvus-api.service`

so the operational configuration is reproducible rather than existing only
inside `/etc/systemd/system`.

## Evidence / Results

Initial systemd startup succeeded.

Service state:

- enabled: yes
- active: yes

API listener changed from:

`0.0.0.0:8096`

to:

`127.0.0.1:8096`

The API health endpoint returned:

- service: OK
- model: OK
- dense recovery: OK
- caught_up: true
- progress_after: 40

A controlled:

`systemctl restart corvus-api.service`

was then performed.

The previous Uvicorn process shut down cleanly and systemd created a new
process.

After restart:

- service remained enabled;
- service returned to active;
- listener remained `127.0.0.1:8096`;
- `/api/health` returned OK;
- model health returned OK;
- dense recovery remained caught up;
- canonical progress remained 40;
- no tmux runtime remained.

The Git working tree was clean immediately after the operational change,
confirming that canonical application data and repository source were not
accidentally modified by the service transition.

## Interpretation

The FastAPI process itself is now suitable as a production-candidate local
origin.

The API no longer depends on an interactive shell or tmux session.

Binding only to loopback removes direct access through the host LAN and
Tailscale interfaces and preserves the intended ingress model:

Internet
-> Cloudflare Tunnel
-> FoxGate
-> loopback Corvus origin

The change did not require modification of Corvus memory, retrieval, session,
or personality architecture.

## Decision

Adopt systemd as the formal Private Corvus FastAPI process supervisor.

The production-like API origin is:

`127.0.0.1:8096`

Direct `0.0.0.0:8096` exposure is retired.

The repository copy under `deploy/systemd/` becomes the version-controlled
deployment source for this service.

## Architecture Impact

Before:

Development shell
-> tmux
-> Uvicorn `0.0.0.0:8096`
-> Corvus

After:

systemd
-> Uvicorn `127.0.0.1:8096`
-> Corvus
-> llama.cpp `127.0.0.1:8095`

The public ingress boundary remains outside the Corvus API process.

## Open Questions

The following deployment gaps remain:

- llama.cpp currently has Docker restart policy `no`;
- startup ordering does not yet guarantee that llama.cpp is ready when the API
  first starts after a host reboot;
- frontend serving is still development-oriented;
- the permanent Private Corvus data path has not yet been separated from the
  repository development data path;
- Private FoxGate realm does not yet exist;
- Demo Corvus runtime and physical data store do not yet exist;
- FoxLuma routing has not yet been configured;
- full host-reboot acceptance has not yet been performed.

## Next Step

Make the existing `corvus-llama` runtime reboot-safe without changing its
loopback-only model endpoint or model configuration.

Then verify model recovery and Corvus API health before proceeding to frontend
productionization.
