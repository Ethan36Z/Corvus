# STT-1a — Whisper conversion privacy preparation

Date: **2026-10-19**

Verdict: **STT1A_BLOCKED**

No validated implementation commit or derivative image was produced. The local
source draft is preserved, uncommitted and explicitly marked NOT DEPLOYABLE.
The mandatory storage/cleanup boundary could not be validated with the attempted
Docker configuration, so work stopped rather than claiming privacy acceptance.

## Baseline and root cause

Reference: [STT-1 blocker](2026-10-19-stt1-whisper-offline-integration.md).

Lab was clean on `lab/ow2e-console` at
`4f8013af2c8e73774fcef91c2510e5808c1fd2c2`. The existing STT worktree was preserved.
A separate local worktree was created on `integration/stt1a-whisper-privacy` from
that exact commit. The reporting branch was clean and aligned with origin before
publication. No implementation branch is published.

The running Whisper image still matches
`sha256:caf0cd77c922e9c53f10a9bc17c2f74cc2295d12e7b0f96b630fb3b3c55a0026`.
Its installed public `examples/server/server.cpp` SHA256 is
`903bf6a6904301a698e0db79c0a72f25bca5bc7c3953b493eb09a68683e53356`.
This was freshly checked in an isolated, read-only, network-disabled container
from the exact local image, without model or deployed data mounts.

The existing server uses the multilingual small model, eight threads, automatic
language detection, CPU-only execution and global `--convert`. It has no tmpfs
configured. The source writes named input/output files and does not remove both
on every failure. Normal success cleanup exists; no claim is made that every
request leaks, or that a particular private recording was retained. Historical
temporary files, logs and private recordings were not inspected or deleted.

## Draft implementation — not an accepted fix

Only these new files were written in the separate local worktree:

- `deploy/whisper/privacy/conversion.h`
- `deploy/whisper/privacy/patch.py`
- `deploy/whisper/privacy/README.md`

The draft approach replaces the named-file converter with anonymous Linux
`O_TMPFILE` descriptors on a dedicated private tmpfs. Input/output descriptors
would be passed to the existing ffmpeg without a shell, then converted bytes
would enter the existing in-memory audio reader. Descriptor lifetime is intended
to remove the need for pathname cleanup. No second STT engine or model is added.

The draft includes a fixed ffmpeg destination, quiet child output, upload/output
limits, a 30-second conversion deadline, client-disconnect polling, child cleanup,
parent-death signal handling and source-hash verification. It also attempts to
replace filename-bearing diagnostics and unsanitized exception responses in the
pinned server. These are implementation intentions, **not validated guarantees**.

The draft requires a mode-0700, same-owner, exact tmpfs mount with `noswap`.
Ordinary tmpfs can use swap; merely describing it as RAM-backed is not a complete
persistent-storage privacy argument. SIGKILL does not execute C++ destructors.
The proposed kernel-managed anonymous-descriptor boundary and child termination
must be tested, including abrupt parent death, before acceptance.

The draft's demuxer allowlist, 25 MiB input bound, 40 MiB output bound and timeout
are new compatibility constraints requiring validation. They are not represented
as preserving every input previously accepted by ffmpeg. No API or model behavior
has changed in the deployed service.

## Exact blockers and stopping point

The isolated probe requested a private tmpfs with:

`rw,nosuid,nodev,noexec,noswap,size=72m,mode=0700`

The Docker daemon returned:

> invalid tmpfs option "noswap"

The command exited 125 before the test process started. It had no network, model
mount or deployed-data mount. No conversion or inference ran. This establishes
that this particular Docker tmpfs configuration is unsupported here; it does
**not** establish that every possible volatile-storage packaging method is
impossible.

The strict mount check was not weakened. No host mount, swap setting, Docker
configuration or deployed container was changed to bypass the failure. A possible
follow-up is a separately reviewed host-created private noswap tmpfs bind mount,
but its permissions, lifecycle and recovery require design/validation; it is not
a prepared deployment instruction.

A second unresolved packaging issue is the offline C++ build environment: the
pinned runtime has gcc and cmake but no g++ frontend. The host g++ 13 compiled the
standalone helper, but this does not establish a compatible Ubuntu 22.04 server
rebuild. No compiler or model was downloaded, no image was pulled, and no newer
upstream version was substituted.

## Checks actually executed

| Check | Observed result |
| --- | --- |
| Clean Lab baseline and separate branch creation | Passed |
| Pinned installed image/source identity | Matched |
| Exact-source transformation | Passed on copied public source |
| Modified-source rejection | Passed |
| Standalone conversion header compilation | Passed with host g++ 13, static probe |
| Private noswap tmpfs runtime probe | Blocked by Docker before process start |
| Full patched server compile/link/startup | Not performed |
| WAV/non-WAV conversion and invalid input | Not performed |
| ffmpeg/read/output failure cleanup | Not performed |
| Cancellation, exceptions, interruption/SIGKILL | Not performed |
| Logging canary/resource-limit/API validation | Not performed |
| Existing A3 transcription scripts | Not rerun in STT-1a; prior STT-1 results are historical only |
| Live inference against deployed Whisper | Zero calls |
| Prepared derivative image | None |

There is no passing conversion regression-suite count. The source checks and
standalone compilation cannot establish request cleanup, supported audio formats,
startup compatibility or privacy of every reachable logging path.

## Remaining risks and deployment prerequisites

The current deployed service retains the original STT-1 risk. STT remains blocked.
The uncommitted draft has not received full correctness/security review. In
particular, all exception paths, child descriptor/process lifetime, client
cancellation, bounded temporary capacity, diagnostics and A3 format compatibility
remain unproven. Do not activate it or infer deployment readiness from this report.

Next, resolve the narrow offline packaging prerequisites: a demonstrably private,
bounded volatile storage boundary and an exact compatible C++ build toolchain.
Then finish the draft review and run the requested synthetic conversion/failure/
termination/API/A3 test matrix. Do not resume WebUI dictation activation until the
shared conversion privacy boundary is accepted.

No ordinary cleanup handler is claimed to run after SIGKILL. No persistent data
restore, historical-file deletion or service restart is part of this stage.

## Rollback and publication

No runtime rollback was needed: no deployment occurred. Whisper, TTS-enabled
WebUI and hardened Kokoro remained running on their existing image identities;
observed container start times were unchanged by this work. Production/Demo,
Kokoro/TTS, Qwen, Hindsight, Arena, Web MVP and canonical data were not modified.

A future shared Whisper deployment must preserve the original image, command,
model mount, CPU/thread/language settings, loopback endpoint and recovery
configuration. Restoring the original image would restore its known privacy
limitation; WebUI dictation must remain disabled in that situation. No activation
or rollback command is supplied for the unvalidated draft.

Local implementation branch: `integration/stt1a-whisper-privacy`.
Base commit: `4f8013af2c8e73774fcef91c2510e5808c1fd2c2`.
**New implementation commit: none. Prepared image: none.**
Only this sanitized report and its index are committed and pushed to
`reports/web-validation`. The draft code remains local and uncommitted.
