# Private Corvus Full-Host Reboot Acceptance

Date: 2026-09-06

## Context

Private Corvus had already passed:

- local authenticated FoxGate acceptance
- isolated Demo/Private authentication realm validation
- Cloudflare Tunnel public routing
- public HTTPS fail-closed validation
- remote authenticated browser acceptance

The final deployment gate was a real full-host reboot.

The purpose was to verify that the complete Private Corvus stack could recover automatically without manually restarting application components.

## Pre-Reboot Baseline

Before reboot:

- Docker was enabled and active.
- cloudflared was enabled and active.
- corvus-api was enabled and active.
- corvus-llama used restart=unless-stopped.
- corvus-web used restart=unless-stopped.
- Private FoxGate Auth used restart=unless-stopped.
- Private FoxGate Gateway used restart=unless-stopped.
- Private Corvus health was OK.
- Public unauthenticated access returned 401.
- Corvus Git working tree was clean.

## Full Host Reboot

A real Linux host reboot was performed.

Observed new boot time:

2026-09-06 09:26:33

No Corvus application component was manually restarted after boot.

## System Service Recovery

The following systemd services recovered automatically:

docker:
enabled
active

cloudflared:
enabled
active

corvus-api:
enabled
active

Result:

PASS

## Container Recovery

The following containers recovered automatically and became healthy:

corvus-llama
status=running
health=healthy
restart=unless-stopped

corvus-web
status=running
health=healthy
restart=unless-stopped

foxgate-auth-private-auth-1
status=running
health=healthy
restart=unless-stopped

foxgate-private-gateway-gateway-1
status=running
health=healthy
restart=unless-stopped

Result:

PASS

## End-to-End Corvus Health

After reboot, the production Corvus web origin returned:

status=OK
service=OK
model_status=OK

Dense recovery returned:

status=OK
caught_up=true
batches=1
indexed=0
progress_after=44

This verifies automatic recovery of:

- llama.cpp model runtime
- FastAPI backend
- production web frontend
- retrieval recovery path

Result:

PASS

## Private Canonical Data Recovery

The active Corvus service retained:

CORVUS_DATA_DIR=/home/ethan/srv/data/corvus/private

Private SQLite verification after reboot:

sqlite_integrity=ok
messages=44
latest_message_id=44

This confirms that canonical private conversation data survived the full-host reboot.

Result:

PASS

## Loopback-Only Security Boundary

Post-reboot listeners remained:

127.0.0.1:8093  Private FoxGate Gateway
127.0.0.1:8094  Private FoxGate Auth
127.0.0.1:8095  llama.cpp
127.0.0.1:8096  Corvus FastAPI
127.0.0.1:8097  Corvus Web

No Private Corvus origin service was observed listening on a public interface.

Result:

PASS

## Cloudflare Recovery

After reboot, the public endpoint:

https://corvus.foxluma.com/api/health

returned:

401

for an unauthenticated request.

This confirms automatic recovery of:

- cloudflared
- Tunnel connectivity
- Cloudflare public routing
- Private FoxGate fail-closed behavior

Result:

PASS

## Private FoxGate Recovery

Local unauthenticated access through the Private FoxGate Gateway returned:

private_unauthenticated_status=401

The Private authentication boundary therefore remained active after reboot.

Result:

PASS

## Browser Acceptance After Reboot

The public application was opened again at:

https://corvus.foxluma.com

The Corvus Memory Playground rendered normally.

Existing private conversations were visible.

The previously issued Private FoxGate browser session remained valid across the host reboot, demonstrating that the persisted Private HMAC key continued to validate the session after service recovery.

No manual service restart was required.

Result:

PASS

## Final Architecture

Internet
→ Cloudflare HTTPS
→ Cloudflare Tunnel
→ 127.0.0.1:8093 Private FoxGate Gateway
→ 127.0.0.1:8094 Private FoxGate Auth
→ 127.0.0.1:8097 Corvus Web
→ 127.0.0.1:8096 Corvus FastAPI
→ 127.0.0.1:8095 llama.cpp
→ /home/ethan/srv/data/corvus/private
   SQLite + LanceDB

Demo and Private FoxGate realms remain independent.

Private credentials and HMAC material remain outside the source repository.

All Private origins remain loopback-only.

## Final Acceptance

The following deployment gates passed:

- production backend
- production frontend
- reboot-safe local model runtime
- canonical private data separation
- isolated Private FoxGate realm
- local authenticated acceptance
- Cloudflare HTTPS routing
- public fail-closed behavior
- remote authenticated browser access
- full-host automatic recovery
- private data persistence
- post-reboot browser acceptance

Final status:

PRIVATE_CORVUS_DEPLOYMENT_SEALED

The Private Corvus deployment is accepted for personal daily use through:

https://corvus.foxluma.com
