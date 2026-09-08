# A3.1a Attachment Storage Foundation

Date: 2026-09-08

## Goal

Establish the persistent storage boundary required for Corvus
multimodal input without changing the existing A0-A2 conversation
authority.

This checkpoint does not yet add an HTTP upload API or UI attachment
controls.

## Architectural principles

Raw user-provided files are evidence.

Derived interpretation is not canonical truth.

The system therefore separates:

1. physical content blobs
2. attachment/evidence occurrences
3. message relationships
4. derived artifacts

Large raw bytes are governed by retention policy rather than assumed
to remain online forever.

## Data model

New SQLite structures:

- `attachment_blobs`
- `attachments`
- `message_attachments`
- `attachment_artifacts`

### attachment_blobs

Represents physical content-addressed storage.

The SHA-256 digest is the blob identity.

The same physical content uploaded multiple times is stored once.

### attachments

Represents one attachment/evidence occurrence.

Multiple attachment records may reference the same physical blob.

This preserves event identity without duplicating raw bytes.

### message_attachments

Associates attachments with canonical Corvus messages and preserves
attachment ordering.

### attachment_artifacts

Stores derived, correctable representations such as future:

- vision descriptions
- STT transcripts
- document text
- OCR output

Derived artifacts do not replace the original evidence.

## Storage

Attachment storage lives under the active `CORVUS_DATA_DIR`.

Example:

`attachments/blobs/<sha-prefix>/<sha256>.blob`

The database stores relative paths rather than machine-specific
absolute paths.

Raw blobs are mode 0600.

Attachment storage directories are mode 0700.

Reads validate both file size and SHA-256.

Path traversal outside `CORVUS_DATA_DIR` is rejected.

## Streaming ingestion

The storage core accepts streaming input rather than requiring the
entire file to be loaded into memory.

A configurable byte limit can terminate oversized ingestion.

Temporary partial files are removed after success or failure.

## Deduplication

Two evidence occurrences containing identical bytes produce:

- two attachment identities
- one SHA-256-addressed physical blob

This separates memory/event identity from storage identity.

## Retention vocabulary

Initial attachment retention classes:

- `PERMANENT`
- `STANDARD`
- `EPHEMERAL`

Blob lifecycle state currently supports:

- `PRESENT`
- `PURGED`

Detailed lifecycle execution remains future A3 work.

## Private migration

The Private Corvus SQLite database was backed up using the SQLite
online backup API before migration.

Pre/post validation:

- integrity: `ok`
- messages: 80 -> 80
- assertions: 0 -> 0
- assertion-message basis: 0 -> 0
- assertion-assertion basis: 0 -> 0
- messages FTS: 80 -> 80
- existing `messages` schema unchanged
- new attachment tables present
- new attachment indexes present

No attachment rows were introduced during migration.

Private API remained healthy.

## Demo migration

Demo migration was performed separately from Private.

Pre/post validation:

- integrity: `ok`
- messages: 0 -> 0
- existing canonical tables unchanged
- existing `messages` schema unchanged
- new attachment tables and indexes present

Private remained unchanged at 80 messages.

Demo API remained healthy.

## Demo lifecycle integration

Demo Corvus is reset to a clean baseline daily.

A synthetic Demo attachment was created and a real reset was executed.

The reset verified:

- Demo message removed
- attachment metadata removed
- raw attachment directory removed
- Demo returned to an empty database
- Private remained unchanged
- Private and Demo APIs remained healthy

The Demo reset backup policy was changed so raw `attachments/`
payloads are excluded from the reset backup archive.

The backup still contained `corvus.db`.

The synthetic raw attachment was confirmed absent from the backup.

This prevents recruiter/demo uploads from silently surviving in the
14-day reset backup retention window.

## Regression contracts

Passing contracts:

- attachment storage round trip
- SHA-256 tamper detection
- path traversal rejection
- content-addressed deduplication
- streaming ingestion
- upload byte limit
- temporary-file cleanup
- temporal adapter contract
- personality runtime contract

## Result

`A3_ATTACHMENT_STORAGE_FOUNDATION: PASS`

Engineering checkpoint:

`A3.1a — Attachment Storage Foundation COMPLETE`

Next:

`A3.1b — Attachment Upload API`

The next checkpoint should expose bounded, validated HTTP attachment
ingestion while preserving the same storage and evidence model.
