# Vision single-store — coordinated Lab rollout and scoped rollback

Date: 2026-10-19 (Lab operator timezone).

**VISION_LAB_ROLLED_BACK**. Vision is paused by the user and was never enabled for image turns. The original working WebUI image, Pipe and image capability/upload settings are restored. A private dictation Whisper process exited during compatibility acceptance; after separate explicit authorization, exactly one start of its original container and one public English recognition check succeeded. STT is healthy again. No further Vision deployment or inference attempt is authorized by this checkpoint.

Continue the [operator handoff](2026-10-19-vision-single-store-operator-handoff.md) and [preserved deployment](2026-10-19-vision-single-store-lab-deployment.md). Reuse implementation `da3d9c38f36be4921843f217d0b8cdbe520a4039` and the retained built image; no rebuild, downloads, implementation push or new architecture.

## Verified staging and actual changes

Independently verified the operator completion markers, expected API source hashes, active Lab API health and effective `CORVUS_SINGLE_STORE_VISION=offline-reviewed-v1`, both protected backup manifests, original WebUI/STT identities and configurations, and exact candidate image. Backups were not repeated and the API was not restarted by the assistant.

Saved the exact current Pipe/model technical fields and current container identities privately for rollback. Installed only the generated Pipe content, preserving its owner, valves and active state. Recreated only Lab WebUI with the retained candidate, original persistent data volume, three read-only STT consumer/protocol mounts, authentication environment, UID, capabilities, security and host routing. Only the reviewed candidate image, Vision flag and narrow upload permission differed. Model Vision/file-upload capabilities remained closed throughout. No image upload, saved synthetic chat or canonical dispatch was reached.

| Runtime checkpoint | Container | Image |
| --- | --- | --- |
| Candidate WebUI, temporarily staged | `009e79f01b169e195859e0787bd41c1189eb82611a355a91ee992adade202289` | `sha256:c734a452b36ea7c0404ad2431287da85aebab879530b598002c045d10c84bfcf` |
| Final restored WebUI, healthy | `84d74e8f7f41e12e1f30ae34f99799b0608597e96082a02d9a652f7a1fa775e9` | `sha256:4b0451913d93774af57defe40873f29323239ef83ed7dfd8f405abe7b4f7ad17` |
| Existing private STT Bridge, unchanged/running | `ae40a734c973aa643369637d9df486e6d1a63710545ee8c7c62d8033f1cbaa5e` | `sha256:5d3cd6aff2db1a9712ce98669942d093858640298e9c04903f3cee3b510dc6b2` |
| Original private dictation Whisper, now healthy | `2ff3bcc648fde90aa61a3f5a63b8a64ec11188afcde6c127a5f7ece43602cf07` | `sha256:caf0cd77c922e9c53f10a9bc17c2f74cc2295d12e7b0f96b630fb3b3c55a0026` |

## Compatibility gate and rollback

The staged WebUI passed health, native authenticated audio/config access, required STT permission, expected voice-provider metadata, and synthetic TTS output validation (mono PCM WAV, 24 kHz). The public Chinese STT fixture returned 200 with the expected public-sample semantic check. The next public English STT request returned **502**. Its initial request latency was not retained; none is invented.

This was treated as a hard functional failure. Image model capability was not enabled. The reviewed scoped rollback restored only the original WebUI image/environment and original Pipe/model technical settings; no volume or canonical data restore/deletion occurred. Pipe source/settings and model metadata were reverified. Native function loading subsequently refreshed its technical `updated_at` timestamp; code, ownership, valves and activation were unchanged.

The Lab API remains at the operator's verified backward-compatible staged checkpoint, healthy, with its flag and two source files intact. It was not restarted or reverted by the assistant. Restored WebUI has no Vision flag, image upload permission is false and the model image capabilities are false. If complete API staging removal is later required, reuse the preserved local operator API rollback procedure; do not install/remove only a drop-in or overwrite canonical data.

After rollback, authenticated health/config, existing Pipe model availability and another public synthetic TTS WAV passed. STT permission remained enabled. The bridge accepted its existing service credential and rejected invalid WAV with 400 without invoking Whisper. Text completion and live Arena inference were **not reached**, so no new functional PASS is claimed for them; original Pipe/Arena settings and baseline WebUI were restored. Exact frontend/gateway Vision asset delivery and all image acceptance were also not reached.

## Private Whisper failure and one authorized recovery

Metadata showed the unchanged private Whisper container exited at `2026-10-20T05:09:04.207577812Z` with **exit code 139**, without an OOM-killed flag or automatic restart. Its image, configuration, mounts, no-convert arguments, resources and networking had not changed. Exit 139 is consistent with a segmentation fault, but no stack trace or exact crash mechanism was established. It is not evidence that a Vision frontend change caused the crash. Content logging is disabled and no private recordings, transcript contents or crash dumps were inspected.

The user explicitly authorized only restoring that original dictation container, keeping all settings, and one minimum recognition check; Vision remained paused. Exactly **one** start and **one** public English inference were performed. The same previously failing 3.302-second public PCM WAV fixture returned **HTTP 200 in 4.161 seconds**, with nonempty text passing the existing English public-phrase check and `private, no-store`. No transcript was logged or retained in the report. Startup reached healthy in 5.121 seconds, and the process remained running/healthy after completion. No repeated starts, retry loop or second Vision attempt occurred.

The original image, UID, read-only configuration, network membership and limits remain unchanged: Whisper 8 CPU / 1088 MiB, equal memory-plus-swap limit; bridge 1 CPU / 256 MiB. After recovery Whisper memory was 992825344 bytes and cgroup swap usage was zero. This is a post-check snapshot, not an inference peak measurement. At failure investigation, host available memory was approximately 10 GiB and host swap was nearly full; these observations do not establish the crash cause. No host swap/dump/security setting changed.

## Preservation, pending work and next step

Production, Demo, legacy A3, Qwen, Hindsight, Kokoro, gateway/auth services, Bridge and unrelated containers retained their identities/start times/configurations. Only WebUI was recreated for the attempted rollout/rollback; only the exact original private Whisper was subsequently started under the additional recovery authorization. API staging was reused without another restart. Existing data, models, credentials, images, prior worktrees and protected backups remain intact. No prune, broad Compose operation or implementation branch push.

No Vision image bytes were uploaded and no canonical chat/inference dispatch was made during this attempt. Consequently reference-only image serialization, authenticated thumbnails/reopen, cross-user image access, upload replay/failure behavior, live A3 image grounding and Hindsight image-turn exclusion remain **NOT RUN live**. Earlier offline evidence remains valid but is not presented as online acceptance. Mac Vision acceptance is pending/unavailable while Vision is paused; no user acceptance is claimed.

The original single-store contract and conservative retention policy remain unchanged: immediate logical revocation, retain uncertain/orphaned/canonically referenced blobs, no automatic physical deletion and no claim of erasure. Existing host/client swap, dumps, browser-memory and volatile gateway-buffering limitations remain unresolved.

**Stop here.** Preserve the crash checkpoint and successful one-shot recovery evidence under the existing deployment directory. Before any future Vision attempt, obtain user direction to resume and perform a narrow fresh drift check against the restored WebUI and explicitly restarted Whisper checkpoint. The observed provider crash remains unexplained; do not silently remove the STT compatibility gate or repeatedly restart/redeploy to force a pass. Implementation stays local at the same commit; no new application-code commit was created.
