# Private Corvus Remote Authenticated Acceptance

Date: 2026-09-06

## Context

Private Corvus had already passed local authenticated acceptance behind an isolated Private FoxGate realm.

The remaining step before full-host reboot validation was to expose the Private FoxGate gateway through the existing Cloudflare Tunnel and verify the complete remote access path over public HTTPS.

The intended public path was:

Internet
→ Cloudflare HTTPS
→ Cloudflare Tunnel
→ 127.0.0.1:8093 Private FoxGate Gateway
→ 127.0.0.1:8094 Private FoxGate Auth
→ 127.0.0.1:8097 Corvus Web
→ 127.0.0.1:8096 Corvus FastAPI
→ Private canonical SQLite + LanceDB

No Corvus or FoxGate origin port was to be directly exposed to the public network.

## Cloudflare Route

A Published Application route was added to the existing `ethan-home` Cloudflare Tunnel.

Hostname:

corvus.foxluma.com

Service:

http://127.0.0.1:8093

This makes the Private FoxGate Gateway, rather than the Corvus web origin, the public security boundary.

## Public DNS

Public DNS resolution succeeded for:

corvus.foxluma.com

Observed Cloudflare addresses included IPv4 and IPv6 edge addresses.

This confirmed that the hostname had been provisioned through Cloudflare.

## Public HTTPS Fail-Closed Acceptance

An unauthenticated HTTPS request was sent to:

https://corvus.foxluma.com/api/health

Observed result:

public_unauthenticated_status=401

Response protocol:

HTTP/2 401

Response server:

cloudflare

This confirms that:

1. public HTTPS reaches Cloudflare,
2. the Tunnel routes traffic to the Private FoxGate Gateway,
3. FoxGate remains the authentication boundary,
4. unauthenticated access fails closed.

## Origin Exposure Check

After enabling the Cloudflare route, the following Private services remained loopback-only:

127.0.0.1:8093  Private FoxGate Gateway
127.0.0.1:8094  Private FoxGate Auth
127.0.0.1:8096  Corvus FastAPI
127.0.0.1:8097  Corvus Web

No direct public listener was created for these services.

Cloudflare Tunnel remains the only remote ingress path.

## Browser Authenticated Acceptance

The public hostname was opened in a browser:

https://corvus.foxluma.com

FoxGate authentication succeeded using the Private realm credential:

username: ethan

The plaintext password is not recorded in this log.

After authentication, the browser successfully entered the Corvus Memory Playground.

Observed behavior:

- Corvus UI rendered normally.
- Existing private conversation history was visible.
- The session remained behind the Private FoxGate authentication boundary.
- The application was usable through the public HTTPS hostname.

This validates the complete remote browser path:

Browser
→ HTTPS
→ Cloudflare
→ Tunnel
→ Private FoxGate
→ authenticated session
→ Corvus Web
→ Corvus backend
→ Private canonical data

## Security Properties Verified

The remote deployment currently satisfies:

- public HTTPS enabled
- Cloudflare Tunnel ingress
- no direct origin exposure
- unauthenticated API requests return 401
- Private FoxGate login works remotely
- Private session reaches Private Corvus
- Demo and Private FoxGate realms remain separate
- Private canonical data remains outside the source repository
- model, API, web, auth, and gateway remain loopback-only

## Acceptance Result

Status:

REMOTE_AUTHENTICATED_ACCEPTANCE_PASSED

Private Corvus is now remotely usable through:

https://corvus.foxluma.com

while preserving the Private FoxGate security boundary.

## Remaining Deployment Gate

The final deployment gate is full-host reboot recovery.

The reboot acceptance must verify automatic recovery of:

- Docker
- cloudflared
- corvus-llama
- corvus-api
- corvus-web
- Private FoxGate Auth
- Private FoxGate Gateway

It must then verify:

- model health
- API health
- web health
- Private canonical data availability
- Cloudflare Tunnel connectivity
- public unauthenticated 401 behavior
- authenticated browser access after reboot

Only after full-host reboot recovery passes should the Private Corvus deployment be considered fully accepted.
