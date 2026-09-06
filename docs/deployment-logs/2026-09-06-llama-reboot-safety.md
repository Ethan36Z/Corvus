# Corvus llama.cpp — Reboot Safety

Date: 2026-09-06

## Context

The Private Corvus FastAPI service had already been moved to systemd and
restricted to the loopback interface.

The remaining runtime weakness was the local llama.cpp container.

Before this change:

- Docker itself was enabled and active;
- `corvus-llama` was healthy;
- the model endpoint was correctly exposed only as:
  `127.0.0.1:8095`;
- the container restart policy was:
  `no`.

That meant a host reboot could leave Corvus API running without its local model
runtime.

## Engineering Question

Can the existing llama.cpp runtime be made reboot-safe without changing:

- model image;
- model file;
- GPU configuration;
- context size;
- inference parameters;
- localhost-only network exposure;
- Corvus API model endpoint?

## Starting Hypothesis

Because Docker already starts automatically at boot, adding:

`restart: unless-stopped`

to the existing `corvus-llama` Compose service should be sufficient.

No inference or application architecture change should be required.

## What We Did

Updated:

`compose.corvus.yml`

to add:

`restart: unless-stopped`

to the `corvus-llama` service.

The Compose configuration was validated before applying the change.

The service was recreated using:

`docker compose -f compose.corvus.yml up -d corvus-llama`

## Evidence / Results

After recreation:

- llama.cpp HTTP health returned `ok`;
- Docker restart policy reported:
  `unless-stopped`;
- container status returned to running;
- Docker health reached:
  `healthy`;
- the host listener remained:
  `127.0.0.1:8095`;
- Corvus API remained healthy;
- model health through Corvus API remained OK;
- dense recovery remained caught up;
- canonical progress remained 40.

No model configuration or memory architecture changes were required.

## Interpretation

The model runtime is now compatible with unattended host restart recovery.

Because Docker itself is enabled at boot and the container uses
`unless-stopped`, llama.cpp should automatically return after a normal host
restart unless it was deliberately stopped by an operator.

The model endpoint remains inaccessible directly from LAN, Tailscale, or public
network interfaces.

## Decision

Adopt `restart: unless-stopped` as the formal restart policy for
`corvus-llama`.

Keep the model endpoint at:

`127.0.0.1:8095`

The existing model, quantization, llama.cpp image, and inference parameters
remain unchanged.

## Architecture Impact

The core Private Corvus runtime now has two independently supervised layers:

systemd
-> Corvus FastAPI
-> `127.0.0.1:8096`

Docker
-> llama.cpp
-> `127.0.0.1:8095`

Both are configured to recover automatically after host startup.

## Open Questions

Full host-reboot acceptance has not yet been performed.

In particular, the FastAPI service may become active before llama.cpp has
finished loading the model.

This is acceptable for now because the runtime has independent health
reporting, but final deployment acceptance must verify recovery behavior after
a real host reboot.

Remaining deployment work includes:

- production frontend serving;
- permanent Private/Demo data separation;
- Private FoxGate realm;
- Demo Corvus runtime;
- FoxLuma routing;
- full remote and reboot acceptance.

## Next Step

Productionize the Corvus web frontend so it no longer depends on the Vite
development server.

Preserve the existing Stage A2 UI behavior while moving frontend delivery to a
stable production runtime.
