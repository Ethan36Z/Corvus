# A3.3 Voice v1 Backend

Date: 2026-09-14

## Status

A3.3b Voice backend implementation completed and validated.

Maturity:

`SEAL_CANDIDATE`

Scope:

- audio attachment ingestion
- localhost Whisper STT
- transcript provenance
- SQLite-first voice conversation runtime
- voice API orchestration
- transient voice modality semantics
- real Mac audio end-to-end validation

This checkpoint does not include TTS or microphone UI.

---

## Architecture

Voice v1 follows:

```text
client audio
→ attachment storage
→ canonical [Voice message]
→ raw audio provenance link
→ Whisper STT
→ TRANSCRIPT attachment artifact
→ Working Context
→ Qwen
→ assistant reply
→ SQLite
→ derived dense sync
```

The important evidence rule is:

> Preserve what the user provided.
> Preserve what Corvus perceived.
> Never confuse perception with canonical evidence.

Raw audio is the supplied evidence.

The STT transcript is derived perception.

The transcript is not stored as if it were typed user text.

---

## Canonical evidence semantics

For a voice turn, the canonical user message is:

```text
[Voice message]
```

The raw audio attachment is linked to that message.

Whisper output is stored separately as:

```text
artifact_kind=TRANSCRIPT
producer=whisper.cpp
producer_version=small-multilingual
```

This means STT output remains:

- attributable
- replaceable
- correctable
- distinct from original evidence

---

## SQLite-first failure ordering

Voice processing follows:

```text
canonical user message
→ raw attachment link
→ STT
→ Working Context
→ model
→ assistant persistence
→ dense sync
```

STT failure occurs only after canonical evidence and raw attachment
provenance are safely stored.

Validated contract:

```text
STT FAILURE PRESERVES RAW EVIDENCE OK
```

Dense indexing remains derived state and cannot erase canonical
conversation evidence.

---

## STT runtime

Runtime:

- whisper.cpp
- `ggml-small.bin`
- CPU-only
- 8 threads
- HTTP server
- localhost test endpoint: `127.0.0.1:8104`

GPU remains available for Qwen.

Real Mac Voice Memo input:

```text
我们今天测试Corvus的语音功能
This is an English sentence.
I hope Corvus can understand Chinese and English.
```

Vocabulary prompting successfully corrected the project name `Corvus`.

Prompt vocabulary used during validation:

```text
Corvus Ethan FoxLuma FoxRove PawCareHub
```

---

## API contract

`POST /api/chat` now supports:

```json
{
  "session_id": "...",
  "attachment_id": "...",
  "attachment_mode": "voice"
}
```

For voice mode, the API owns the canonical marker and does not trust
client-provided text as canonical speech content.

The API response exposes:

- transcription status
- transcript artifact id
- transcript
- transcription errors when applicable

Existing text and vision behavior remains backward compatible.

---

## Transient modality semantics

The local text model does not directly consume raw audio.

For voice turns only, Corvus adds a transient system-context note
explaining that the current text came from speech recognition and may
contain transcription errors.

This note is not persisted into:

- SQLite Evidence Log
- FTS
- attachment artifacts
- user memory

It exists only for the current model invocation.

This prevents the model from incorrectly claiming that Corvus cannot
process audio merely because the model component receives text.

---

## Validation

### Transcription adapter

```text
TRANSCRIPTION ADAPTER CONTRACT OK
TRANSCRIPT ARTIFACT PROVENANCE OK
NON-AUDIO REJECTION OK
```

### Vision regression

```text
RUNTIME BACKWARD SIGNATURE CONTRACT OK
TEXT TURN REGRESSION CONTRACT OK
VISION TURN ORDER CONTRACT OK
LINK FAILURE PRESERVES USER EVIDENCE OK
VISION FAILURE PRESERVES CANONICAL EVIDENCE OK
A3 VISION CONVERSATION RUNTIME: PASS
```

### Voice runtime

```text
VOICE SQLITE-FIRST ORDER OK
VOICE TRANSCRIPT PERCEPTION OK
VOICE CURRENT-TURN MODEL INPUT OK
STT FAILURE PRESERVES RAW EVIDENCE OK
A3.3 VOICE CONVERSATION RUNTIME: PASS
```

### Voice API

```text
VOICE API CANONICAL MARKER OK
VOICE API TRANSCRIPTION RESPONSE OK
TEXT API BACKWARD COMPATIBILITY OK
A3.3 VOICE API CONTRACT: PASS
```

### Real audio E2E

A real `.m4a` Voice Memo recorded on Mac was:

1. uploaded through `/api/attachments`
2. persisted as an attachment
3. sent through `/api/chat` in voice mode
4. transcribed by whisper.cpp
5. stored as a TRANSCRIPT artifact
6. passed into Working Context
7. answered by Qwen
8. persisted to SQLite

Final semantic validation:

```text
voice_modality_semantics=PASS
canonical_voice_marker=PASS
derived_transcript_provenance=PASS
assistant_persistence=PASS

A3_3B_REAL_VOICE_SEMANTIC_E2E_PASS
```

The final model response correctly understood that the user had supplied
spoken audio rather than claiming that Corvus was unable to process it.

---

## Temporary E2E retrieval note

The isolated E2E environment used a fresh temporary data directory.

Its SQLite schema was initialized, but its LanceDB dense table was not.

Therefore the first real E2E correctly reported:

```text
retrieval=DEGRADED
dense=DEGRADED
Table 'evidence_dense_v1' was not found
```

This was expected for the disposable test environment.

It did not affect:

- STT
- model inference
- canonical message persistence
- attachment persistence
- transcript artifact persistence
- assistant persistence

This also demonstrated the existing Corvus rule that derived index
failure must not destroy canonical conversation evidence.

---

## Files

Implementation:

- `app/transcription.py`
- `app/conversation_runtime.py`
- `app/playground_api.py`

Tests:

- `tests/test_transcription_adapter.py`
- `tests/test_voice_conversation_runtime.py`
- `tests/test_voice_api_contract.py`

---

## Deferred

Not part of this checkpoint:

- TTS
- Web push-to-talk UI
- VAD
- streaming STT
- barge-in
- realtime duplex voice
- transcript search / historical Evidence Recall integration
- final raw-audio retention policy
- native Apple microphone integration

Those remain later A3.3 work.

---

## Checkpoint conclusion

A3.3b now provides a working backend path:

```text
real spoken audio
→ Corvus perception
→ persistent provenance
→ local model response
```

without confusing STT-derived text with original user evidence.

`A3_3B_VOICE_BACKEND_SEAL_CANDIDATE`
