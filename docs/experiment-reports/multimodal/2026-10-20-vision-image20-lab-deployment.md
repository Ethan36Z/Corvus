# Vision — 20 MiB original-image Lab deployment

Date: 2026-10-20. **VISION_LAB_READY_FOR_MAC_ACCEPTANCE**.

The existing single-store implementation now accepts one original PNG/JPEG of
at most 20 MiB with accompanying text. No compressor, uploader, storage engine,
model, authorization or lifecycle redesign was introduced. Real Mac photo
acceptance remains pending.

## Minimal changes and runtime

Local-only implementation: `4f138cf28916b4d1a82f6abcefe84838d888a265`.
The existing native selection/send helper, WebUI Vision adapter and Lab A3
operation upload limits changed from 6 MiB to 20 MiB; the A3 Vision reader changed
from 16 MiB to 20 MiB. The native optional image-resize branch is bypassed on this
path so the selected original bytes are retained. Other image/type/ownership,
Arena, retry, timeout and reference-only persistence gates remain intact.

The derivative reuses the working Vision image and all existing assets. After
volatile build dependencies were lost on reboot, an exact SHA-pinned incremental
packager changed three compiled constants and the resize branch, plus import
URLs/source contents. Four affected JS assets/import parents have fresh
`-vision20` URLs and the frontend version was advanced. Edited source-map mappings
were omitted rather than presented as accurate generated columns. No full
Svelte compilation, dependency installation, model download or unrelated rebuild
was performed. The actual built helper/FileReader callback and all four changed
JS files were checked directly.

- Previous image retained for rollback:
  `sha256:c734a452b36ea7c0404ad2431287da85aebab879530b598002c045d10c84bfcf`.
- New active WebUI image:
  `sha256:069eb156400b032f8e7b087bd80a7c661a2c8f9d96ffd9b70bea4512f58d6b43`.
- New WebUI container:
  `237a3f5e94e1b13382f1a6b7dc60097de372785a079e2c6063c99c390e953fb9`;
  healthy, `unless-stopped`.

The local operator restarted only Lab API to load its two updated source files;
the retained scoped procedure recreated only Lab WebUI. Persistent STT secret
mounts, data volume, authentication, environment and security/restart settings
were preserved. Pipe source/valves/model configuration are unchanged; only the
normal function update timestamp advanced during use. STT Bridge, private and
legacy Whisper, TTS/Kokoro, Qwen, Hindsight, FoxGate, Production, Demo and other
containers retained their identities and process start times. FoxGate was not
modified; its previously deployed Lab-only 32 MiB request limit was reused.

## Focused evidence

- Existing isolated operation tests: 2 passed, including exact 20 MiB acceptance,
  20 MiB+1 rejection and A3 original-byte loading. Existing A3 Vision input test
  passed. Existing WebUI adapter suite: 19 passed with mocked A3, including the
  added 20 MiB upload/display case and existing authorization/failure/Pipe/Arena
  contracts.
- Actual compiled PNG/JPEG helper: exact 20 MiB bytes retained; +1 rejected.
  Actual native FileReader callback retains the original data URL even with the
  resize preference enabled. Four changed JS assets pass syntax checks.
- One valid public synthetic PNG, exactly 20,971,520 bytes: authenticated native
  upload succeeded; a +1-byte request was rejected HTTP 413 before image storage.
  The PNG uses a valid ancillary padding chunk to isolate encoded-size bounds
  from image dimensions; this does not prove every phone-photo codec/dimension.
- Exactly one canonical A3/Qwen dispatch returned HTTP 200 in **3.750 s**;
  red/blue and square/circle grounding checks passed. No automatic inference retry.
- Reference-only native chat/File metadata checked for this synthetic turn;
  no raw/Base64 image in WebUI chat JSON, no File byte path/data and no additional
  persistent WebUI upload/image/audio cache files. Corvus remains the sole active
  image-byte store. Bearer/cookie display bytes matched the original, including
  after native chat reload; response is `private, no-store`.
- Unauthenticated upload/content: HTTP 403. Actual different-identity binding
  function: HTTP 404; a second browser/user HTTP login was not performed.
  Existing duplicate dispatch claim and image+Arena pre-write rejection passed.
- WebUI/API health, authenticated configuration/model route, TTS provider metadata,
  fixed STT credential/admission and invalid-WAV bridge boundary passed. No live
  STT/TTS inference or extra text/Arena inference was run; unchanged configuration
  and existing focused Pipe/Arena regression evidence were reused.

## Recovery and remaining acceptance

The fresh protected baseline backup was reused, not repeated: complete current
WebUI volume/configuration/Pipe/model snapshot, both SQLite integrity checks
passed; consistent volume pause was 1.396 s. Prior images/backups remain intact.
Current-baseline rollback Compose, original API source copies and private recovery
checkpoint are retained outside `/tmp`. Rollback recreates only WebUI with its
previous image/configuration while preserving the current data volume. If API
capacity rollback is necessary, restore only the two retained source files and
have the local operator restart only Lab API. Do not restore an old database or
invoke a full-stack shutdown. Conservative image access-revocation/orphan
retention policy is unchanged; logical revocation is not physical erasure.

The Lab remains running for the user's >7 MB real-photo Mac test: refresh the
page, select one PNG/JPEG no larger than 20 MiB, add text, send, inspect the reply
and thumbnail, then reopen the conversation. Real browser/photo acceptance is
not claimed. No implementation branch was pushed and main was not modified.
