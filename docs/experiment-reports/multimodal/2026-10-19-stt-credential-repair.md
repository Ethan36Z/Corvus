# STT credential permission repair — offline only

Date: 2026-10-19.

Verdict: **STT_CREDENTIAL_FIX_READY**

The confirmed UID/credential mismatch is repaired and validated using the exact
existing candidate images. No image was rebuilt, downloaded or deleted. **No
second activation occurred:** active Lab was not restarted/recreated, its native
STT permission remains false, and no live STT service or admission was enabled.

## Baseline and exact repair

Read the complete [controlled activation and rollback report](2026-10-19-stt-lab-activation.md).
The isolated repair worktree starts from preserved blocked local commit
`6dfc5225574fc28073917546f3f07d4b364cb958`. Earlier STT worktrees, uncommitted drafts,
backups and original credential are preserved.

Local-only repair commit: **`6a2a5eb1bab2c4c107dc34b60e2919071795bec1`**, branch
`integration/stt-credential-repair`. No implementation branch was pushed.

Root cause was not reinvestigated: WebUI UID 0 with zero capabilities cannot read
a UID-10001-owned 0400 credential. The existing validator also explicitly requires
UID 10001, so changing the file owner alone would still fail validation.

The existing independent 256-bit credential was reused without rotation, printing,
logging, publishing a credential hash or committing its contents. Two separate
read-only consumer files now hold the same value:

| Consumer | File UID/GID | File mode | Consumer directory |
| --- | --- | --- | --- |
| WebUI | 0/0 | 0400 | UID/GID 0/0, mode 0700 |
| Bridge | 10001/10001 | 0400 | UID/GID 10001/10001, mode 0700 |

The copies remain under a protected operator-owned mode-0700 parent outside Git.
Equality against each other and the original was checked privately in memory.
Original credential metadata was unchanged; source was mounted read-only.
Distribution uses exclusive file creation, no-follow opens, exact metadata/format
checks and fresh protected directories. Existing outputs are not overwritten.

Pure mount changes cannot satisfy the hard-coded WebUI owner check. To avoid an
image rebuild, `webui_protocol()` verifies the pinned existing shared module
source and generates a WebUI-only artifact changing exactly
`metadata.st_uid != 10001` to `metadata.st_uid != 0`. AST comparison proves this
is the sole semantic change. The source pin was also checked against the public
module in the exact existing WebUI image. Compose mounts this artifact read-only
over the WebUI protocol module. Bridge source/image validation remains UID 10001.
There is no new STT abstraction, auth bypass or modified transport behavior.

Both secret targets remain fixed `/run/secrets/corvus_stt_bridge`; separate host
sources use `CORVUS_STT_WEBUI_SECRET_FILE` and `CORVUS_STT_BRIDGE_SECRET_FILE`.
`CORVUS_STT_WEBUI_PROTOCOL_FILE` supplies the pinned public module artifact.
Bind mounts remain read-only with missing-source creation disabled. Credential
checks retain fixed no-symlink paths, exact owner, regular file, 0400 mode,
64-byte length and lowercase hexadecimal format. No permissions were broadened.

Credential copying used one network-disabled provisioning helper with only the
temporary DAC_OVERRIDE/CHOWN/FOWNER capabilities needed for cross-owner copying;
these were never added to WebUI or bridge. A separate read-only private audit
helper used DAC_OVERRIDE only to verify both protected copies. Both helpers were
identity-checked and removed. Consumer capabilities remain fully dropped.

## Exact implementation scope

Only four files changed:

- `deploy/lab/stt/activation/compose.yml` — two consumer-specific secret sources
  and the single WebUI owner-validator module mount.
- `deploy/lab/stt/activation/credential_repair.py` — pinned one-line public-module
  generation and protected copying of the existing credential; no secret output.
- `deploy/lab/stt/activation/README.md` — offline preparation, required variables,
  security boundary and separate-activation instructions; failed attempt retained
  as historical evidence.
- `tests/test_stt_credential_repair.py` — ownership/Compose checks and actual-image
  isolated consumer/authentication/dispatch/negative tests.

No edits to Whisper.cpp, R1 transport, R2–R4 architecture, recorder/composer,
WebUI UID, dropped capabilities, TTS, Pipe, Arena, active Lab configuration,
Production, Demo, legacy A3, Hindsight, Qwen or Kokoro.

## Actual-image validation

No build was needed. Tests used these exact retained images:

| Consumer | Image ID |
| --- | --- |
| WebUI | `sha256:88330ac2e1aa941386d8d2aaff5640f77d7343557969b74452798a6968bc60de` |
| Bridge | `sha256:5d3cd6aff2db1a9712ce98669942d093858640298e9c04903f3cee3b510dc6b2` |

WebUI ran UID/GID 0/0; bridge ran UID/GID 10001/10001. Actual effective capability
masks were zero and no-new-privileges was 1. Both used read-only credential mounts,
no access/Docker logging, no Lab data/model mounts and no published ports.
Bridge retained read-only root, one CPU, 256 MiB/equal memory-plus-swap, bounded
PIDs, core limit zero and one worker/request admission. The WebUI helper used a
read-only root and test resource/core bounds without changing the active WebUI.

The bridge ran only in a network-disabled test namespace. WebUI test helpers
shared that isolated namespace to exercise the unchanged fixed loopback bridge
URL; no named network or active Lab network was used. Its port existed only
inside this namespace, with no host binding. The R1 upstream opener was mocked
before dispatch; synthetic finite PCM16 WAV was the only audio. No Whisper engine
was started, model mounted or live inference called.

| Check | Observed result |
| --- | --- |
| Assigned WebUI credential under UID 0/capabilities dropped | Read and strict owner-0 validation passed |
| Assigned bridge credential under UID 10001/security constraints | Read and actual app credential initialization passed |
| CLOSED admission | Native authenticated and bridge requests returned intended 503 disabled response |
| OPEN admission | Native handler → existing fixed bridge client → authenticated bridge → R1 multipart/mock upstream returned expected public synthetic Chinese/English text |
| Correct service credential | Actual bridge HMAC authentication and HTTP dispatch passed |
| Invalid/missing service authentication | HTTP 401 |
| Native unauthenticated request | HTTP 403 in extracted exact native handler with synthetic verified-user dependency |
| Missing credential, either consumer | Sanitized 503; bridge app initialization refused |
| Opposite-owner unreadable credential, either consumer | Sanitized 503 with zero capabilities; bridge initialization refused |
| Canonical writes | SQLite access guarded to fail during isolated dispatch; zero accesses; existing no-persistence regression guards passed |
| Private equality/metadata audit | Both copies equal original; exact file/directory ownership/modes passed |
| Secret leakage | Actual credential bytes absent from all six captured consumer logs and complete candidate diff; only boolean metadata printed, no credential digest published |

There were six isolated case results (closed/open WebUI and four missing/unreadable
consumer cases), with the valid bridge initialized throughout. Seven consumer
containers plus provisioning/audit helpers were removed after exact-ID/image/label
checks. Test admission was returned closed. Protected credential copies, public
validator artifact and private test evidence remain outside Git for a later
review; no active configuration points to them.

Native authentication here uses a synthetic dependency around the exact image's
native handler/signature to avoid starting WebUI/database or issuing real user
tokens. Real service authentication between containers is exercised. This is not
fresh live JWT, mounted-page or target-device acceptance.

Additional checks:

- Eight activation/repair unit tests passed (six existing plus two repair tests).
- All **62** existing STT/TTS/Pipe/Arena offline regression tests passed. An initial
  sandboxed run stalled and only its identified test process was stopped; the same
  mocked suite completed outside the restricted sandbox in 15.754 seconds under
  a two-minute deadline. No service was stopped.
- Merged old/repaired Compose comparison proved only the two credential sources
  and one WebUI protocol bind differ. All other service/network configuration,
  native authentication, TTS/Pipe/Arena settings and false STT permission matched.
- `git diff --check` passed; implementation scope is the four files listed above.

## Preservation and activation boundary

Before/after Docker identity/image/start/network snapshots matched for active Lab
WebUI, legacy A3 Whisper and Kokoro. Lab stayed healthy on its restored original
image with native STT permission false. No STT services started on an active Lab
network; no host port was published. All owned test/provisioning/audit helpers
were absent at completion; no Docker prune, service recreation/restart or image
removal occurred. Nine earlier STT worktrees retain their recorded HEAD/status and
draft hashes; R7, the preserved blocked activation candidate and active Lab Git
worktrees remain clean. Existing backups were not modified.

The narrow credential blocker is resolved offline. A second controlled activation
still requires separate authorization and fresh drift/backup checks. Its runner
must use the two new secret variables plus the validated module artifact; the
old shared-secret variable/old one-off runner is insufficient. Keep the existing
consumer UIDs/capabilities, fixed service targets, no legacy fallback and closed
admission until the authorized activation gates are satisfied. Revalidate the
host artifact against its source pin before recreation; a read-only container
mount does not protect against operator modification on the host.

Live Chinese/English/mixed accuracy, bounds/provider-fault/cancellation/privacy,
resource observations and authenticated mounted native composer/manual-send/TTS/
Pipe/Arena acceptance remain uncompleted from the rollback. External HTTPS
previously returned Cloudflare 401 to this host; no external browser authentication
or target-device acceptance is claimed. Mac Safari and iPhone Safari remain
pending. Host/client swap/dumps, hibernation, decoder allocations/persistence,
synchronous worker cancellation and legacy A3 converter retention remain as
previously documented risks, not solved by this credential repair.

Only this sanitized report and the multimodal index are published to
`reports/web-validation`. No credential, credential hash, private audio,
conversation, backup or content-bearing log is included. Stop here: no deployment.
