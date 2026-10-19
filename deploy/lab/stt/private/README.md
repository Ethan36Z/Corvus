# STT-R6 — private no-convert Whisper candidate

Baseline: local R4 `83ca1d38836a45088fa6574ed177b1064a0cd87d`.
Option B is selected. This is offline preparation, not deployment. Both R2 live
entry points remain disabled with no environment/header enable switch.

## Revised delivery scope

The user explicitly narrowed delivery to application-level private dictation:
no conversion temp audio, no persistent dictation cache/content logs, authenticated
private bridge, fixed target/no legacy fallback, bounded requests/responses,
explicit timeout/admission, constrained filesystem and scoped failure/rollback.
Host/client swap, core/crash dumps, hibernation, browser memory persistence and
legacy A3 retention are residual risks, not solved or silently reclassified as
verified protections. This supersedes R5's decision to block on those broader
unverified boundaries; it does not change their technical status.

## One service candidate, no shared A3 change

`compose.yml` defines only `corvus-whisper-dictation`, using the existing pinned
image and the existing model FILE read-only. `CORVUS_STT_MODEL_FILE` must identify
the reviewed ggml-small.bin; missing configuration fails before creation, and
create_host_path=false prevents creation of a missing model path. Future preflight
must verify a regular readable file of the reviewed identity, not a directory.
No image/model copy or download is required. The manifest was rendered/validated,
not started. Its profile is an additional review boundary, not authorization.

The command omits --convert and uses the pinned server's existing byte-buffer
reader and /inference. CPU-only, eight inference threads, automatic language and
multilingual small model remain. The independent dictation instance has no
private startup prompt; existing R1 multipart prompt behavior remains unchanged.
Original A3 process/target/model/settings/ports/provenance/ffmpeg stay unchanged.
No shared host settings or other audio services are modified.

The engine runs UID/GID 10001, read-only root, all capabilities dropped,
no-new-privileges, 64 PIDs, no writable persistent mounts or audio tmpfs. The sole
bind is the read-only model. Docker logging is none and both server output streams
are redirected to /dev/null, suppressing even upstream transcript diagnostics.
No input is interpolated into its fixed shell command. core=0 is defense in depth,
not a claim that the host's piped collector is suppressed.

There are no host ports, host networking or public proxy routes. The sole network
is a new internal network, corvus-stt-dictation-private. The native unauthenticated
Whisper endpoint must be reachable only by the authenticated standalone bridge.
Network membership must be verified before activation: engine + bridge only;
WebUI reaches the bridge, never Whisper directly. No shared legacy network or
existing volume is attached. This topology is statically validated; measurement
used network=none/loopback and did not deploy the proposed network/DNS topology.

## Existing bridge, fixed target and admission

Only `app.stt_bridge.WHISPER_BASE` changes to the fixed private service DNS target.
R1 remains the sole multipart transport; A3's default URL and transport are not
modified. Legacy/external addresses are rejected, never retried or used as a
fallback. Existing native WebUI authentication and independent service credential
checks remain. Neither credential provisioning nor working exported dispatch is
introduced here; successful tests inject synthetic credentials/callables only.

After authentication, one request owns the admission slot before body consumption.
Other requests get 429 without body consumption. Body limit/deadline remain
8 MiB / 5 seconds; PCM16 WAV at 16 kHz, at most 120 seconds; reply at most 64 KiB /
16 Ki characters. Native multipart has its existing bounded envelope. No audio
spooling, files, attachments, SQLite, chat/Pipe or memory calls are added.

Inference has a 25-second logical deadline, within the existing native 30-second
HTTP-hop budget for the normal bounded upload path. If upload plus inference
exceeds that outer budget, the native timeout may win; it still fails closed.
R1's socket timeout is also 25 seconds, but is not a hard total CPU deadline.
Disconnect is polled approximately every 100 ms. Timeout => 504; disconnect =>
499; provider failures => sanitized 502. No retries or automatic resubmission.

The synchronous worker can continue after HTTP timeout/disconnect/ASGI cancellation.
Its admission slot remains occupied until the real worker settles; late output
is discarded and late exceptions are consumed without content logging. A hung
worker deliberately leaves dictation unavailable (429) instead of admitting more
work. The server's existing disconnect callback is cooperative, not hard process
cancellation. No immediate memory erasure or termination guarantee is claimed.
Run one bridge process/Uvicorn worker only; multiple workers/replicas would multiply
this per-process slot. There is no queue. Bounded native ingress still needs its
existing no-disk-buffering/admission configuration reviewed at activation.

## Measured budget

See `resource-evidence.json`, sanitized synthetic silence measurements only.
All measurement containers used the existing image/model file read-only, UID
10001, read-only root, network=none, no published ports, no logging, no-new-privileges,
cap-drop ALL and core=0. No running Whisper was called. Exact identities and mounts
were checked before removing only the temporary containers; no volumes/prune.

An exploratory 2-CPU/2-GiB containment run exceeded its 35-second per-case timeout.
The ceiling was experimental containment based on the prior 562 MiB snapshot,
not an operational limit. It is not a passed measurement. Reusing the engine's
8-thread workload with an 8-CPU quota then completed 1/120-second synthetic WAVs
in about 4/10 seconds; observed cgroup peak was 712,343,552 bytes (679.34 MiB).

Chosen candidate limit: ceil(1.5 * observed peak / 64 MiB) * 64 MiB + one 64 MiB
reserve = 1088 MiB, with memory-plus-swap equal. The 50% plus 64 MiB margin is an
explicit engineering reserve, not a measured worst-case speech bound. A confirming
run under this limit passed both WAV lengths, peak 695,803,904 bytes (663.57 MiB),
no OOM, swap.max=0 and swap.current=0. Startup was 0.438 seconds (warm model cache),
not an uncached cold-start benchmark. CPU time was about 31.5/79.4 CPU-seconds.
The model file remains shared on disk; context/process RAM is independent.

Silence may cost less than speech/complex decoding. Eight CPUs can contend with
A3/TTS/other workloads, and were not measured concurrently with private traffic.
The quota bounds this candidate; it does not reserve CPUs or prove latency/QoS.
Operator headroom approval and a controlled public-speech workload remain activation
review/acceptance actions. No bound is inferred from model file size alone.

The original filesystem check expected an empty Docker diff and was too strict:
Docker adds /models and its model-file mountpoint during start. Both completed
runs showed only those scaffolding paths, no audio files; root/model were read-only.
No historical/private directory contents were inspected. The opt-in measurement
harness is retained as `measure.py <existing-ggml-small.bin-file>`; it uses only
new uniquely labeled test resources and must not be run as an activation command. The initial assertion
failure did not indicate an audio cache and is not hidden as a passing assertion.

## Offline verification

Render only (never up/start here), with an explicitly supplied existing model path:

```
CORVUS_STT_MODEL_FILE=<existing-file> docker compose -f deploy/lab/stt/private/compose.yml --profile stt-private-review config --format json > <temporary-json>
python3 -B tests/check_private_whisper_config.py <temporary-json>
```

Config checks cover one service, fixed command/image, internal-only network,
no host ports, constrained filesystem/mounts/logging and measured limits; five
unsafe mutations and missing model configuration are rejected. Native R2 auth,
WAV/multipart, response/cache/canonical/logging tests remain; new tests cover
busy-before-body, timeout, disconnect, ASGI cancellation and a real synthetic
worker thread held beyond the logical deadline. A poller cleanup bug was found
and fixed using an explicit stop event, then suites passed.

R3/R4 frontend tests verify native editable-composer/no-auto-send and cancellation
with synthetic WAV/mocked codecs/APIs. Actual browser codec acceptance from R4
is reused; no browser microphone or fresh compressed fixture is used in R6.
Existing A3 transport/artifact attribution/order/text, TTS and Pipe tests pass.
No full image build or deployed networking/UI acceptance is claimed.

## Separately authorized activation/recovery checklist

1. Review/approve this exact code and scope, residual risks, 8-CPU/1088-MiB budget
   and host headroom. Confirm actual model identity/read permissions and image
   pin, no pulls. Retain current WebUI image/config and the two disabled gates.
2. Prepare the existing bridge runtime with R1/protocol modules, one Uvicorn worker,
   access/debug logging disabled, constrained filesystem, bounded ingress without
   persistent spooling, and an independently provisioned service credential.
   Keep it outside canonical chat/HTTPS unauthenticated routes. This is future
   packaging/wiring of R2, not included as a second service candidate here.
3. Under separate authorization, create only the owned internal network/private
   engine. Verify exact image/command/no-convert, model-only read-only mount,
   actual cgroup limits, logging none and network membership/no published ports.
   Attach only the standalone bridge to this backend network; verify its fixed DNS
   resolution cannot hit legacy A3 and unreachable engine fails without fallback.
4. Review the minimal explicit code wiring that supplies the credential/working
   bridge callable and native dispatch; neither gate can be enabled by an env
   flag today. Package the R2/R4 native API/recorder edits with the existing
   TTS/branding baseline. Obtain approval before enabling either live gate.
5. Perform separately authorized synthetic public-speech acceptance for latency,
   resource margin, auth, size limits, errors/disconnect/timeout, no disk/cache/log
   content, and browser review-before-send, especially Safari/iPhone. Do not claim
   Chinese/English recognition or device acceptance from silence measurements.
6. On rollback/fault: close both dictation admissions first. Stop the bridge and
   only the owned private engine; verify the old worker/engine is gone before
   reopening. Restart/reload only the private candidate under authorization if
   recovery is selected. Remove only exact owned resources after identity and
   exclusive-network-consumer checks; stop if ownership is uncertain. Retain A3
   and every existing volume. Never fall back to legacy Whisper or run a broad
   compose down/prune. Restore the retained WebUI config with dictation disabled
   if its packaging was activated. No runtime rollback is needed for R6 itself.

Host/client swap/dumps/hibernation, browser native allocation/GC and memory
persistence, legacy A3 temp retention and intentional A3 evidence remain unresolved.
The synthetic container's swap limits do not prove whole-system/client privacy.
This is READY FOR ACTIVATION REVIEW under the explicitly revised product scope,
not deployment authorization or complete privacy acceptance.
