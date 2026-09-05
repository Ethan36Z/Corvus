# FoxLuma Deployment & Security Baseline

Date: 2026-09-05

## Context

Corvus Stage A2 has been sealed as:

`PRODUCTION_CANDIDATE_DAILY_USE_BACKEND`

Current deployment work is focused on turning the existing working Corvus into
a secure remotely accessible personal AI service under FoxLuma, while also
supporting a portfolio/demo instance for job applications.

This checkpoint records deployment and security decisions before
production-like deployment changes begin.

## Engineering Question

How should Corvus be exposed through FoxLuma so that:

- Ethan can use a real private Corvus remotely;
- recruiters can interact with a real Corvus demo;
- private canonical memory is never exposed to demo users;
- the existing FoxGate and Cloudflare infrastructure can be reused;
- Corvus does not need to become a multi-user SaaS before job applications;
- future iPhone and iPad clients can use the same backend contract.

## Starting Position

Existing infrastructure already includes:

- Cloudflare Tunnel managed as a systemd service;
- FoxGate V2 signed-cookie authentication;
- an existing demo credential realm used for portfolio applications;
- localhost-hosted web applications;
- Corvus llama.cpp on `127.0.0.1:8095`;
- Corvus FastAPI backend currently running on port `8096`;
- React/Vite Corvus frontend;
- SQLite canonical Evidence Log;
- LanceDB derived dense retrieval index.

The existing FoxGate credential has previously been shared with recruiters and
must therefore be treated strictly as a demo credential.

## Runtime Audit Evidence

Observed on the Linux host:

- Repository HEAD before deployment work:
  `4a62997 Add P3 reviewer benchmark artifacts`
- working tree clean after committing the historical P3 reviewer artifacts;
- `data/corvus.db` exists and contains current canonical Corvus history;
- `data/corvus-retrieval.lancedb` exists;
- `CORVUS_DATA_DIR` is currently unset, so development data resolves under the
  repository `data/` directory;
- `corvus-llama` is healthy and published only as:
  `127.0.0.1:8095 -> container:8080`;
- llama.cpp currently has Docker restart policy `no`;
- Corvus FastAPI currently runs through tmux and listens on:
  `0.0.0.0:8096`;
- Corvus Vite development server listens on:
  `127.0.0.1:5173`;
- UFW is currently inactive;
- FoxGate V2 gateway listens on:
  `127.0.0.1:8091`;
- FoxGate auth service listens on:
  `127.0.0.1:8092`;
- both FoxGate containers use `restart=unless-stopped`;
- Cloudflare Tunnel is enabled and active under systemd;
- the tunnel is remotely managed using a token rather than a local ingress
  `config.yml`;
- `foxwords.foxluma.com` currently resolves publicly;
- `corvus.foxluma.com` currently has no public DNS resolution.

## Decisions

### 1. FoxGate becomes two independent authentication realms

The existing FoxGate deployment becomes the:

`Demo Realm`

It continues to use the existing recruiter-facing demo credentials.

A second independent deployment will become the:

`Private Realm`

The Private Realm will use:

- credentials known only to Ethan;
- a separate session signing/HMAC key;
- separate localhost listeners;
- no shared authentication state with the Demo Realm.

This is deployment isolation, not merely two user roles inside one FoxGate
realm.

### 2. Corvus will have Private and Demo runtime instances

Both environments will reuse the same Corvus codebase and software
architecture.

They may also reuse:

- the same frontend source/build;
- the same FastAPI implementation;
- the same retrieval implementation;
- the same local Qwen model;
- the same internal llama.cpp service.

They must not share persistent Corvus data.

### 3. Private and Demo memory stores are physically separated

Private Corvus and Demo Corvus must use different `CORVUS_DATA_DIR` values.

Conceptually:

Private Corvus:

- `private/corvus.db`
- `private/corvus-retrieval.lancedb`

Demo Corvus:

- `demo/corvus.db`
- `demo/corvus-retrieval.lancedb`

The separation applies to:

- SQLite canonical Evidence Log;
- LanceDB derived retrieval index.

No `guest` flag or logical tenant field inside the private canonical database
will be used as the primary isolation mechanism.

### 4. Demo users must never access Private canonical memory

Recruiters may interact with a functional Corvus demo, including persistent
conversation and retrieval behavior, but all writes and recall must remain
inside the Demo data environment.

Demo data may later be periodically reset or restored from a clean snapshot.

Private canonical history must never participate in that reset process.

### 5. Public ingress remains thin

The intended boundary is:

Internet
-> Cloudflare HTTPS
-> Cloudflare Tunnel
-> FoxGate
-> Corvus web/API origin
-> internal model and data services

The following must remain non-public:

- llama.cpp model endpoint;
- SQLite;
- LanceDB;
- retrieval internals;
- arbitrary backend ports.

### 6. Private Corvus must not use recruiter demo credentials

The existing FoxGate credential is intentionally treated as public/demo access
because it has been distributed with portfolio/job-application materials.

Private Corvus must therefore never rely on that credential.

### 7. Native clients remain first-class

FoxGate is an access-control layer, not a UI layer.

Future iPhone and iPad clients may use native SwiftUI interfaces and communicate
with the same Corvus HTTP API.

The native application does not need to visually embed the FoxGate HTML login
page. Authentication transport and native UI should remain separate concerns.

### 8. Do not redesign Corvus for deployment

Deployment must not trigger unnecessary changes to:

- memory architecture;
- Evidence Recall;
- conversation runtime;
- Stage A2 API contract;
- personality architecture;
- UI structure.

Deployment changes should remain operational unless a real deployment defect
requires an application change.

## Security Invariants

The following are deployment invariants:

1. Private and Demo credentials are independent.
2. Private and Demo session signing keys are independent.
3. Private and Demo SQLite files are physically separate.
4. Private and Demo LanceDB indexes are physically separate.
5. llama.cpp remains loopback/internal-only.
6. Corvus API should not remain exposed on `0.0.0.0` in the final deployment.
7. Canonical Private Evidence Log must survive service restart, host reboot,
   and deployment updates.
8. Demo reset operations must be incapable of targeting Private data.
9. Unknown public hostnames must fail closed.
10. Deployment must preserve the principle:
    `Always Maintain a Working Corvus.`

## Initial Deployment Architecture

Internet
  |
  v
Cloudflare
  |
  v
Cloudflare Tunnel
  |
  +-----------------------------+
  |                             |
  v                             v
Demo FoxGate               Private FoxGate
Demo credentials           Ethan-only credentials
  |                             |
  +--------+--------+           |
  |        |        |           |
  v        v        v           v
JobTrack  PawCare  Demo       Private
                 Corvus       Corvus
                   |             |
                   v             v
               Demo Data     Private Data
                    \           /
                     \         /
                      v       v
                    shared llama.cpp
                    127.0.0.1:8095

Candidate hostnames:

- `corvus.foxluma.com` -> Private Corvus
- `demo.corvus.foxluma.com` -> Demo Corvus

These hostnames remain candidates until Cloudflare and FoxGate routing are
actually configured and verified.

## Immediate Deployment Gaps

The audit identified the following concrete gaps:

- FastAPI currently runs via tmux rather than a reboot-safe service;
- FastAPI currently binds to `0.0.0.0:8096`;
- llama.cpp currently has no automatic Docker restart policy;
- the frontend currently runs as a Vite development server;
- Private FoxGate realm does not yet exist;
- Private and Demo Corvus data directories have not yet been created;
- Corvus Cloudflare hostnames have not yet been configured;
- remote deployment acceptance has not yet been performed.

## Decision

Proceed with a minimal, incremental private-and-demo deployment.

Do not build multi-user Corvus, database-level guest tenancy, SaaS account
management, or other unrelated product infrastructure as a prerequisite for
job-application deployment.

Security is achieved first through independent runtime, authentication, and
physical data boundaries.

## Next Step

Before public routing changes:

1. preserve and verify the existing canonical Corvus data;
2. replace the temporary tmux FastAPI runtime with a loopback-only,
   reboot-safe backend service;
3. make the llama.cpp runtime reboot-safe;
4. productionize frontend serving;
5. establish Private FoxGate;
6. establish physically isolated Private and Demo Corvus data runtimes;
7. configure FoxLuma routing;
8. perform authenticated remote deployment acceptance.
