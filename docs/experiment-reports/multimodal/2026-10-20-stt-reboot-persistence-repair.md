# STT — reboot persistence repair and local root handoff

Date: 2026-10-20.

**BLOCKED_PENDING_LOCAL_ROOT**. The mount/restart repair is committed locally and a private persistent runtime packet is prepared. WebUI is still unreachable and Bridge remains stopped; no restoration or successful live STT is claimed. The user-manually-restarted private Whisper is healthy and has not been restarted or changed by this work. No actual host reboot was performed.

## Confirmed narrow failure

| Component | Existing image / observed state |
| --- | --- |
| Lab WebUI | `sha256:4b0451913d93774af57defe40873f29323239ef83ed7dfd8f405abe7b4f7ad17`; exited 127; local 3003 unreachable; Docker `unless-stopped` |
| STT Bridge | `sha256:5d3cd6aff2db1a9712ce98669942d093858640298e9c04903f3cee3b510dc6b2`; stopped; Docker `no` |
| Private dictation Whisper | `sha256:caf0cd77c922e9c53f10a9bc17c2f74cc2295d12e7b0f96b630fb3b3c55a0026`; running/healthy; Docker `no` |

Both credential bind sources were under the deleted temporary credential-material directory. A previous resolved Compose maintenance packet and build contexts also referenced `/tmp`; they are unavailable after reboot. The actual WebUI protocol override and admission source are already persistent protected recovery files, not deleted temporary files. Whisper's model mount is persistent. Historical Compose labels are provenance, not files read by Docker to restart an existing container.

The existing boot mechanism is the already-enabled Docker service plus container restart policies. The reviewed Lab boot overlay already uses `unless-stopped` for WebUI; no separate container systemd supervisor is needed. Bridge/Whisper lack a corresponding boot policy. Existing API systemd configuration, including preserved Vision staging, is untouched.

## Credential recovery boundary

The original independent service credential survives in the protected prior activation recovery directory: file UID/GID 10001/10001, mode 0400; parent mode 0700. Its contents, digest and format were not read by the unprivileged preparation. The credential-repair report identifies this as the original source; no rotation was attempted. Existing sudo rules provide no applicable passwordless privilege to copy it safely across consumer ownership.

The minimal human-executed root helper reuses the existing credential-repair distribution function. It checks the original's fixed path/metadata/format, makes owner-specific 0400 copies, privately verifies equality, validates the exact public WebUI UID-0 owner-check specialization, and copies the unchanged admission state. No credential value or credential digest is printed or committed. Existing outputs are verified rather than overwritten; partial or unexpected state fails closed. Missing/unrecoverable original material requires a separate operator decision, never silent rotation.

Target files outside Git: `/etc/corvus-lab/stt`, root parent 0700; WebUI consumer directory 0/0 0700 with credential 0/0 0400; Bridge directory 10001/10001 0700 with credential 10001/10001 0400. Public protocol remains 0444, owner 0; admission remains 0444, owner 1000. Each consumer receives only its assigned read-only bind, with source auto-creation disabled; process UIDs/capabilities are not relaxed.

Review and execute locally as the normal operator:

```sh
less /home/ethan/srv/apps/corvus-stt-reboot-repair/deploy/lab/stt/boot/persist_material.py
sudo /usr/bin/python3 -I /home/ethan/srv/apps/corvus-stt-reboot-repair/deploy/lab/stt/boot/persist_material.py
```

Use only sudo's local interactive password prompt; no password is requested through chat, captured or stored. This command changes no service. Expected output: `PERSISTENT_STT_MATERIAL_READY` (or complete-material already-verified equivalent). Its root operations have **not** been executed by the assistant. Do not assume sudo authentication in another terminal authorizes agent calls.

## Prepared local implementation and focused validation

Local-only commit **`3b93d3ae0b60fad4c96bb9afae8243a84ee81d4d`**, branch `fix/stt-reboot-persistent-mounts`, persistent isolated worktree `/home/ethan/srv/apps/corvus-stt-reboot-repair`, based on existing credential repair `6a2a5eb1bab2c4c107dc34b60e2919071795bec1`. Earlier worktree records/backups are not pruned or overwritten. No implementation branch is pushed and main is unchanged.

Four new files under `deploy/lab/stt/boot`: `compose.yml` (persistent binds and existing Docker policy), `persist_material.py` (local root copy using the existing primitive), `recover.py` (retained scoped runtime snapshot/recreation/one-request verification), and `README.md` (operator/recovery instructions). No STT transport, frontend, engine, model or credential framework is replaced.

Preparation saved current metadata plus a resolved Compose packet in protected persistent operator configuration, directory 0700/files 0600, outside Git. It pins the actual three images and environments, retains data/security/resources/networking, removes unused old build contexts, and replaces only STT binds/restart policies. Docker Compose parsing and environment round-trip validation passed. Existing private settings are not included in this report.

Focused checks passed: Python syntax, surviving public protocol bytes against the existing pinned one-line specialization, unchanged admission value, and both existing credential-repair unit contracts. Resource values represented equivalently by preserved Compose were normalized only for comparison; no budgets were changed. Actual consumer reads/authentication and live acceptance remain pending the root copy. No new test framework, image build, dependency/model download, inference or restart was performed.

## Exact continuation and limits

After operator confirmation, independently validate the persistent files using the exact existing consumer images, effective UID 0/10001, dropped capabilities, read-only roots, no network/model/data mounts. Then target only Bridge and WebUI through the persistent Compose packet with `--no-deps --no-build --pull never`. Preserve the existing WebUI data volume, authentication, Pipe, Arena, branding and TTS. Update only the existing healthy Whisper container's Docker restart policy to `unless-stopped`, without restarting its process, and verify its ID/start time/resources remain unchanged. All three policies are retained in Compose.

Finally verify local health HTTP 200, Bridge/authentication, Whisper health, persistent actual mounts, and exactly one authenticated known-public synthetic STT request. Reuse the protected public TTS acceptance fixture, with only in-memory stdlib resampling to a finite canonical WAV test fixture; no production converter is added. No transcript/audio logging or canonical chat dispatch is required. One-attempt checkpoints prevent automatic repeated inference or recreation.

Do not reboot for this repair. Configuration and live checks would establish persistent prerequisites, not prove an actual reboot test. `unless-stopped` is the existing Docker mechanism and also governs eligible process failures; it does not solve the previously observed exit-139 issue. Provider readiness may lag container startup; early requests must fail closed.

On drift/failure, retain the checkpoint; do not restore an old database, delete volumes, prune Docker, rotate credentials, point back at missing temporary mounts or restart unrelated services. Production, Demo, Qwen, Hindsight, Kokoro, legacy A3, current canonical data and Vision admission remain untouched. Existing host swap/dump and privacy limitations are unchanged.
