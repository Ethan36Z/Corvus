# Lab activation candidate — rolled back

This backend-only candidate is **not approved for reactivation**. The first live
public synthetic transcription returned HTTP 503. The original Lab WebUI image,
environment, host network and existing data volume were restored; only the new
owned STT services/networks were removed. R7 frontend artifacts were reused.

## Verified blocker

The independent bridge credential is a regular 64-byte hexadecimal file, owned by
UID 10001 with mode 0400. This works for the bridge's UID 10001. Existing Lab WebUI
runs as UID 0 with all capabilities dropped. UID 0 cannot read another UID's 0400
file without DAC override. A network-disabled check of the actual derivative
WebUI image and existing capability policy reproduced PermissionError and the
sanitized service_token() HTTP 503. Unit tests and the bridge-image tests passed
but did not exercise this WebUI filesystem identity. No successful transcription
or mounted-browser dictation acceptance occurred. No legacy fallback was added.

Do not add DAC override, make the credential world-readable, change the WebUI
runtime UID against its existing volume, or bypass the strict secret validator.
The next candidate should distribute the same independent credential through
separate read-only files with each consumer's existing owner (WebUI UID 0 and
bridge UID 10001), validate each fixed owner/mode, and test both actual images
under their deployed users and dropped capabilities. This requires review and a
new controlled activation, not an unreported retry.

## Candidate files and controls

- `prepare.py` pins the R7 audio source and creates backend-only derivative image
  contexts. The only native route change selects `webui_active.py`; native
  verified-user authentication and all other audio handlers are retained.
- `app/stt_active.py` supplies the R1/R6 transcriber to the existing bounded,
  authenticated bridge; it never starts canonical chat.
- `app/stt_protocol.py` supplies fixed-path, strict secret checks and a shared
  fail-closed admission marker. No credential value is stored in Git.
- `compose.yml` appends to the existing Lab stack, R6 private and R7 package
  overlays. It preserves the fixed loopback bridge target/private engine network.
  Native STT permission defaults false. Secret mounts are read-only and missing
  files cannot be silently created.

The operator-owned marker must contain exactly `open\n` to admit requests in both
wrappers. Missing/malformed/closed marker rejects before body/provider work.
The marker is bind-mounted as a file: update its existing inode with a bounded
write and fsync; do not replace the inode. Closing it stops new admissions, not
already executing synchronous inference. It is not a credential or a substitute
for native/bridge authentication.

## Protected recovery and rollback

Backup/configuration/credential material belongs outside Git in a protected
operator-owned directory. Preserve the original immutable WebUI image, environment
snapshot, exact five-file Compose stack, sole existing data volume and consistent
volume archive. Check integrity and permissions before any recreation.

On acceptance failure, close admission, restore only Lab WebUI from the retained
original stack/image with native STT disabled and the same volume, then stop/remove
only exact recorded new container IDs after image/owner/project/service checks.
Remove only owned empty STT networks after identity/membership checks. Do not use
project-wide up/down, volume removal or prune. Verify native auth, HTTPS health,
TTS, Pipe and Arena technical configuration plus unchanged A3/Kokoro identities.
The rollback executed for this candidate; there is no active STT endpoint now.

## Scope and remaining risks

This delivery targets application-level no conversion files, no persistent
recording cache, no content logs, fixed authenticated routing, bounds and scoped
failure. It does not solve host/client swap, crash/core dumps, hibernation,
browser decoder allocation/persistence, synchronous worker cancellation, or
legacy A3 converter retention. No target-device acceptance is claimed.
