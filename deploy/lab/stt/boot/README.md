# Restore retained Lab STT after a reboot

This repairs host-file persistence and existing Docker restart policies. It does
not build an image, deploy Vision, restore a database, or add a service manager.
Start from the actual retained WebUI/Bridge/Whisper IDs/images, not old image
values in the R7 package defaults. The existing enabled Docker service owns boot.

## Prepared checkpoint (2026-10-20)

The current WebUI and Bridge reference deleted temporary credential files.
WebUI uses `unless-stopped`; Bridge and Whisper used `no`. The protocol override
and admission file already survived under a protected home recovery directory.
The original service credential also survives there as UID/GID 10001, mode 0400;
its value/format/equality are not read by the unprivileged preparation step.

`recover.py prepare` saves current container metadata and a resolved runtime-only
Compose packet under `/home/ethan/.config/corvus-lab/stt-runtime` (0700, files 0600).
It reuses the protected full configuration, pins actual images/environment,
removes obsolete build contexts, replaces only STT bind sources and restart
policies, and checks resolved environment/resource compatibility. No runtime
change occurs in prepare. Private packets contain authentication settings: never
print or commit them. Existing data volumes and protected backups are retained.

## Local operator boundary

Review the committed helper and unchanged credential-repair primitive first.
As ethan in a local interactive terminal, execute only:

```sh
sudo /usr/bin/python3 -I /home/ethan/srv/apps/corvus-stt-reboot-repair/deploy/lab/stt/boot/persist_material.py
```

The password is handled only by local sudo. Never send it through chat, stdin
pipes, environment variables or files. The assistant must not assume sudo in a
separate terminal authorizes its calls.

The helper reads the existing protected original credential without printing or
hash-publishing it, reuses `activation/credential_repair.py` to make the two
consumer-specific copies, and privately verifies equality. It validates the
exact pinned one-line WebUI owner-check specialization before copying it. It
preserves the existing admission value, with no automatic enable/disable toggle.

Persistent files outside Git:

| File below `/etc/corvus-lab/stt` | UID/GID | Mode |
| --- | --- | --- |
| `webui/credential` | 0/0 | 0400 |
| `bridge/credential` | 10001/10001 | 0400 |
| `webui-protocol.py` | 0/0 | 0444 |
| `stt-admissions` | 1000/1000 | 0444 |

The root parent is 0700; consumer directories are owner-specific 0700. Docker
resolves bind sources as the daemon; consumers see only their assigned read-only
files and retain dropped capabilities. Nothing is made world-readable beyond
the unchanged public-module/admission file modes under a protected parent.
The original protected credential/backup files are not changed. Existing complete
outputs are verified rather than overwritten; partial/unexpected outputs fail
closed for review. Missing/invalid original material never triggers rotation.

Success prints `PERSISTENT_STT_MATERIAL_READY` (or already-verified equivalent).
Stop and notify the assistant so it can independently verify and finish the
already authorized scoped recovery. This root helper itself changes no service,
Compose runtime, systemd unit, database or image.

## Resume after material provisioning

Use the same committed worktree; no old `/tmp` runners are necessary:

```sh
python3 -B deploy/lab/stt/boot/recover.py consumer-checks
python3 -B deploy/lab/stt/boot/recover.py restore
python3 -B deploy/lab/stt/boot/recover.py verify
```

The actual pinned consumer images first check their assigned credential/protocol
mounts under effective UID 0 and UID 10001 with dropped capabilities, read-only
roots and no network/data/model mounts. Only owned isolated helpers are removed.
Then the retained Compose packet targets only `corvus-stt-bridge open-webui`,
using `--no-deps --no-build --pull never`. It preserves data, Pipe, Arena, TTS,
authentication, existing networks, fixed targets and all resources. Whisper gets
only `docker update --restart unless-stopped` on its exact existing ID; its
healthy process is not restarted/recreated. All three policies are also recorded
in Compose, so later reviewed recreations retain them.

Verify checks local HTTP 200, native unauthenticated rejection, actual states,
resources, persistent bind sources and one authenticated public synthetic STT
request. The retained known-public TTS fixture is resampled only in memory with
existing Python stdlib support to make a finite canonical WAV test fixture; no
converter is added to the product. No audio/transcript is printed or persisted.
One-attempt checkpoints prevent automatic repeated inference/recreation.

## Failure, retention and boot limits

On drift, bad metadata, authentication failure or failed acceptance, stop and
preserve private snapshots/checkpoints. Do not rotate credentials, replay a
failed inference, restore an old database, delete volumes, prune Docker or point
back at deleted temporary paths. A full old database restore is never a rollback
for this mount-only repair. The original images, data and backups stay intact.

`unless-stopped` is the existing Docker policy: running containers restart after
normal daemon/host restarts; deliberately stopped containers remain stopped. It
also handles eligible process failures; it is not proof that the earlier pinned
Whisper exit-139 issue is solved. No systemd unit for these containers is added.
An old `/tmp` path in Whisper's historical Compose label is provenance, not a
boot dependency: its actual mounts and daemon-persisted restart policy matter.
Persistent Compose now provides a surviving maintenance entry point.

No actual host reboot is performed. Configuration/consumer/live checks cannot
be described as a demonstrated reboot test. Startup is not readiness ordering;
early requests may fail closed until providers become healthy. Existing swap,
dumps, browser memory and A3 converter limitations are unchanged. Vision API
staging and all unrelated services are untouched.
