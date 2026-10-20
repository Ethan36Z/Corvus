# Vision — single-store decision addendum

Date: 2026-10-19 (Lab operator timezone).

**SINGLE_STORE_REQUIRES_LARGER_CHANGE** — feasible with existing UI, databases,
A3 storage and Qwen, but not a Pipe-only patch. Accept the user's single-store
requirement; supersede the two-store recommendation in the
[reuse audit](2026-10-19-image-integration-reuse-audit.md). No implementation or
deployment is authorized here. Only this addendum/index are written.

## Verified reasons

The current native Chat.svelte saves user-message image data URLs before calling
the Pipe. Its composer onChange can also serialize image files into localStorage
when text exists. The generic WebUI upload writes a Storage copy before inserting
File metadata; process=false does not prevent that copy. Moving conversion into
the Pipe or substituting a URL after Send cannot undo these persistent copies.

A3 has upload/read/inference/provenance, but no authenticated native ownership
binding, idempotent upload key or complete orphan/purge lifecycle. Its foundation
log explicitly leaves lifecycle execution for later work. Generic WebUI deletion
calls Storage.delete_file and is unsuitable for Corvus references. A3 attachment
UUIDs and client-provided chat/reference IDs never prove authorization.

## Exact minimum change boundaries

Upstream paths refer to the pinned current Lab WebUI source, not a new UI.

| Existing file | Necessary change |
| --- | --- |
| src/lib/components/chat/MessageInput.svelte | Existing preview/remove remains; memory-only image draft; one bounded PNG/JPEG; bypass generic WebUI raw storage |
| src/lib/components/chat/Chat.svelte | Reference-only draft/history serialization and initial chat creation; upload-before-reference-save; current-turn-only inference |
| backend/open_webui/routers/files.py | Narrow authenticated Corvus-image upload action; reference-aware content/delete branches, bypassing Storage and persistent caches |
| backend/open_webui/models/files.py | Reuse File rows as metadata-only owner/chat/user-message/operation/attachment bindings; atomic state helpers and protected metadata |
| backend/open_webui/routers/chats.py and backend/open_webui/models/chats.py | Guard create/update/import/message writes against raw images and forged references; revoke bindings for deleted messages/chats, including bulk paths |
| deploy/open-webui/corvus_pipe.py | Resolve the current authorized reference to attachment_id; claim dispatch durably; preserve text/task safeguards and existing A3 chat authority |
| app/playground_api.py, memory/attachments.py, memory/store.py | Lab-scoped upload idempotency/status and retention-safe cleanup metadata/operations around existing storage; preserve legacy A3 callers |

Reuse native verified-user/chat-ownership helpers and File.user_id. File records
contain references/authorization metadata only, no image bytes, Base64 or derived
thumbnails. Keep Corvus reference records out of generic Storage/RAG/file-mutation
paths. Existing Image/UserMessage/ImagePreview components can render the returned
same-origin URL; native authentication supports token cookies for img requests.
Lab vision/menu permissions and limits from the audit still need narrow enablement;
general document/tool capabilities stay closed. Reuse current packaging without
changing STT/TTS, Arena, Hindsight, Qwen, Production or Demo.

## Complete flow

1. **Draft:** native + creates an in-memory Blob/object URL or data URL; editing
   and removal remain native. Browser draft persistence stores text/references,
   never image bytes. The transient preview must not be the serializable history.
2. **Send:** reject image+Arena and invalid mode/type/count/size before upload,
   reference, saved-turn or canonical writes. For a new chat, after validation
   create an owned text/metadata-only placeholder and actual user-message ID;
   initial chat creation must never receive raw image data.
3. **Upload once:** the authenticated adapter verifies that saved chat and user
   message belong to the caller, establishes a server-bound operation/reference,
   streams to fixed Lab Corvus upload, and records its attachment ID. Corvus must
   atomically reuse that operation on retries; SHA blob deduplication alone still
   creates duplicate attachment evidence IDs. No WebUI Storage upload occurs.
4. **Save/send:** save only type=image, opaque reference ID and server-generated
   same-origin content URL on the user message. Pipe rechecks the binding and
   resolves its attachment ID for existing /api/chat and Vision v1. Injected
   metadata.message_id is the assistant response ID: validate its real user
   parent rather than confusing the two. Historical images are display-only.
5. **Display/reload:** thumbnail, click-to-view and reopened history use the same
   authenticated content branch. Every access verifies user, current owned chat,
   exact user-message membership, immutable binding and live retention status,
   then serves bounded PNG/JPEG from Corvus. Missing/revoked references display
   unavailable; they never grant access by possession of a URL or UUID.

## Necessary adapters, not another system

A narrow raw upload subroute under the existing authenticated files router is
necessary: native data URLs do not produce Corvus attachments, while ordinary
file upload persists a second copy. Existing GET files/{ref}/content and DELETE
can be extended for this provider; a second public image-download API is not
required. Use native bearer authentication for mutations and same-origin/CSRF
checks when cookie mutation is permitted. Image GET may use the native cookie;
no URL tokens, public signed-URL authorization or direct A3 content exposure.
Serve private/no-store with nosniff, fixed upstream, bounded streaming, no redirects,
filesystem-path input, persistent proxy cache or generated thumbnail storage.
Raw upload must fit the existing 10 MiB gateway ceiling and Corvus limits; a
16 MiB A3 limit does not override that ceiling.

Private A3 operation/status and cleanup support is necessary to reconcile a lost
upload response and safely retire bytes. WebUI must not import Corvus code across
containers or mount its SQLite/blob directory. Extend existing loopback APIs and
SQLite transactions; do not add an engine or storage framework. Client imports,
clones, shares or generic metadata edits must not silently transfer/rebind image
access; reject unsupported references until an explicit transfer policy exists.

## Failure, deletion and retention rules

Persist pending/ready/claimed/uncertain/revoked operation state. Conflicting bytes
or ownership under one key fail closed; concurrency must not duplicate attachment
IDs. A browser abort does not prove Corvus stopped. Reconcile uploads by operation
status; do not retry blindly. A durable Pipe claim prevents automatic duplicate
canonical dispatch; lost/partial chat results remain UNCERTAIN and reconcile via
canonical provenance. Do not claim exactly-once chat or automatically regenerate.

Draft removal before Send only releases memory. Failed uploads/saves leave tracked
pending operations. Chat/message deletion revokes image access immediately; raw
purge is a separate Corvus-owned action after every shared-blob reference and
retention protection permits it. Preserve canonical text/provenance and tombstones;
never unlink via WebUI file.path or purge another user's/retained A3 blob.
Unattached uploads require an explicit grace/reconciliation policy; uncertain
canonical linkage is a hold, not permission to purge. Retention labels alone are
not cleanup. Grace duration and canonical raw-retention policy must be selected
before activation; access revocation is not physical erasure.

Back up Corvus blobs with Corvus metadata; WebUI backups contain references and
ownership metadata only. Recovery copies are not another active image store.
Restore compatible instance/user/reference identities; missing/mismatched bindings
fail closed. Do not silently migrate or erase preexisting copies. No automatic
image-turn Hindsight retention is introduced: pass the actual attachment ID through
A3's existing guarded path, and reject image+Arena before writes.

## Minimum offline acceptance before separately authorized activation

Use existing tests/helpers and synthetic PNG/JPEG only: prove no raw/Base64 in
WebUI history/messages/drafts/imports/backups/cache; native preview/remove/reload;
cross-user/chat/message, copied/imported reference and revoked-session denials;
format/count/body limits and image+Arena zero writes; upload cancel/crash/lost
response/concurrent replay; canonical partial failure without redispatch;
shared-blob-safe cleanup and coordinated restore; current-image-only A3 invocation
and Hindsight exclusion; focused unchanged text/STT/TTS/Arena contracts. Actual
native-browser acceptance follows only after separately authorized deployment.

Only the narrow source boundaries and prior audit were reviewed. No private image,
conversation or credential access, new tests, inference, application/configuration
edits, builds or service changes occurred. Stop at this decision; implementation
requires authorization for this larger but bounded reuse-based scope.
