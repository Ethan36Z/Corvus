# STT-R7 — Final offline Lab integration preflight

Date: 2026-10-19 checkpoint; completed by resuming the preserved worktree/artifacts.

Verdict: **STT_R7_READY_FOR_LAB_DEPLOYMENT**

**Ready means the pinned, disabled Lab package is prepared. No deployment,
existing-service restart, active configuration change or live-gate enablement
occurred. It is not live dictation or target-device acceptance.**

## Baseline, continuity and implementation

Continue from local R6 `c0b818fa2c72a4eeb6f8691f5e25f06eea8b87e1` and its
[activation checklist](2026-10-19-stt-r6-private-whisper.md). R1–R6 decisions,
contracts, resource measurements and residual risks are reused. No alternative
architecture, new STT engine, microphone UI, converter or model was introduced.

After the interruption, existing Git state, generated package, successful builds,
image/test evidence and Docker cleanup were inspected. Builds and completed broad
suites were not restarted. Only final packaging/preservation checks were repeated.

Local-only implementation commit: **`4be6907622e9f0634e5b1c327ae5054cca9200ef`**
on `integration/stt-r7-lab-preflight`, in a separate R6-based worktree.
Eight exact implementation files:

- `deploy/lab/stt/prepare_frontend.py`
- `deploy/lab/stt/webui.py`
- `deploy/lab/stt/package/prepare.py`
- `deploy/lab/stt/package/compose.yml`
- `deploy/lab/stt/package/artifacts.json`
- `deploy/lab/stt/package/rollback_plan.py`
- `deploy/lab/stt/package/README.md`
- `tests/test_stt_r7_package.py`

Nine earlier STT worktrees retain their original HEAD/status and privacy/storage
draft hashes, including the uncommitted O_TMPFILE draft. Active Lab remains clean.
Existing Lab WebUI and A3 image/start/state/network metadata match the preflight
snapshot. Production, Demo, TTS, Arena, Hindsight and canonical data were not changed.
No implementation branch or image was pushed, no downloads or Docker prune occurred.

## Exact local artifacts and preserved behavior

| Artifact | Immutable local identity |
| --- | --- |
| Current TTS-enabled WebUI parent | `sha256:72252f095805fa8aebb6ed17e7fb44c3746e9d2a289ec3ff395769aad0c44e3b` |
| Existing Node 22 builder | `sha256:35d1e2d251585b806c41f71d0933d7ba3afb6374ee3745523c2ae406480f6bc7` |
| New disabled Lab WebUI | `sha256:6a1d1843c52be7b5a1a66d503a8c16514f617d4a478ddd9dc6e09b45858487db` |
| New disabled STT bridge | `sha256:538fbebfc017b2cd628e540cb4a537aee99b7704cc637e9932f1801d1e4a997b` |
| Unchanged R6 Whisper image | `sha256:caf0cd77c922e9c53f10a9bc17c2f74cc2295d12e7b0f96b630fb3b3c55a0026` |

Both successful new images remain present locally. The WebUI derivative retains
version 0.6.5, exact current HTTPS main/TTS helper and every non-STT audio handler.
Only the native authenticated STT handler and rebuilt frontend are replaced.
Existing WebUI environment, host networking, persistent volume, installed Pipe,
TTS settings and Arena UI remain. The bridge reuses the same pinned Python runtime
and only the existing R1/R2/R6 modules and their standard-library storage definitions;
no canonical application is started and no persistence entry point is invoked.

The existing branding verifier regenerated and verified 117 original branded/Arena
files from the checksum-verified cached archive. All 989 cached dependency version
entries matched the pinned npm lock. Full frontend build used existing Node 22,
read-only cached modules and no networking/install/Pyodide fetch. Packaged public
Pyodide assets were reused. Generated contexts/proof remain isolated from active Lab.

Two concrete packaging mismatches were fixed:

1. R3's composer pin predated the current Memory A/B control. The exact reviewed
   Arena composer pin replaces it after checking the diff; drift is still rejected.
   The native microphone, Memory A/B control and existing editable composer remain.
2. Full frontend regeneration could reintroduce the TTS content-debug call removed
   from the active compiled image. The exact original ResponseMessage source gets
   that same one-call removal before rebuilding. TTS behavior is unchanged.

Dictation retains real MIME, browser-only normalization, authoritative R2 WAV
validation, native authentication, review-before-send and no auto-submit. Stored
speechAutoSend remains. No recording/transcript cache or content log is added by
the dictation path. Historical caches/logs/browser assets are not purged.

## Fixed topology and source-compatible integration

Lab WebUI currently uses host networking for its working TTS/Pipe/Corvus paths.
Docker-only bridge DNS is therefore not a usable native-route target. R7 preserves
host networking and fixes the native helper to
`http://127.0.0.1:18106/v1/transcribe`.

The authenticated bridge alone publishes 127.0.0.1:18106. It attaches to a
bridge-only ingress network and the internal `corvus-stt-dictation-private` backend.
Whisper attaches only to the internal backend, has no published port and uses
fixed /inference without --convert. The bridge retains the fixed private Whisper
DNS target and R1 as its sole multipart transport, without legacy fallback,
request-selected address, external redirect, proxy-environment use or retry.
No public Whisper or unauthenticated HTTPS transcription route is introduced.

An actual isolated test found that this host's Docker did not publish a port for
a container attached only to an internal network: it was running, with a requested
binding but no allocated host port. A bridge-only normal ingress attachment was
the minimal routing correction. This gives the bridge a normal network route;
complete egress isolation is not claimed. Application targets stay fixed and
Whisper remains internal. No shared service network was changed.

The corrected isolated test verified loopback HTTP 503 from the packaged disabled
bridge, private DNS and actual R1 multipart against a synthetic HTTP stand-in.
Backend membership was exactly bridge + stand-in; ingress membership bridge only;
no upstream host port. No model was loaded or real Whisper called. An initial
startup connection-reset was corrected to readiness retry. All temporary containers
and networks from failed and successful probes were identity-checked and removed.

## Resource/headroom and disabled gates

R6's eight CPU / 1088 MiB private Whisper budget and read-only model-file mount
remain unchanged. Its synthetic inference evidence is reused, not repeated.
Bridge budget: one CPU / 256 MiB, with equal memory-plus-swap. Its packaging tests
peaked at 158,208,000 bytes; 1.5 times that rounded to 32 MiB yields 256 MiB. A
confirmatory 19-test run under that limit peaked at 156,794,880 bytes and passed.
These are test-profile limits/margins, not worst-case speech or QoS guarantees.
Combined new limits are 1344 MiB and nine CPU quota, not resource reservations.

Read-only completion checks found 9,788,728 KiB (about 9.3 GiB) available RAM,
16 visible CPUs, load averages 0.19/0.11/0.13 and zero current memory-pressure
averages. Earlier port check found 18106 unused. Recheck immediately before
activation; simultaneous A3/TTS/speech contention and latency remain unmeasured.

Bridge has one worker, read-only root, no data mounts, dropped capabilities,
no-new-privileges, bounded PIDs, core=0, no access logs, discarded output and Docker
logging none. Whisper retains equivalent R6 constraints. WebUI candidate logging
is also disabled. Existing WebUI chat persistence is retained; dictation invokes
no canonical chat/memory/artifact/attachment APIs.

Both exported R2 live gates remain disabled, without an environment/request enable
flag. Native STT permission remains false. No real service credential was created,
read or stored in Git; Compose rendering used a deliberately synthetic value.
A separately reviewed backend-only credential/callable wiring patch is still
required for live activation. Intentional disabled gates are not represented as
a functioning live feature or as a missing package dependency.

## Focused acceptance evidence

| Check | Result |
| --- | --- |
| Full pinned Node 22 frontend build | Passed offline; no installs/downloads |
| Native recorder/composer against current Arena source | 15 tests passed; both native components compile |
| R2/R6 backend in newly built bridge runtime | 19 methods passed; repeated only to confirm 256 MiB bound |
| Built WebUI payload | Passed version, TTS/helper/main/non-STT AST, branded assets, Memory A/B and removed TTS-debug checks |
| Merged Compose and scoped rollback | Seven focused tests passed, including the resume check |
| Actual isolated routing | Private DNS/R1 multipart and loopback disabled 503 passed; no models/live gates |
| Original WebUI config preservation | Environment including TTS/Pipe, host network and data volume unchanged in normalized stack |
| Cached dependencies | 989 version entries match immutable npm lock |
| Runtime/draft preservation | Existing Lab/A3 identity/start metadata unchanged; nine earlier worktrees/drafts preserved |
| Cleanup/publication scope | No R7 test containers/networks remain; local images retained; docs-only push |

R1–R6 A3/TTS/Pipe/codec/resource results are historical reused evidence, not recounted
as newly rerun suites. No fresh microphone, model inference, speech accuracy,
mounted browser UI, Safari/iPhone, or deployed TTS/Pipe/Arena acceptance is claimed.
The local builds and focused checks were reused after interruption without
unnecessary rebuilds. No remaining offline packaging failure was identified.

## Exact deployment checklist — requires separate authorization

1. Approve the local code/image IDs and residual-risk scope. Recheck runtime drift,
   image/model identity/read permissions, ownership/absence of new resources,
   headroom and loopback port. Retain current Lab image/stack and verify a protected
   consistent WebUI-volume backup; do not inspect chats or canonical data.
2. Provision one independent high-entropy bridge credential outside Git, with
   reviewed ownership/permissions and read-only distribution to WebUI/bridge.
   Do not reuse a browser JWT or WebUI signing key and do not print credentials.
3. Review/test the minimal backend-only activation wiring supplying that credential
   and whisper_text to create_app, plus the same credential via the fixed local
   native dispatch callable. Neither gate is enabled in R7; no frontend rebuild
   is needed for this wiring. Explicit authorization must cover enabling them.
4. Preview the retained stack followed by R6 private and R7 package overrides,
   without printing real private configuration. Exact order: compose.webui.yml,
   compose.boot.yml, compose.arena-ui2.yml, compose.https.yml, compose.tts.yml,
   stt/private/compose.yml, stt/package/compose.yml; use only the review profile
   and pinned local images, no pull/build of unreviewed artifacts.
5. Create only the owned new bridge/Whisper and two networks under approval.
   Verify full IDs/owner labels, membership, private DNS, no engine host port,
   actual read-only mounts/cgroups/logging and no legacy fallback. Record these
   exact identities for rollback. Do not issue a project-wide up/down.
6. Recreate only Lab WebUI with retained volume/auth/HTTPS/TTS/Pipe configuration.
   Verify TTS/Arena preservation; leave STT permission false until explicitly
   authorized gate/permission transition and bounded public synthetic speech
   acceptance. Do not restart A3, Kokoro, Corvus API, Hindsight or other services.
7. Check auth, Chinese/English, bounds/errors/disconnect, storage/log privacy,
   editable review-before-send and target browsers/Safari/iPhone. Refresh old
   browser assets deliberately. No private recordings for initial acceptance.

## Rollback boundary and remaining risks

Close dictation admissions and STT permission first. Stop only the owned bridge
and independent Whisper, verify old work has ended, and restore only Lab WebUI's
retained image/stack with the same existing volume and STT disabled if needed.
No canonical/database restore, volume removal or broad stack teardown.

The plan-only rollback helper executes nothing. It accepts only full IDs for the
two expected new services, exact pinned images, Lab project and r7-lab owner label.
Tests reject legacy A3, Production, wrong labels/images and duplicates. Network
removal requires fresh zero-consumer inspection with exact new names/ownership;
container and network phases are separate. Stop on uncertainty. Never prune or
fall back to legacy Whisper. Paired stop/verification avoids reopening admission
while an old cancelled engine request still runs.

Remaining activation prerequisites are credential/gate wiring, protected backup,
controlled recreation and synthetic/browser acceptance, all intentionally outside
this task's authorization. System/client swap, core/crash dumps, hibernation,
browser native memory/GC, worker lifetime and legacy A3 converter retention remain
risks under R6's explicit scope. Complete privacy and hard process cancellation
are not claimed. No runtime rollback is necessary now because no deployment occurred.

Only this sanitized report and the multimodal index are pushed to
reports/web-validation. Implementation and images remain local.
