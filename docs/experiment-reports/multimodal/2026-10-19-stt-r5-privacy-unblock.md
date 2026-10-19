# STT-R5 — Privacy unblock architecture decision

Date: 2026-10-19

Verdict: **STT_R5_BLOCKED**

**Preferred architecture: B, a separate private no-convert dictation instance of
the existing pinned Whisper image/model, leaving A3 unchanged. No option is yet
accepted against the complete mandatory privacy contract. No implementation or
deployment is authorized by this decision.**

## Baseline and evidence reused

Local baseline: R4 `83ca1d38836a45088fa6574ed177b1064a0cd87d`.
Read the complete [R4 report](2026-10-19-stt-r4-browser-wav.md),
[STT-1a draft](2026-10-19-stt1a-whisper-conversion-privacy.md),
[recovery decision](2026-10-19-stt1a-recovery-feasibility.md),
[noswap probe](2026-10-19-stt1a-noswap-storage-probe.md),
[volatile-storage blocker](2026-10-19-stt1a2-volatile-storage.md) and
[conversion compatibility gate](2026-10-19-stt-conversion-boundary.md).
No mount/failure/codec experiments or broad investigations were repeated.

The source copies still match the earlier pinned evidence:

- Image: `sha256:caf0cd77c922e9c53f10a9bc17c2f74cc2295d12e7b0f96b630fb3b3c55a0026`.
- server.cpp: `903bf6a6904301a698e0db79c0a72f25bca5bc7c3953b493eb09a68683e53356`.
- common-whisper.cpp: `852fbc77d2461322a82b9c571cf4703bac3c78c5c51d3a90e80792ce0c04e313`.
- CMakeCache.txt: `84bdcc5b52c89bfd6121fff59ef06c01df07579a358729c8ed97af30a17f3707`.

Only a read-only resource snapshot, model-file size metadata and source-contract
assertions were added. No audio, historical temp files, service logs, credentials
or model contents were inspected. The running service was not called or changed.

## Three-option comparison

| Option | A3 compatibility and maintenance | Privacy and resource implications | Rollback safety |
| --- | --- | --- | --- |
| A: Remove --convert on shared instance | Not compatible by evidence alone. A3 sends original compressed audio, including ordinary trailing-moov M4A. Needs validated seekable-memory preprocessing and Corvus-runtime packaging, preserving original evidence and provenance. R4 browser code does not cover A3 uploads. | One model process remains; new conversion CPU/buffers and adapter lifecycle require validation. No Whisper conversion names after preprocessing, but other persistence/cancellation paths remain. Strict stdin conversion already failed the M4A gate despite exit 0. | Shared restart changes every A3 caller. Restoring --convert restores known file-retention risk; dictation must close first. |
| B: Separate pinned no-convert instance | Reuses existing engine/image/model, memory reader, /inference and one R1 multipart transport. No C++ fork or A3 adapter change. Adds one service/network identity, resource policy and lifecycle. | No converter process or named conversion audio for this route. Adds a second model/context footprint and potential concurrent inference CPU. Still needs process swap/dump/logging controls and cancellation/admission policy. | Close dictation admissions and retire only owned new resources; A3 instance/endpoint remains unchanged. Never fall back to shared converter. |
| C: Complete O_TMPFILE draft | Reuses existing ffmpeg/seekable descriptor conversion and model process, but patches pinned C++ and needs compatible full-server build/link/runtime acceptance. New format/size/deadline constraints require A3 regression validation. | Anonymous files avoid names; reclamation follows final FD closure, including process death, if all child-held FDs are closed. Noswap storage and separate process-memory controls still required. No second model, but converter/anonymous storage and memory copies remain. | Shared derivative activation affects A3. Reverting image reintroduces retention; keep dictation disabled on rollback. Larger compatibility/maintenance test surface. |

**B is the smallest change to the dictation conversion boundary.** R4 already
produces canonical WAV and the pinned memory reader already consumes bytes.
An extra instance is an operational cost, not a new STT engine or proof of
privacy. Conversely, the more complex C++ draft does not automatically improve
swap/dump/cancellation protection. C is relevant if the required scope is to fix
the existing shared A3 converter too, or a second model cannot be admitted.
A and C are not selected for implementation here.

## Verified no-convert path and A3 boundary

Pinned server.cpp defaults `ffmpeg_converter=false`. Its no-convert inference
branch passes upload bytes/length to `read_audio_data`; that overload uses
`ma_decoder_init_memory`, the existing frame reader and `ma_decoder_uninit`.
The selected branch does not create a temp filename, open an audio ofstream,
call ffmpeg or perform pathname cleanup. Source evidence supports absence of
conversion files, not universal absence of every unrelated server output.

The build cache has `WHISPER_COMMON_FFMPEG=OFF`. It is not sound to infer raw
MP4/AAC compatibility for this memory reader. Existing A3 accepts audio/* and
posts original retained attachment bytes, with language/optional prompt and a
derived TRANSCRIPT linked to the original evidence. Those paths must remain
unchanged. R4 normalization belongs to native browser dictation, not all A3
clients, so it does not by itself make A safe.

B preserves A3 by leaving its process, target, --convert, model, language/prompt,
CPU settings and provenance code untouched. Existing A3 conversion retention
remains a known separate risk. This is not acceptance or cleanup of old A3 files.
If the mandatory contract covers all shared A3 conversion as well as new private
dictation, B alone cannot meet it; an explicit scope decision is needed, and C
(or validated A3 preprocessing) would still be required. Intentional original A3
evidence retention is distinct from unwanted conversion scratch retention.

The current R2 bridge still has the fixed legacy Whisper target. A future B
candidate must change only the dictation bridge's fixed target to the new private
service, retaining R1 as its sole multipart transport. It must have no request-
selected target and no failure fallback to the legacy converter. Both existing
R2 exported dispatch entry points remain disabled; none was wired or enabled.

## Privacy properties: what each mechanism actually supplies

| Property | Decision / evidence boundary |
| --- | --- |
| No named conversion files | B has no conversion-file path; A only after all A3 normalization is proven; C intends anonymous descriptors but is not runtime-validated. |
| No persistent recording cache | R2/R4 add none. B still requires read-only root/no writable data mounts, bounded ingress without disk spooling, fixed metadata and suppressed body/transcript/debug logs. No complete runtime acceptance exists. |
| Failure cleanup | With B there are no conversion files to unlink. Freed request buffers are not guaranteed zeroed immediately, and an alive server/context can retain sensitive state. C needs validated final FD closure/child termination on every path. |
| Process cancellation | Pinned server registers a cooperative `req.is_connection_closed()` abort callback. This is not a hard deadline or proof of immediate cancellation. R2's synchronous HTTP worker cannot be forcibly stopped by ASGI cancellation. All three options retain an unresolved end-to-end cancellation gate. |
| Process death | Kernel releases process descriptors/address-space ownership; SIGKILL runs no application cleanup. This does not establish secure RAM erasure, no core capture or absence of prior copies. |
| Host swap | Historical evidence shows active swap; current shared instance has unset memory/swap limits. Probe verified memory.swap.max=0 only for its synthetic containers. A future dictation process and bridge need their own verified effective controls. Noswap tmpfs alone protects filesystem pages, not all process buffers. |
| Core/crash dumps | Earlier evidence shows a piped systemd-coredump collector and no accepted effective suppression. Nominal core=0 is not sufficient proof for that collector. No crash was induced or policy changed. |
| Hibernation/kernel crash dumps | Not demonstrated disabled/protected. Neither no-convert nor O_TMPFILE nor noswap prevents whole-RAM capture. |

No mandatory failure/persistence requirement is waived. Browser-side copies are
also covered by R4's explicit limitations: native decoder allocations precede
validation, cancellation does not synchronously stop decoding, and browser/host
swap/dump/hibernation or immediate erasure are not established. Server container
settings cannot prove client-device protection.

## Resource cost identified, not benchmarked

A narrow metadata snapshot found the existing pinned service running with
Docker memory/memory-plus-swap limits unset (0), no NanoCPU/cpuset limit and only
the existing read-only model mount. Docker stats reported **562 MiB memory,
0.00% CPU and 17 PIDs** at that instant. This is a current snapshot, not a measured
idle baseline, peak/RSS benchmark, no-swap proof, free-memory figure or proposed
limit. No inference was induced. Model file size metadata is **487,601,967 bytes**
(about 465 MiB); disk file size is not a process-memory reservation.

B reuses the same on-disk model read-only and image layers, so it needs no model
copy/download or derivative image. It creates an independent Whisper context
through the existing model initializer, with its own weights/state/workspace and
request buffers. Do not assume those allocations are shared simply because the
file is shared. A second footprint comparable to the current model process is a
planning estimate only; peak and cold-start costs remain unmeasured. No arbitrary
memory limit is selected from 562 MiB or the earlier 128 MiB storage probe.

Keeping eight inference threads/default one processor gives a second nominal
8-thread inference workload; simultaneous A3/dictation can contend with up to
16 requested inference threads plus other runtime threads. Thread count is not
a CPU quota. No latency/throughput or safe concurrent admission has been measured.
B needs an operator-approved host headroom/CPU policy and a measured model startup
and synthetic workload peak before positive equal memory/memory-plus-swap limits
can be selected and effective memory.swap.max=0 verified. It also needs private
network ownership, independent service authentication, no host/HTTPS exposure,
startup/health supervision and scoped retirement. A same-process shared change
avoids this duplicate model cost but entails A3 compatibility/rebuild risk.

R4's 120-second mono ceiling is 3,840,044 encoded WAV bytes; the pinned reader's
mono float32 sample array alone is 7,680,000 bytes at that length, before upload
copies, multipart buffers, bridge copies and model workspaces. These arithmetic
bounds do not establish total per-request memory. C adds anonymous converter
input/output and ffmpeg resource use; its draft caps are unvalidated compatibility
limits, not resource budgets accepted by this decision.

## Offline checks and exact stopping point

Five read-only assertion groups passed:

1. Three existing public source/build SHA256 pins match the prior report.
2. The no-convert branch selects the byte reader without named conversion writes.
3. The memory decoder and compiled-FFmpeg-off evidence are retained; raw A3 MP4
   compatibility is not assumed.
4. Independent model-context initialization and cooperative disconnect callback
   are identified, without treating them as hard cancellation.
5. R2 disabled gates, legacy fixed target and synchronous worker are unchanged.

These are source-contract checks, not synthetic reader execution or failure/
termination acceptance. R4's previously published browser/WAV and regression
results are reused as historical evidence, not rerun or counted as new R5 tests.
No new audio test, model startup/load, inference, C++ compile, container, volume,
image build, deployed-data inspection or service restart occurred. The only new
runtime measurement was the existing service's read-only resource metadata.

**Local implementation commit: none.** No implementation files/worktrees were
modified. A runnable B candidate cannot yet be justified against the mandatory
host persistence and end-to-end lifetime requirements; a manifest with guessed
resource limits or an unconditional do-not-run wrapper would not resolve them.
Rather than create another blocked infrastructure draft, this stage publishes
the bounded architecture decision and exact prerequisites. Earlier drafts remain
unchanged, including all three uncommitted O_TMPFILE files.

## Exact unresolved blocker and shortest path

There is no verified effective host/client swap/dump/hibernation boundary covering
private buffers, no accepted hard request-lifetime/cancellation policy, and no
evidence-backed second-instance memory/admission budget. The existing image's
no-convert branch solves conversion-file creation; it does not establish those
independent mandatory properties. Therefore live STT remains blocked.

An explicit operator decision is required on the privacy scope: new dictation
versus also repairing legacy A3, whether protection includes host/client dumps
and hibernation, and what post-cancellation buffer lifetime is acceptable. To
retain the original strict contract, demonstrate effective controls and lifecycle
rather than accept residual persistence. Any consciously accepted exclusion or
lifetime change must be recorded as a contract revision, not called a verified
protection. This task requests/assumes no such revision and changes no settings.

After those decisions/evidence, the smallest implementation is **one B candidate**:
reuse the exact image/model with --convert absent, unchanged /inference and CPU/
language behavior; a private-only target and read-only filesystem; verified
process swap/dump controls and evidence-backed memory/CPU/admission limits;
no body/transcript logs or disk spooling; scoped lifecycle/rollback and an explicit
cancellation policy. Repoint only the stateless R1-reusing dictation bridge, with
no fallback and both live gates still disabled for offline tests. Then validate
synthetic success/failure/disconnect/process-death, resource peaks and target-
browser/native-composer contracts before requesting separately authorized live
acceptance. A3 remains untouched. If B's extra model cost or scope is rejected,
return to the preserved C draft; do not build both alternatives.

Only this sanitized report and the multimodal index are committed/pushed to
reports/web-validation. No implementation branch is pushed, no force push or
prune is used, and no deployment follows publication.
