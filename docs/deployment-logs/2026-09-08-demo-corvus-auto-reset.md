# Demo Corvus Auto Reset

Date: 2026-09-08

## Context

Demo Corvus is a recruiter-facing deployment that is physically separated
from Private Corvus.

Trial conversations should not accumulate indefinitely, so the Demo
deployment is automatically returned to a clean baseline once per day.

## Schedule

A persistent systemd timer performs the reset at 04:00 local server time.

Current host timezone is Pacific time.

## Data Boundaries

Demo:

    /home/ethan/srv/data/corvus/demo

Private:

    /home/ethan/srv/data/corvus/private

The reset script contains explicit safety guards requiring both resolved
paths to match these exact locations.

It refuses to continue if:

- Demo path differs from the expected Demo path.
- Private path differs from the expected Private path.
- Demo and Private resolve to the same location.
- Either data directory is a symlink.
- Private SQLite integrity fails.
- Private message count changes across the reset.
- Demo message count is nonzero after reset.

Only the Demo data directory is cleared.

## Backup

Before each reset, the current Demo data is archived under:

    /home/ethan/srv/backups/corvus-demo-resets/

Old reset backups are pruned after the configured retention period.

## Initial Acceptance Failure

The first reset implementation correctly cleared only Demo data, but the
Demo API was started before the empty SQLite schema had been recreated.

Observed result:

    dense_recovery error="no such table: messages"
    demo_messages=no_messages_table

Private Corvus remained intact:

    private_integrity=ok
    private_messages=52

## Fix

The reset flow was changed to explicitly initialize the canonical Demo
SQLite schema after clearing the Demo directory and before starting the API.

Schema initialization runs as the ethan user with:

    CORVUS_DATA_DIR=/home/ethan/srv/data/corvus/demo
    python -m memory.store

This prevents root-owned runtime data and ensures the canonical messages
table and related SQLite structures exist before API startup.

## Final Acceptance

Reset service:

    Result=success
    ExecMainStatus=0

Data:

    private_integrity=ok
    private_messages=52
    demo_integrity=ok
    demo_messages=0

Demo health:

    status=OK
    service=OK
    model=OK
    dense_recovery=OK
    caught_up=true
    progress_after=0

Public Demo remained fail-closed:

    HTTP/2 401

Timer:

    enabled
    active
    OnCalendar=*-*-* 04:00:00
    Persistent=true

## Installed Components

    deploy/scripts/reset-corvus-demo-data.sh
    deploy/systemd/corvus-demo-reset.service
    deploy/systemd/corvus-demo-reset.timer

Installed systemd units:

    /etc/systemd/system/corvus-demo-reset.service
    /etc/systemd/system/corvus-demo-reset.timer

## Result

    DEMO_CORVUS_AUTO_RESET_INSTALLED
