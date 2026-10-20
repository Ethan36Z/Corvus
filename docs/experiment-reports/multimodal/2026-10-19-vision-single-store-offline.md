# Vision — single-store offline implementation

Date: 2026-10-19 (Lab operator timezone).

**SINGLE_STORE_OFFLINE_READY** — a bounded offline vertical slice is implemented
and tested. This is not deployment, live Vision acceptance or permission enablement.
Continue the [single-store decision](2026-10-19-vision-single-store-decision.md);
Corvus Attachment Store remains the sole intended active image-byte store.

## Local candidate and scope

Local-only implementation: `da3d9c38f36be4921843f217d0b8cdbe520a4039`, branch
`integration/vision-single-store-offline`, based on the retained STT-enabled local
baseline `953d7c853a876d296bf776ce63637d0ad708111d`. No implementation branch is
pushed. The initial local implementation commit `96c868ddd34b4be3a097f777abeeba4f7c671196`
is preserved. The current Lab, original Pipe, prior drafts, backups and main are untouched.

| Committed file | Change |
| --- | --- |
| `memory/attachments.py` | Optional server operation key reuses an attachment evidence ID; existing SQLite write transaction serializes replay/conflicts and existing SHA-addressed blob storage still deduplicates bytes |
| `app/playground_api.py` | Default-disabled Lab upload operation extension and metadata-only reconciliation/status; existing legacy callers keep their protocol |
| `deploy/open-webui/prepare_vision.py` | Exact source pins; emits patches into a new isolated directory only, without builds or runtime writes |
| `deploy/open-webui/vision.py` | Narrow native authenticated image adapter, immutable ownership bindings, reference-only chat guards, durable dispatch claim and revocation |
| `deploy/open-webui/vision.ts` | Transient native draft validation, fixed same-origin upload and reference-only draft/recovery helpers |
| `deploy/open-webui/README.md` | Offline preparation, supported scope, conservative retention and later activation boundaries |
| `tests/test_attachment_operation.py` | Synthetic Corvus operation/API replay and concurrency tests |
| `tests/test_webui_vision_single_store.py` | Pinned WebUI SQLAlchemy models with mocked users/A3 HTTP; authorization, persistence, failure and Pipe contracts |
| `tests/test_webui_vision_frontend.mjs` | Existing Vite/Svelte compilation and actual native submit/send functions with mocked APIs |

Generated native boundaries are `Chat.svelte`, `MessageInput.svelte`,
`models/chats.py`, `models/files.py`, `routers/chats.py`, `routers/files.py`, plus the narrow adapter,
helper and generated Lab Pipe. The original installed/source Pipe stays unchanged;
the generated candidate adds a gated current-image hook to that exact variant.
Existing native preview/remove/Image/ImagePreview components are reused. There
is no new uploader UI, storage engine, model, converter or lifecycle service.

## Implemented flow and authority

One PNG/JPEG, at most 6 MiB, with nonempty accompanying text; tools, temporary
image chats and image+Arena fail before the initial image-turn write. Native
selection/paste/preview/removal remains in memory. Local draft persistence omits
images. First chat/message saves carry text and a pending marker, never data URLs.

The bearer-authenticated native files subroute verifies the actual owned saved
chat and user-message, derives its operation server-side, and uploads bounded
bytes to the fixed Lab A3 endpoint. Native model overrides and saved message/response
model bindings must select the existing Corvus Pipe. Existing A3 storage performs the only durable
image-byte write. File rows contain metadata/bindings only: no file path, raw
bytes, Base64 or derived thumbnail. Generic uploads are rejected before multipart
parsing, including while Vision is disabled; generic file mutation cannot alter
or erase these protected bindings.

After upload confirmation, chat JSON saves only the bound image reference and
server-generated same-origin content URL. Pipe resolves the actual owned parent
of the saved assistant response, not a client UUID or presumed user-message ID.
It claims the operation durably before one existing A3 `/api/chat` call with the
real attachment ID. Historical images remain display-only. The existing A3
provenance and image-turn Hindsight exclusion are preserved; text Arena retains
its existing route. No new Hindsight call is introduced.

Content/reload checks installation, authenticated user, owned chat, exact
user-message membership, immutable binding and Corvus blob availability/integrity.
It uses the existing verified-user dependency, including native cookie support,
and a bounded fixed upstream read with `private, no-store` and `nosniff`.
The legacy unauthenticated A3 content endpoint is not exposed through WebUI.
Possessing an attachment ID, chat UUID or reference URL grants no access. Native
message-mutation/event routes also deny cross-user admin image operations while
preserving the existing ordinary-text admin behavior.

## Failures, deletion and retention

PENDING/READY/CLAIMED/COMMITTED/UNCERTAIN/REVOKED are metadata states in the existing
File table; no additional database or operation framework. Concurrent/replayed
uploads reuse one evidence ID, and conflicting bytes fail closed. Reload can
reconcile a pending upload and restore its reference for review without inference.
A lost canonical result or cancellation holds the claim; a process death may
leave CLAIMED. Neither state is automatically retried, reset or regenerated.
Confirmed canonical IDs are recorded only after a confirmed reply.

Deletion revokes access; removing the owned chat/message invalidates content
membership immediately. Already-delivered browser bytes and in-flight canonical
work cannot be recalled. No blob is deleted by WebUI: uncertain, orphaned, shared
or canonically referenced Corvus data is retained conservatively. Logical
revocation is not physical erasure. Explicit raw-retention/orphan grace and safe
reconciliation policy remain activation prerequisites. Imports, shares and clones
carrying image references fail closed instead of transferring authority.

Backups must pair Corvus metadata/blobs with WebUI ownership/reference metadata.
Compatible installation/user/chat/message identities must survive restore;
missing or mismatched bindings fail closed. No existing data is migrated, purged
or overwritten, and no live backup or canonical database was accessed.

## Focused offline validation

| Evidence | Result |
| --- | --- |
| Corvus operation/API tests | 2 pass: default-disabled gate, bounded/type rejection, same-operation replay, conflicting replay, status metadata; 8 concurrent identical writes yield one evidence ID; two operations share one blob |
| Existing attachment storage/upload and Vision input scripts | 3 pass: legacy behavior, streaming/deduplication, media/signature/size/availability boundaries |
| Retained WebUI image, actual patched File/Chat SQLAlchemy models and temporary SQLite | 18 pass: mocked authentication, cross-user/forged/import/share rejection, reference-only saves, same-origin adapter content, PNG/JPEG, pre-parser generic-upload rejection, limits, cancellation/lost response, revocation/deletion, concurrent claim, mismatched restore, current-only Pipe and text Arena preservation |
| Existing Vite/Svelte tools | Both changed native components compile; helper validates final bytes; actual native submit/send functions demonstrate reference-only first/save queues, upload-before-dispatch, preserved text, Arena zero writes, failed upload no dispatch and cancellation without late dispatch; native model override is rejected before writes |
| Existing STT/TTS/text Pipe regressions | 58 pass; original Pipe and Arena source pins preserved |
| Existing Pipe contracts against generated Vision Pipe | 25 pass with Vision disabled; enabled image/text-Arena paths are covered separately above |
| Existing A3 Vision runtime assertions | Pass: backward signature/text behavior, turn/provenance order and partial failure preservation |
| Diff/syntax/scope review | Pass; implementation remains local, documentation publication is separate |

WebUI tests used retained image
`sha256:88330ac2e1aa941386d8d2aaff5640f77d7343557969b74452798a6968bc60de`
in identity-checked disposable containers with no network, read-only roots,
dropped capabilities, bounded tmpfs and only read-only candidate/test mounts.
Those containers were removed after identity verification. Native authentication
users and upstream HTTP were mocked; this is not live authenticated-browser proof.
An initial sandbox thread-scheduling stall was cleared by rerunning the same
isolated ASGI tests outside that sandbox; they passed. No packages, models or
images were downloaded, no replacement image was built, and no inference ran.

## Remaining limits and next authorized step

This checkpoint supports image plus text, not image-only turns or reference
transfer/edit/regeneration after dispatch. Existing native optional browser image
compression can change the preview/upload representation; no claim is made that
it preserves the original camera-file bytes. A3's existing image recognition and
codec/runtime limits are reused, not replaced by a new parser or image engine.

Actual native browser thumbnail/click/reopen behavior, live A3 Vision quality,
gateway request-buffering/cache behavior and coordinated recovery remain later
acceptance checks. Host/client memory, swap and dumps are not solved here.
Conservative retention can accumulate held blobs; this is explicit, not an erasure
claim. All feature gates and current Lab permissions remain unchanged.

Next: obtain explicit authorization for Lab-only packaging/deployment review;
select retention/reconciliation policy, confirm gateway buffering cannot create a
second durable copy, install the complete pinned overlay and generated Pipe as
one candidate, then perform controlled synthetic and native-browser acceptance.
Do not enable only the Pipe or only the UI. No deployment is authorized by this
report. Production, Demo, STT, TTS, Arena, Hindsight and Qwen runtime are unchanged.
