# Vision — single-store Lab deployment preflight and privilege blocker

Date: 2026-10-19 (Lab operator timezone).

**VISION_LAB_BLOCKED** — deployment authorization was granted, but the safe
execution path for the required Lab API service configuration is unavailable.
No running service, application source, permissions, Pipe record or canonical data
was changed. Vision was not enabled. No rollback was needed.

Continue the [offline implementation](2026-10-19-vision-single-store-offline.md),
local-only commit `da3d9c38f36be4921843f217d0b8cdbe520a4039`. Its isolated worktree
is clean. This attempt does not reopen architecture or R1–R7 development.

## Verified current baseline

| Component | Observed identity / state |
| --- | --- |
| Lab WebUI | Container `25afa4a67ba7591bac1250e86173a0ca822db4b8a1088c9477ec60418fdd61e5`; healthy; image `sha256:4b0451913d93774af57defe40873f29323239ef83ed7dfd8f405abe7b4f7ad17` |
| Private STT Bridge | Container `ae40a734c973aa643369637d9df486e6d1a63710545ee8c7c62d8033f1cbaa5e`; running; image `sha256:5d3cd6aff2db1a9712ce98669942d093858640298e9c04903f3cee3b510dc6b2` |
| Private dictation Whisper | Container `2ff3bcc648fde90aa61a3f5a63b8a64ec11188afcde6c127a5f7ece43602cf07`; healthy; image `sha256:caf0cd77c922e9c53f10a9bc17c2f74cc2295d12e7b0f96b630fb3b3c55a0026` |
| Lab API | Existing `corvus-lab-api.service` active; loopback 18096; unchanged Lab checkout `4f8013af2c8e73774fcef91c2510e5808c1fd2c2` |
| Lab gateway | Container `3c6e90bc728ce6f4904879f384b70abbf128e0a5547c7f964969133dae1c9355`; healthy; image `sha256:a8b39bd9cf0f83869a2162827a0caf6137ddf759d50a171451b335cecc87d236` |
| Installed Pipe | Active; exact existing Lab source SHA-256 `68967bd0ed499aaf2ecce38bc6afc80c3fc3cdeb805aab6a57182a2e907af861`; technical metadata only, no conversation access |

The current WebUI HTML exactly matches the retained Cluster-fix build. Actual
container file hashes for File/Chat models and routers match the Vision source
pins. Both proposed Corvus API/storage files have unchanged deployed predecessors
matching the implementation parent. STT consumer mounts and service identities
remain unchanged. Existing TTS, branding and Arena patches are inherited, rather
than rebuilding from the earlier wired image.

## Prepared artifacts, not a deployment

The complete current STT-enabled frontend source was copied into a new isolated
deployment directory. The committed Vision preparer verified its pins and emitted
the native frontend, backend and generated Pipe overlay there.

- Existing pinned Node/dependencies compiled the full frontend successfully in
  an isolated no-network build; no package, browser or model download.
- One derivative WebUI image was built from the **exact current 4b045… image**:
  `sha256:c734a452b36ea7c0404ad2431287da85aebab879530b598002c045d10c84bfcf`
  (`corvus-lab-webui:vision-da3d9c3`). It is retained locally, not running.
- Only the complete frontend and pinned Vision backend modules changed in that
  derivative. The generated Pipe remains a separate, uninstalled technical-data
  update required for coordinated rollout.
- BuildKit initially interpreted the raw local image ID as a repository and
  failed metadata resolution. The existing classic builder then used the exact
  local ID successfully. No image layers or dependencies were downloaded.
- Build containers were removed by the existing scoped build procedures; existing
  images, volumes and prior worktrees were not deleted or pruned.

Artifacts and logs remain under `/tmp/corvus-vision-lab-deploy`. Do not rebuild the
successful frontend or image merely to resume. Candidate runtime startup smoke,
coordinated installation and live acceptance were **not run** after the blocker.
The earlier offline tests remain evidence, not live deployment results.

## Single-store and recovery preflight

The gateway limit is 10 MiB; the candidate's raw image limit is 6 MiB. The image
body is raw PNG/JPEG, not Base64 JSON; binding IDs are in the route. Existing text
and reference JSON use a separate bounded gateway request.

Actual gateway configuration/mount metadata shows:

- Read-only root; request-body temporary path `/tmp/client_temp` and proxy
  temporary path `/tmp/proxy_temp` reside on the actual 16 MiB tmpfs mount.
- Proxy buffering and proxy caching are off; no request-body log variable or
  debug logging was found in the loaded configuration.
- Request buffering is **not explicitly disabled**. The observed temporary path
  is volatile filesystem storage, not a second persistent image store. No live
  upload/spill/cleanup test was performed in this blocked attempt.
- This tmpfs has no verified noswap option. The host has approximately 2 GiB swap,
  almost fully used at inspection. Swap exposure is unresolved; volatile tmpfs
  is not a nonswappable or complete privacy guarantee. Host settings were not
  modified. Available host memory at preflight was approximately 8.1 GiB.

The approved conservative initial policy is recorded: deletion immediately
revokes authenticated reference access; uncertain, orphaned, shared and still
referenced Corvus blobs are retained without automatic physical deletion. No
fixed erasure deadline or exactly-once canonical commit is claimed. Named gateway
RAM buffers and host/client memory risks must not be described as instant erasure.

The retained protected WebUI backup manifest/integrity verification passed, and
the original current image remains available. A fresh consistent current WebUI
and Corvus recovery checkpoint is still required before the eventual cutover;
no fresh backup, source replacement or service stop was attempted after this
privilege blocker. Existing backups remain untouched. Rollback must restore only
affected image/source/technical configuration, never overwrite canonical data or
delete a volume.

## Precise blocker and smallest resume step

The committed Corvus upload/status extension is disabled unless
`CORVUS_SINGLE_STORE_VISION=offline-reviewed-v1` reaches the Lab API process.
Its existing system service has no operator-writable environment-file hook.
The dedicated systemd drop-in directory is owned by UID 0, mode 0755, and is not
writable by the current execution user. `sudo -n` requires a password; inspection
of the existing sudo rules found no matching passwordless service/configuration
management rule. No credential values or passwords were requested, inspected or exposed.

A reviewable, **unapplied** Lab-only drop-in is staged at
`/tmp/corvus-vision-lab-deploy/70-vision-single-store.conf`:

```ini
[Service]
Environment=CORVUS_SINGLE_STORE_VISION=offline-reviewed-v1
```

Do not install it alone or enable only WebUI. An appropriately privileged local
operator must provide the scoped ability to install/remove this Lab-only service
environment and execute the necessary Lab API reload/restart/rollback operations.
This is an execution-privilege prerequisite, not missing user deployment consent.
No broad privilege change, shared-manager environment change, privileged-container
host-write workaround or weakening of the committed gate was attempted.

After that prerequisite is satisfied: reuse the retained artifacts, refresh drift
checks and protected consistent backups, prepare exact rollback, and coordinate
the two Corvus source files, Lab API environment, full WebUI overlay, generated
Pipe and narrow native image capabilities. Only then run the requested synthetic
live ownership/storage/quality/retry and STT/TTS/text/Arena preservation checks,
followed by the user's separate Mac acceptance.

## Preservation and acceptance state

No WebUI recreation, API restart, permission enablement, Pipe update, canonical
write, inference, private-image inspection or live synthetic upload occurred.
The original Lab WebUI and both private STT container IDs/images were rechecked
unchanged at stop. Existing STT/TTS/text/Arena stay on that working baseline;
this attempt does not claim fresh live functional acceptance for them.
Production, Demo, legacy A3, Qwen, Hindsight, Kokoro and gateway/authentication
services were not modified or restarted. No implementation code is pushed.
Mac Vision acceptance remains pending, not user accepted.
