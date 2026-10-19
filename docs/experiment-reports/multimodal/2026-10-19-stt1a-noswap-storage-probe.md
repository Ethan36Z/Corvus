# STT-1a.1 — Docker local-driver noswap storage probe

Experiment: **STT-1a.1**

Date: **2026-10-19**

Verdict: **NOSWAP_PROBE_PASS**

Related Lab baseline: `4f8013af2c8e73774fcef91c2510e5808c1fd2c2`

## Decision and scope

**Docker local-driver tmpfs accepts a private, bounded `noswap` mount on this
host. Configuration-only conversion-storage isolation is feasible.** This is a
storage acceptance result, not acceptance of Whisper conversion, A3 integration,
WebUI dictation, complete audio privacy or deployment readiness.

The [recovery feasibility report](2026-10-19-stt1a-recovery-feasibility.md) was read
first. Its broad investigation was not repeated. The existing uncommitted
`O_TMPFILE` draft was not executed or changed.

The experiment created exactly one uniquely named and labeled temporary
local-driver tmpfs volume and seven isolated test containers. It used only
synthetic text markers and zero-filled files. Every container used the existing
pinned local Whisper image with `/bin/sh` as entrypoint; Whisper itself was not
started and no model was mounted or loaded.

Image: `sha256:caf0cd77c922e9c53f10a9bc17c2f74cc2295d12e7b0f96b630fb3b3c55a0026`.
The image was checked for implicit volumes and declared none. Containers used
`--pull=never`, no network, read-only roots, all capabilities dropped,
no-new-privileges, a 32-process limit, and unprivileged synthetic test identities.
There were no host-data, model or deployed-volume mounts. No packages or images
were downloaded, no builds ran, and no inference or private-audio inspection occurred.

## Exact storage configuration tested

The single Docker volume used the built-in `local` driver with:

```text
type=tmpfs
device=tmpfs
o=rw,nosuid,nodev,noexec,noswap,size=4m,nr_inodes=128,mode=0700,uid=10001,gid=10001
```

Containers mounted that volume at `/probe` with `volume-nocopy`. The owner was
UID/GID 10001; the permission-negative test used UID/GID 10002. These are synthetic
identities, not a proposed change to the deployed Whisper user.

The previous Docker `--tmpfs ... noswap` rejection did not recur through this
local-driver route. Success was established by actual container startup and
inspection inside the mounted namespace, not merely by successful volume creation.

## Verified behavior

| Requested check | Observed result |
| --- | --- |
| 1. Local driver accepts noswap | Volume creation and mounted-container startup succeeded with the exact options above. |
| 2. Actual mount type | The exact `/probe` mountinfo entry reported `tmpfs`; `stat -f` independently reported `tmpfs`. |
| 3. Effective noswap setting | Kernel mountinfo reported `noswap` among the actual tmpfs superblock options. This verifies the kernel accepted and reports the no-swap setting; no host swap-pressure test was performed. |
| 4. Restricted permissions | Actual ownership was 10001:10001 and mode 0700. A container using identity 10002 could neither read the marker nor create a file. Privileged host administrators are outside that access restriction. |
| 5. Container usability | The owner wrote and read a synthetic marker successfully. |
| 6. Enforced size bound | Writing an 8 MiB zero-filled file hit ENOSPC at a 4 MiB filesystem capacity. The fill file reached 4,190,208 bytes; the existing marker occupied the other page. `df` reported 4,194,304 bytes total and zero available. The fill file was then removed. The configured inode limit was not separately exhausted. |
| 7. Process failure | An exec child wrote a synthetic marker and killed itself with SIGKILL, returning 137. Its named file remained while the container and mount stayed alive. |
| 8. Container removal | The first container was killed with SIGKILL, returned 137 and was removed. With a second consumer still attached, both markers remained readable. After the last consumer was killed and removed, a new container mounting the same volume found both markers absent. This establishes the tested last-consumer unmount/remount behavior. |
| 9. Safe destruction | Every test container was removed after exact identity checks. The sole volume was removed after checking its exact name, experiment label, local driver and full option set. Subsequent inspect calls confirmed absence; experiment-label inventories found no remaining containers or volumes. |
| 10. Fail-closed behavior | A temporary launch check accepted the valid mount, but rejected a missing mount, an existing proc filesystem supplied as the target, and a correctly mounted target with the wrong owner. Each rejection exited 78 before the synthetic work-start marker. |

The temporary launch check examined the exact mountpoint, tmpfs type and
`noswap` option in mountinfo, and required owner identity and mode 0700. It was a
probe harness, not a shipped Whisper startup guard. A complete operational guard
must additionally enforce the selected size/inode bounds, mount flags, swap/core
policy and fixed temp path. Only the tested rejection cases are claimed here.

## Swap and core-dump metadata

| Boundary | Evidence | Limit of conclusion |
| --- | --- | --- |
| Test-container memory | Docker memory and memory-plus-swap settings were each 134,217,728 bytes; effective cgroup `memory.max` was 134217728 and `memory.swap.max` was 0. | Container swap prohibition was verified as an effective control value; this was not a pressure or forensic swap experiment. |
| Test-container core limit | Docker specified core soft/hard limits of 0; `/proc/self/limits` also reported 0/0. | These limits alone do not prove that the host's piped core collector cannot persist process data. No core-generating crash was induced. |
| Host core exposure | The test namespace saw a core pattern piped to systemd-coredump. | Effective collection suppression was not established. No host settings were modified. |
| Existing Whisper metadata | Memory and memory-plus-swap settings remain 0/unset, with no explicit Docker ulimits. Container ID, image and start time matched before and after the experiment. | The probe's hardened limits were not applied to Whisper; prior recovery findings about its effective unlimited swap/core exposure remain unresolved. |

The prior investigation established active host swap. This experiment neither
changed swap nor re-audited it. It made no changes to hibernation or coredump
settings. Hibernation/crash-dump persistence, swap encryption and effective core
collection policy are not accepted by this result.

## Storage privacy versus immediate reclamation

The accepted `noswap` tmpfs setting prevents this filesystem from using swap;
process buffers require their own effective swap prohibition. Neither control
is a proof against core collection, hibernation, privileged copying or all other
persistence paths.

**Volatile storage is not immediate cleanup.** The SIGKILL tests demonstrated that
named files survive process death and can survive container removal while another
consumer holds the mount. The final-consumer remount test found no old marker
files, but does not justify assuming every possible mount lifecycle has ended.
Repeated conversion failures could fill the bounded RAM filesystem before teardown.
SIGKILL executes no application cleanup handler.

For the proposed design, immediate per-request file reclamation still requires
the `O_TMPFILE` draft or an equivalent anonymous/unlinked-file descriptor design,
with correct final descriptor closure and child termination. Merely selecting
this mount cannot supply that behavior. This experiment did not test O_TMPFILE,
ffmpeg descriptor handling, C++ exception paths or A3 format compatibility.

The three draft files on `integration/stt1a-whisper-privacy` remain uncommitted
and byte-for-byte unchanged, verified by SHA256 before and after the probe.
There is no source derivative, compatible server-build acceptance or deployment
claim in this result.

## Smallest next implementation step

Prepare a reviewable configuration-only Whisper storage proposal in a separate
isolated worktree, leaving the existing draft untouched. Reuse the tested
local-driver tmpfs mechanism at a fixed private audio path, select validated
ownership and operational capacity, explicitly set existing `--tmp-dir`, and
add a fail-closed launch check. Include effective process swap protection and an
explicit unresolved gate for core/hibernation policy.

Keep the exact image/model, CPU settings, `/inference`, existing `--convert`, A3
multipart interface and WebUI TTS. Do not infer that the probe's 4 MiB storage or
128 MiB process limit is suitable for a real model workload, or that Whisper has
been validated under the synthetic non-root identity. No C++ rebuild is needed
for the storage mechanism itself. If immediate per-request reclamation is
mandatory, select and validate the preserved anonymous-file path instead, including
its compatible offline build prerequisites.

Later synthetic conversion/failure/A3 checks and any shared-service activation
require their own scoped authorization. No deployment is recommended on storage
evidence alone.

## Cleanup, harness correction and publication

An initial preflight stopped before creating any Docker resource because its
absence-message assertion expected different capitalization. The assertion was
corrected to compare case-insensitively. A subsequent complete run produced the
passing evidence above. The initial run is not counted as a failed mount probe.

Cleanup used only exact IDs and experiment labels recorded for this run; it
verified image, no-network/read-only settings and allowed mounts before container
removal. No unrelated Docker volume was touched and no prune was used. All seven
test containers and the single temporary volume were confirmed absent. Only
local synthetic probe scripts/evidence remain outside Git as investigation artifacts.

Lab remained clean at the stated baseline. No existing service was restarted;
Production, Demo, Whisper, Lab WebUI, Kokoro, Hindsight, Memory Arena and canonical
data were not modified. The original draft was preserved. Only this sanitized
report and the chronological multimodal index are committed and pushed to
`reports/web-validation`; no implementation branch is pushed.

The publication omits raw terminal transcripts, private data, startup prompts,
credentials and unnecessary host/account details. It preserves measured bounds,
negative results, cleanup evidence and the limits of the privacy conclusion.
