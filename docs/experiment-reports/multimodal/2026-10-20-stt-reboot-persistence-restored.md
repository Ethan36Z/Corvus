# STT — reboot persistence restoration completed

Date: 2026-10-20.

**STT_REBOOT_REPAIR_RESTORED**. Continue the [original repair/root handoff](2026-10-20-stt-reboot-persistence-repair.md). The operator completed the protected copy of the original service credential. The assistant independently checked both consumer mounts, restored only Lab WebUI and STT Bridge, and completed one authenticated public synthetic STT request. Vision remained untouched.

## Actual runtime

| Component | Final container ID | Existing image ID | Result |
| --- | --- | --- | --- |
| Lab WebUI | `b329488eff5c158ac2cea25515fb5945806f9ac10c17b0188e80010766ede204` | `sha256:4b0451913d93774af57defe40873f29323239ef83ed7dfd8f405abe7b4f7ad17` | running; healthy; `unless-stopped` |
| STT Bridge | `7eb33a6ca8f0e5e6f22fe0244f3e4f0d63c73fc02a1cad474306ba1897e4480c` | `sha256:5d3cd6aff2db1a9712ce98669942d093858640298e9c04903f3cee3b510dc6b2` | running; live request verified; `unless-stopped` |
| Private Whisper | `2ff3bcc648fde90aa61a3f5a63b8a64ec11188afcde6c127a5f7ece43602cf07` | `sha256:caf0cd77c922e9c53f10a9bc17c2f74cc2295d12e7b0f96b630fb3b3c55a0026` | running; healthy; `unless-stopped` |

WebUI and Bridge were recreated with the same pinned images and runtime settings. Whisper received only an existing-Docker restart-policy update; its container ID, process start time, image, model, security and resource limits were preserved. All unrelated container identities/start times remained unchanged. No image build, pull, dependency/model install, Linux reboot, database restore, volume deletion, Docker prune or implementation push occurred.

## Persistent material and boot configuration

All required STT host bind sources now live under `/etc/corvus-lab/stt`, outside `/tmp` and Git. The root parent is protected mode 0700. Separate consumer directories retain 0700 and exact credential ownership: WebUI UID/GID 0/0, mode 0400; Bridge UID/GID 10001/10001, mode 0400. Actual mounted credential metadata and strict reads under each exact consumer image passed with dropped capabilities and no network/model/data mounts. The original credential was copied, not rotated, and no value or digest was published.

The exact WebUI-only UID-0 validator override and unchanged admission file are also persistent, read-only mounts. Source auto-creation is disabled. Existing environment, data-volume identity, authentication, Pipe/Arena/branding, TTS configuration, bridge fixed target, networking and resources were preserved. The active original WebUI image has no Vision enable flag; existing API Vision staging was neither modified nor restarted.

WebUI, Bridge and Whisper now have actual Docker `unless-stopped` policies, also present in the surviving protected Compose packet at `/home/ethan/.config/corvus-lab/stt-runtime/compose.json` (directory 0700/files 0600). Obsolete build contexts were removed from that maintenance packet. The existing Docker service is enabled; no second supervisor or new systemd unit was added. Docker starts eligible containers from stored metadata, without the old temporary Compose paths. Deliberately stopped containers remain stopped; readiness ordering is not guaranteed and early requests may fail closed.

## Focused verification

- Original credential-repair unit contracts and syntax/public-artifact checks passed during preparation; actual-image isolated consumer reads passed during restoration. Only exact owned temporary consumer-check containers were removed.
- Local WebUI page `/` and `/health`: **HTTP 200**. Public Lab HTTPS unauthenticated request: **401**, consistent with the existing FoxGate access boundary, rather than the earlier 502. This is not authenticated Mac browser acceptance.
- Native unauthenticated transcription request: **403**.
- Exactly **one authenticated public synthetic STT request**: **HTTP 200 in 5.123 seconds**, nonempty text passing the public fixture check, response `private, no-store`. Reused the existing public TTS recovery fixture with in-memory stdlib fixture resampling only; no product converter, audio file/cache or transcript output was introduced by the verification script.
- Bridge is running and actual service authentication/dispatch succeeded; Whisper remains healthy without a process restart.
- Persistent actual mount sources, unchanged data-volume identity, expected ownership/read-only mounts and all three runtime restart policies verified. No canonical conversation was sent or old database snapshot restored.

The verifier initially hit a local HTTP-client namespace collision before any recognition request was sent. That verifier-only defect was corrected and locally committed; the one-request checkpoint confirms no STT inference retry occurred. Product code and images were unchanged.

Local implementation remains unpushed: initial repair `3b93d3ae0b60fad4c96bb9afae8243a84ee81d4d`, final verifier correction **`75e3cf9b2042891709fdc1fde18a1158a0767d67`**, persistent branch `fix/stt-reboot-persistent-mounts`. Private runtime configuration and original/provisioned credentials stay outside Git. Existing backups and earlier worktree records remain intact.

No actual reboot was performed, so this verifies persistent startup prerequisites and present live behavior, not a demonstrated reboot. The previous pinned-Whisper exit-139 defect is not claimed solved by restart policy. Existing host/client swap, dumps and other privacy limitations are unchanged. Mac microphone use can now be retried through the usual FoxGate → WebUI login at `https://lab-corvus.foxluma.com`; no new user acceptance is claimed.

Restoration complete. Stop; no further inference, deployment or service restart.
