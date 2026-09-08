# Demo Corvus Remote HTTPS Acceptance

Date: 2026-09-07

## Context

Demo Corvus had already passed local runtime isolation, physical Private/Demo memory isolation, and local Demo FoxGate authentication acceptance.

The public Demo hostname is:

demo-corvus.foxluma.com

During public acceptance, the existing Demo Auth runtime was found to have been started from the base Compose profile with FOXGATE_COOKIE_SECURE=false.

The tracked production Compose override already defined the correct setting:

FOXGATE_COOKIE_SECURE=true

The Demo Auth container was recreated using both the base and production Compose profiles. Credentials and the persisted session HMAC key were unchanged.

## Public Architecture

Internet
→ Cloudflare HTTPS
→ ethan-home Tunnel
→ 127.0.0.1:8091 Demo FoxGate
→ 127.0.0.1:8092 Demo Auth
→ 127.0.0.1:8099 Demo Corvus Web
→ 127.0.0.1:8098 Demo Corvus API
→ 127.0.0.1:8095 shared llama.cpp runtime

## Cloudflare Route

demo-corvus.foxluma.com

routes to:

http://127.0.0.1:8091

The public route terminates at Demo FoxGate rather than directly exposing a Corvus origin.

## Remote Acceptance

Validated over the real public HTTPS hostname:

- Public unauthenticated API access returned HTTP 401.
- Browser navigation redirected to FoxGate.
- Existing Demo credentials authenticated successfully.
- Login returned HTTP 303.
- FoxGate issued foxgate_session_v1.
- The session cookie was HttpOnly.
- The session cookie was Secure.
- The session cookie used SameSite=Lax.
- The session cookie was host-only.
- Authenticated public /api/health returned HTTP 200.
- Corvus status was OK.
- Corvus service status was OK.
- Shared local model status was OK.
- Private SQLite integrity remained OK.
- Demo SQLite integrity remained OK.

## Security Boundary

Private Corvus remains available only at:

corvus.foxluma.com

behind its independent Private FoxGate realm.

Demo and Private share Corvus source code and the local model runtime while retaining independent authentication trust and canonical memory.

## Decision

Status:

DEMO_REMOTE_HTTPS_ACCEPTANCE_PASSED

## Next Step

Perform real browser recruiter-path acceptance:

demo-corvus.foxluma.com
→ FoxGate login
→ Demo Corvus UI

Then perform full-host reboot recovery acceptance before sealing the Demo Corvus deployment.
