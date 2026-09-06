# Private Corvus Data Boundary

Date: 2026-09-06

## Context

Corvus had already been productionized into three loopback-only runtime layers:

- llama.cpp on `127.0.0.1:8095`;
- FastAPI on `127.0.0.1:8096`;
- production Nginx web origin on `127.0.0.1:8097`.

However, the Private Corvus canonical data still lived inside the application
repository under:

`/home/ethan/srv/apps/small-vram-companion/data`

That was acceptable during development but was not suitable as the permanent
Private Corvus data boundary.

## Engineering Question

Can the existing canonical Private Corvus data be moved outside the source
repository without changing:

- canonical conversation history;
- SQLite integrity;
- LanceDB retrieval data;
- FastAPI behavior;
- frontend behavior;
- model runtime;
- memory or retrieval architecture?

## Starting Hypothesis

Corvus already supports the environment variable:

`CORVUS_DATA_DIR`

Therefore the deployment should require only:

1. a consistent copy of the current data;
2. an explicit Private data directory;
3. a systemd configuration update;
4. restart and verification.

No memory subsystem rewrite should be required.

## What We Did

The permanent Private Corvus data directory was established as:

`/home/ethan/srv/data/corvus/private`

Before the cutover, the existing source data was verified:

- SQLite integrity: `ok`
- canonical messages: 40

The Corvus API service was stopped to create a consistent copy.

Copied:

`data/corvus.db`

to:

`/home/ethan/srv/data/corvus/private/corvus.db`

and:

`data/corvus-retrieval.lancedb`

to:

`/home/ethan/srv/data/corvus/private/corvus-retrieval.lancedb`

The systemd service was then updated to use:

`CORVUS_DATA_DIR=/home/ethan/srv/data/corvus/private`

The old repository data was intentionally preserved as a rollback copy.

## Evidence / Results

Copied Private SQLite:

- integrity check: `ok`
- message count: 40
- latest message ID: 40

LanceDB size before cutover:

`432K`

LanceDB size after copy:

`432K`

After service restart:

- Corvus API returned OK;
- model health returned OK;
- dense recovery remained caught up;
- dense progress remained 40;
- actual process environment reported:
  `CORVUS_DATA_DIR=/home/ethan/srv/data/corvus/private`;
- `/api/sessions` through the production web origin returned the existing
  canonical Private sessions;
- systemd remained enabled and active.

The previous repository data remained intact.

## Interpretation

Private personal data is no longer operationally coupled to the source code
checkout.

This reduces deployment risk because source operations such as:

- Git updates;
- frontend rebuilds;
- repository cleanup;
- application replacement;

do not need to modify the active Private canonical memory store.

The same software can now support a future Demo Corvus using a completely
different physical data directory.

## Decision

Adopt:

`/home/ethan/srv/data/corvus/private`

as the permanent Private Corvus data root.

The active Private data files are:

- `/home/ethan/srv/data/corvus/private/corvus.db`
- `/home/ethan/srv/data/corvus/private/corvus-retrieval.lancedb`

The repository-local `data/` directory is no longer the production Private
runtime store.

Do not delete the old repository copy until final deployment and reboot
acceptance are complete.

## Architecture Impact

The deployment boundary is now:

Application source:

`/home/ethan/srv/apps/small-vram-companion`

Private canonical data:

`/home/ethan/srv/data/corvus/private`

This creates the physical isolation required before introducing a separate Demo
Corvus runtime.

## Security Impact

Private Corvus data is now structurally separated from the future Demo runtime.

The Demo Corvus must use a different data root and must never point to the
Private directory.

No logical guest flag, shared SQLite tenant field, or shared LanceDB namespace
is used as the primary isolation boundary.

## Open Questions

Remaining deployment work includes:

- creating the independent Private FoxGate authentication realm;
- creating the Demo Corvus runtime;
- creating the Demo physical data directory;
- configuring FoxLuma hostnames;
- performing authenticated remote acceptance;
- performing final full-host reboot acceptance;
- deciding when the old repository-local rollback data can be safely archived
  or removed.

## Next Step

Create the independent Private FoxGate realm with:

- Private-only credentials;
- separate session signing key;
- separate localhost gateway/auth listeners;
- no authentication-state sharing with the existing Demo realm.

After that, connect Private Corvus to its FoxLuma hostname without exposing the
Corvus origin directly.
