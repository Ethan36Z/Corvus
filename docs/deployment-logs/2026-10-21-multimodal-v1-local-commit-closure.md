# Multimodal v1 — local commit closure

Date: 2026-10-21 (America/Los_Angeles). Local Git work only: no push, deploy,
service restart, image build, dependency install, model benchmark or inference.
Existing implementation branches were preserved; nothing was merged into main,
reset, pruned or discarded. Remote classification uses existing local origin
refs; no remote refresh/publication verification was performed.

## New functional commits

| Commit | Branch | Saved work |
|---|---|---|
| `0abe328ef10beb270a5a2ce119648994722831c1` | chore/multimodal-v1-local-closure | Exact cumulative deployed native frontend source patch, pins and reuse instructions |
| `03102dc7cc1e8f9c5caf1a52bde225eedd4795f0` | chore/multimodal-v1-local-closure | Existing Lab API systemd unit/drop-ins and already-installed Pillow requirement |
| `0406e2d509981b40c06ecf28cb2ca32482775a67` | chore/tts-runtime-local-closure | Existing Kokoro activation Compose and provenance notes |

This inventory is a subsequent documentation-only commit. Its own hash is
reported after committing, so the captured table shows the immediately prior
HEAD for the documentation branch.

## Module preservation

- **STT / Whisper / bridge — ALREADY_COMMITTED, UNPUSHED.** R1-R7,
  activation/credential repair and browser WebM fix remain on their existing
  refs. `75e3cf9` contains the persistent-mount/restart recovery work. Current
  bridge/transcription/protocol code, the mounted WebUI UID-0 protocol generated
  by `credential_repair.py`, and the existing native route code are saved. Do not
  deploy the old R7 `/tmp` packet defaults; use the committed boot overlay with
  current image identities and independently provisioned protected material.
- **TTS — ALREADY_COMMITTED, UNPUSHED.** Native WebUI helper is in `3793b13`;
  Kokoro logging derivative is `7c0b5d0`. The four installed derivative files match
  that commit. The runtime Compose gap is now committed in `0406e2d` on its own
  TTS branch. No synthesis or recording was used during closure.
- **Vision — ALREADY_COMMITTED, UNPUSHED.** Single store `da3d9c3`, 20 MiB
  `4f138cf`, upload cancellation `4845db5`, thumbnail order `4d5b584`, memory
  preview `e5afa68`, next-turn guard `a7558fd`, inference resize `98ae271`.
  Existing protected operator metadata records the resize deployment as ready;
  the active source matches that committed file. This is not Mac acceptance.
- **WebUI native integration — ALREADY_COMMITTED + packaging gap CLOSED.**
  Seven native frontend files and three existing helpers reproduce the deployed
  cumulative source exactly from the verified pinned branding/Arena base. The
  source checkpoint uses the existing Node/Svelte/Vite workflow, not generated
  JS/minifier edits or a new builder. Current installed TTS helper and Vision
  Pipe match committed source/generators. User-owned Function/model settings are
  private runtime data, not duplicated in Git.
- **Web Search — ALREADY_COMMITTED, UNPUSHED.** `50a6385` is the MVP integration;
  `4f8013a` aligns existing packaging pins; `01dd02e` / `9b374cf` preserve earlier
  prototypes separately. Runtime Lab Web MVP activation is captured in its
  existing systemd drop-in. Current installed Pipe matches its generator.
- **Gateway / persistence — ALREADY_COMMITTED + config gaps CLOSED.** The actual
  Lab nginx files match `7dc2478`; there is no separate Git repository at the live
  lab-access directory. Its source is already in Corvus. The Lab service unit
  and drop-ins are now saved; STT boot files were already saved on their branch.

The exact locally retained WebUI image is
`sha256:2427456fa33f5eccf8a854f9ad37f3af05f0cc443ae6348468f136a25a0745dc`,
bridge `sha256:5d3cd6aff2db1a9712ce98669942d093858640298e9c04903f3cee3b510dc6b2`,
private Whisper `sha256:caf0cd77c922e9c53f10a9bc17c2f74cc2295d12e7b0f96b630fb3b3c55a0026`,
and Kokoro `sha256:94d19bad32ccb34df77cccc2f5c9bc4ebd1a225878be2522d27b16edc5ae3c44`.
These are local artifact identities, not registry availability guarantees.
Models, dependencies and pinned image caches remain outside Git by design.

## Existing worktree inventory

Observed: **32 registered worktrees; 13 directories present, 19 missing**.

| Worktree | Branch | HEAD at capture | Status |
|---|---|---|---|
| `/home/ethan/srv/apps/small-vram-companion` | `main` | `c315d0e767e3` | clean; UNPUSHED |
| `/home/ethan/srv/apps/corvus-lab` | `lab/ow2e-console` | `4f8013af2c8e` | UNCOMMITTED mirror: 4 tracked files (see below); UNPUSHED |
| `/home/ethan/srv/apps/corvus-lab-gateway-upload` | `fix/lab-gateway-body32` | `7dc247842019` | clean; UNPUSHED |
| `/home/ethan/srv/apps/corvus-multimodal-closure` | `chore/multimodal-v1-local-closure` | `03102dc7cc1e` | clean; UNPUSHED |
| `/home/ethan/srv/apps/corvus-reports` | `reports/web-validation` | `e7d35644e158` | clean; in local remote refs |
| `/home/ethan/srv/apps/corvus-stt-reboot-repair` | `fix/stt-reboot-persistent-mounts` | `75e3cf9b2042` | clean; UNPUSHED |
| `/home/ethan/srv/apps/corvus-tts-runtime-closure` | `chore/tts-runtime-local-closure` | `0406e2d50998` | clean; UNPUSHED |
| `/home/ethan/srv/apps/corvus-vision-live-state` | `fix/vision-reference-display-order` | `47f3791d2a82` | clean; UNPUSHED |
| `/home/ethan/srv/apps/corvus-vision-preview` | `fix/vision-immediate-memory-preview` | `f243fe16cc73` | clean; UNPUSHED |
| `/home/ethan/srv/apps/corvus-vision-upload-abort` | `fix/vision-upload-abort-lifecycle` | `4845db585b3c` | clean; UNPUSHED |
| `/home/ethan/srv/apps/corvus-vision20` | `fix/vision-image20` | `4f138cf28916` | clean; UNPUSHED |
| `/tmp/corvus-chat-recovery-fix` | `fix/chat-after-completed-error` | `a7558fdc39ac` | clean; UNPUSHED |
| `/tmp/corvus-stt-boundary-integration` | `integration/stt-conversion-boundary` | `4f8013af2c8e` | directory missing; branch/commit retained; staged index has no changes; UNPUSHED |
| `/tmp/corvus-stt-credential-repair` | `integration/stt-credential-repair` | `6a2a5eb1bab2` | directory missing; branch/commit retained; staged index has no changes; UNPUSHED |
| `/tmp/corvus-stt-lab-active-integration` | `integration/stt-lab-activation` | `6dfc5225574f` | directory missing; branch/commit retained; staged index has no changes; UNPUSHED |
| `/tmp/corvus-stt-r1-integration` | `integration/stt-r1-legacy-reuse` | `688a8bbd94a9` | directory missing; branch/commit retained; staged index has no changes; UNPUSHED |
| `/tmp/corvus-stt-r2-integration` | `integration/stt-r2-webui-adapter` | `3affe0f0899d` | directory missing; branch/commit retained; staged index has no changes; UNPUSHED |
| `/tmp/corvus-stt-r3-integration` | `integration/stt-r3-native-dictation` | `0489bd7409f5` | directory missing; branch/commit retained; staged index has no changes; UNPUSHED |
| `/tmp/corvus-stt-r4-integration` | `integration/stt-r4-browser-wav` | `83ca1d38836a` | directory missing; branch/commit retained; staged index has no changes; UNPUSHED |
| `/tmp/corvus-stt-r6-integration` | `integration/stt-r6-private-whisper` | `c0b818fa2c72` | directory missing; branch/commit retained; staged index has no changes; UNPUSHED |
| `/tmp/corvus-stt-r7-integration` | `integration/stt-r7-lab-preflight` | `4be6907622e9` | directory missing; branch/commit retained; staged index has no changes; UNPUSHED |
| `/tmp/corvus-stt-retry3-integration` | `integration/stt-lab-retry3` | `dc46ab579be3` | directory missing; branch/commit retained; staged index has no changes; UNPUSHED |
| `/tmp/corvus-stt-webm-cluster-fix` | `fix/stt-webm-unknown-cluster` | `953d7c853a87` | directory missing; branch/commit retained; staged index has no changes; UNPUSHED |
| `/tmp/corvus-stt1-integration` | `integration/stt1-whisper-webui` | `4f8013af2c8e` | directory missing; branch/commit retained; staged index has no changes; UNPUSHED |
| `/tmp/corvus-stt1a-integration` | `integration/stt1a-whisper-privacy` | `4f8013af2c8e` | directory missing; branch/commit retained; staged index has no changes; UNPUSHED |
| `/tmp/corvus-stt1a2-integration` | `integration/stt1a2-volatile-storage` | `4f8013af2c8e` | directory missing; branch/commit retained; staged index has no changes; UNPUSHED |
| `/tmp/corvus-tts1-integration` | `integration/tts1-kokoro-webui` | `4f8013af2c8e` | directory missing; branch/commit retained; staged index has no changes; UNPUSHED |
| `/tmp/corvus-tts21-integration` | `integration/tts21-kokoro-privacy` | `7c0b5d0bbbfe` | directory missing; branch/commit retained; staged index has no changes; UNPUSHED |
| `/tmp/corvus-vision-inference-resize` | `fix/vision-inference-resize` | `98ae27167b0c` | clean; UNPUSHED |
| `/tmp/corvus-vision-single-store` | `integration/vision-single-store-offline` | `da3d9c38f36b` | directory missing; branch/commit retained; staged index has no changes; UNPUSHED |
| `/tmp/corvus-w2-1-integration` | `integration/w2-web-mvp` | `50a63850f835` | directory missing; branch/commit retained; staged index has no changes; UNPUSHED |
| `/tmp/corvus-w2-prototype` | `prototype/w2-evidence-acceptance` | `01dd02e1aa82` | directory missing; branch/commit retained; staged index has no changes; UNPUSHED |

All present worktrees had no untracked files before closure. The two new closure
worktrees are checked clean after their final commits. The active Lab worktree
continues to contain these four deployment mirrors, deliberately left untouched:

| Uncommitted Lab path | Exact bytes already saved in |
|---|---|
| app/playground_api.py | `4f138cf` |
| app/vision_input.py | `98ae271` |
| memory/attachments.py | `da3d9c3` |
| deploy/lab/foxgate/nginx/nginx.conf | `7dc2478` |

They are UNCOMMITTED in that worktree but ALREADY_COMMITTED elsewhere. No duplicate
implementation commit or active checkout replacement was used just to make its
status clean. Main remains clean and unchanged at `c315d0e`; its two pre-existing
unpublished commits are `f240896` and `c315d0e`.

## Remaining/excluded material

- **Unknown preservation:** old `/tmp` draft directories no longer exist. All
  retained missing-worktree indexes were checked and have no staged changes.
  Earlier O_TMPFILE `conversion.h`, `patch.py`, README and STT-1/1a.2 experimental
  uncommitted drafts were not found in these worktrees/refs. No claim is made that
  they were saved; no private backups were opened to search for them. Their
  missing status predates closure; no worktree/admin metadata was pruned.
- **RUNTIME_ONLY, intentionally excluded:** credentials, admissions state,
  private resolved Compose/env packets, protected backups and operator checkpoint
  JSON, WebUI users/chat/Pipe ownership records, model/voice files, databases,
  images/recordings, node_modules/Pyodide/build output, dependency caches and
  temporary experiment logs/scripts. Safe definitions, pins and existing
  provisioning/recovery source are versioned; values/data are not.
- This preserves source/configuration for reuse with the retained pinned build
  inputs and separately managed credentials/data. It is not a tested bare-host
  disaster recovery, a fresh deployment, or a promise that unpublished local
  image digests can be pulled elsewhere. Existing scoped procedures still apply.

## Validation and review

- Existing branding/Arena source verification: 117 pinned files.
- Cumulative source patch: strict `git apply --check --whitespace=error`, isolated
  reapplication and all 10 final source hashes matched. Patch context whitespace
  uses the same scoped attribute convention as existing branding patches.
- Existing Vision input and conversation runtime scripts: PASS (synthetic data,
  original byte preservation, in-memory resize, format/orientation, text order).
- Existing attachment operation tests: 2 PASS; Web MVP/Pipe tests: 42 PASS.
  The initial sandbox attachment test stalled; only that owned test process was
  terminated, then both mocked modules passed outside sandbox under a timeout.
- Kokoro Compose render validation and Lab `systemd-analyze verify`: PASS.
- Installed STT bridge/protocol/transcription, WebUI TTS helper, UID owner override,
  Vision Pipe and Kokoro guard/launcher/verifier/lock match saved source.
- `git fsck --connectivity-only --no-dangling`: PASS. New staged paths were explicit,
  diff scope/whitespace reviewed, and checked for credential signatures and
  forbidden data/artifact filenames. This is not a forensic audit of old history.

## Existing local commits absent from local remote refs

This is a unique commit list, not a sum of per-branch ahead counts:

```text
03102dc7cc1e8f9c5caf1a52bde225eedd4795f0 Record existing Lab API unit and Vision runtime dependency
0406e2d509981b40c06ecf28cb2ca32482775a67 Preserve deployed Kokoro runtime Compose configuration
0abe328ef10beb270a5a2ce119648994722831c1 Preserve exact deployed multimodal frontend source assembly
98ae27167b0c1e34e2b616351f77757b61c0da08 Resize only in-memory Vision inference images with existing Pillow
a7558fdc39acbe29ca5813182b155b0b65766798 Allow a new chat turn after a completed error response
f243fe16cc73e1d863ea66ab76ec02d661d215a4 Record verified Lab immediate preview deployment
e5afa6837299b96f30b0457b64f745a7c3cadf99 Prepare transient native Vision previews and manual draft recovery
47f3791d2a82e5fcaf0df85b62f585cbbe2463b8 Record Lab thumbnail-order fix deployment and preserved rollback
4d5b5847cb35db03e63af305d473c4f69aea188c Commit Vision image references before native thumbnail rendering
4845db585b3cf4ad50929d9ec721d7da808a5d17 Fix native Vision upload reactive controller self-abort
4f138cf28916b4d1a82f6abcefe84838d888a265 Raise Lab single-store original image limit to 20 MiB
7dc2478420194429249e53bac0520e9a15d58e8c Raise only Corvus Lab gateway body limit and stream requests
75e3cf9b2042891709fdc1fde18a1158a0767d67 Fix recovery verifier HTTP client namespace collision
3b93d3ae0b60fad4c96bb9afae8243a84ee81d4d Prepare persistent STT credential mounts and Docker boot recovery
da3d9c38f36be4921843f217d0b8cdbe520a4039 Enforce image ownership in native message mutation routes
b5a48be13d734785b3ab1b8a33316d72a5ea3703 Bind native image turns to the Corvus model
96c868ddd34b4be3a097f777abeeba4f7c671196 Prepare offline single-store Corvus Vision integration
953d7c853a876d296bf776ce63637d0ad708111d Fix browser normalization of streaming WebM Clusters
dc46ab579be3b91b6b11cba730e5da98644bc4c8 Preserve Retry 3 live acceptance and separate mixed-language quality review
6a2a5eb1bab2c4c107dc34b60e2919071795bec1 Repair STT credential ownership per consumer without image rebuilds
6dfc5225574fc28073917546f3f07d4b364cb958 Preserve rolled-back Lab STT activation candidate and credential blocker
4be6907622e9f0634e5b1c327ae5054cca9200ef Package disabled Lab dictation integration with pinned offline images
c0b818fa2c72a4eeb6f8691f5e25f06eea8b87e1 Prepare private no-convert Whisper candidate and bounded dictation admission
83ca1d38836a45088fa6574ed177b1064a0cd87d Normalize native dictation audio to canonical WAV in browser offline
0489bd7409f5e6a95a41acf42027fca651a1e658 Prepare native dictation metadata and review-before-send UX offline
3affe0f0899d2158a66b4259cb7295ef0a4b0810 Prepare disabled authenticated WebUI STT bridge offline
688a8bbd94a96239daa50c9277521ea22c706196 Extract reusable A3 Whisper byte transcription transport
7c0b5d0bbbfe993d4cd4910f1e9c1306de9e3b51 Prepare pinned Kokoro content-free logging derivative
4f8013af2c8e73774fcef91c2510e5808c1fd2c2 Align packaging Pipe pins with reviewed Web MVP
3793b13d1f6855d5df7a3b139d47036b1879e4e0 Prepare private Kokoro Read Aloud integration
50a63850f83506724aaff4c2af4f50811d00d646 Integrate source-first Web MVP with honest fallbacks
9b374cf2ef46ea08399b124e0c2a725d96c92a38 Prototype explicit Web evidence acceptance and source mapping
01dd02e1aa826d49bd628891641892f3450b698f Prototype explicit Web evidence acceptance and source mapping
975645963291ec992d64df0474a3ee9d0ba33dcd Record Corvus remote and mobile PWA milestone
c43412ce8a3101178d44464164d7aac1670e5e83 Record R0.5b Lab HTTPS activation
279688ed393a2376f079c03abec0ce39f91b5ff8 Record R0.4 local Lab FoxGate acceptance
0f9094cde3cedd7731c06e8c23354195338cf82b Prepare Lab HTTPS and PWA remote compatibility
562433898f7f13a448c2b624bac24de305b38308 Prepare isolated Lab FoxGate remote access
7f389f183d01b6c1ad5e542b53a0132ee3cf1a0e Complete Memory Arena UI-2 offline validation
c315d0e767e31fde3c82ba4dfb08659a268c267a Enable Production foreground registry publisher
f2408963881624c6e52c43d266438772beae5020 Port foreground registry publisher for Production
66a1afa28fa44bd4e5c36e51b7d142a5f6ca235b Add OW1 Open WebUI v0.6.5 Corvus Pipe contract
```

## Push readiness

The reviewed local source/configuration commits can be selected for a separately
authorized branch push. No implementation/main/report branch was pushed here.
Do not push all refs, automatically merge branches, include private recovery
packets, or treat lost early drafts as recovered. Origin refs were not refreshed,
so actual remote branch state must be checked before a later push. The active
Lab worktree's four mirrors remain dirty; all known bytes are committed elsewhere.
