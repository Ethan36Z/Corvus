# Image integration — reuse-first audit

Date: 2026-10-19 (Lab operator timezone).

Verdict: **REUSE_READY** — the existing Vision v1 backend, model and native UI
are reusable. This is readiness for a small authorized adapter implementation,
not configuration-only enablement, deployment approval or live image acceptance.
Application code, runtime configuration, services and canonical data were read-only;
only this report and index are written/published.

## Verified local baseline

The three original A3 engineering logs were read, together with the actual Lab
vision/upload/runtime/storage/API code and installed Pipe. The running Lab API's
working directory is the isolated Lab checkout at
`4f8013af2c8e73774fcef91c2510e5808c1fd2c2`, not the current main checkout.
Its actual OpenAPI exposes the attachment upload/content, session-history,
chat-with-attachment and Arena routes. No attachment-content or session-content
request was made.

Current WebUI is 0.6.5, image
`sha256:4b0451913d93774af57defe40873f29323239ef83ed7dfd8f405abe7b4f7ad17`.
Its running frontend index matches the retained current build. Runtime hashes of
`functions.py`, `utils/middleware.py`, `routers/files.py` and `routers/chats.py`
match the inspected pinned source. Installed active Pipe hash is
`68967bd0ed499aaf2ecce38bc6afc80c3fc3cdeb805aab6a57182a2e907af861`:
it matches the Lab checkout, but the main checkout's Pipe differs. Future work
must extend the installed Lab variant, preserving its Arena/text safeguards.

Read-only function/model configuration queries confirm the Pipe target is Lab
`127.0.0.1:18096/api/chat`, Arena is enabled, and model capabilities `vision` and
`file_upload` are false. Ordinary-user native file-upload permission is false;
STT/TTS permissions remain true and calls false. Persistent WebUI configuration
is disabled. Native generic file size/count environment limits are unset
(source defaults are None). No individual user's settings were inspected.

The actual local Qwen server reports model
`Qwen_Qwen3.5-9B-Q5_K_M.gguf` and `modalities.vision=true`. This verifies retained
runtime capability, not a new inference-quality test. No model call, image upload,
private image inspection, browser recording or canonical chat was performed.

## Direct reuse and native UI contracts

| Existing component | Verified reusable behavior |
| --- | --- |
| `app/attachment_upload.py` | Raw-body bounded streaming upload, existing spool and content-addressed storage; no new uploader/storage engine needed |
| `memory/attachments.py` | SHA/size/path integrity, independent attachment IDs, blob deduplication, retention classes and message provenance |
| `app/vision_input.py` | Single PNG/JPEG, PRESENT blob, signature/MIME and 16 MiB vision bound; transient OpenAI-compatible image data URL |
| `app/conversation_runtime.py` | Canonical text first, attachment association, existing text context, current-turn-only image inference, normal assistant persistence |
| `app/playground_api.py` | Existing raw `POST /api/attachments?filename=...`, JSON `POST /api/chat` with `attachment_id`, content GET and session attachment metadata |
| Native WebUI composer/history | Existing + selection, draft preview/removal, text editing, same user-message files, thumbnail and click-to-preview, saved-history reload |

Native UI support is verified from the exact current build/source, not a new
interactive browser acceptance. It is gated off for this Pipe/model today.
Images take a different path from ordinary uploaded documents:
`MessageInput.svelte` reads them with FileReader as data URLs and stores
`{type: "image", url: "data:image/...;base64,..."}` in the draft. On Send,
`Chat.svelte` copies these into the user message's `files`, clears the composer,
and persists the normal chat history. `UserMessage.svelte` renders the existing
Image component, which opens ImagePreview. The normal authenticated chat
persistence/read path supports reopening those stored images; Corvus session
history is not the source of Open WebUI's thumbnail rendering.

The model request's user `content` becomes a list of text and
`image_url: {url: <data URL>}` parts. The current serializer includes images from
historical user messages too. Top-level `files` is separate document/collection
metadata; it is not a reliable source of the native current image. WebUI
middleware moves that field into metadata and functions.py injects it as
`__files__`; the adapter must inspect both channels without conflating them.

## Exact integration gaps

1. `deploy/open-webui/corvus_pipe.py`: `_reject_unsupported` rejects nonempty
   files/attachments/images and the Pipe rejects `__files__`. Its message loop
   rejects every non-string `content` with “OW1 does not support media or tool
   messages.” It never uploads image bytes or forwards an attachment ID.
2. Lab model metadata has vision=false and ordinary-user native + upload
   permission is off. Changing only these settings would still hit the Pipe's
   media rejection. General document/RAG/file capabilities must remain rejected.
3. The native data URL is neither a Corvus attachment ID nor a native file ID.
   It needs a bounded server-side transport adapter to the already existing raw
   attachment API; browsers must not call loopback Corvus URLs themselves.
4. `Chat.svelte` serializes old images again. Vision v1 supports only the current
   image. Normalize historical messages to text for this model request while
   preserving their stored UI `files`; otherwise old images bloat every request
   even if the Pipe later discards them.
5. The existing Arena request is strict text-only (`app/arena.py`, extras
   forbidden). Image plus Memory A/B must fail closed before upload/canonical
   writes, rather than silently using Arena or silently dropping its opt-in.

## Minimal implementation recommendation — no second vision system

Extend only the installed Lab Pipe and small existing frontend request/selection
boundaries, plus Lab-only model/permission/limit configuration:

- Keep native +, composer, preview, history and image viewer. A small existing
  MessageInput guard should consistently allow one PNG/JPEG and a bounded size
  across selection/paste/drop; do not add a new upload UI or open document/RAG
  handling by enabling the native attachment menu.
- In the existing Chat request serializer, include image bytes only for the
  latest user turn; keep the persisted image thumbnails/history untouched.
- Extend the Pipe to require an authenticated user and an owned saved chat,
  retain the existing instance/user/chat session namespace, accept exactly one
  bounded inline PNG/JPEG plus nonempty text, and reject remote URLs, arbitrary
  paths, supplied Corvus attachment IDs, tools and unsupported modes. Native
  chat ownership must be checked server-side; a valid UUID/session hash alone
  is not proof of ownership. Use existing native ownership helpers.
- Decode transport base64 with strict limits (not a new image parser), then
  call the existing fixed Lab raw upload endpoint and existing `/api/chat`
  with its returned attachment ID. Reuse Vision v1 integrity/format/model
  handling. No redirects, automatic retries, request-selected upstream or
  direct Qwen path. Preserve the existing uncertain-result behavior.
- Enable only the Lab vision capability and required native menu permission;
  keep unrelated media/tool/RAG features closed. Use the existing frontend
  packaging and focused synthetic contracts when implementation is authorized.

No new Corvus endpoint, image storage implementation, visual model or A3 React
UI transplant is required for this minimal two-existing-store plan. No edits to
VisionInput, the model client, A3 storage, STT/TTS or Hindsight are presently
necessary. Reject image+Arena while leaving ordinary text Arena unchanged.

## Safety and data-consistency gates before implementation/activation

**Two retained copies are the smallest native-UI tradeoff.** WebUI retains base64
in its authenticated chat JSON; Corvus retains a blob plus attachment/provenance.
Corvus deduplicates bytes within its own store, not across both stores. Deleting
or purging one does not remove the other. Retention, deletion, export/backup and
orphan policy need explicit agreement; STANDARD is not evidence of automatic
expiry. Avoid additionally uploading the same image to WebUI's generic file
store, which would add another copy. Eliminating the UI copy would require an
owned, authenticated content-reference/proxy integration and is a larger option,
not a prerequisite to reuse Vision v1 if the two-store policy is accepted.

**Do not expose the old content API.** A3 attachment upload/content/chat endpoints
have no built-in per-user authentication; attachment lookup is by ID and its
schema has no user owner column. Existing loopback isolation is their trust
boundary. Preserve fixed server-side access, create the attachment from the
current authenticated request, and never treat a UUID or SHA as authorization.
A future authenticated proxy must verify user/chat/message/attachment ownership
before returning bytes; the existing Corvus content GET cannot be directly made
public. WebUI's native chat routes and generic file routes already have ownership
helpers; the image adapter must reuse them where relevant.

**Upload and chat are not one transaction.** Each upload creates an evidence ID,
even if its bytes deduplicate. Upload-success/chat-failure can leave orphans;
canonical user text/link may already exist when model validation or inference
fails. Native saved-message identity and returned Corvus attachment/message
identity must be correlated for recovery. In this native request, injected
metadata.message_id is the assistant response ID, not the image-bearing user
message ID; do not equate them. Preserve no-auto-retry, make partial
outcomes explicit, and do not claim exactly-once operation without a demonstrated
idempotency contract. No new distributed storage system is recommended.

**Limits must agree.** Existing A3 upload default is 32 MiB and vision is 16 MiB,
but the actual Lab HTTPS gateway ceiling is 10 MiB for the complete JSON body.
Base64 expands bytes by about 4/3, so a 16 MiB native image cannot pass it.
Choose a lower raw-image bound with text/JSON headroom and enforce the full body
bound; do not silently raise the shared gateway limit. Removing historical image
payloads is part of keeping this bounded. Browser compression may resize and
re-encode JPEG as PNG; it must be disabled if original-byte evidence is required,
or that representation choice must be explicit. Original filename metadata is
not retained by the native image object; use a safe generated filename or a
small metadata-preserving native patch, not an invented original filename.

**Hindsight is already guarded for real A3 image turns.** In the actual
`/api/chat` handler, background retain scheduling requires attachment_id is None
and vision mode. Passing the real attachment ID therefore skips automatic image
turn retain. Do not flatten image data/descriptions into the text-only or Arena
endpoint: Arena schedules its canonical text reply for Hindsight. Keep image
payloads out of logs and search memory. This is a direct image-turn guarantee;
it is not a claim that later ordinary text can never mention earlier visual
content. A broader semantic exclusion would require a separate explicit policy.

## Preservation and next authorization

No implementation, build, inference, deployment, restart, dependency/model download,
Git implementation change or canonical-data write occurred. Existing STT/TTS,
Pipe/Arena text behavior and Hindsight services were not changed. Runtime identities
were read-only checked; no user settings, conversations, private images, attachment
bytes or credentials were accessed. The only database reads were technical
function/model configuration with read-only/query-only SQLite access.

Next smallest authorized task: implement the single-image Lab Pipe adapter,
current-turn-only native serialization and narrow native format/size guards,
after confirming the two-store retention policy and image+Arena fail-closed rule.
Validate only synthetic native payload, ownership, bounds, partial-failure,
Hindsight exclusion and existing text/audio/Arena contracts. Do not deploy until
separately authorized. Only documentation is published in this audit.
