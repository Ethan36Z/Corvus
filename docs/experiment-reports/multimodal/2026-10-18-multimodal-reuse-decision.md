# Corvus — Multimodal Reuse Decision

Date: **2026-10-18**

Verdict: **MULTIMODAL_REUSE_DECISION**

Mode: completed read-only audit; documentation publication only.

Objective: choose the smallest practical STT, TTS and Vision integration for the existing Lab Open WebUI 0.6.5, reusing installed engines and preserving Corvus evidence ownership.

**Decision:** retain whisper.cpp, Kokoro and Qwen; reuse Open WebUI's recording, playback and image/camera interface. Implement narrowly scoped adapters and media privacy/ownership checks before enabling features. Recommended order: TTS, reviewed-text STT dictation, then one-image Vision. Full evidence-preserving voice messages remain a separate integration.

This report records the audit already completed in the operator session. Publication did not rerun the audit, tests or inference. It is an integration decision, not deployment or browser acceptance.

## Evidence labels and publication scope

- **Verified:** directly inspected local source, selected non-secret runtime metadata/configuration, or non-mutating health responses during the completed audit.
- **Historical:** existing A3 acceptance records; not a new runtime test or proof of current browser reliability.
- **Recommendation:** proposed future implementation, not an installed feature.
- **Unknown:** not established by the audit; no measurement or success is inferred.

The public copy omits account-specific paths, private identities, credentials, cached media, conversation content, personal memory and database contents. Loopback ports and code paths are retained where needed to explain interfaces. Configuration inspection was limited to selected non-secret settings and installed Function metadata. No raw terminal transcript is included.

## 1. Verified Lab baseline

| Item | Completed audit observation |
| --- | --- |
| Lab branch | `lab/ow2e-console` |
| Lab HEAD | `50a63850f83506724aaff4c2af4f50811d00d646` |
| Worktree | Clean |
| Open WebUI | Running WebUI reported version `0.6.5` |
| Running image | `corvus-open-webui:0.6.5-arena-ui2.1-https-r03b` |
| Active Compose order | `deploy/lab/compose.webui.yml` → `compose.boot.yml` → `compose.arena-ui2.yml` → `compose.https.yml` |
| Installed Function | Existing active, non-global `corvus_pipe`; source matched reviewed Lab implementation |
| Pipe settings | Lab API port `18096`, `WEB_MODE=auto`, timeout 300 seconds, Arena enabled |
| WebUI permissions | Configured STT, TTS, file-upload and call permissions were false |
| Native Web search | Remains disabled; no native search activation was part of this audit |
| Service availability | WebUI, Lab API, Whisper, Kokoro and Qwen health endpoints returned HTTP 200; API/model health OK |

The installed WebUI audio router, configuration and middleware file hashes matched the inspected pinned source snapshot. The running image and Compose metadata were checked rather than treating a base Compose file or public main branch as runtime truth. See the preceding [W2.2 activation checkpoint](../web/2026-10-18-w2-2-operator-handoff-activation.md).

Permission defaults are not a universal backend authorization boundary: inspected UI controls allow administrator bypass in relevant places, and group/user/device settings were not exhaustively audited. No authenticated audio configuration endpoint exposing keys was called. The unauthenticated public configuration response did not establish effective audio settings for every signed-in user.

## 2. Corvus STT implementation

**Verified:** `app/transcription.py` sends multipart audio to whisper.cpp `/inference`, with language/prompt fields and JSON response format. It validates attachment existence, audio media type and blob integrity before transcription; successful text becomes a derived `TRANSCRIPT` attachment artifact with producer information.

The running service uses multilingual `ggml-small.bin`, CPU inference, eight threads, automatic language detection and ffmpeg conversion. It is published only on loopback port `8104`. Lab has no explicit STT environment override; the inspected defaults point to this service with a 60-second timeout. The service is already shared; no new model load is required.

**Historical:** A3 records describe real Mac audio, Chinese/English transcription and subsequent Qwen response. Voice v1 retains raw audio and distinguishes transcription from original evidence. Recognition mistakes remain possible, particularly for short speech, mixed language and names.

Reviewed references: `app/transcription.py`, `app/conversation_runtime.py`, `tests/test_transcription_adapter.py`, `tests/test_voice_conversation_runtime.py`, `tests/test_voice_api_contract.py`, and the A3 voice backend/push-to-talk logs dated 2026-09-14 and 2026-09-15. Tests cover request/provenance contracts, user-first ordering and STT-failure preservation; they were inspected, not rerun.

## 3. Open WebUI 0.6.5 STT capabilities

**Verified:** the existing microphone UI records audio, calls the authenticated transcription endpoint, and inserts returned text into the editable composer. Submission may follow a user setting for speech auto-send. This is naturally a dictation interface.

The default local backend is `faster-whisper`, not the installed whisper.cpp process. Its loader can attempt a download following local initialization failure. Selecting that default is therefore not equivalent to reusing the existing service and can introduce another model/runtime.

The supported external OpenAI-style branch calls `<base>/audio/transcriptions` with a multipart `file` and model. Existing whisper.cpp instead exposes `/inference`; changing a base URL alone does not align those contracts. The inspected OpenAI STT request has no explicit `requests.post` timeout argument.

The pinned recorder creates `MediaRecorder(stream)` without selecting an encoding, then labels its Blob `audio/wav` and filename `recording.wav`. **Relabeling does not convert the captured bytes.** The OpenAI backend branch includes format detection and conversion, but that code is not proof of Mac/iPhone compatibility. The transcription endpoint also has a restricted MIME allowlist.

Native transcription writes audio and transcript files under the WebUI cache. No Corvus raw-audio attachment or canonical transcript artifact is created merely by inserting the transcript into the composer.

## 4. STT comparison and recommendation

| Choice | Benefit | Persistence and integration cost |
| --- | --- | --- |
| WebUI dictation + existing whisper.cpp | Smallest path to speech-assisted ordinary chat; editable text before Send | Small protocol/format/privacy adapter; canonical evidence is user-confirmed text, without A3 raw-audio provenance |
| A3 Voice v1 + WebUI interface | Preserves raw audio, voice marker and derived transcript provenance | Requires an audio attachment UI/ownership bridge and a narrowly supported Pipe voice path |
| WebUI default local Whisper | Existing native backend code | Duplicates the installed STT runtime/model; no demonstrated need |

**Recommendation:** first release explicitly labeled **dictation**, using the existing Whisper engine and WebUI recording UI. Require review and explicit Send; keep speech auto-send off initially. This does not silently replace A3 Voice v1.

Minimum adapter: map the OpenAI-style request to `/inference`, bound upload size and duration, handle actual encoding, return `{text}`, and clean private temporary audio/transcripts. Keep the normal text Pipe unchanged. A3 attachment/transcription/runtime components remain reusable for later evidence-preserving voice messages.

Known blockers: protocol mismatch, recording-format labeling, cache privacy and disabled permissions. Real testing still needed: Mac/iPhone recordings, Chinese, English, mixed speech, cancellation, permission denial, timeouts and cleanup. Recommended integration order: **second**.

## 5. Corvus Kokoro TTS implementation

**Verified:** `app/tts.py` treats speech as derived presentation. It calls existing Kokoro `/v1/audio/speech`, explicitly requests WAV and validates the RIFF/WAVE response. Defaults are model `kokoro`, voice `af_mica`, language `z`, speed `0.95`, and a 60-second timeout. Lab has no overriding TTS settings.

The existing CPU-only Kokoro service is loopback-bound on `8105`, uses `hexgrad/Kokoro-82M-v1.1-zh`, and has a read-only voice mount. No new engine is required.

The Corvus TTS endpoint loads an existing assistant message, rejects missing/non-assistant messages, and returns `audio/wav` with `Cache-Control: private, no-store`. Speech does not replace canonical assistant text and is not persisted by default.

**Historical:** the A3.3c record reports Chinese playback acceptance and acceptable pronunciation of project names. This is not fresh bilingual listening or current iPhone acceptance.

Reviewed references: `app/tts.py`, the TTS endpoint in `app/playground_api.py`, `tests/test_tts_adapter.py`, `tests/test_tts_api_contract.py`, and `docs/project-logs/2026-09-15-a3-3c-tts-backend.md`. The inspected tests cover request parameters, WAV validation, failures and assistant-message provenance; they were not rerun.

## 6. Open WebUI TTS capabilities

**Verified:** existing response speaker controls provide playback/stop. With an external TTS engine, the UI splits displayed response text and calls the authenticated audio speech route. That route can forward OpenAI-compatible speech requests. Kokoro supports the same speech endpoint structure and MP3/WAV formats; WebUI caches the external response as MP3.

Two concrete mismatches prevent treating direct configuration as a complete integration:

1. Installed Kokoro's voice list is `{"voices": ["voice-name", ...]}`; WebUI expects entries with `id` and `name`. The inspected WebUI parser otherwise falls back to generic OpenAI voice names.
2. WebUI's normal speech request omits Corvus's explicit `lang_code="z"` and speed `0.95`. Installed Kokoro derives language from the voice prefix when language is absent. Selecting `af_mica` alone does not reproduce Corvus's accepted Chinese parameters.

WebUI also provides browser speech synthesis and a browser-Kokoro option. Browser speech depends on installed/device voices. Browser-Kokoro introduces client-side model loading and is unnecessary for reusing the existing server engine.

## 7. TTS comparison and recommendation

**Recommendation:** keep existing Kokoro, reuse WebUI's speaker UI, and adapt the existing audio backend rather than changing the chat Pipe.

Reuse the engine, installed voice, canonical text and playback controls unchanged. The minimum adapter corrects voice-list representation, selects explicit supported language/voice/speed parameters, bounds input/deadlines and returns private transient audio instead of a shared persistent cache. MP3 is compatible with the inspected Kokoro schema; Corvus's existing WAV request need not be forced through a route that labels output MP3.

Existing Corvus speech preparation/parameter behavior is reusable. If the Corvus message-ID endpoint is reused, add ownership verification rather than exposing arbitrary message IDs. Alternatively synthesize authorized displayed text through the authenticated WebUI audio route without reading Corvus messages or submitting a turn.

Known blockers: voice-list mismatch, Chinese-language defaults and audio/text cache privacy. Real tests: Chinese/English/mixed text, names, format/MIME playback, interruption, iPhone user gestures and background behavior. Browser speech synthesis can be an optional device-dependent convenience, but was not quality-tested.

Recommended integration order: **first**, manual playback only. It is independent of canonical chat writes and needs no additional inference model.

## 8. Corvus Qwen Vision implementation

**Verified:** the running shared llama.cpp uses Qwen3.5-9B Q5_K_M and its matching BF16 multimodal projector. The command includes `--mmproj`, `--no-mmproj-offload`, GPU language-model offload and an 8192-token context, on loopback port `8095`.

`app/vision_input.py` resolves a retained attachment, verifies blob integrity/size and PNG/JPEG signatures, then creates a transient image data URL for the current model-facing user message. Vision v1 accepts one image; its separate model-facing limit is 16 MiB.

`process_turn` persists user text first, links the attachment, constructs existing text context, supplies transient image input, then persists assistant text and derived dense state. Raw image encoding is not inserted into canonical message text. Historical image reinjection and visual retrieval are outside this scope.

**Historical:** A3 logs record deterministic image understanding, isolated and deployed attachment provenance, and text regressions. They do not prove current WebUI integration or broad visual/OCR accuracy.

Reviewed references: `app/vision_input.py`, `app/attachment_upload.py`, `memory/attachments.py`, `app/conversation_runtime.py`, Vision/upload tests, and the A3 attachment/Vision project logs dated 2026-09-08. Tests were inspected, not rerun.

## 9. Open WebUI Vision capabilities

**Verified from pinned source:** the existing interface supports image selection, preview, and a mobile camera file input with `capture="environment"`. The image path reads data URLs and builds user-message content containing `text` and `image_url` entries. This is not automatically a Corvus attachment ID or canonical provenance link.

WebUI recognizes more image formats than A3, including formats outside PNG/JPEG. Camera acceptance of `image/*` does not establish that an iPhone's chosen representation is accepted by Corvus. Its history serialization can resend earlier image messages, whereas A3's model-facing image contract is current-turn only.

WebUI file records have owner/access checks, but the ordinary image data-URL path is distinct from those records. Do not assume every image is an ownership-checked uploaded file.

## 10. Vision comparison and recommendation

**Recommendation:** keep the shared Qwen/projector and A3 attachment/runtime implementation; reuse WebUI image preview and camera controls through a narrow attachment bridge.

Minimum adapter:

- Accept one current-turn PNG/JPEG and explicit accompanying text.
- Validate MIME, bytes, size and authenticated saved-chat ownership before forwarding.
- Store the image once as Lab attachment evidence; pass the resulting attachment ID into the existing Corvus turn path.
- Preserve distinct WebUI presentation state and Corvus evidence authority; do not create a second canonical conversation writer.
- Exclude prior image history from new current-turn image ingestion; reject extra images and unsupported media.
- Reject caller-supplied external image URLs and filesystem paths; no arbitrary image fetching.

Do not merely remove media guards. Known blockers are representation conversion, ownership, disabled permissions and differing request limits. Real tests: Mac upload, iPhone camera/photos, format rejection, size limits, cross-user denial, history behavior and uncertain completion. Recommended integration order: **third**.

## 11. Pipe/API compatibility

The installed Pipe validates authenticated user identity and consistent saved-chat identity, derives the Corvus session mapping, uses an administrator-selected loopback endpoint, suppresses helper tasks, and performs no automatic transport retry. Its current source rejects files, attachments, image/audio/video fields, media features, tool operations and non-string message content.

- TTS presentation can remain outside the chat Pipe.
- Reviewed-text dictation can use the unchanged text Pipe.
- Vision and full A3 voice need deliberately scoped media support, including retained metadata and file arguments; guard removal is insufficient.

Corvus API already has raw-body attachment upload, attachment content/transcript reads, voice/vision chat parameters and assistant-message TTS. These are local contracts, not automatically safe public WebUI-user APIs. Keep current endpoint/identity validation, no-retry behavior and uncertain-outcome errors.

Memory A/B remains text-only. Do not enable native WebUI search or create another search pipeline as part of multimodal work.

## 12. Authentication and media security

**Verified concern:** the inspected WebUI audio router writes recordings/transcripts and speech audio/request text to disk. Its cache mount lacks a per-user authorization dependency in the inspected source. FoxGate protects realm entry, but does not establish WebUI-user ownership of cached files. This is a source-derived privacy gap; no cached media or private files were read, and no exploit was attempted.

Prefer transient processing and authenticated audio responses. If caching is retained, require explicit retention and owner-scoped access; unguessable names are not ownership checks. Prevent private media/text in logs and delete temporary material on errors as well as success.

Existing Corvus UUID attachment routes and message-ID TTS do not themselves validate WebUI-user ownership. Keep API/service ports loopback-only and add a server-derived user/chat/attachment ownership bridge before remote use. Do not trust caller-supplied IDs, session mappings, paths or service destinations.

**Verified limits:** active Lab FoxGate permits 10 MiB request bodies; Corvus upload defaults to 32 MiB and Vision has a 16 MiB model-facing limit. Base64 enlarges image requests. Choose a smaller coordinated MVP ceiling instead of silently raising infrastructure limits. No FoxGate, Cloudflare, authentication or network change is recommended as a documentation action.

## 13. Canonical persistence implications

| Feature | Required evidence boundary |
| --- | --- |
| Dictation | User reviews generated text and explicitly sends it as confirmed text; no claim of raw-audio provenance |
| A3 Voice v1 | Raw audio attachment is supplied evidence; `[Voice message]` is canonical user marker; transcript is derived perception |
| TTS | Existing assistant text stays canonical; audio is derived presentation and must not submit a chat turn |
| Vision | User text and retained image attachment/provenance remain canonical; image encoding is transient model input |

Keep existing user-first and assistant persistence ordering. A failure after user persistence must not be represented as proof that nothing was saved. No playback/transcription action should duplicate canonical turns, and no uncertain chat request may be resubmitted automatically.

Retain existing Hindsight lifecycle and Memory Arena boundaries. The audit did not access personal memory, private conversation content or canonical rows, and did not submit any chat turn.

## 14. CPU/GPU resource considerations

Whisper and Kokoro already run on CPU. Qwen uses the existing GPU language model with the projector kept off GPU. This avoids another model service or GPU model swapping for the proposed MVP.

The read-only GPU snapshot reported an RTX 2080 Ti with 11264 MiB total and 8997 MiB used. This is one occupancy snapshot, not an inference capacity or concurrency benchmark. No new STT/TTS RAM, CPU utilization, throughput or multimodal latency measurement was taken.

Images still consume CPU/projector work and model context. Existing shared-engine availability does not establish contention-free concurrent use. Avoid WebUI-local Whisper, browser-Kokoro or a second Qwen runtime; bound requests and test shared-resource behavior in a later authorized stage.

## 15. Mac/iPhone compatibility and license implications

Mac and iPhone are browser clients of the existing server engines. The HTTPS/PWA derivative is installed; this supplies the intended secure origin but does not prove installed-PWA microphone, camera or audio behavior.

Mac audio has historical A3 evidence. Current Safari/PWA recording format, permission lifecycle, camera encoding, playback gestures, background interruption and mixed-language quality remain unverified. Do not infer iPhone acceptance from desktop source inspection.

License observations from the completed audit:

- Pinned WebUI source has BSD-3-Clause terms; retain version 0.6.5 and notices.
- Installed whisper.cpp has MIT terms; upstream [Whisper license](https://raw.githubusercontent.com/openai/whisper/main/LICENSE) is MIT.
- [Kokoro-82M-v1.1-zh model card](https://huggingface.co/hexgrad/Kokoro-82M-v1.1-zh) declares Apache-2.0 and Chinese/English support.
- [Qwen3.5-9B model card](https://huggingface.co/Qwen/Qwen3.5-9B) declares Apache-2.0.
- The [upstream Kokoro-FastAPI license](https://raw.githubusercontent.com/remsky/Kokoro-FastAPI/master/LICENSE) is Apache-2.0, but this does not independently verify the exact installed fork, community voice assets, converted model artifacts or every bundled dependency.

Artifact-specific provenance and attribution review remains necessary before redistribution. This audit is not a complete dependency/license inventory. No newer WebUI code, new engine or dependency was adopted.

## 16. Final component reuse decisions

| Feature | Engine | UI | Adapter scope | Relative maintenance |
| --- | --- | --- | --- | --- |
| TTS | Existing CPU Kokoro | Existing speaker controls | Voice schema, explicit language/format, bounded private audio route | Smallest independent integration |
| STT dictation | Existing CPU whisper.cpp | Existing recorder/editable composer | OpenAI-style protocol to `/inference`, real format handling, deadlines/cleanup | Small, with browser-format testing |
| Vision | Existing shared Qwen/projector | Existing image/camera preview | One-image ownership/provenance bridge into A3 runtime | Larger than audio presentation; security-sensitive |
| Full voice evidence | Existing Whisper and A3 runtime | Later WebUI adaptation | Raw-audio attachment, provenance and guarded voice submission | Deferred; not equivalent to dictation |

No demonstrated need exists for another model, frontend, agent or multimodal framework. This is an architecture recommendation based on inspected interfaces and historical evidence, not a fresh comparative quality benchmark.

## 17. Minimum integration plan

1. **TTS first:** adapt existing WebUI audio handling to the installed Kokoro contract, preserve explicit Chinese parameters, remove shared persistent audio/text caching, and retain manual play/stop. Test mocked protocol, privacy, errors and no canonical writes offline.
2. **Dictation second:** route existing recorder output to existing Whisper with format-aware bounded processing and private cleanup. Return editable text, require explicit Send, and leave the normal text Pipe unchanged.
3. **One-image Vision third:** add authenticated current-turn ownership/provenance forwarding, coordinated limits, strict PNG/JPEG validation and narrow Pipe support. Keep other media and Arena paths rejected.
4. Separately authorize controlled Mac/iPhone acceptance and shared-resource checks. Preserve no-retry/uncertain-outcome behavior. Defer full voice-evidence messages and realtime/full-duplex voice.

Use existing dependencies and services; implement no new runtime service or generic HTTP proxy. Each step needs review and authorization before deployment.

## 18. Remaining blockers and unknowns

- Cache privacy and per-user media ownership must be resolved before enabling remote media.
- STT needs endpoint/format adaptation and an explicit dictation-versus-voice-evidence product boundary.
- TTS needs voice-list and language parameter adaptation; English/mixed-language listening quality is not freshly verified.
- Vision needs safe current-turn attachment forwarding, not broad removal of Pipe guards.
- Group/user/browser effective settings and current iPhone PWA behavior were not exhaustively inspected.
- No new inference, upload, live chat, recognition/playback acceptance, throughput measurement or offline test execution occurred during the audit.
- No code/configuration change, deployment, restart or database write was performed by the audit. Report publication changes documentation only; running services remain unchanged by publication.

**Final decision: MULTIMODAL_REUSE_DECISION.** Existing engines plus existing WebUI controls are the MVP foundation. Adapter correctness, privacy and ownership are the next implementation scope; daily-use acceptance remains pending.
