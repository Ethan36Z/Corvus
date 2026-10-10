# H1.7c-4 — Foreground registry deployment and provisioning audit

Date: 2026-10-09

Baseline: `lab/ow2e-console` at `8673146abcd9af5dcb6ea87e500f971dd8d2c7f2`

Verdict: **PASS WITH CONSTRAINTS**. The completed read-only audit establishes a
minimal deployment plan for the
[H1.7c-3 registry core](2026-10-09-h1-7c-3-shared-foreground-registry-core.md).
The expected branch, HEAD, and clean worktree were verified before sealing.
No provisioning, publisher integration, or runtime rollout was performed.

## Verified deployment boundary

Lab runs from `/home/ethan/srv/apps/corvus-lab` under
`corvus-lab-api.service`, as `ethan:ethan` (UID/GID 1000). Its service uses
`ProtectSystem=strict`, `PrivateTmp`, and `Restart=no`. The API listens on
loopback port 18096 with one Uvicorn worker. Its writable data root remains
`/home/ethan/srv/data/corvus/lab`; the service sandbox permits writes there and
blocks access to Production's code/private data paths. Stop timeout is 10s.

Production runs from `/home/ethan/srv/apps/small-vram-companion`, on clean
`main` at `f453ed161994c8131bf8d9ed7c43cc15914176cf`, under
`corvus-api.service`, as `ethan:ethan`. It uses `ProtectSystem=full`,
`PrivateTmp`, and restart-on-failure with a 3s delay. The API listens on loopback
port 8096. Its data root remains `/home/ethan/srv/data/corvus/private`.
Stop timeout is 30s. Production remained unmodified and clean during the audit.

Both services run on the same Linux host, restart independently, and share the
Qwen3.5-9B llama.cpp process on `:8095`. Environment settings come from their
installed service definitions and are consumed by the runtime configuration;
neither currently configures a foreground registry path.

Both use the same `app/conversation_runtime.py:process_turn` step-5
`generate_fn(model_messages)` seam. Read-only `git apply --check` verified that
the H1.7c-1 tracker/instrumentation source patch and H1.7c-3 registry module patch
apply to Production at this seam. This does not require merging unrelated Lab
Hindsight work. Production does not yet publish, and the Lab core is not yet
wired to service startup or tracker transitions. A path setting alone cannot
enable publication.

## Runtime registry decision

Use **`/run/corvus-foreground/`**, with owner/group **`ethan:ethan`**, directory
mode **0700**, and registry file mode **0600**. `/run` is host-local tmpfs.
The registry contains process identity, activity counts, timestamps, and lock
identity metadata only; no conversation content or canonical/private data.

Provision through `/etc/tmpfiles.d/corvus-foreground.conf`:

```text
d /run/corvus-foreground 0700 ethan ethan - -
```

The installed systemd 255 tmpfiles mechanism creates the directory on boot.
The `d` entry and unset cleanup age avoid removal of its contents during normal
cleanup. Both API units already follow `systemd-tmpfiles-setup.service` in their
effective ordering. Initial installation must explicitly apply provisioning
before enabling a publisher; startup must reject missing or untrusted state.

Do **not** use service-owned `RuntimeDirectory` cleanup. Independent Lab or
Production restarts must not remove the shared directory, peer records, or lock
inodes. Preserve directory and lock-file identity while services are running;
never replace/delete another live publisher's lock inode.

## Required future service changes

Lab needs an additional `ReadWritePaths=/run/corvus-foreground` allowance while
retaining its existing sandbox/data isolation. Both deployments should use the
same explicit, opt-in registry-path configuration after publisher integration
exists. Production's current `ProtectSystem=full` restrictions already permit
ordinary `/run` writes subject to ownership and permissions, so an additional
write allowance is not required for its present sandbox.

Future service-definition changes require a manager reload, followed by
controlled API restarts to load new code/configuration. No service definitions,
systemd/tmpfiles settings, or runtime environments were changed in this audit.

## Publisher lifecycle contract

- Initialize the registry and create the publisher after worker/process start
  (after any fork), before accepting requests. Open the publisher's stable
  busy/fault lock files at that point and keep the publisher for process life.
- Use a fresh PID/start-ticks/UUID process identity. Validate the header's boot
  identity and monotonic clock domain; inherited publishers cannot be reused.
- Serialize local tracker transitions and publication so stale snapshots cannot
  overtake newer state. Publish 0→1 and acquire busy ownership before foreground
  model generation. Failed publication must prevent that model request.
- Publish overlapping local counts and completion timestamps while retaining
  busy ownership whenever local count is positive. On 1→0, commit the completion
  watermark and zero count before releasing the busy lock.
- On normal service stop, drain foreground work before closing publisher
  ownership. Do not close a live busy publisher merely because shutdown began.
  If forced exit occurs, kernel descriptor closure supplies crash recovery.
- Crash automatically releases kernel flock ownership. Stale positive metadata
  cannot remain BUSY; the reader applies one recovery-grace timestamp because
  the exact interrupted-call finish time is unknown.
- Independent restart creates a new identity and preserves shared watermark and
  peer records. Boot recreates volatile `/run` state and a fresh validated
  registry header; it does not carry monotonic timestamps across boots.

## Future Hindsight read access

Only after both publishers are verified, expose
`/run/corvus-foreground` → `/run/corvus-foreground` through a **read-only** bind
mount. Hindsight must consume metadata only, without importing Corvus internals
or receiving access to private/canonical Corvus data.

The audited `hindsight-lab` container currently has only its data/cache named
volumes and no registry bind. Its user is UID/GID 1000 with an identity user
mapping, compatible with the proposed ownership. Host/API/container boot identity
and monotonic namespace offsets matched during the audit. Revalidate these
assumptions during rollout, including lock inode visibility through the bind.

Use an explicit bind source that must already exist. Adding the mount requires
a later controlled container recreation, preserving its existing cached image,
configuration, ports, network, and named volumes; a container restart alone
cannot add a mount. No mount or Hindsight change was made during this audit.
Hindsight admission remains disconnected.

## Controlled rollout order

1. Complete and test Corvus publisher integration, configurable and disabled by
   default, preserving the process-local tracker and registry core.
2. Provision the neutral runtime directory and initialize/validate it without
   touching canonical data.
3. Enable the Lab publisher, restart Lab under controlled conditions, and verify
   identity, permissions, and behavior without real inference.
4. Selectively deploy and enable the Production publisher, with its own
   controlled restart and verification.
5. Verify cross-process aggregation, completion watermark, crash recovery, and
   independent service restart behavior.
6. Only then mount the registry read-only into Hindsight; admission integration
   remains a separate later step.

## No-real-inference acceptance requirements

Confirm Lab and Production publisher records match each live API's PID/start
identity and appear idle before testing. Use disposable runners exercising the
same integrated tracker/publisher wrapper with fake model generation and
sandbox-equivalent permissions. Do not submit real foreground completions or
use canonical data initialization for these runners.

Acceptance must prove simultaneous count aggregation and **2→1→0** transitions,
advancing completion watermark, and preservation of the other publisher's
identity/inodes/state during an independent idle API restart. Kill a disposable
busy publisher to verify automatic lock release and stale-record recovery.
Exercise malformed metadata and publication failures in temporary test
registries and require **UNKNOWN**, without corrupting the live registry.
Inspect the metadata-only contract and isolated data-root configuration to
confirm no private data crosses the Lab/Production boundary.

## Known limitations and next objective

Admission cannot preempt a memory generation that has already started.
UNKNOWN must defer/fail safe. Auxiliary model calls and unconfigured callers
remain untracked. Service stop timeouts (Lab 10s, Production 30s) may expire
before the default 60s model timeout; shutdown cannot assume a foreground call
has finished. Directory and lock inode identities must stay stable. Malformed
or interrupted registration state requires deliberate repair rather than
guessing IDLE or deleting potentially live ownership.

Next engineering objective: **Implement publisher integration in Corvus using
the existing process-local tracker and registry core, disabled/configurable by
default, without deploying or restarting Lab or Production yet.**

This sealing task created only this project log. No application code,
Production files, Hindsight settings, services, tmpfiles configuration, bank
state, or running endpoints were changed. `/run/corvus-foreground/` was not
created. No inference, reboot/shutdown, or push occurred.
