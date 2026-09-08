# Demo Corvus Full-Host Reboot Acceptance

Date: 2026-09-07

## Context

Demo Corvus had already passed:

- isolated local runtime acceptance
- physical Private/Demo canonical-data isolation
- Demo FoxGate local authentication acceptance
- public Cloudflare HTTPS acceptance
- production Secure-cookie acceptance
- real recruiter browser-path acceptance
- cleanup to a zero-message public baseline

A full-host reboot was then performed to validate unattended recovery of the complete deployed stack.

## Reboot Evidence

Observed boot start:

2026-09-07 22:49:31

No Corvus, FoxGate, model-runtime, Web, API, Docker, or Cloudflare service was manually restarted after the host reboot.

## Automatic Recovery

The following systemd services recovered automatically:

- docker
- cloudflared
- corvus-api
- corvus-demo-api

The following containers recovered automatically under restart=unless-stopped:

- corvus-llama
- corvus-web
- corvus-demo-web
- foxgate-auth-phase2-auth-1
- foxgate-v2-phase3-gateway-1
- foxgate-auth-private-auth-1
- foxgate-private-gateway-gateway-1

## Runtime Security

Demo Auth retained:

FOXGATE_COOKIE_SECURE=true

All Corvus / FoxGate / model application listeners on ports 8091-8099 remained loopback-only during post-reboot acceptance.

Unauthenticated public API access remained fail-closed:

- corvus.foxluma.com → HTTP 401
- demo-corvus.foxluma.com → HTTP 401

## Data Boundary

Private Corvus:

/home/ethan/srv/data/corvus/private

Demo Corvus:

/home/ethan/srv/data/corvus/demo

Post-reboot SQLite integrity:

- Private: OK
- Demo: OK

Post-reboot canonical message counts:

- Private: 52
- Demo: 0

The clean recruiter-facing Demo baseline therefore survived reboot without affecting Private Corvus.

## End-to-End Recovery

Post-reboot local health:

- shared llama.cpp runtime: HTTP 200
- Private Corvus: HTTP 200
- Demo Corvus: HTTP 200

Private and Demo FoxGate realms both continued to fail closed for unauthenticated requests.

A final real-browser recruiter-path check was performed after reboot.

The Demo FoxGate login page loaded successfully, authentication succeeded, Corvus UI loaded successfully, and the recruiter-facing conversation list remained clean with no test data.

## Operational Note

The Demo Auth production deployment uses both:

auth/compose.yaml

and:

auth/compose.production.yaml

The production override is required to retain:

FOXGATE_COOKIE_SECURE=true

when intentionally recreating the Demo Auth container.

## Decision

The Demo deployment has satisfied:

- runtime isolation
- canonical-data isolation
- authentication-realm isolation
- public HTTPS access control
- secure production cookie behavior
- recruiter browser usability
- clean public-memory baseline
- persistence across full-host reboot
- automatic service recovery
- fail-closed public behavior

Status:

DEMO_CORVUS_DEPLOYMENT_SEALED

## Public Demo

https://demo-corvus.foxluma.com

## Architecture

Internet
→ Cloudflare
→ Demo FoxGate :8091
→ Demo Auth :8092
→ Demo Web :8099
→ Demo API :8098
→ shared llama.cpp :8095
→ /home/ethan/srv/data/corvus/demo

Private Corvus remains independently isolated at:

https://corvus.foxluma.com
