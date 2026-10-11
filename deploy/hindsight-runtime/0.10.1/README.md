# Guarded Hindsight 0.10.1 runtime recipe

H1.7d-3c **stopped and rolled back during startup acceptance**. The derived image is validated, but foreground admission is not enabled in the live container. No real BUSY/defer/resume memory operation was submitted. Do not treat this recipe or its commit as successful live admission acceptance.

## Offline derived image

From the Lab repository, with access to the local Docker daemon:

```sh
python3 -B deploy/hindsight-runtime/0.10.1/build.py --output /tmp/hindsight-derived-image.json
python3 -B deploy/hindsight-runtime/0.10.1/test_runtime.py
```

`build.py` requires exact cached base image `sha256:b4d3b76f363aa40cf348450e7f8f52a50653008731b99824b14623a196182e73`. It verifies a local immutable-purpose base tag against that ID, uses the daemon-local legacy builder with `--pull=false` and `--network=none`, and installs no packages. A bare `sha256:` FROM expression was rejected by BuildKit as a registry image name; the verified local tag avoids that resolution.

The builder extracts only guarded files from a stopped, isolated scratch container (never runs its command or mounts persistent data), applies the existing version/hash-guarded patch with host Git, and puts six exact changed/new outputs into the build context. The cached image has no Git. `install_verified.py` therefore checks the installed distribution/version, all ten original source hashes and introduced-file absence **inside the build layer**, validates every replacement against its patched hash before writing any, and verifies all outputs after installation. A final stage inherits the exact original image and copies only the six patched modules plus readonly verification metadata. No unrelated upstream source is vendored or rebuilt.

The final image is verified without networking or service startup. Its actual sources are then copied out and tested with the existing 28 admission tests and 27 control-flow tests. Scratch containers are removed without persistent mounts or volume-deletion options. The local derived tag is `corvus-hindsight:0.10.1-h17d3b-47201c6`; output JSON records the actual image ID rather than assuming reproducible timestamps produce a particular ID.

## Exact inspected runtime

Capture `docker inspect hindsight-lab` and the base image inspect into a private 0600 JSON snapshot outside Git. Runtime `plan()` clones the captured Config, HostConfig and configured network endpoints. Only the following semantic differences are permitted:

- derived patched image;
- readonly bind `/run/corvus-foreground:/run/corvus-foreground:ro`;
- `CORVUS_FOREGROUND_REGISTRY_DIR=/run/corvus-foreground`;
- `CORVUS_FOREGROUND_EXPECTED_PUBLISHERS=lab,production`;
- `CORVUS_FOREGROUND_IDLE_GRACE_SECONDS=30`.

All existing environment/model routing, named/cache volumes, command/entrypoint, UID/GID, localhost ports, network configuration, restart/security/resource settings, labels and working directory are preserved. Docker-generated endpoint IDs/dynamic addresses necessarily belong to the new container. Docker also normalizes unset `OomKillDisable` to `false` on create: both permit normal kernel OOM killing. The validator allows only that equivalent default representation, rejecting every other host/security/resource difference. Tests cover that exception and reject changed model environment, writable registry, resource/security changes or wrong data volume.

The actual original snapshot is `/tmp/corvus-h17d-3c/before.json`, mode 0600. It contains environment values and must not be committed. The reviewed task-specific helper is `/tmp/corvus-h17d-3c/rollout.py`; it repeats baseline/source/data checks, calls this recipe and performs post-recreation acceptance with automatic rollback. Deployment requires explicit authorization and fresh preflight; the current task was halted per its stop rule.

## Replacement and rollback

`runtime.deploy()` creates a **stopped** replacement and validates its full configuration while the original still serves. No replacement process opens the persistent volumes at this stage. It then stops only Hindsight with a 60-second grace, renames the original to `hindsight-lab-h17d3c-rollback-<original-id-prefix>`, renames/starts the replacement, and calls startup acceptance. It never deletes the original container or image and never removes a persistent volume.

On startup/acceptance failure, it stops/removes only the replacement **without volume removal**, restores the original name and starts the retained original. Health and original configuration/image/mounts are checked afterward. The H1.7d-3c failure exercised this automatic rollback successfully. Live `hindsight-lab` is currently the original unpatched container again.

After a future successful authorized rollout, the explicit rollback command is:

```sh
python3 -B deploy/hindsight-runtime/0.10.1/runtime.py --snapshot /tmp/corvus-h17d-3c/before.json --image sha256:344abefa75512314309102e9d0391a0a346a6258d538bbbd881620cc5da69689 --rollback
```

This command is **not needed now**: rollback already completed. It refuses to remove the original if the original is already live and verifies the current candidate before any removal. It restores the same persistent volumes; rollback never deletes acceptance data.

## Halted acceptance and prerequisite for resumption

The patched container became healthy and all eleven patched/dependency hashes verified. Its bind was readonly according to Docker inspect. A new standalone reader must observe a recovery grace strictly longer than 30 seconds. The task helper inadvertently used a 30-second subprocess timeout around a reader test whose own bound was 35 seconds, so it timed out before it could report trustworthy IDLE or test readonly write rejection. Automatic rollback restored the original exactly.

The helper's subprocess timeout has been corrected **offline** to 45 seconds, with its reader bound still 35 seconds. The corrected helper has not been executed. Per task step 6, no further rollout or real memory acceptance was attempted. Before resumption, repeat all baseline checks and verify the corrected bounded acceptance harness; then obtain an explicit instruction to resume. Do not advance to bounded consolidation until real BUSY → DEFER → grace → same-operation COMPLETED acceptance passes.

A future purpose-built acceptance seam is prepared under `/tmp/corvus-h17d-3c/accept-once.py`: it uses Lab's real `ForegroundActivityTracker` in a separate test process/logical identity, leaving live Lab/Production publishers untouched, and submits one synthetic durable retain with a prerecord/fsync client UUID. It has **not run or been validated against the live runtime**. No new network API, framework or scheduling worker is introduced.
