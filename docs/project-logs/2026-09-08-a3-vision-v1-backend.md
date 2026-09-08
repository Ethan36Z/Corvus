# A3.2 Vision v1 Backend

Date: 2026-09-08

Baseline:

`87483a3 Enable production Qwen vision runtime`

## Goal

Connect stored image attachments to the existing Corvus conversation
authority without creating a separate multimodal chat system or changing
A0 Evidence Recall into a multimodal retrieval architecture.

The required path is:

user text
→ canonical SQLite message first
→ attachment provenance link
→ existing text Working Context
→ transient multimodal model input
→ production Qwen3.5 Vision
→ assistant reply
→ same canonical Evidence Log
→ derived dense sync

## Vision v1 scope

Vision v1 currently supports:

- one optional image attachment per chat turn
- PNG
- JPEG
- raw blob status PRESENT
- model-facing image data only for the current turn

Vision v1 does not yet include:

- multiple images per turn
- video
- historical image re-injection
- visual embedding retrieval
- OCR fallback
- Web UI image selection

## Vision input adapter

`app/vision_input.py` establishes the model-facing image boundary.

It:

- resolves the attachment evidence identity
- requires a PRESENT raw blob
- reuses attachment SHA-256 and size verification
- accepts only image/png and image/jpeg
- verifies image bytes against PNG/JPEG signatures
- enforces a separate Vision v1 size limit
- creates an OpenAI-compatible image data URL only transiently

The canonical Working Context remains text-only.

Base64 data is never persisted into:

- messages
- SQLite FTS
- dense Evidence Recall
- historical conversation evidence

## Conversation runtime integration

`process_turn()` remains the single conversation authority.

For an image turn the order is:

1. persist canonical user text
2. link attachment provenance to the canonical message
3. build normal text Working Context
4. convert only the final model-facing user message into text + image
5. call the existing local Qwen model
6. persist assistant reply
7. run derived dense synchronization

The existing text-only dependency-injection boundary and behavior remain
compatible.

Failure rules were explicitly tested.

Attachment link failure does not erase the already committed user message.

Vision input validation failure does not erase:

- canonical user evidence
- attachment provenance already committed

Model-facing multimodal state remains derived and transient.

## Chat API

`POST /api/chat` remains JSON.

Existing requests remain valid:

```json
{
  "session_id": "default",
  "message": "hello"
}
```

Vision requests may additionally include:

```json
{
  "attachment_id": "<attachment-id>"
}
```

`attachment_id` is optional, preserving existing clients.

Responses expose attachment ID and attachment processing status.

## Isolated real Corvus E2E

A real isolated Corvus API was started against a temporary data root while
reusing the production multimodal llama.cpp service.

A deterministic PNG contained:

- red square on the left
- blue circle on the right

The image was uploaded through the real attachment HTTP API and then supplied
to `/api/chat` through its attachment ID.

Corvus responded:

`There is a red square on the left and a blue circle on the right.`

The isolated SQLite database confirmed:

- canonical user text remained plain text
- assistant reply was persisted normally
- message-to-attachment provenance existed
- no base64 data existed in messages
- no image data URL existed in messages

Result:

`A3_REAL_CORVUS_VISION_E2E: PASS`

## Fresh-data lifecycle observation

The isolated acceptance exposed that a completely fresh CORVUS_DATA_DIR
requires explicit SQLite schema initialization before starting the API.

This remains a deployment/lifecycle responsibility and was not folded into
Vision runtime behavior.

## Demo dense reset lifecycle bug

The deployed Vision acceptance then exposed an existing Demo lifecycle gap.

The Demo reset recreated SQLite but did not recreate the empty LanceDB
`evidence_dense_v1` table.

As a result, the first post-reset turn could successfully:

- call the model
- persist user evidence
- persist assistant evidence

but retrieval and dense synchronization were DEGRADED because the derived
table did not exist.

The fix was made in:

`deploy/scripts/reset-corvus-demo-data.sh`

Demo reset now explicitly performs:

1. SQLite schema initialization
2. empty dense index reconstruction
3. Demo API restart

`rebuild_dense_index()` already supports an empty Evidence Log and creates a
valid zero-row `evidence_dense_v1` table without requiring message embeddings.

Acceptance confirmed:

- reset → dense table exists with 0 rows
- first text turn → overall OK
- retrieval OK
- dense OK
- dense table grows to 2 rows
- second reset → messages 0 and dense rows 0 again
- Private data remains unchanged

Result:

`A3_DEMO_DENSE_RESET_LIFECYCLE: PASS`

## Real deployed Vision acceptance

The final deployed acceptance used the real Demo Nginx, Demo API, attachment
storage, production multimodal Qwen runtime, SQLite Evidence Log, A0 retrieval,
and LanceDB dense index.

Text regression:

`CORVUS_DEPLOYED_TEXT_OK`

Status:

- overall OK
- retrieval OK
- model OK
- persistence NORMAL
- dense OK

A real PNG upload through Demo returned:

- HTTP 201
- media type image/png
- blob status PRESENT
- retention EPHEMERAL

A real deployed Vision chat returned:

`There is a red square on the left and a blue circle on the right.`

Status:

- attachment USED
- overall OK
- retrieval OK
- model OK
- persistence NORMAL
- dense OK

Canonical evidence verification confirmed:

- user text remained plain text
- assistant reply remained plain text
- one message_attachments provenance link existed
- retention was EPHEMERAL
- no base64 data existed in canonical messages
- no image data URL existed in canonical messages

The Demo dense table contained four rows after the text and vision acceptance
turns.

The normal Demo reset was then executed.

After reset:

- messages: 0
- attachment blobs: 0
- attachment records: 0
- raw attachment directory absent
- dense table exists
- dense rows: 0
- Private data unchanged

Private remained:

`80 messages : 0 blobs : 0 attachments`

Final Private and Demo health were OK.

Result:

`A3_DEPLOYED_VISION_BACKEND_ACCEPTANCE: PASS`

## Architecture result

Vision does not replace or redefine canonical evidence.

The current boundary is:

- user text = canonical message evidence
- uploaded image = canonical attachment evidence while retained
- message-to-image link = provenance
- multimodal model payload = transient inference input
- model interpretation = perception, not canonical user truth
- assistant reply = canonical assistant conversation evidence

This preserves the Corvus principle:

**Evidence first. Perception second.**

## Result

`A3.2 Vision v1 Backend — COMPLETE`

Next:

`A3.2d Web UI image interaction`

The Web UI should allow image selection, preview, upload, cancellation, and
sending an attachment ID through the existing `/api/chat` endpoint without
changing the backend authority established here.
