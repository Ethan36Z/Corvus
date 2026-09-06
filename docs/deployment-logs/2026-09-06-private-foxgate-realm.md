# Private FoxGate Realm Deployment

Date: 2026-09-06

## Context

Corvus already had a production-candidate daily-use backend, production Nginx frontend, reboot-safe local model runtime, systemd-managed FastAPI service, and canonical private data physically separated from the source repository.

Before exposing Private Corvus through FoxLuma, the remaining security requirement was to create an authentication realm completely independent from the recruiter/demo credentials already used by FoxGate.

Requirements:

- Demo FoxGate credentials must never authorize Private Corvus.
- Private Corvus must use independent credentials and session-signing material.
- Private and Demo gateways/auth services must run as separate processes and ports.
- All origins must remain loopback-only.
- Unknown hosts and unauthenticated requests must fail closed.

## Architecture

### Demo Realm

Demo applications
→ 127.0.0.1:8091 FoxGate Demo Gateway
→ 127.0.0.1:8092 FoxGate Demo Auth

Existing Demo applications include JobTrack, PawCareHub, and FoxWords.

### Private Realm

corvus.foxluma.com
→ 127.0.0.1:8093 FoxGate Private Gateway
→ 127.0.0.1:8094 FoxGate Private Auth
→ 127.0.0.1:8097 Corvus production web origin
→ 127.0.0.1:8096 Corvus FastAPI
→ Private canonical SQLite + LanceDB

Private canonical data:

/home/ethan/srv/data/corvus/private

Private FoxGate secrets:

/home/ethan/srv/shared/secrets/private-access

Private FoxGate deployment configuration:

/home/ethan/srv/infrastructure/private-access

## FoxGate Reusability Hardening

Before creating the Private realm, two FoxGate assumptions were removed.

### Single-user credential generalization

FoxGate previously hardcoded the only allowed username as `demo`.

The parser was generalized to support exactly one safe username while preserving the single-user security model.

Result:

Demo realm    → demo
Private realm → ethan

FoxGate commit:

424934d Generalize FoxGate single-user credentials

Tests confirmed Demo compatibility and support for a distinct Private username.

### Realm-aware Auth healthcheck

FoxGate Auth previously hardcoded its healthcheck endpoint to:

127.0.0.1:8092

That could allow a Private Auth instance on port 8094 to accidentally healthcheck the Demo Auth service.

The healthcheck was changed to use the configured FOXGATE_LISTEN_ADDR.

FoxGate commit:

1009bba Make FoxGate healthcheck realm-aware

Go 1.24 tests passed before deployment.

## Private Credentials and Session Isolation

The Private realm username is:

ethan

The plaintext password is not stored in Git, Compose configuration, or deployment documentation.

Only a bcrypt password hash is persisted in:

/home/ethan/srv/shared/secrets/private-access/gated.htpasswd

The Private realm has an independent 32-byte session HMAC key:

/home/ethan/srv/shared/secrets/private-access/session-hmac.key

Observed file permissions:

-rw------- gated.htpasswd
-rw------- session-hmac.key

The Private credential file and Demo credential file are physically separate.

The Private HMAC key and Demo HMAC key are physically separate.

FoxGate's session cookie does not set a Domain attribute, so it is host-only at the browser layer. Realm isolation is additionally enforced cryptographically by independent HMAC keys.

## Runtime

Private Auth:

container: foxgate-auth-private-auth-1
listen:    127.0.0.1:8094
status:    healthy
restart:   unless-stopped

Private Gateway:

container: foxgate-private-gateway-gateway-1
listen:    127.0.0.1:8093
status:    healthy
restart:   unless-stopped

Existing Demo services remained healthy:

foxgate-v2-phase3-gateway-1
foxgate-auth-phase2-auth-1

Observed listeners after deployment:

127.0.0.1:8091  Demo Gateway
127.0.0.1:8092  Demo Auth
127.0.0.1:8093  Private Gateway
127.0.0.1:8094  Private Auth
127.0.0.1:8097  Private Corvus Web

No FoxGate or Corvus origin was exposed directly on a non-loopback interface.

## Fail-Closed Acceptance

Unauthenticated Private Corvus API request through the Private Gateway:

Host: corvus.foxluma.com
GET /api/health
→ 401

Observed:

unauthenticated_status=401

Unknown Host request through the Private Gateway:

→ 404

Observed:

unknown_host_status=404

The existing Demo realm remained protected:

demo_unauthenticated_status=401

The direct Private Corvus origin remained healthy:

status=OK
service=OK
model_status=OK
dense_recovery_status=OK
dense_recovery_caught_up=true
dense_recovery_progress_after=40

## Authenticated End-to-End Acceptance

A real Private FoxGate login was performed through:

127.0.0.1:8093
Host: corvus.foxluma.com

using the Private `ethan` credential.

Observed:

login_status=303
login_redirect=/api/health
session_cookie=issued
session_token_length=102

The issued Private session was then used through the Private Gateway.

Observed:

private_authenticated_status=200
corvus_status=OK
model_status=OK

The same Private session cookie was deliberately sent to the Demo FoxGate realm.

Observed:

private_cookie_on_demo_status=401

Therefore:

Private login → Private session → Private Corvus: PASS
Private session → Demo realm: REJECTED

This verifies that recruiter/demo credentials and sessions do not provide an authentication path into Private Corvus.

## Security Boundary

Demo realm:

- separate credential
- separate HMAC key
- separate Auth process
- separate Gateway process
- separate ports

Private realm:

- separate credential
- separate HMAC key
- separate Auth process
- separate Gateway process
- separate ports
- separate Corvus canonical data

The two realms reuse FoxGate code but do not share authentication state.

## Decision

Private FoxGate Realm local deployment is accepted.

Status:

LOCAL_AUTHENTICATED_ACCEPTANCE_PASSED

## Next Step

Route:

corvus.foxluma.com
→ Cloudflare HTTPS / Tunnel
→ 127.0.0.1:8093
→ Private FoxGate Gateway

Then perform remote acceptance covering:

1. public DNS resolution
2. HTTPS
3. unauthenticated access denial
4. successful Private login
5. authenticated Corvus UI/API access
6. Demo/Private realm isolation
7. origin ports remaining non-public

After remote acceptance, perform final full-host reboot recovery validation.
