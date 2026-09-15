# A3.3c — Text-to-Speech Backend

Date: 2026-09-15

## Status

A3.3c TTS backend is complete and accepted.

## Architecture

Canonical assistant text remains the conversation record.

Speech is a derived presentation layer:

assistant message in SQLite
→ Corvus TTS API
→ speech-text preparation
→ local TTS adapter
→ Kokoro
→ WAV audio

TTS does not replace or mutate canonical assistant text.

Generated speech audio is not persisted by default.

## TTS Runtime

Engine:

- Kokoro-FastAPI-zh
- CPU-only
- loopback: 127.0.0.1:8105
- Docker Compose service: corvus-kokoro
- restart policy: unless-stopped

Model:

- hexgrad/Kokoro-82M-v1.1-zh

Voice:

- af_mica

Language:

- z

Default speed:

- 0.95

The container image is pinned by digest in compose.corvus.yml.

## Corvus Adapter

Added:

- app/tts.py

The adapter owns the narrow local TTS contract and hides the
underlying speech engine from the rest of Corvus.

It provides:

- derived speech-text preparation
- local HTTP synthesis
- WAV validation
- timeout handling
- unavailable-service handling
- upstream HTTP error handling

This preserves engine replaceability.

## API

Added:

GET /api/tts/{assistant_message_id}

The endpoint:

1. loads an existing message from canonical SQLite storage
2. rejects missing messages
3. rejects non-assistant messages
4. synthesizes the persisted assistant content
5. returns audio/wav

The chat endpoint is not coupled to TTS.

A TTS failure therefore does not invalidate or destroy the
canonical assistant reply.

## Validation

Passed:

- TTS adapter contract
- invalid-response contract
- timeout contract
- unavailable-service contract
- assistant-message provenance contract
- user-message rejection contract
- missing-message contract
- TTS API response contract
- TTS API failure contract
- existing Voice API regression suite
- compose validation
- Python static compilation
- git diff check

Real integration passed:

app/tts.py
→ corvus-kokoro
→ WAV
→ local playback

Private production-path E2E also passed:

persisted assistant message
→ Private Corvus API
→ /api/tts/{assistant_message_id}
→ TTS adapter
→ Kokoro
→ WAV
→ human listening validation

Human listening validation confirmed acceptable Chinese speech and
correct pronunciation of Ethan and Corvus.

## Product Boundary

Voice v1 keeps text and speech separate.

Text is canonical.

Speech is optional derived presentation.

Future Web UI work may add:

- voice replies toggle
- autoplay toggle
- replay control

Those UI features are outside this backend checkpoint.
