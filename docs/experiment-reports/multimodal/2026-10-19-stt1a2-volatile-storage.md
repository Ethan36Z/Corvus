# STT-1a.2 — Volatile conversion-storage candidate and offline gate

Experiment: **STT-1a.2**

Date: **2026-10-19**

Verdict: **STT1A2_BLOCKED**

Reviewed Lab baseline: `4f8013af2c8e73774fcef91c2510e5808c1fd2c2`

## Decision

A small configuration-only storage candidate and offline regression suite were
prepared in a separate worktree. **Twenty-three focused checks passed**, but the
mandatory privacy requirements and evidence-backed operational sizing are not
satisfied. The launcher deliberately cannot start Whisper at this checkpoint.
There is no configuration-ready verdict, implementation commit or deployment.

The [STT-1a.1 noswap probe](2026-10-19-stt1a-noswap-storage-probe.md) was read first.
Its mount/lifecycle findings are reused; the broad investigation and SIGKILL
lifecycle experiment were not repeated. The [recovery feasibility report](2026-10-19-stt1a-recovery-feasibility.md)
remains the prerequisite reference.

## Exact implementation scope and Git state

New local branch: `integration/stt1a2-volatile-storage`.

New isolated worktree: `/tmp/corvus-stt1a2-integration`.

Branch HEAD remains the reviewed baseline above. **Local implementation commit:
none**, following the blocked-workflow instruction to preserve work. These six
new files are retained uncommitted under `deploy/whisper/volatile/`:

| File | Prepared behavior |
| --- | --- |
| `compose.yaml` | Standalone, pinned existing image; local-driver private noswap tmpfs; required byte/inode/memory budgets; equal memory and memory-plus-swap limits; read-only root; no image pull/build; core limits zero; fixed loopback endpoint and read-only existing model bind proposal. |
| `guard.sh` | Verify exact real tmpfs mount/root, noswap and mount flags, owner/mode, capacity/inode counts, empty-mount counters, fixed TMPDIR, readonly root and effective cgroup-v2 memory/swap controls. |
| `start.sh` | Run storage checks before any server start; reject extra arguments and the unresolved piped core collector; retain an unconditional final privacy block with no environment bypass. Intended server command is unreachable and present for review only. |
| `README.md` | Resource evidence/formula, privacy blockers, failure/lifecycle evaluation and scoped future recovery/rollback procedure. |
| `tests/offline.py` | Synthetic, isolated Docker regression runner with exact-identity cleanup and no model/server launch. |
| `tests/a3_contract.py` | Execute only the existing A3 transcription contract with isolated synthetic storage and denied network/subprocess/deployed-home access. |

The image is pinned to
`sha256:caf0cd77c922e9c53f10a9bc17c2f74cc2295d12e7b0f96b630fb3b3c55a0026`.
No Whisper.cpp source was edited or compiled. The intended command retains
`/models/ggml-small.bin`, eight threads, automatic language, CPU-only `--no-gpu`,
`--convert`, port 8080 inside the container, loopback host port 8104 and the
unchanged upstream `/inference` default. It adds only the fixed private
`--tmp-dir /run/corvus-audio`. The reviewed existing startup prompt must be
provided unchanged; it is not copied into this report or new configuration.
The image's existing root user is preserved instead of assuming non-root model
compatibility. WebUI, TTS and Kokoro are outside the change.

The older branch `integration/stt1a-whisper-privacy` remains at its prior baseline
with its three uncommitted draft files byte-for-byte unchanged; SHA256 checks
matched before and after this task. That C++ draft was not executed.

## Storage configuration and fail-closed boundary

The proposed dedicated volume uses Docker's existing local driver with
`type=tmpfs`, `device=tmpfs` and:

```text
rw,nosuid,nodev,noexec,noswap,size=<required bytes>,nr_inodes=<required count>,mode=0700,uid=0,gid=0
```

It is mounted exclusively at the fixed private audio path with `volume-nocopy`.
The root filesystem is read-only, and TMPDIR matches the explicit server temp
path. The guard rejects alternate temp arguments, symlinks/different resolved
paths, non-root ownership, wrong permissions, wrong filesystem/mount root,
missing noswap/required mount flags, mismatched actual byte/inode bounds, and
retained files detected through free-block/inode counters. It does not enumerate
or read recording filenames/content and does not silently purge retained files.

The guard requires the tested root cgroup-v2 namespace layout, matching finite
`memory.max`, `memory.swap.max=0` and `memory.swap.current=0`. Unsupported layouts
are rejected rather than guessed. Process-memory protection complements the
filesystem's noswap setting; one does not substitute for the other.

The launcher sets/checks core limit zero and rejects the host's piped collector.
An additional unconditional block preserves the unresolved cleanup and host
hibernation/crash-dump gates. This is a blocked candidate, not a usable activation
override. Removing the block or supplying arbitrary budget values is not an
accepted privacy fix.

## Operational resource evidence — blocker, not invented defaults

No operational defaults were selected. Compose requires explicit audio bytes,
inodes and process-memory budgets and rejects missing values. The regression
suite's **8 MiB / 256 inodes / 64 MiB process-memory** settings are synthetic test
limits only. They are not suitable model-workload recommendations, and neither
are the earlier probe's 4 MiB / 128 MiB settings.

The exact public server source serializes conversion inside the inference mutex,
but waiting HTTP uploads may already occupy memory. Input and converted output
coexist. Its existing 16 kHz, signed 16-bit conversion uses 32,000 payload bytes
per second for mono or 64,000 for stereo, plus measured WAV/container overhead.
The existing attachment helper accepts an optional max_bytes value defaulting
to None. This review did not establish an enforced service-wide decoded-duration
or waiting-upload bound. No new format/admission restriction was silently added.

For admitted input B, decoded duration D, channel count C and retained-failure
budget F, a planning lower bound is page-rounded
`(F+1) * (B + 16000*2*C*D + measured_WAV_overhead) + metadata/page_reserve`.
Inodes need at least two per active/retained conversion plus root/metadata
reserve. A finite F requires enforced recovery/admission; repeated failures in
the unchanged server otherwise have no finite steady-state accumulation bound.
Compressed upload size alone does not bound decoded PCM duration adequately.

The process-memory budget needs measured model/runtime peak, bounded waiting
uploads/PCM/ffmpeg/tmpfs and justified headroom. No model loading or inference
was authorized, so that measurement is absent. Configuration cannot derive a
safe operational number from the tiny synthetic probe or host RAM alone.
Operational sizing therefore remains explicitly blocked.

## Offline validation actually performed

The final suite completed **23 focused checks**:

| Group | Results |
| --- | --- |
| Syntax/configuration (3) | Shell syntax; Compose rendering and intended baseline command/endpoint contract; missing operational budgets rejected. Compose memory strings are compared numerically. Rendering does not mount or start the proposed service. |
| Guard recognition/rejection (14) | Correct mount accepted; missing mount, persistent wrong filesystem, ordinary swappable tmpfs, wrong mode, wrong execution identity, byte mismatch, inode mismatch, alternate TMPDIR, memory mismatch, effective swap allowed, invalid numeric budget, dirty mount and extra arguments rejected. |
| Capacity/fallback (3) | Synthetic zero-filled write hit the exact 8,388,608-byte bound; inode exhaustion occurred at 255 files plus root for 256 total; writing a synthetic fallback under read-only `/app` failed. |
| Launcher (2) | Missing storage rejected; correct storage still refused server startup under the unresolved privacy gate. Both returned 78; no Whisper process started. |
| Existing A3 contract (1) | Original transcription adapter executable passed with a mocked HTTP opener and temporary synthetic attachment/database state; transcript provenance and non-audio rejection passed. No live HTTP inference or deployed canonical access. |

The owner/mode/root guards and kernel/statfs/cgroup checks ran in actual isolated
containers, not only mocked mountinfo. The configured effective no-swap controls
were verified by the positive guard and the swap-allowed negative case. No swap
pressure test, forensic persistence test or core-generating crash was performed.
No full real-model API or ffmpeg conversion compatibility acceptance is claimed.

An initial pre-resource test assertion was corrected for Compose's string-valued
memory serialization. A complete 22-check run then passed. Adding dirty-mount
rejection justified one final complete run, which passed the 23 checks above.
Both completed runs verified cleanup; the final suite used 19 containers and two
uniquely labeled temporary tmpfs volumes. All used the existing local image,
`--pull=never`, no network, read-only roots, dropped capabilities, no model and
no deployed-data mounts. Cleanup checked exact IDs/labels/image/mount identities
before removing only owned resources and confirmed no experiment resources remain.
No Docker prune, existing-volume change or deployed service restart occurred.

## Remaining mandatory privacy limitations

- **Immediate failure cleanup is unsatisfied.** Named recordings can remain after
  conversion failures or process death. Noswap changes their backing, not their
  lifetime. SIGKILL executes no cleanup. The guard refuses a dirty startup but
  does not reclaim files after each failed request while the server stays active.
- **Exhaustion/availability remains unresolved.** Retained files fill byte or
  inode capacity. Upstream does not robustly check every upload write; ENOSPC can
  mean partial/truncated input. Read-only root and the fixed path prevent the
  proposed persistent fallback, not failed conversion or continued availability.
- **Lifecycle must remain exclusive.** Reused STT-1a.1 evidence shows files survive
  with a second consumer and disappear after tested last-consumer teardown/remount.
  This is not a guarantee of cleanup on every process/container transition.
- **Core-dump safety is not demonstrated.** Zero limits alone do not establish
  suppression under the piped host collector. The launcher refuses it; no host
  collection setting was changed or crash tested.
- **Hibernation/kernel crash-dump safety is not demonstrated.** Those paths may
  capture RAM independently of container swap limits. The final block is retained.
- Existing filename/ffmpeg diagnostics remain unchanged. This is not a complete
  logging privacy fix. O_TMPFILE or equivalent still needs descriptor/child,
  exception and compatibility validation for the stronger cleanup requirement.

**Full Whisper cleanup requirements are not satisfied.** Configuration-only
storage isolation is technically useful but cannot be substituted for that
mandatory requirement or represented as privacy acceptance.

## Recovery boundary and next smallest required action

No runtime rollback is needed because no deployment occurred. The local README
contains a scoped future procedure: retain original owning configuration before
any separately authorized activation; stop admissions before recovery; verify
exact container/volume ownership and exclusive mount consumers; use normal owned
container teardown and verify empty remount before resuming. Stop on uncertain
identity/unmount. Do not inspect historical recordings, prune, use blanket volume
removal or claim the original persistent-storage configuration is privacy-safe.

The next smallest required action is a separately authorized completion/review
of the preserved anonymous-file conversion fix and compatible offline build
plan, because configuration alone cannot meet mandatory failure cleanup. Define
an enforced input/duration/retention/admission contract and obtain model-memory
evidence before selecting operational budgets. Host dump/hibernation policy also
needs a demonstrated boundary or an explicit separate privacy decision; this task
changes none of it. Do not resume WebUI dictation or deploy this candidate.

## Publication and preservation

Only this sanitized report and the multimodal index are published on
`reports/web-validation`. No implementation branch is pushed. New work remains
uncommitted in its isolated worktree; the earlier three-file draft is preserved.
Lab remains clean at the reviewed baseline. Production, Demo, Lab WebUI, Kokoro,
Hindsight, Memory Arena and canonical data were not modified. No source rebuild,
model download or live inference occurred.

Raw terminal transcripts, prompt contents, credentials, private recordings,
conversations and unnecessary host/account details are excluded. The published
result distinguishes passing offline guard checks from the explicitly blocked
operational/privacy verdict.
