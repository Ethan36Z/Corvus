# Lab activation, credential repair and controlled acceptance

The original uncorrected candidate must not be reactivated. The first live
public synthetic transcription returned HTTP 503. The original Lab WebUI image,
environment, host network and existing data volume were restored; only the new
owned STT services/networks were removed. R7 frontend artifacts were reused.
The credential repair and separately authorized Retry 3 acceptance are described
below; historical failure instructions are not a statement of current runtime.

## Credential repair (offline only)

The original failed attempt below remains historical evidence. This worktree
repairs credential distribution without rebuilding or deleting either candidate
image. It has not been deployed and requires a new activation authorization.

Use the exact images pinned by `credential_repair.py`. The bridge keeps its
original UID-10001 validator. `webui_protocol()` verifies the shared module's
exact source SHA and changes only `metadata.st_uid != 10001` to
`metadata.st_uid != 0`. Save the returned public source to a read-only artifact
outside Git and supply `CORVUS_STT_WEBUI_PROTOCOL_FILE`; Compose mounts it over
only the WebUI protocol module. No authentication, transport, bounds, target,
recorder, TTS, Pipe or Arena logic changes. Recheck this artifact against the
pinned generator before any later recreation; a read-only mount protects the
container side, not an operator editing the host source.

`distribute()` copies the existing independent credential (no rotation) inside a
network-disabled provisioning helper. Mount only the existing credential read-only,
the repair source read-only and a new empty mode-0700 output directory writable.
Run the helper as root with only the temporary DAC_OVERRIDE/CHOWN/FOWNER capabilities
needed for copying across owners. Those capabilities are never assigned to either
consumer. Its output has separate `webui/credential` (UID/GID 0, 0400) and
`bridge/credential` (UID/GID 10001, 0400), each within a matching-owner 0700 directory,
under the existing protected operator directory. It verifies both copies equal
in memory without printing or hashing them. Do not overwrite the old secret,
backups or output files; preserve source and output paths outside Git.

Supply the respective files using `CORVUS_STT_WEBUI_SECRET_FILE` and
`CORVUS_STT_BRIDGE_SECRET_FILE`. The old shared `CORVUS_STT_SECRET_FILE` is no
longer used by this overlay. Mounts remain read-only, fixed container paths,
with missing-source creation disabled. Secret validators still require a regular
64-byte lowercase-hex file at the fixed no-symlink path and exact owner/0400 mode.
The private module/Compose patches do not enable admissions or permission.

Validation must use these exact images under their existing UIDs and dropped
capabilities. Use only an isolated network-disabled namespace and synthetic WAV,
with the existing R1 upstream opener mocked. Test both admission states, correct
and incorrect bridge authentication, missing and opposite-owner unreadable
credentials. Never mount Lab data or contact live Whisper. Actual isolated tests
passed for this repair; see the separate sanitized credential-repair report.

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

## Retry 3 live acceptance and Mac handoff

`live_acceptance.py` preserves the previous operational acceptance script and
fixed native target. It imports the existing protected operational runner from
`CORVUS_STT_OPERATIONS_DIR` (default `/tmp/corvus-stt-retry3`); no credentials or
real private configuration are placed in this source tree. It is an operator
script, not a new deployed service or endpoint.

Mixed-language successful text gets a quality classification. A keyword miss
alone does not throw a system exception: known public equivalent renderings are
ACCEPTED, demonstrably unrelated public outro text is QUALITY_FAIL, and unresolved
meaning is QUALITY_REVIEW_REQUIRED. Only status/reason/concept flags are retained,
never raw transcript. Primary-language checks and all protocol/auth/storage/resource
hard gates remain. SYSTEM_FAILURE closes admission and invokes scoped rollback.

The existing script also completes the previously unrun live provider-unavailable,
provider-deadline and client-cancellation/admission-recovery checks. Fault injection
is restricted to the exact owned new engine ID. A client cancellation is not
represented as synchronous engine/thread termination. Invalid credential/audio
probes cannot run inference. No canonical chat is submitted.

Once deployment hard gates pass, keep the two STT services and admission running
for Mac user acceptance. Pending browser/device acceptance is not a rollback
condition. Use the Lab HTTPS origin, legitimate Lab FoxGate login followed by the
independent WebUI login, and the existing recorder/composer. Only the user can
confirm real microphone, editable review and manual Send acceptance. Never collect
passwords/tokens or claim STT_LAB_USER_ACCEPTED before that user confirmation.

The pinned `/api/config` endpoint authenticates from the native `token` cookie;
Bearer alone returns the public configuration without audio/permission fields.
`native_config()` uses the existing protected short-lived acceptance token only
for that native cookie and emits booleans. It never prints the response or token.
This fixes the operational checker mismatch; it does not change WebUI auth.
