# A3.2 Vision v1 — Web Image Interaction

Date: 2026-09-08

Backend baseline:

`c8d3018 Complete A3 Vision v1 backend`

## Goal

Expose the completed Corvus Vision v1 backend through the existing
Private and Demo Web UI without creating a second conversation system.

The final interaction is:

user selects image
→ local browser preview
→ raw attachment upload
→ attachment_id
→ existing `/api/chat`
→ canonical user text committed first
→ attachment linked to that message
→ transient multimodal Qwen input
→ assistant reply
→ canonical session history
→ image remains attached to the user message

## Supported scope

Vision v1 Web currently supports:

- one image per turn
- PNG
- JPEG
- maximum 16 MiB model-facing image size
- local image preview before sending
- image removal before sending
- text plus image submission
- Private deployment
- Demo deployment

It does not yet support:

- multiple images per turn
- image-only turns
- video
- camera streaming
- historical visual re-injection
- visual embedding retrieval

## Composer semantics

Before send, the selected image belongs to the composer draft.

After Send, the image immediately moves into the optimistic user
message and the composer becomes available for the next turn.

This preserves the UI boundary:

composer
= uncommitted intent

message history
= committed conversation experience

If the raw upload fails before Corvus receives the turn, the text and
selected image return to the composer for retry.

If canonical user evidence exists but later processing fails, the UI
recovers the canonical session state rather than inventing local state.

## Canonical attachment presentation

The initial Web implementation successfully uploaded images and invoked
Vision, but exposed an important presentation gap:

after Send, the image remained in the composer while inference was
running and disappeared after canonical session history reloaded.

The root cause was that `/api/sessions/{session_id}` returned message
text only.

A3.2d therefore added canonical attachment presentation.

Session messages now include public attachment metadata derived from:

- `message_attachments`
- `attachments`
- `attachment_blobs`

The API does not expose:

- raw storage paths
- SHA256 values used internally for storage integrity

## Read-only attachment content

A read-only endpoint was added:

`GET /api/attachments/{attachment_id}/content`

The endpoint:

- resolves attachment identity through Corvus metadata
- requires blob state `PRESENT`
- permits displayable Vision v1 PNG/JPEG content
- reuses the existing attachment reader
- verifies blob size
- verifies SHA256 integrity
- enforces the existing DATA_DIR path boundary
- sets `X-Content-Type-Options: nosniff`
- never exposes filesystem storage paths

If raw bytes are no longer retained, attachment provenance can remain
while the UI represents the image as unavailable.

This preserves the project principle:

**Memory permanence != raw-byte permanence.**

## Contract validation

The new presentation contract verified:

- message attachment metadata
- ordinal preservation
- attachment content URL generation
- storage-path privacy
- no public SHA256 exposure
- safe attachment content reading
- PNG media response
- `nosniff` response protection

Existing contracts remained green for:

- Vision conversation runtime
- Vision input adapter
- attachment storage
- attachment upload
- upload streaming
- upload size limits

The production React/Vite build also passed.

## Deployment acceptance

Both Corvus APIs were restarted independently so the new read-only
content route could load.

The following remained untouched:

- llama.cpp runtime
- Docker daemon
- host networking
- SSH
- canonical data

Private and Demo OpenAPI both exposed:

`/api/attachments/{attachment_id}/content`

The route was verified through both Nginx Web proxies.

Private and Demo API health remained OK.

Private and Demo Web deployments both became ready.

## Real browser acceptance

Real image interaction was tested through the deployed Corvus Web UI.

Observed behavior:

1. image selected in composer
2. image preview displayed
3. text entered
4. Send pressed
5. image moved from composer into the user message
6. Corvus performed real Vision inference
7. assistant response correctly described the image
8. image remained associated with the user message
9. session history continued to render the attachment correctly

The user additionally verified the Private Corvus deployment was
working normally with Vision v1.

Both Private and Demo are therefore accepted for daily-use Vision v1.

## Architecture result

Vision remains an additional perception channel over the existing
Corvus conversation authority.

The system did not convert A0 Evidence Recall into multimodal retrieval.

Canonical text remains canonical text.

Attachment identity and provenance remain explicit.

Raw image bytes remain separately managed evidence.

Vision input is transient model context.

The key boundary remains:

**Evidence first. Perception second.**

## Result

A3.2a — Production Vision Runtime: SEALED

A3.2b — Vision Conversation Integration: COMPLETE

A3.2c — Deployed Backend Acceptance: COMPLETE

A3.2d — Web Image Interaction: COMPLETE

# A3.2 Vision v1 — COMPLETE

Next:

A3.3 — Voice v1 / Push-to-Talk
