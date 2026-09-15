# A3.3d — Push-to-Talk Voice UX

Date: 2026-09-15

Status:

**SEALED**

Project:

**Corvus — Persistent Personal AI on Consumer Hardware**

Stage:

**A3.3 — Voice v1**

Substage:

**A3.3d — Web Push-to-Talk Voice UX**

---

## 1. Goal

A3.3d turns the previously completed Voice backend into a usable
end-to-end voice messaging experience in the Corvus Web UI.

The goal is not realtime/full-duplex voice.

The goal is a reliable push-to-talk interaction:

microphone
→ audio evidence
→ STT
→ Corvus conversation runtime
→ text reply
→ optional TTS playback.

The text chat remains canonical for assistant replies.

For user voice input:

- the submitted audio is retained as attachment evidence according to
  attachment retention policy;
- the canonical user message remains `[Voice message]`;
- Whisper output is stored as a derived `TRANSCRIPT` artifact;
- transcript text is never silently treated as exact user wording.

Core principle:

**Store what the user provided.**

**Store what Corvus perceived.**

**Never confuse perception with truth.**

---

## 2. Final Voice v1 Architecture

Client:

Browser MediaRecorder
→ audio/webm or compatible browser audio format
→ attachment upload
→ `/api/chat` with `attachment_mode="voice"`.

Backend:

audio attachment
→ canonical `[Voice message]`
→ attachment/message linkage
→ Whisper STT
→ `TRANSCRIPT` artifact
→ Working Context
→ Qwen
→ assistant text reply
→ SQLite
→ dense synchronization.

Presentation:

assistant persisted text
→ optional Kokoro TTS
→ replay button.

Voice input presentation:

raw user audio
→ replayable voice bubble
→ optional derived transcript expansion.

---

## 3. Formal Whisper Runtime

Whisper was promoted from an earlier smoke-test container to a formal
Corvus Compose service.

Service:

`corvus-whisper`

Host endpoint:

`127.0.0.1:8104`

Image:

`ghcr.io/ggml-org/whisper.cpp@sha256:caf0cd77c922e9c53f10a9bc17c2f74cc2295d12e7b0f96b630fb3b3c55a0026`

Model:

`/models/ggml-small.bin`

Runtime:

- whisper.cpp server
- CPU inference
- 8 threads
- multilingual language auto-detection
- ffmpeg conversion enabled
- prompt:
  `Corvus Ethan FoxLuma FoxRove PawCareHub`

Persistent model source:

`/home/ethan/srv/shared/models/whisper`

Container policy:

`restart: unless-stopped`

---

## 4. Whisper Container Entrypoint Fix

The official Whisper image uses:

`ENTRYPOINT ["bash", "-c"]`

A normal Compose command list therefore caused only `whisper-server`
to be interpreted as the shell command while the remaining arguments
were not passed to the process as intended.

Symptoms included:

- default `ggml-base.en.bin` loading;
- GPU mode unexpectedly enabled;
- port 8104 never becoming ready.

The formal Compose service now explicitly overrides the image entrypoint:

`entrypoint: ["whisper-server"]`

and supplies only server arguments through `command`.

Validated runtime:

- model: `ggml-small.bin`
- GPU: disabled
- threads: 8
- HTTP server: ready on 8104.

---

## 5. Host NVIDIA Upgrade Incident

During deployment validation, the llama container temporarily failed
after a host package upgrade.

Observed state:

loaded NVIDIA kernel module:

`580.173.02`

installed userspace libraries / new DKMS module:

`580.178.04`

This produced:

`Failed to initialize NVML: Driver/library version mismatch`

and prevented the GPU-backed llama container from starting.

A host reboot loaded the matching NVIDIA module.

Validated post-reboot:

- NVIDIA driver: 580.178.04
- loaded kernel module: 580.178.04
- `nvidia-persistenced`: active
- llama server: healthy
- Corvus API health: OK.

This was a host runtime mismatch, not a Corvus application failure.

---

## 6. Browser Recording UX

The Web UI now includes a microphone control next to the normal send
control.

Recording uses:

`navigator.mediaDevices.getUserMedia`

with:

- echo cancellation
- noise suppression
- automatic gain control.

Preferred MediaRecorder formats:

1. `audio/webm;codecs=opus`
2. `audio/webm`
3. `audio/mp4`

Recording mode provides:

- animated voice activity presentation;
- elapsed recording time;
- cancel action;
- stop/send action.

The normal composer returns after the recording is submitted.

---

## 7. Warm Microphone Lease

Repeated `getUserMedia()` calls introduced noticeable microphone
startup latency.

A short-lived microphone lease was added.

The MediaStream may be reused for subsequent voice turns instead of
immediately closing and reopening the physical input device.

Important lifecycle rule:

the grace timer does **not** begin when recording ends.

The microphone remains warm while Corvus processes the turn:

recording stop
→ upload
→ Whisper
→ Qwen
→ assistant reply.

Only after the voice turn finishes does the 30-second microphone grace
period begin.

Therefore model response latency does not consume the user's warm-mic
window.

The microphone is released when:

- the grace period expires;
- voice capture fails and cleanup is required;
- the component is torn down.

This improves repeated voice-turn latency without keeping the
microphone permanently active.

---

## 8. Voice Message Bubble

Audio attachments are no longer rendered through the image attachment
renderer.

This removes the previous broken-image behavior where `audio/webm`
was incorrectly requested as an `<img>`.

Voice messages now have a dedicated presentation.

The voice bubble supports:

- play original submitted audio;
- stop playback;
- waveform-style presentation;
- transcript expansion.

The original `[Voice message]` engineering marker is hidden when a
valid audio attachment is present.

---

## 9. Safe Audio Playback

The existing attachment content endpoint was extended with an explicit
media allowlist.

Supported display/playback types now include the existing image types
plus selected audio types such as WebM, MP4, OGG, WAV and MPEG audio.

The endpoint remains read-only and still validates:

- attachment existence;
- retention state;
- blob availability;
- integrity.

Arbitrary attachment types are not exposed.

---

## 10. Transcript Read Path

Whisper transcription was already persisted in:

`attachment_artifacts`

with:

`artifact_kind = TRANSCRIPT`.

A read path was added for the latest artifact of a requested type.

A dedicated API endpoint exposes the derived transcript for an audio
attachment.

The Web UI loads this artifact only when the user requests the
transcript.

No second Whisper inference is required.

Semantics remain explicit:

**raw audio = user-provided evidence**

**TRANSCRIPT = derived perception**

The transcript does not replace or rewrite canonical evidence.

---

## 11. Assistant Voice Replay

Assistant text remains the canonical persisted reply.

A speaker control can request:

`GET /api/tts/{assistant_message_id}`

and play derived speech generated from the persisted assistant message.

TTS playback is presentation only.

It does not alter conversation history or memory.

---

## 12. Voice Model Stack

Current Voice v1 runtime:

Input:

Browser MediaRecorder

STT:

whisper.cpp
`ggml-small.bin`
CPU
8 threads

LLM:

Qwen3.5-9B-Q5_K_M
llama.cpp
RTX 2080 Ti

TTS:

Kokoro FastAPI zh
CPU
`af_mica`

This intentionally avoids frequent model swapping on the 11 GB GPU.

---

## 13. Runtime Ports

Current relevant private runtime:

- Whisper STT: `127.0.0.1:8104`
- llama.cpp / Qwen: `127.0.0.1:8095`
- Corvus private API: `127.0.0.1:8096`
- Corvus private Web: `127.0.0.1:8097`
- Kokoro TTS: `127.0.0.1:8105`

Port 8094 remains reserved for FoxGate Auth and was not touched.

---

## 14. Validation

Validated during A3.3d:

- browser microphone capture;
- WebM/Opus upload;
- ffmpeg conversion;
- Whisper multilingual inference;
- Chinese language detection;
- transcript artifact creation;
- voice turn through `/api/chat`;
- Qwen response;
- canonical persistence;
- dense recovery;
- raw voice replay;
- transcript expansion;
- assistant TTS replay;
- repeated voice turns;
- warm microphone reuse;
- private API health;
- private Web health;
- restart recovery of core runtime services.

Static validation:

- Python compile: PASS
- TypeScript compile: PASS
- Vite production build: PASS
- `git diff --check`: PASS
- Compose validation: PASS

---

## 15. Known Limitations

Voice v1 is intentionally not realtime voice.

Current interaction is turn-based push-to-talk.

Whisper `small` multilingual can make recognition mistakes,
particularly for:

- short utterances;
- mixed Chinese/English speech;
- uncommon names;
- project-specific terminology.

The original audio remains available so derived transcription can be
inspected rather than treated as unquestionable truth.

Realtime streaming STT, VAD-driven automatic turns, streaming TTS,
barge-in, echo handling and full-duplex conversation are deferred.

---

## 16. Deferred Realtime Voice

Future realtime voice should be implemented as a separate stage rather
than extending A3.3d indefinitely.

Candidate architecture:

continuous microphone
→ VAD
→ streaming / incremental STT
→ turn manager
→ LLM streaming
→ streaming TTS
→ interrupt / barge-in controller.

A first realtime-lite version may use automatic end-of-turn detection
while retaining the existing Whisper, Qwen and Kokoro engines.

Full-duplex voice is explicitly outside A3.3d.

---

## 17. Result

A3.3d establishes a usable Voice v1 for Corvus.

The user can:

- record a voice message;
- send it through the normal Corvus memory/conversation path;
- receive a normal persisted text response;
- replay the original voice evidence;
- inspect the derived Whisper transcript;
- hear the assistant reply through TTS;
- continue voice interaction with reduced microphone restart latency.

Status:

**A3.3d — SEALED**

Next major capability candidates:

- Web v1
- Realtime Voice
- Apple thin client / product packaging
