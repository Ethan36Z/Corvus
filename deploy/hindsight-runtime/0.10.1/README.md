# Guarded Hindsight 0.10.1 runtime recipe

H1.7d-3c-r1 **passed live rollout and one durable BUSY/defer/grace/resume acceptance** after the first attempt safely rolled back. The exact cached derived image is now live with readonly registry admission and unchanged 30-second grace. See the [rollout record](../../../docs/project-logs/2026-10-10-h1-7d-3c-live-foreground-admission-rollout.md) for the full timeline, single operation identity and residual race limitation.

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

The current rollback snapshot is `/tmp/corvus-h17d-3c-r1/before.json`, mode 0600. It contains environment values and must not be committed. The reviewed retry helper is `/tmp/corvus-h17d-3c-r1/rollout.py`; it repeats baseline/source/data checks, calls this recipe and performs post-recreation acceptance with automatic rollback. It uses a **75-second** startup/outer admission acceptance horizon, a 70-second reader observation bound and one-second polling. Grace remains **30 seconds**; timeout is observation policy only. Deployment always requires explicit authorization and fresh preflight.

## Replacement and rollback

`runtime.deploy()` creates a **stopped** replacement and validates its full configuration while the original still serves. No replacement process opens the persistent volumes at this stage. It then stops only Hindsight with a 60-second grace, renames the original to `hindsight-lab-h17d3c-rollback-<original-id-prefix>`, renames/starts the replacement, and calls startup acceptance. It never deletes the original container or image and never removes a persistent volume.

On startup/acceptance failure, it stops/removes only the replacement **without volume removal**, restores the original name and starts the retained original. Health and original configuration/image/mounts are checked afterward. The first H1.7d-3c failure exercised this automatic rollback successfully. The authorized retry passed; the live `hindsight-lab` is now the derived patched container, with the stopped original retained for rollback.

The explicit rollback command for the successful retry is:

```sh
python3 -B deploy/hindsight-runtime/0.10.1/runtime.py --snapshot /tmp/corvus-h17d-3c-r1/before.json --image sha256:344abefa75512314309102e9d0391a0a346a6258d538bbbd881620cc5da69689 --rollback
```

Use this only for an authorized rollback; acceptance passed and it was not performed after the retry. It refuses to remove the original if the original is already live and verifies the current candidate before any removal. It restores the same persistent volumes; rollback never deletes acceptance data.

## Acceptance horizon and evidence

The first startup helper placed a 30-second subprocess timeout around a reader that itself requires strictly more than 30 seconds of recovery grace. That observation timeout caused automatic rollback. The retry changes only harness timing to 75 seconds; it does not shorten grace or relax UNKNOWN/fail-closed behavior. The reader returned UNKNOWN initially, then IDLE after 30.026 seconds. Its UID/GID 1000:1000 could read the registry; a non-truncating write-open failed with EROFS, confirming the bind is readonly.

The same cached image was reused without rebuild/download; version 0.10.1 and all eleven guarded patched/dependency hashes verified. The 55 existing focused patch tests correspond to those unchanged image bytes; four runtime-preservation tests passed again.

One safe acceptance seam used Lab's actual tracker/publisher in a separate test process and submitted exactly one synthetic durable async retain while BUSY, with its client UUID prerecord/fsync. It sent no Corvus chat and left canonical data/Production untouched. The worker deferred BUSY, deferred UNKNOWN during recovery grace, then resumed the same child and completed with retry count zero. The model's only slot dispatch began 59.149 seconds after foreground finished. Bank changed from eight to nine documents and stayed at nine memories (zero facts extracted); naturally queued consolidation completed with zero processed.

The one-shot observer initially omitted `include_payload=true`, then assumed HTTP access lines that this llama.cpp build does not emit. Read-only follow-up used the same operation UUID, the optional payload flag and actual slot-dispatch logs. No second POST, replacement work or manual retry occurred. The detailed record states the evidence limits rather than claiming an unobserved deferred payload hash.

Client UUID: `7d4326b3-fb95-4090-9434-2b228cf163e4`; child UUID: `46a7fb59-84de-4c45-b52f-d43fdcdb60bf`. Private request/status/log evidence is under `/tmp/corvus-h17d-3c-r1/`. Both real publishers remain healthy/idle; Lab, Production and model service identities are unchanged. Admission does not preempt a memory call already admitted; bounded consolidation remains the next objective, not part of this rollout.
