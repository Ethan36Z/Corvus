# Vision single-store — Lab activated for Mac acceptance

Date: 2026-10-20.

**VISION_LAB_READY_FOR_MAC_ACCEPTANCE**. The existing candidate is deployed. Exactly one public synthetic PNG upload and one native WebUI → existing Pipe → A3 → Qwen Vision dispatch returned HTTP 200. Authenticated image display and saved-history reload passed. No real Mac browser acceptance is claimed.

Continue the [earlier Vision rollback](2026-10-19-vision-single-store-lab-resume.md) from the [recovered persistent STT baseline](2026-10-20-stt-reboot-persistence-restored.md). Reuse implementation `da3d9c38f36be4921843f217d0b8cdbe520a4039` and existing image `sha256:c734a452b36ea7c0404ad2431287da85aebab879530b598002c045d10c84bfcf`. No image rebuild, pull, dependency/model download, new architecture or new implementation commit.

## Protected baseline and minimal changes

Fresh current WebUI configuration, Pipe/model technical settings and a consistent WebUI volume archive were saved in a new protected persistent recovery directory, 0700/files 0600. The existing read-only backup helper briefly paused and always unpaused only WebUI. Archive contents/completeness and both SQLite copies passed integrity checks; no conversation rows were queried for backup verification. Existing archives/data were not overwritten or restored. API and all other services were not paused or restarted.

Candidate and rollback packets were derived from today's surviving STT Compose configuration, not old `/tmp` packets. The three read-only WebUI STT binds remain under `/etc/corvus-lab/stt`, data volume remains `corvus-lab-open-webui-data`, and all three STT-related restart policies remain `unless-stopped`. Existing credentials, UID, capabilities, resources, host routing and authentication were preserved. The API's already staged source/flag matched the existing implementation and needed no modification/restart.

Only these runtime changes remain:

- Lab WebUI image changed from `sha256:4b0451913d93774af57defe40873f29323239ef83ed7dfd8f405abe7b4f7ad17` to the retained Vision candidate. Environment adds `CORVUS_SINGLE_STORE_VISION=offline-reviewed-v1` and enables the reviewed native image-upload permission.
- Installed `corvus_pipe.content` uses the existing generated Vision extension, source SHA-256 `c29da4554be7d30e68e17efb26ce2faf3d0f01c54e1df161f6d677351df648de`; owner, valves, active state, fixed Lab target, TTS/text/Arena safeguards are retained.
- Only the existing Corvus model's `meta.capabilities.vision` and `file_upload` were enabled after compatibility checks. Native model/config HTTP responses expose the enabled capabilities. General document/RAG multipart upload remains rejected before parsing.

Only WebUI was recreated using service-scoped `--no-deps --no-build --pull never`; no Bridge, Whisper, API, Qwen, Hindsight, Kokoro, gateway/auth, Production, Demo or A3 service restart/recreation. Existing source/worktree records and canonical user data remain intact.

## Actual final runtime

| Component | Container ID | Image | State/policy |
| --- | --- | --- | --- |
| Lab WebUI | `b303ebfcccda1939e078e698e279583afd74302c12aaf3ff62d8e4902230b8d5` | `sha256:c734a452b36ea7c0404ad2431287da85aebab879530b598002c045d10c84bfcf` | healthy; unless-stopped |
| STT Bridge | `7eb33a6ca8f0e5e6f22fe0244f3e4f0d63c73fc02a1cad474306ba1897e4480c` | `sha256:5d3cd6aff2db1a9712ce98669942d093858640298e9c04903f3cee3b510dc6b2` | running; unless-stopped |
| Private dictation Whisper | `2ff3bcc648fde90aa61a3f5a63b8a64ec11188afcde6c127a5f7ece43602cf07` | `sha256:caf0cd77c922e9c53f10a9bc17c2f74cc2295d12e7b0f96b630fb3b3c55a0026` | healthy; unless-stopped |

## Focused evidence and one-image result

Compatibility passed: WebUI health/authentication, installed module matching the existing source pin, mounted Vision JS asset delivery, existing Pipe/model/Arena settings, TTS voice-provider metadata, unchanged STT credential/admission and authenticated invalid-WAV bridge rejection. No additional STT/TTS inference or broad R1–R7 suite was run; the current user-accepted STT/TTS baseline was preserved.

One in-memory public synthetic PNG (two colored shapes, 512×256) was uploaded once through the native authenticated image adapter. WebUI saved only its bound reference: File path NULL/data empty, exact user/chat/message binding, no Base64/raw image serialization in this synthetic chat, and unchanged persistent WebUI upload/audio/image-cache inventories. Existing A3 storage holds the image bytes. No additional uploader, store, converter or model was introduced.

One native `/api/chat/completions` request through the installed Pipe returned **HTTP 200 in 2.721 seconds**. Its reply correctly identified the red square and blue circle. Confirmed canonical user/assistant IDs were retained by the existing binding state, state COMMITTED, and the new canonical user message has exactly one provenance link to that attachment. No reply/image content is published here.

Checks passed: native image+Arena rejection before write (400); unauthenticated native upload/content rejection (403); owner Bearer and cookie content reads (200, exact bytes, `private, no-store`); same owned chat/reference after native history reload; cookie-authenticated image reads after reload; nonowner identity rejected by the actual bound authorization function (404); duplicate dispatch claim rejected before another canonical call. The nonowner check reused the existing test's direct authorization-function pattern, without creating a new account; a second real-user HTTP login test was not performed. Existing image-turn Hindsight exclusion remains in the unchanged A3 path, with a non-null attachment; Hindsight service/data were not inspected or modified.

The final Lab page/health return 200. Public HTTPS without FoxGate authentication returns 401 as expected. Native model capability and upload/STT permission delivery were checked. This demonstrates backend/native contracts, not Mac visual/microphone interaction. Existing offline native composer, transient draft and display evidence is reused; actual Mac preview/remove/click/reopen remains the user's acceptance.

## Verifier corrections, scoped recovery and retention

Two deployment-verifier assumptions triggered conservative scoped WebUI/Pipe rollbacks before any canonical image dispatch: the actual native unauthenticated status is 403 rather than the mocked-test 401, and module startup diagnostics preceded a successful nonowner-rejection marker. Both were verification defects, not an authentication bypass or product compatibility failure. Only verifier handling was corrected; no product code/security gate changed. The same saved synthetic turn and confirmed READY attachment were resumed. Total: **one upload, one canonical dispatch**, no reupload, duplicate model request or data restore. Only WebUI was recreated during those rollbacks; all unrelated service start times remained unchanged.

The rollback baseline is today's working persistent configuration, original WebUI image/Pipe/model capabilities, never the obsolete temporary credential packet. The retained scoped rollback entry point is:

```sh
python3 -B /home/ethan/.config/corvus-lab/vision-runtime/operate.py rollback
```

It restores only current-baseline WebUI/Pipe/capabilities and persistent STT settings, preserving the data volume and new canonical/test records. It does not restore an old database or stop API/STT services. Protected configuration and runtime journals stay outside Git. Current active candidate/rollback packets are on persistent storage; earlier rollback-result files are historical checkpoints, not current status.

Conservative retention is unchanged: deletion revokes access; uncertain/orphaned/canonically referenced blobs are retained pending safe cleanup. No physical-erasure claim or automatic purge. Existing 6 MiB PNG/JPEG bound, 10 MiB gateway bound, authenticated fixed same-origin routing, tmpfs gateway buffering and disabled proxy cache remain unchanged. Host/client swap, dumps and browser memory limitations are not solved by this delivery. No actual reboot was performed.

**Stop engineering work and leave Vision running.** Mac acceptance: sign in through FoxGate then WebUI at `https://lab-corvus.foxluma.com`, refresh, select Corvus, add one PNG/JPEG up to 6 MiB with the native `+`, include text and send manually with Arena off. Check preview/removal, image-grounded reply, thumbnail/click view, and reopened-chat image display. Only the user's actual confirmation can establish `VISION_LAB_USER_ACCEPTED`.
