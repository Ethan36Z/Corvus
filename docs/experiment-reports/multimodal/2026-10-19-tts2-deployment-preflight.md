# TTS-2 — Controlled Lab deployment preflight

Date: **2026-10-19**

Verdict: **TTS2_BLOCKED**

Mode: read-only runtime preflight and conditional deployment plan. **Deployment is not authorized and was not performed.**

The prepared image, Git history, installed Pipe, HTTPS/authentication settings, volume and service health match the reviewed baseline. **Activation is blocked by a verified upstream privacy exposure:** the existing shared Kokoro service defaults to DEBUG logging, has reachable statements that print text excerpts, and uses Docker's persistent `json-file` log driver. WARNING/ERROR paths also include text. The WebUI adapter cannot remove content after Kokoro has logged it, and changing only `API_LOG_LEVEL=INFO` would not address those warning/error messages.

No operational logs, private conversations, cached audio or credential contents were read. No synthesis, chat, search or inference request was made. Only read-only metadata and health requests were used. The interrupted checkpoint was resumed; completed TTS implementation and test work were not repeated.

## A. References and verified source baseline

Reviewed in full with the completed conversation evidence:

- [Multimodal reuse decision](2026-10-18-multimodal-reuse-decision.md)
- [TTS-1 offline integration](2026-10-18-tts1-kokoro-offline-integration.md)
- [TTS-1.1 packaging baseline review](2026-10-19-tts1-packaging-baseline-review.md)

| Item | Current verified observation |
| --- | --- |
| Lab checkout | Clean `lab/ow2e-console`, `50a63850f83506724aaff4c2af4f50811d00d646` |
| Isolated integration | Clean `integration/tts1-kokoro-webui`, `4f8013af2c8e73774fcef91c2510e5808c1fd2c2` |
| TTS implementation | `3793b13d1f6855d5df7a3b139d47036b1879e4e0`, followed by the reviewed pin correction |
| Reporting baseline | Clean `reports/web-validation`, `3f416dc18892bac512521a3afadd67a1e771ba18` |
| Promotion scope | Exactly eight deployment/test/lock files; no Corvus API, Pipe, Arena or Hindsight behavior-file changes |

Ancestry and exact scope were rechecked. The active four Compose files are byte-identical to the corresponding integration files. TTS-1.1's corrected packaging metadata is local to the integration branch; no Lab source promotion occurred here. Its previously completed 41 affected and 22 TTS tests are historical evidence, not newly executed tests in this preflight.

## B. Current runtime and drift checks

| Boundary | Fresh observation |
| --- | --- |
| Active WebUI image | `corvus-open-webui:0.6.5-arena-ui2.1-https-r03b` |
| Exact active image | `sha256:453f9f2c4cee37c5e0d158ed3fcbdfc1e099bc6ef55ab47a7cbcce8b7331df76` |
| Prepared TTS image | `corvus-open-webui:0.6.5-arena-ui2.1-https-tts1` |
| Exact prepared image | `sha256:72252f095805fa8aebb6ed17e7fb44c3746e9d2a289ec3ff395769aad0c44e3b` |
| Version | Installed 0.6.5; no newer image or dependency |
| Active stack | WebUI → boot → Arena UI-2 → HTTPS; no TTS override |
| Container identity | Existing Lab WebUI, unchanged start time `2026-10-18T06:36:42.414146053Z`, healthy |
| Volume | External local volume `corvus-lab-open-webui-data` at `/app/backend/data`; sole container consumer is Lab WebUI |
| Network/security | Host network, application `127.0.0.1:3003`, `cap_drop=ALL`, no-new-privileges, restart unless-stopped |
| Lab API | Active/running on loopback 18096; same observed PID as TTS-1; Web MVP TRUE |
| Shared model / Hindsight configuration | Existing model endpoint 8095 and Lab async-retain setting preserved; no bank or memory access |
| Installed Pipe | Existing active, non-global `corvus_pipe`, owner present; source SHA256 `68967bd0ed499aaf2ecce38bc6afc80c3fc3cdeb805aab6a57182a2e907af861` |
| Pipe valves inspected | Lab endpoint 18096, `WEB_MODE=auto`, timeout 300 s, `ARENA_ENABLED=true`; private instance identity not disclosed |
| Native Web search | Environment false; selected persisted setting absent; persistent config false |
| Current TTS | Engine/model/voice environment unset; TTS user-permission default false |
| Other media | STT, call and file-upload defaults remain false |
| Authentication | WebUI auth/login enabled, signup/API keys disabled; existing HTTPS URL, both Secure-cookie flags true, both SameSite settings lax |

Selected persisted audio/permission settings were absent and no groups existed. No private user preferences or authentication secrets were read. Environment/configuration evidence is not an authenticated browser check of every user's effective settings; native admin overrides and volatile in-process configuration remain acceptance considerations.

Fresh non-mutating health requests returned HTTP 200 for Lab WebUI, Lab API, Kokoro, Production API/web and Demo API/web. API/model health was OK for Lab, Production and Demo. Relevant containers remained running; configured health checks were healthy. Relevant WebUI/API/Kokoro/model/FoxGate listeners remain loopback-only. Production/Demo use separate existing projects/services; no promotion or recreation command targets them.

The fixed active/prepared image identities match TTS-1, as do the active audio source hash and installed Pipe. No unexpected image, stack or configured runtime drift was observed. This is scoped evidence, not a claim that user data or every host process is byte-identical to an older snapshot.

## C. Adapter security review and upstream blocker

The reviewed implementation still retains native verified-user route dependencies, fixed loopback Kokoro destination, model `kokoro`, voice `af_mica`, language `z`, speed `0.95`, bounded JSON/text/audio and timeouts. It returns validated `audio/wav` with private/no-store headers. It forwards no credentials/user profile, writes no shared speech/text cache, logs no request text, and imports no canonical conversation/Hindsight/Arena writer. The exact compiled frontend patch removes the prepared-speech-text debug statement without replacing UI controls.

**New verified upstream finding, from source and non-secret configuration only:**

- Installed `api/src/main.py:26` selects `API_LOG_LEVEL`, defaulting to DEBUG. The variable is unset in container and observed API-process environments; the entrypoint does not override it.
- `services/text_processing/text_processor.py:65,76` and other split paths log text excerpts at DEBUG.
- `services/tts_service.py` includes chunk-text excerpts in the WARNING and ERROR branches of `generate_audio_stream()`.
- The non-streaming speech route calls `generate_audio()`, which internally uses `generate_audio_stream()` and text processing. `stream=false` therefore does not avoid these paths.
- The active container log driver is `json-file`, retaining stdout/stderr. No existing log contents were inspected and no past disclosure is claimed or measured.

These statements establish a reachable content-retention risk for future private Read Aloud requests, not an observed private transcript. Suppressing DEBUG alone does not sanitize the explicit WARNING/ERROR excerpts or raw exception messages. `no-store` HTTP headers and memory-only handling in WebUI do not control upstream logging.

**Required next fix before activation:** separately review and authorize narrowly scoped Kokoro logging hardening that removes text/phoneme excerpts and sanitizes error messages on the actual speech path, with offline success/error privacy tests. Any required change/restart of this shared service needs new explicit approval and Production/Demo regression planning. It is forbidden in TTS-2 and was not attempted. No new engine/model is justified. Do not enable the prepared override as a workaround or infer safety from a synthetic-only smoke test.

## D. Protected backup plan — not executed

Exact recovery boundary: original four-file Lab HTTPS stack, original `453f9f…` image and existing `corvus-lab-open-webui-data` volume. Retain the existing protected WebUI environment file unchanged; metadata-only inspection found directory mode 0700 and file mode 0600. No credential value was read or regenerated.

Volume metadata showed 39 regular files, 241,924,890 logical bytes, 15 file symlinks, and the expected `webui.db` and `vector_db/chroma.sqlite3`; no additional SQLite files were detected. The existing backup filesystem had 526,975,340,544 bytes free when checked. These are sizing observations, not a validated backup. Recheck immediately before backup.

After the blocker is resolved and backup/deployment is explicitly authorized:

1. Ask the operator to quiesce Lab browser activity; verify no in-flight Lab turn and no other volume writer. Record code/image/stack/volume identity and a protected metadata manifest. Use a fresh exclusive backup directory, 0700, files 0600, with umask 077; never overwrite an existing checkpoint.
2. Require free space greater than `max(3 × current logical volume size + 1 GiB, 2 GiB)` and account for verification copies. Do not reuse an old pre-W2 backup as the current checkpoint.
3. Briefly pause **Lab WebUI only** for a consistent opaque full-volume archive, including SQLite/WAL state and vector storage. Always unpause in `finally`, including failure. A helper must use the existing local image, no network, read-only source volume, dropped capabilities, no-new-privileges and `--log-driver none`; do not send archive bytes to persistent Docker logs. No app/model process should be started in the helper.
4. Stream the archive into an exclusively created protected host file. Validate full archive readability/checksum, reject escaping paths/devices/unsafe links, and verify SQLite integrity on restricted temporary copies with their required WAL state. Do not print/select private rows or media. Preserve original data untouched.
5. Confirm metadata stability, backup permissions/manifest, successful WebUI unpause and health, and protected availability of the original image/stack. **A verified new backup is a hard prerequisite to recreation.** If any check fails, stop without activation.

No backup or pause was performed in this preparation stage. Backup contents are private recovery material and must never enter Git/report artifacts. Routine rollback below does not restore the archive or overwrite databases.

## E. Conditional activation commands — DO NOT RUN NOW

These commands are a reviewed plan, not authorization. The upstream logging blocker must first be resolved, the fresh backup verified, runtime drift rechecked, and the operator must explicitly approve activation. Public examples use operator-supplied paths; do not print the existing environment file or merged secret values.

```bash
# Set these to the already verified local paths; do not generate credentials.
CORVUS_LAB_REPO=/path/to/existing/corvus-lab
CORVUS_LAB_ENV_FILE=/path/to/existing/protected/webui.env

# Only after clean-tree/ancestry gates and the protected backup have passed:
git -C "$CORVUS_LAB_REPO" merge --ff-only 4f8013af2c8e73774fcef91c2510e5808c1fd2c2

docker compose -p corvus-lab-open-webui \
  --env-file "$CORVUS_LAB_ENV_FILE" \
  -f "$CORVUS_LAB_REPO/deploy/lab/compose.webui.yml" \
  -f "$CORVUS_LAB_REPO/deploy/lab/compose.boot.yml" \
  -f "$CORVUS_LAB_REPO/deploy/lab/compose.arena-ui2.yml" \
  -f "$CORVUS_LAB_REPO/deploy/lab/compose.https.yml" \
  -f "$CORVUS_LAB_REPO/deploy/lab/compose.tts.yml" \
  up -d --no-deps --no-build --pull never --wait --wait-timeout 180 open-webui
```

Before the `up` command, verify the TTS tag still resolves to exact `72252f…`, the original image remains local and the effective configuration matches the reviewed merge. Do not pull, build, update the Pipe or change its valves. The integration promotes only the eight reviewed deployment/test/lock files; API behavior source is unchanged.

The fresh Compose comparison passed: final order is WebUI → boot → Arena UI-2 → HTTPS → TTS; only image/build and four TTS environment settings change. Authentication, existing secret reference, volume, HTTPS, host binding, project/security policy and other permissions are retained. The plan recreates only Lab WebUI. It does not restart Corvus API, Kokoro, Qwen, Hindsight, Production/Demo or FoxGate and makes no Cloudflare/network change.

Expect Lab UI/Socket interruption during recreation; no downtime duration is measured. Require health within the bounded wait and stop/rollback on failure rather than automatically repeating an uncertain operation. If the blocker fix introduces another reviewed code commit, update/review this exact promotion target before approval; do not silently include unrelated commits.

## F. Rollback plan — conditional, not executed

Use the same command above **without the final `compose.tts.yml` file**. Verify first that the four-file stack resolves to exact original `453f9f…` and still names the same external volume. Then recreate only `open-webui` with `--no-deps --no-build --pull never --wait --wait-timeout 180`.

Verify original image, volume, HTTPS/authentication, disabled TTS/default permissions, installed Pipe identity/auto mode, Web MVP/Arena settings and health. Keep new code files unused if needed; do not force-reset the checkout, restore whole databases, remove volumes, delete messages, regenerate credentials or restart another service. Escalate a data-integrity failure separately; the archive is a disaster-recovery checkpoint, not an automatic rollback action.

## G. Small acceptance plan — no requests executed

Only after new authorization and logging hardening:

1. Capture a quiescent metadata baseline for canonical turn counts/watermarks, shadow/Arena append state, protected audio-cache file inventory and monitored service identities. Do not select conversation/media contents. TTS must not submit a chat request or add a canonical turn.
2. Verify native unauthenticated rejection and authenticated single-voice response, fixed configuration, Secure authentication and private/no-store headers. Check effective logged-in TTS permission; leave STT/call/upload/search settings unchanged and avoid browser-Kokoro.
3. Propose at most **three short synthetic TTS calls** for Chinese speech, manual replay and stop/cancel behavior, using public text such as “这是 Corvus 的语音播放测试。” No Qwen/chat/search call is needed. Verify RIFF/WAVE, `audio/wav`, actual playback and refreshed frontend assets on Mac. Use an operator-approved non-private assistant fixture for the existing Read Aloud button; if none is available, defer that UI test rather than creating or reading a private conversation.
4. Exercise input/authorization errors without upstream work. Retain mocked timeout/upstream-failure tests; do not stop or misconfigure shared Kokoro or alter networking to force a live failure. Record any naturally occurring failure without automatic retry.
5. Verify no new persistent speech audio/text JSON and no synthetic sentinel in new logging output after hardening, without reading unrelated historical logs. Verify no canonical turn or Arena result was created by TTS. Treat unrelated concurrent activity or uncertain outcomes as unresolved, never delete/restore evidence to make counts match.
6. Ordinary chat and Arena compatibility initially use health, installed identity/configuration and existing offline contracts. A positive live chat/Arena trial would itself write data and requires separate authorization; do not claim it from read-only rendering or a TTS request.
7. Later authorize iPhone PWA playback/user-gesture/background tests. Browser Stop may stop playback without cancelling all upstream work; verify actual behavior. Audio quality, latency and CPU contention remain unmeasured.

## H. Final boundary

Current configuration and packaging checks passed; **upstream persistent content logging blocks safe private activation under the current scope**. Required logging work cannot be performed while the shared Kokoro service must remain unchanged.

No implementation branch, Lab or main is pushed. Only this sanitized report and its index entry are published on `reports/web-validation`. No deployed code, service, database, credential or persistent user setting was changed. Previous reports and their historical verdicts remain intact.

**Stop state: TTS2_BLOCKED; TTS_NOT_ENABLED; NO_BACKUP_CREATED; NO_DEPLOYMENT_PERFORMED.**
