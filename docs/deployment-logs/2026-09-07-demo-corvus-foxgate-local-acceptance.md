# Demo Corvus FoxGate Local Acceptance

Date: 2026-09-07

## Context

Demo Corvus had already passed local runtime and physical memory isolation acceptance.

This checkpoint attached the isolated Demo Corvus instance to the existing Demo FoxGate authentication realm.

## Architecture

demo.corvus.foxluma.com
→ 127.0.0.1:8091 Demo FoxGate Gateway
→ 127.0.0.1:8092 Demo FoxGate Auth
→ 127.0.0.1:8099 Demo Corvus Web
→ 127.0.0.1:8098 Demo Corvus API
→ 127.0.0.1:8095 shared llama.cpp runtime

Demo canonical data:

/home/ethan/srv/data/corvus/demo

Private Corvus remains on its independent FoxGate realm and private canonical data boundary.

## FoxGate Change

Added:

demo.corvus.foxluma.com
→ http://127.0.0.1:8099

The Corvus route uses 600-second send/read proxy timeouts for local-model requests.

Existing JobTrack, PawCareHub, and FoxWords routes were retained.

## Acceptance

Validated:

- Existing Demo hosts remained fail-closed with HTTP 401.
- Demo Corvus returned HTTP 401 when unauthenticated.
- Unknown Host returned HTTP 404.
- Browser navigation redirected to FoxGate login.
- Existing Demo credentials authenticated successfully.
- FoxGate issued a Demo session cookie.
- Authenticated Demo Corvus /api/health returned HTTP 200.
- Corvus service status was OK.
- Shared model status was OK.
- Demo session cookie was rejected by the independent Private FoxGate realm with HTTP 401.
- Private SQLite integrity remained OK.
- Demo SQLite integrity remained OK.

## Security Boundary

Demo and Private share Corvus source code and model capability while retaining independent:

- authentication realms
- session HMAC keys
- credentials
- API processes
- Web origins
- SQLite Evidence Logs
- LanceDB indexes

## Decision

Status:

DEMO_FOXGATE_LOCAL_ACCEPTANCE_PASSED

## Next Step

Publish demo.corvus.foxluma.com through the existing Cloudflare Tunnel to:

http://127.0.0.1:8091

Then perform remote recruiter-path acceptance over public HTTPS.
