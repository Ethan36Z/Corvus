# STT-1a recovery — storage and build feasibility gate

Experiment: **STT-1a recovery**
Date: **2026-10-19**
Verdict: **STT1A_CONFIGURATION_ONLY_CANDIDATE_REQUIRES_VALIDATION**
Related Lab baseline: `4f8013af2c8e73774fcef91c2510e5808c1fd2c2`

## Objective and decision

Identify the smallest sound way to prevent private Whisper conversion recordings
from reaching persistent storage after conversion failure or process death.
This report preserves the completed bounded read-only investigation; publishing
it does not repeat that investigation or authorize implementation.

**Recommendation: validate configuration-only storage isolation first.** Source
changes are unnecessary for keeping conversion files off persistent storage if
the prerequisites below hold. Automatic per-request file reclamation is a
stronger requirement and still calls for the preserved anonymous-file approach.
Neither approach is accepted or deployable on this evidence alone.

References:

- [STT-1 integration blocker](2026-10-19-stt1-whisper-offline-integration.md)
- [STT-1a conversion privacy draft and blocker](2026-10-19-stt1a-whisper-conversion-privacy.md)

## Verified environment and root cause

The Lab checkout remained clean at the stated baseline. The existing Whisper
image remained `sha256:caf0cd77c922e9c53f10a9bc17c2f74cc2295d12e7b0f96b630fb3b3c55a0026`.
Selected container settings confirmed working directory `/app`, writable root,
no tmpfs, and only the existing read-only model bind. Startup retains the existing
multilingual small model, eight threads, automatic language selection, CPU-only
operation and `--convert`.

The previously copied public server source still matches SHA256
`903bf6a6904301a698e0db79c0a72f25bca5bc7c3953b493eb09a68683e53356`.
Its default `tmp_dir="."` resolves to `/app`. Conversion writes named input and
output files, and reachable failure paths return before removing both. Process
death does not unlink those directory entries. Normal success cleanup exists;
this is not evidence that a particular private recording was retained.
SIGKILL runs no C++ destructors or application cleanup handlers.

| Capability | Verified evidence and limit |
| --- | --- |
| Host swap | Active approximately 2 GiB `/swapfile`, approximately 1.39 GiB used at inspection; swappiness 60. Swap encryption was not established. |
| Docker | Client and Engine 29.9.1; overlayfs storage; AppArmor, seccomp and cgroup namespace support reported. |
| Kernel | 7.0.0-38-generic; tmpfs and ramfs listed; TMPFS, SWAP, MEMFD_CREATE, COREDUMP and HIBERNATION configured. |
| Existing storage | No dedicated audio noswap mount established by inspection. Ordinary tmpfs must not be described as nonswappable. |
| Server interface | Existing `--tmp-dir` controls the input path and derived ffmpeg output path; `/inference` and `--convert` can remain unchanged. |
| Runtime swap limits | Whisper cgroup `memory.max` and `memory.swap.max` both read `max`. |
| Core collection | Host core pattern pipes to systemd-coredump; Whisper soft and hard core limits are unlimited. Effective suppression is unproven. |
| Resume | Current resume device reads `0:0`; this does not establish that every hibernation or crash-dump path is disabled. |
| Host build tools | g++ 13.3 and make available; CMake absent from PATH. |
| Whisper runtime build tools | Ubuntu 22.04.5; gcc 11.4, CMake 3.22.1 and make available; no g++/c++ frontend established. Public source and CMake cache remain present. |
| Existing converter | `/usr/bin/ffmpeg` exists and is executable, matching the draft's fixed executable path. |

The earlier STT-1a probe failed because Docker rejected `noswap` in the requested
`--tmpfs` option string before the probe process started. That establishes a
failure of that packaging route, not absence of kernel support or impossibility
of all volatile-storage configurations. The independent build blocker remains:
no complete compatible offline server builder was established. Host g++ alone
does not prove that a rebuilt binary will run in the Ubuntu 22.04 image.

## Smallest solution options

| Option | Persistent-storage safety | Limitation / decision |
| --- | --- | --- |
| Ordinary Docker tmpfs | Insufficient alone with active swap | Reject as a standalone privacy argument. |
| Docker local-driver tmpfs with `noswap` | Technically viable candidate, pending an isolated mount test | Preferred configuration-only route; reuses Docker without a separate host mount service. |
| Host-created `noswap` tmpfs, bind-mounted | Sound fallback when correctly verified | Requires additional mount ordering, ownership, lifecycle and fail-closed startup management. |
| ramfs | Filesystem data is nonswappable | Lacks tmpfs capacity controls; less suitable for bounded conversion storage. |
| Preserved `O_TMPFILE` source draft | Can combine nonpersistent storage with anonymous-file reclamation | Requires source review, compatible offline build tooling and comprehensive synthetic tests. |

The kernel documents tmpfs `noswap`, while ordinary tmpfs can swap. Kernel
version and configuration support feasibility; they are not a successful mount
test on this host. [Linux tmpfs documentation](https://cdn.kernel.org/doc/html/latest/filesystems/tmpfs.html)

Docker documents a built-in local-driver tmpfs volume and forwarding of local
mount options to the Linux mount syscall. This provides a candidate route around
the rejected `--tmpfs` syntax. Actual `noswap` acceptance here remains untested.
[Docker local tmpfs volume](https://docs.docker.com/reference/cli/docker/volume/create/#driver-specific-options--o---opt),
[local mount forwarding](https://docs.docker.com/engine/storage/volumes/#how-mounting-block-devices-works)

## Configuration-only prerequisites and limits

Use a dedicated local-driver volume with `type=tmpfs`, `device=tmpfs`, and mount
options `rw,nosuid,nodev,noexec,noswap,size=<validated bound>,mode=0700`, with
correct ownership. Mount it only for Whisper at `/run/corvus-audio`, use
`volume-nocopy`, and explicitly set `--tmp-dir /run/corvus-audio`. Validate the
actual mount type, options, ownership and effective path before serving requests;
startup must fail closed rather than fall back to a persistent directory.
Capacity must be sized for concurrent input and converted output, not copied
uncritically from the draft's single-conversion budget.

Protect process buffers as well as filesystem pages: configure an appropriate
memory limit and equal memory-plus-swap limit, and verify effective
`memory.swap.max=0`. A noswap filesystem does not protect ordinary process-memory
copies. Docker documents that equal positive memory and memory-plus-swap limits
prevent container swap. [Docker swap controls](https://docs.docker.com/engine/containers/resource_constraints/#--memory-swap-details)

Effective core-dump suppression and hibernation/crash-dump policy must also be
established before claiming private audio never reaches persistent storage.
Do not assume a nominal core limit alone proves suppression under the host's
piped collector.

This configuration retains the exact engine/model, CPU operation, existing
ffmpeg conversion, A3 multipart protocol and `/inference`; it requires no server
rebuild. Existing WebUI TTS remains outside the change. Removing `--convert` is
not recommended: A3 format compatibility without conversion has not been established.

**Storage safety is not ordinary cleanup.** Failed requests can still leave named
recordings in RAM until removal or mount destruction, including after server
process death if the mount survives. Repeated failures can exhaust capacity.
Unmount/container lifecycle behavior must be verified, especially for a shared
or host-owned mount. No immediate disappearance after each failed request is
claimed. No approach here removes historical persistent files.

## Preserved draft and minimum source/build alternative

The existing worktree is `/tmp/corvus-stt1a-integration`, on
`integration/stt1a-whisper-privacy`, based on the stated Lab commit. These files
remain uncommitted and byte-for-byte preserved, verified by SHA256 before and
after investigation:

- `deploy/whisper/privacy/conversion.h`
- `deploy/whisper/privacy/patch.py`
- `deploy/whisper/privacy/README.md`

The draft is reusable if immediate per-request reclamation is selected. It
replaces named conversion files with anonymous `O_TMPFILE` descriptors and keeps
the existing ffmpeg-to-audio-reader path. The kernel can reclaim an anonymous
file on final descriptor closure, including after process death; this is not a
claim that SIGKILL executes cleanup. Child-held descriptors still matter.

Its strict private noswap mount check remains relevant. Full-server compile,
link and runtime behavior are unvalidated. Review must cover threaded fork
behavior, descriptor inheritance and final closure, child parent-death handling,
exceptions, cancellation and deadline paths, logging, capacity, and A3 format
compatibility. The draft introduces demuxer, upload/output and deadline limits;
these have not been demonstrated compatible with all existing inputs.

If this stronger option is selected, the minimum work is to finish the pinned
server conversion-path/helper review and prepare a derivative using a compatible
Ubuntu 22.04 C++ toolchain or validated equivalent. Do not substitute a newer
engine/model or assume the host compiler output is runtime-compatible. The
historical standalone compilation is not a full-server build acceptance.

## Exact next implementation task and remaining gate

Prepare an isolated, synthetic **configuration-only feasibility test** using the
pinned local image, without model or deployed-data mounts. Validate local-driver
`noswap` mounting, effective permissions and path, fail-closed behavior, effective
swap prohibition, capacity failure, and process/container termination lifecycle.
Prepare a reviewable configuration proposal without deployment. Do not represent
this storage test as inference, full A3 acceptance or WebUI dictation acceptance.

If immediate disappearance after every failed request is required, select the
preserved anonymous-file approach instead and resolve its compatible offline
builder before implementation. A later acceptance plan must cover synthetic
conversion/error/termination and A3 compatibility before any shared-service change.

Unresolved assumptions are actual local-driver `noswap` acceptance, lifecycle and
fallback behavior; storage/concurrency and memory sizing; effective core/dump and
hibernation policy; and, for the source alternative, descriptor/child correctness
and compatible build packaging. No safety assumption is silently waived.

## Scope, privacy and publication

The investigation used selected configuration, toolchain and public-source
reads only. It performed no source edits, builds, deployment, service restarts,
model downloads, inference, private recording inspection, credential access,
pruning or canonical-data changes. It did not repeat the broad multimodal audit.
No Production, Demo, Lab WebUI, Kokoro, Hindsight or Memory Arena changes occurred.
No new conversion/runtime acceptance tests are claimed.

This publication changes only this sanitized report and the multimodal index.
Unnecessary host/account details, startup prompt contents, raw terminal output,
credentials, recordings, conversations and canonical contents are excluded.
Implementation branches and the uncommitted draft are not published. Reporting
publication does not authorize implementation, activation or a service restart.
