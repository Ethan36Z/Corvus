# Vision single-store — local operator privilege handoff

Date: 2026-10-19.

**AWAITING_LOCAL_OPERATOR**. Resume the [preserved deployment attempt](2026-10-19-vision-single-store-lab-deployment.md), not a new implementation. No running service, deployed source, systemd configuration, Pipe setting, upload permission or canonical data was changed in this checkpoint. Vision remains disabled; working Lab STT remains running.

## Retained candidate and completed checks

Reuse local implementation `da3d9c38f36be4921843f217d0b8cdbe520a4039` and the already built image `sha256:c734a452b36ea7c0404ad2431287da85aebab879530b598002c045d10c84bfcf`. No rebuild, dependency/model download or implementation push.

The candidate's actual image successfully imported native File/Chat/Vision routers in an isolated, network-disabled container with synthetic temporary SQLite databases, read-only root, dropped capabilities, no persistent mounts and disabled Docker logging. Both image routes retain native verified-user dependencies; the fixed Lab API target and 6 MiB limit were checked. The owned smoke container was removed after exact identity checks. This is import/contract evidence, not live Vision acceptance.

Read-only handoff preflight passed against the original healthy WebUI container/image and unchanged running private STT services recorded in the prior report. The exact installed Pipe remains active and unchanged; the `corvus_pipe` model image capabilities remain disabled. The local feature worktree is clean and pinned. Unit configuration and deployed source hashes are pinned for another check immediately before mutation.

## Reviewable local handoff

Existing deployment directory: `/tmp/corvus-vision-lab-deploy`.

The protected `handoff` subdirectory contains `operator.sh`, `coordinate.py`, local checksum manifest, instructions, and private candidate/rollback Compose packets. Directory mode is 0700; files are 0600. Private packets contain existing runtime settings and must not be printed, committed or shared. Compose interpolation was round-trip checked; the original environment is retained, with only candidate image, Vision gate and narrow upload permission differing in the candidate packet. Existing consumer mounts, host routing, security configuration and UID are preserved. The packets are prepared for the subsequent coordinated WebUI step, not executed at this checkpoint.

Operator runs as the normal Lab owner in a real local terminal:

```sh
cd /tmp/corvus-vision-lab-deploy/handoff
less operator.sh coordinate.py
sha256sum --check --status SHA256SUMS
bash ./operator.sh apply
```

Do not sudo the wrapper or coordinator. Only the fixed root commands inside the wrapper use interactive sudo on the operator's terminal. No password is requested through chat, read by the coordinator, stored, or logged. No passwordless rule is installed, and authentication in another terminal is not assumed.

The bounded sequence is:

1. Recheck pinned artifacts, clean feature worktree, deployed source/unit/container/config identity, health, installed Pipe and disabled image capabilities. Refuse drift or repeated apply.
2. Stop only `corvus-lab-api.service` through local interactive sudo.
3. Before any code/drop-in change, reuse the protected consistent WebUI volume backup procedure, briefly pausing and always unpausing only Lab WebUI. Back up stopped Lab API storage and original source as opaque protected archives; verify archive completeness and SQLite integrity on private copies without querying conversation rows. Exclude existing read-only model/cache directories from API storage backup. Verify disk headroom; fail closed on unexpected archive entries. Existing backups remain intact.
4. Stage only `app/playground_api.py` and `memory/attachments.py` from the pinned implementation. Install the one fixed environment drop-in only after backup/source staging succeeds. Root code refuses symlink/unsafe-parent paths and existing drop-in collisions. Preserve service user and sandbox configuration.
5. Reload systemd, start only Lab API, and check API health, expected source and effective flag plus unchanged WebUI/STT identities.
6. Stop at `BACKEND_STAGED_VISION_UI_CLOSED` and notify the assistant. The original WebUI image, Pipe, model capabilities and upload permission are untouched. This backward-compatible private API staging checkpoint does not expose a partial user-facing Vision integration.

Shell, coordinator and fixed privileged Python syntax checks passed; read-only preflight passed. Privileged apply/rollback, fresh backups and service restart have **not** been executed. The existing protected backup is retained; fresh current-state backups are mandatory within apply before source/drop-in mutation. Do not install the drop-in separately.

## Recovery and coordinated continuation

On a staging failure the wrapper attempts API-only rollback. Unknown source, unit ownership or unexpected state causes a stop rather than an overwrite. API rollback restores only the two original source files and removes only the exact owned drop-in, then reloads/starts the same Lab service and verifies health. It never restores or deletes canonical data, WebUI volumes, images, networks or unrelated services.

After reconciling an interrupted operation, the exact local API rollback entry point is:

```sh
cd /tmp/corvus-vision-lab-deploy/handoff
bash ./operator.sh rollback
```

Rollback refuses a Vision-enabled or non-original WebUI image. After any later WebUI cutover the assistant must first close Vision and restore original WebUI/Pipe/capability settings using the prepared scoped recovery configuration; the operator API rollback is not a substitute for coordinated WebUI rollback. Existing STT rollback runners must not be used because they affect working STT.

After the operator confirms successful staging, inspect the completion marker and actual runtime; then resume the preserved scoped WebUI/Pipe rollout using the retained image and private configuration. Keep image admission closed until backend/frontend compatibility and existing STT/TTS/text/Pipe/Arena gates pass. Then perform the previously authorized synthetic single-store ownership, retry/failure, inference, reload, no-second-copy and Hindsight-exclusion acceptance. Mac user acceptance remains pending.

Production, Demo, A3, Qwen, Hindsight, Kokoro, gateway/authentication services and private STT require no change. Conservative retention remains immediate logical access revocation with uncertain blobs retained; physical erasure is not claimed. Existing host swap/dump and volatile gateway buffering limitations remain unchanged.
