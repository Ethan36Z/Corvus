# A3.1b Attachment Upload API

Date: 2026-09-08

## Context

A3.1a established the persistent attachment storage foundation:

- content-addressed raw blobs
- independent attachment evidence identity
- message-to-attachment relationships
- derived attachment artifacts
- retention classes
- Private / Demo lifecycle isolation

A3.1b exposes that storage boundary through a bounded HTTP upload API.

This checkpoint does not yet perform vision, STT, document extraction,
or model inference over attachments.

## API contract

Endpoint:

`POST /api/attachments?filename=<name>`

The request body is the raw attachment payload.

The request `Content-Type` becomes the attachment media type.

A successful request returns HTTP 201 with:

- attachment ID
- original filename
- media type
- byte size
- SHA-256
- retention class
- blob status

The existing `/api/chat` endpoint remains JSON-only and unchanged.

## Why raw-body upload

The initial API deliberately does not use multipart/form-data.

One request represents one attachment.

This avoids an unnecessary multipart dependency and gives Web and
future native Apple clients a simple streaming upload contract.

## Upload limits

Corvus backend semantic limit:

`32 MiB`

Environment variable:

`CORVUS_ATTACHMENT_MAX_BYTES=33554432`

Nginx hard request ceiling:

`40 MiB`

This provides two boundaries:

1. Nginx rejects clearly excessive requests before application handling.
2. Corvus retains authority over the actual attachment policy.

## Streaming

Nginx uses:

`proxy_request_buffering off`

The backend consumes incoming request chunks incrementally.

The storage adapter uses bounded spooling and then delegates to the
content-addressed attachment storage layer.

The complete attachment does not need to reside in Python memory.

## Oversize streaming regression

During real deployment acceptance, a 33 MiB upload initially produced:

- Uvicorn backend response: HTTP 413
- client-visible Nginx response: HTTP 502

Root cause:

The backend returned 413 immediately from `Content-Length` while Nginx
was still streaming the request body to the upstream server.

The upstream therefore finished before the proxy completed forwarding
the body.

The implementation was corrected so that once the backend byte limit
is exceeded:

1. no further payload bytes are written to temporary storage
2. the remaining request body is drained
3. no attachment metadata or raw blob is persisted
4. HTTP 413 is returned after safe stream completion

Real production retest:

`33 MiB -> Private Nginx -> HTTP 413`

Private attachment counts remained unchanged.

This closes the streaming early-response 502 regression.

## Private policy

Private Corvus uses:

`CORVUS_ATTACHMENT_DEFAULT_RETENTION=STANDARD`

Private deployment acceptance confirmed rejected oversized requests
produce no attachment persistence.

Existing canonical messages remained unchanged.

## Demo policy

Demo Corvus uses:

`CORVUS_ATTACHMENT_DEFAULT_RETENTION=EPHEMERAL`

A real 2 MiB attachment was uploaded through the deployed Demo Nginx
endpoint.

Acceptance confirmed:

- HTTP 201
- one attachment record
- one raw blob
- retention class EPHEMERAL

The normal Demo reset was then executed.

After reset:

- attachment records: 0
- attachment blobs: 0
- raw attachment directory removed
- Demo integrity: ok
- Private data unchanged

Demo raw attachment payloads remain excluded from reset backup archives.

## Nginx deployment

Both Private and Demo Nginx configurations now include:

`client_max_body_size 40m;`

and:

`proxy_request_buffering off;`

Private and Demo API systemd units explicitly define their attachment
size and retention policies.

## Acceptance results

Verified:

- isolated real HTTP upload > 1 MiB
- HTTP 201 success
- duplicate content creates independent attachment evidence IDs
- duplicate content shares one physical SHA-256 blob
- empty upload rejection
- 32 MiB backend semantic limit
- oversize request creates no attachment persistence
- oversize request body is fully drained
- 40 MiB Nginx hard ceiling
- Private STANDARD retention
- Demo EPHEMERAL retention
- Demo daily reset lifecycle
- Private / Demo isolation
- `/api/chat` JSON contract preservation
- attachment storage contract
- temporal adapter contract
- personality runtime contract

## Result

`A3_ATTACHMENT_UPLOAD_FINAL_ACCEPTANCE: PASS`

`A3.1 — Attachment Foundation COMPLETE`

The next stage is:

`A3.2 — Vision v1`

A3.2 should connect stored image attachments to the already verified
Qwen3.5 multimodal runtime without creating a second conversation
authority.
