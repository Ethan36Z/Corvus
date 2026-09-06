# Corvus Production Frontend

Date: 2026-09-06

## Context

Corvus previously used the Vite development server for its React frontend.

The Private Corvus API and llama.cpp runtime had already been hardened into
reboot-safe, loopback-only services.

The remaining frontend deployment gap was replacing the development server
with a stable production origin.

## Engineering Question

Can the existing React interface be served in production without changing the
Stage A2 UI or API contract?

## Starting Hypothesis

The frontend already uses relative `/api/...` requests.

Therefore no React application rewrite should be required.

A production Nginx origin can:

- serve the Vite build output;
- proxy `/api/` to Private Corvus FastAPI;
- remain loopback-only;
- become the single upstream origin for FoxGate.

## What We Did

Created:

`playground/Dockerfile.production`

and:

`deploy/nginx/corvus-web.conf`

Added the `corvus-web` service to:

`compose.corvus.yml`

The frontend image uses a multi-stage build:

Node 24
-> `npm ci`
-> `npm run build`
-> Nginx 1.28 Alpine

Nginx listens on:

`127.0.0.1:8097`

Static React content is served from `/`.

Requests under:

`/api/`

are proxied to:

`127.0.0.1:8096`

The container uses:

`restart: unless-stopped`

## Evidence / Results

The production image built successfully.

The production root returned HTTP 200 and served the generated Vite assets.

The frontend health endpoint returned:

`ok`

The production Nginx API path successfully returned Corvus health data.

`/api/sessions` successfully returned canonical Private Corvus session data.

The frontend listener was confirmed as:

`127.0.0.1:8097`

No listener remained on the old Vite development port:

`127.0.0.1:5173`

A controlled `docker restart corvus-web` was performed.

After restart:

- `/healthz` recovered;
- `/api/health` recovered;
- the production origin remained available.

## Interpretation

Corvus no longer depends on a Vite development server for normal operation.

The web UI and API now share one production origin:

`127.0.0.1:8097`

This simplifies the security boundary because FoxGate can protect one upstream
instead of separate frontend and backend endpoints.

No change was required to `App.tsx` or the Stage A2 API contract.

## Decision

Adopt `corvus-web` as the formal production web origin.

Retire Vite `:5173` from deployment use.

The Private Corvus web/API origin is now:

`127.0.0.1:8097`

The underlying FastAPI origin remains:

`127.0.0.1:8096`

and llama.cpp remains:

`127.0.0.1:8095`

None of these ports should be exposed directly to the public Internet.

## Architecture Impact

Current Private Corvus runtime:

Cloudflare / FoxGate
-> Corvus Nginx `127.0.0.1:8097`
   -> React static frontend
   -> `/api/*`
      -> FastAPI `127.0.0.1:8096`
         -> llama.cpp `127.0.0.1:8095`

Persistent Corvus data remains local and unchanged.

## Open Questions

Remaining deployment work includes:

- moving Private persistent data to its permanent isolated runtime path;
- creating the independent Private FoxGate realm;
- creating the physically isolated Demo Corvus runtime;
- configuring FoxLuma hostnames and Cloudflare routing;
- performing full remote authentication acceptance;
- performing final host reboot recovery acceptance.

## Next Step

Establish the permanent Private Corvus runtime/data boundary before connecting
the service to any public FoxLuma hostname.

Then create the independent Private FoxGate authentication realm.
