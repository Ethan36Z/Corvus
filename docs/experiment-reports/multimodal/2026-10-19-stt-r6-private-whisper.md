# STT-R6 — Independent private no-convert Whisper candidate

Date: 2026-10-19

Verdict: **STT_R6_READY_FOR_ACTIVATION_REVIEW**

**Offline candidate only. No deployment, existing-service restart or live-gate
enablement occurred. Both R2 exported STT entry points remain disabled.**

## Selected architecture and revised delivery scope

The user selected option B after the [R5 decision](2026-10-19-stt-r5-privacy-unblock.md).
No alternatives were revisited or built. Reuse the exact pinned Whisper image,
existing ggml-small.bin and /inference in a separate private instance. Original
A3 Whisper, compressed-audio conversion, settings, ports and provenance remain
unchanged. The [R4 browser normalization](2026-10-19-stt-r4-browser-wav.md) already
supplies canonical WAV; no C++ patch, rebuild or new converter is introduced.

The user explicitly revised delivery to application-level private dictation:
no conversion temporary audio, no persistent dictation cache/content logging,
authenticated private bridge, fixed local-only target/no fallback, bounded
requests/responses, timeout/admission policy, constrained storage and scoped
failure/rollback. System/client swap, core/crash dumps, hibernation, browser-memory
persistence and legacy A3 issues are recorded residual risks. This is an explicit
scope revision, not a claim that the broader R5 properties are solved.

## Implementation and preservation

Baseline: local R4 `83ca1d38836a45088fa6574ed177b1064a0cd87d`.
New isolated branch: `integration/stt-r6-private-whisper`.
Local-only implementation commit: `c0b818fa2c72a4eeb6f8691f5e25f06eea8b87e1`.

Seven implementation/test/documentation files:

- `app/stt_bridge.py`
- `deploy/lab/stt/private/compose.yml`
- `deploy/lab/stt/private/README.md`
- `deploy/lab/stt/private/measure.py`
- `deploy/lab/stt/private/resource-evidence.json`
- `tests/test_private_whisper.py`
- `tests/check_private_whisper_config.py`

The code branch is not pushed. Eight earlier STT worktrees retain HEAD/status and
all privacy/storage draft hashes, including the three uncommitted O_TMPFILE files.
Active Lab stays clean. A3 transport/runtime, R4 frontend and native WebUI handler,
TTS/Pipe/Arena/Hindsight implementation and Production/Demo remain untouched.
No dependency, browser, model or image downloads, Docker prune or host setting
changes occurred.

## One new service candidate

The manifest defines only `corvus-whisper-dictation`, in a review-only profile.
Pinned image:
`sha256:caf0cd77c922e9c53f10a9bc17c2f74cc2295d12e7b0f96b630fb3b3c55a0026`.
The existing model file is its sole read-only bind; the configured path is required
and Docker must not create missing host paths. Future preflight verifies the
regular file/read permissions/identity. No model-directory or deployed-data mount,
writable persistent audio path, converter tmpfs or image build is required.

Fixed command: existing server, /inference on container port 8080, multilingual
small model, eight threads, automatic language, CPU-only and **no --convert**.
The pinned byte-buffer reader avoids conversion-file creation. The independent
instance does not add a private startup prompt; existing R1 multipart prompt and
language behavior is preserved. No request can control command/upstream settings.

UID/GID 10001, read-only root, no capabilities, no-new-privileges, 64 PID limit,
core=0, Docker logging none and stdout/stderr redirected to /dev/null constrain
execution and suppress upstream content diagnostics. core=0 is defense in depth;
it does not establish host piped-coredump suppression. Synthetic inference under
the same storage/user/logging constraints succeeded.

No host port, host networking or HTTPS route is published. The sole proposed
network is internal `corvus-stt-dictation-private`. Only the engine and standalone
authenticated bridge may join; WebUI reaches the bridge, never unauthenticated
Whisper directly. This is static Compose validation, not deployed DNS/membership
acceptance. Measurement used network=none with requests inside its own loopback.
No candidate network or production topology was created.

## Bridge reuse, bounds and lifetime policy

Only the dictation bridge target changes to fixed
`http://corvus-whisper-dictation:8080/inference`. R1 remains its sole multipart
transport. Legacy and external targets fail closed, without retries or fallback.
A3's default URL, artifact creation and original-audio evidence are unchanged.
Native WebUI verified-user authentication and the independent exact service
credential boundary remain. No real secret was generated, read or provisioned.

After authentication, one request owns the bridge slot before reading audio.
Busy requests return 429 without consuming their body; no queue is added. Exactly
one bridge process/worker is required. Body limit/deadline remain 8 MiB/5 seconds;
canonical PCM16 WAV at 16 kHz, maximum 120 seconds; response at most 64 KiB and
16 Ki characters. Existing native multipart/auth/no-store/error contracts remain.
No disk spooling, attachment, artifact, SQLite, canonical chat or memory calls are
added. Bounded native ingress/no persistent proxy buffering remains an activation
configuration check.

Worker deadline: **25 seconds**, inside the existing native hop's 30-second budget
for a normal bounded upload. Upload plus inference may instead hit that outer
deadline first; this also fails closed. R1 socket timeout is 25 seconds, not a
proven total CPU deadline. Disconnect is polled approximately every 100 ms.
Logical timeout returns 504, disconnect 499, provider errors sanitized 502.

A synchronous worker may outlive timeout/disconnect/ASGI cancellation. Its slot
remains occupied until the real worker settles; late output is discarded and late
exceptions consumed without logging. A hung worker leaves dictation unavailable
instead of admitting more work. This is explicit admission/failure behavior,
not forced process cancellation, immediate buffer reclamation or secure erasure.
The existing engine disconnect callback is cooperative. Tests include both
injected async workers and an actual synthetic worker thread beyond deadline.

Both exported R2 entry points remain disabled by construction, with no environment
or request enable flag. No bridge runtime/service was started. Working credentials,
network attachment and the minimal explicit live wiring require later review.

## Isolated resource evidence

Three uniquely named/labeled temporary containers reused the existing image/model,
with no network, published ports, private recordings or deployed-data mounts.
Only a read-only model FILE was mounted. Requests used generated mono PCM16 WAV
silence at 16 kHz; no private audio or running Whisper service was called.
No transcript content is published or logged; only sizes/timing/status metrics
were retained. Exact IDs/image/labels/mounts were checked before removing each
owned container. A final label inventory confirmed none remain. No volume/prune.

An exploratory 2-CPU run with a 2-GiB containment ceiling exceeded its 35-second
per-case deadline and was stopped/removed. That ceiling came from generous
containment around the prior 562 MiB snapshot, not an operational recommendation.
The phase was not a passed workload result. Matching the engine's eight threads
with an 8-CPU quota completed both durations in two subsequent runs:

| Confirmatory synthetic input | HTTP | Wall time | CPU time | WAV bytes |
| --- | --- | --- | --- | --- |
| 1-second silence | 200 | 3.987 s | 31.515 CPU-s | 32,044 |
| 120-second silence | 200 | 9.999 s | 79.416 CPU-s | 3,840,044 |

Reference observed cgroup peak: **712,343,552 bytes (679.34 MiB)**.
Candidate memory policy: round 1.5 times that peak up to 64 MiB, then add one
64 MiB reserve = **1088 MiB**. The 50% plus 64 MiB reserve is an explicit engineering
margin, not measured worst-case speech memory. Confirmatory run under this limit
and equal memory-plus-swap limit peaked at **695,803,904 bytes (663.57 MiB)**,
with zero OOM kills, effective memory.swap.max=0 and memory.swap.current=0.
Warm-cache startup was 0.438 seconds; no uncached startup claim is made.

Eight CPU quota/eight threads bound the independent workload but do not reserve
cores or establish latency alongside A3/TTS. Silence is not a worst-case speech
benchmark or Chinese/English recognition acceptance. Actual public-speech resource
margin and host headroom require controlled acceptance review. The model file is
reused on disk; the second model/context/process adds its own memory footprint.

Both successful resource/inference phases initially ended in overly strict
harness filesystem assertions: Docker diff showed only added /models and its model
mountpoint, not an empty diff. These are mount scaffolding created at start; root
and model remained read-only and no audio paths appeared. The corrected analysis
accepts only those exact scaffolding entries. The retained opt-in measurement
harness incorporates this correction and parses successfully; it was not rerun
solely to repeat already completed inference measurements. Those earlier nonzero
harness exits are not described as passing whole-harness runs.

## Offline validation and limits

| Validation | Result |
| --- | --- |
| New bridge target/admission/timeout/disconnect/cancellation/thread tests | 8 passed |
| Existing R2 auth/multipart/bounds/cache/canonical/logging tests | 11 passed |
| Existing TTS/Pipe regressions | 22 + 25 passed |
| Existing R1 transport/delegation | 9 passed |
| Existing A3 executable contracts | 4 scripts passed: transcription/provenance, voice order, voice API/text, vision/text regression |
| Native recorder/composer and cancellation | 15 tests passed; both Svelte components compile |
| Mock WebAudio/PCM normalization | 11 passed |
| Normalized Compose config | One service/fixed command/internal network/no ports/RO/logging/measured limits verified |
| Unsafe config rejection | Five mutations rejected; missing model configuration rejected before creation |
| Isolated model inference/resources | Two completed 8-CPU measurement phases, each 1/120-second synthetic WAV; caveats above |
| Regression isolation | Zero forbidden network/model/deployed-data access violations in guarded mock suites |
| Git/privacy scope | Whitespace, sanitized evidence, preserved drafts and reporting-only publication verified |

The first cancellation test exposed a poller-cleanup stall; it was fixed with an
explicit stop event. The exact stalled test process was terminated, and the final
66 backend/private/TTS/Pipe tests passed. Compose JSON elides numeric zero core
fields and serializes memory values as strings; validation accounts for that
representation without weakening the requested zero/equal settings.

R4 actual Chrome codec results are reused, not rerun as new R6 browser acceptance.
No actual microphone, new compressed-codec experiment, full WebUI image build,
mounted browser/native DOM, Safari/iPhone acceptance or live STT traffic occurred.
All model inference was restricted to the isolated synthetic measurement containers.

## Residual risks and exact next activation actions

System/client swap, core/crash dumps, hibernation, browser-native allocation/GC and
memory persistence remain unresolved. Container swap prohibition observed here
is not whole-system/client privacy proof. Legacy A3 conversion retention and its
intentional canonical original evidence remain unchanged. No complete privacy,
hard process-cancellation or immediate RAM-erasure guarantee is claimed.

For a controlled, separately authorized Lab activation:

1. Review this exact local commit, revised scope/residual risks and 8-CPU/1088-MiB
   budget against current host headroom. Verify pinned image and existing model
   regular-file identity/read permissions; no pulls/downloads. Retain current
   WebUI image/config and keep both gates disabled during preparation.
2. Package the existing R2 bridge/R1 modules with one Uvicorn worker, independent
   service credential, disabled access/debug logs, constrained storage and bounded
   ingress without persistent spooling. Keep it outside canonical chat and
   unauthenticated HTTPS routes. No second STT engine is needed.
3. Under separate authorization, create only the owned private engine/network;
   verify actual no-convert command, model-only RO mount, cgroups, logging and no
   host ports. Attach only the bridge to the backend network and verify private
   DNS/membership plus unreachable-upstream failure without legacy fallback.
4. Review/package the minimal explicit credential/callable/native-dispatch wiring
   and R2/R4 recorder/API edits with the current TTS/branding baseline. Neither
   live gate can be enabled by configuration today. Obtain activation approval
   before enabling them or making any service change.
5. Run separately authorized public synthetic speech acceptance: latency/resource
   margin, language behavior, auth/bounds/errors/disconnect, no disk/cache/log
   content, native editable review-before-send and target-browser/Safari/iPhone
   behavior. Silence inference does not replace these checks.
6. On fault/rollback, close both dictation admissions first; stop only the bridge
   and owned private engine and verify old work is gone before reopening. Restore
   the retained WebUI configuration with dictation disabled if needed. Remove only
   exact owned resources after identity/exclusive-network checks; stop if uncertain.
   Never fall back to legacy Whisper, restart A3 or broadly remove volumes/stacks.

No runtime rollback is needed now: no deployment occurred. Only this sanitized
report/index is pushed on reports/web-validation. Implementation stays local.
