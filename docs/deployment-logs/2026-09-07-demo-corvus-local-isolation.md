# Demo Corvus Local Isolation Deployment

Date: 2026-09-07

## Context

Private Corvus deployment was already SEALED.

Demo deployment was intentionally designed as the same Corvus code and model release with physically separate runtime state and canonical memory.

## Architecture

Shared model runtime:

127.0.0.1:8095 — llama.cpp / Qwen3.5-9B

Private:

127.0.0.1:8096 — Private API
127.0.0.1:8097 — Private Web
/home/ethan/srv/data/corvus/private — Private canonical data

Demo:

127.0.0.1:8098 — Demo API
127.0.0.1:8099 — Demo Web
/home/ethan/srv/data/corvus/demo — Demo canonical data

## Deployment Profile

Added:

deploy/systemd/corvus-demo-api.service
deploy/nginx/corvus-web-demo.conf
compose.corvus.demo.yml

The Demo API uses the same Corvus source tree and Python environment as Private Corvus but receives a different CORVUS_DATA_DIR.

The Demo Web is built from the same production frontend source and Dockerfile while mounting a separate tracked Nginx deployment profile.

## Data Boundary

Demo canonical storage was initialized from an empty state.

The repo-local legacy data directory was not used.

The Private data directory was not copied.

Demo SQLite and LanceDB were created under:

/home/ethan/srv/data/corvus/demo

## Isolation Acceptance

Before the Demo chat:

Private messages: 52
Demo messages: 0

A Demo-only marker was written through the real Demo Web/API path.

After the Demo chat:

Private messages: 52
Demo messages: 2

Marker validation:

Private marker hits: 0
Demo marker hits: present

Therefore the Demo write changed only the Demo canonical Evidence Log.

## Runtime Acceptance

Demo API:

127.0.0.1:8098

Demo Web:

127.0.0.1:8099

Both origins remained loopback-only.

Demo API and Web reached the shared model runtime at:

127.0.0.1:8095

Private Corvus remained healthy after the Demo isolation test.

## Decision

Status:

DEMO_LOCAL_DATA_ISOLATION_PASSED

The Demo instance now shares Corvus code and model capability with Private Corvus while maintaining a physically independent canonical memory boundary.

## Next Step

Add demo.corvus.foxluma.com to the existing Demo FoxGate realm on 127.0.0.1:8091, routing authenticated Demo traffic to 127.0.0.1:8099.

Then expose that hostname through Cloudflare Tunnel and perform remote Demo acceptance.
