# TTS-1 — Kokoro × Open WebUI offline integration

Date: **2026-10-18**

Verdict: **TTS1_IMPLEMENTED_WITH_CONSTRAINTS**

**Implemented and committed locally; not deployed or enabled.** The existing Open WebUI 0.6.5 Read Aloud controls now have a prepared, authenticated, memory-only Kokoro adapter. The offline derivative image builds and its 22 focused tests pass. An existing baseline Pipe-checksum mismatch prevents a fully green broader branding/Arena regeneration suite; it was reproduced without TTS changes and is recorded below rather than bypassed.

This follows the [multimodal reuse decision](2026-10-18-multimodal-reuse-decision.md). No new model, dependency, frontend, runtime service, conversation writer or generic media framework was introduced.

## A. Baseline and source checkpoint

| Item | Verified result |
| --- | --- |
| Starting Lab branch | `lab/ow2e-console` |
| Starting and final Lab HEAD | `50a63850f83506724aaff4c2af4f50811d00d646` |
| Lab worktree | Clean; not edited by integration |
| Isolated implementation branch | `integration/tts1-kokoro-webui` |
| Implementation commit | `3793b13d1f6855d5df7a3b139d47036b1879e4e0` |
| Parent | Exact Lab baseline above |
| Reporting branch before this report | `reports/web-validation` at `8f181348228d5150078a31283f2669da3ac5f795` |
| Active WebUI image | `corvus-open-webui:0.6.5-arena-ui2.1-https-r03b` |
| Exact derivative base | `sha256:453f9f2c4cee37c5e0d158ed3fcbdfc1e099bc6ef55ab47a7cbcce8b7331df76` |

The complete reuse report, current Lab adapter/tests, pinned WebUI audio route and installed Kokoro API/codec source were inspected. The audio source SHA256 was `1626d6fd494097836018f72bc8579a72544d8012ffdfe85ae32c20a501a8e3ba`, matching the public cached source fixture. No assumption was made that public main matched Lab.

The implementation is local only. This documentation branch does not publish the implementation commit or its code history.

## B. Actual implementation and changed files

Exactly six files were added on the implementation branch:

| File | Purpose |
| --- | --- |
| `deploy/lab/tts/kokoro.py` | Fixed-destination, transient synthesis and single-voice response |
| `deploy/lab/tts/prepare_audio.py` | Fail-closed exact-source backend/frontend build patch |
| `deploy/lab/tts/Dockerfile` | Derivative of exact active HTTPS/UI-2.1 image; no dependency installation |
| `deploy/lab/compose.tts.yml` | Prepared final Lab-only override; not activated |
| `deploy/lab/tts/README.md` | Limits, offline checks, deployment prerequisites and rollback boundary |
| `tests/test_lab_webui_tts.py` | Focused synthetic route, privacy, transport and artifact tests |

No existing tracked implementation file was edited. Normal chat Pipe, Corvus API/runtime, canonical persistence, Web MVP, Hindsight and Arena source remain unchanged.

The build patch retains the exact native `/api/v1/audio/speech` and `/voices` route decorators and `Depends(get_verified_user)` signatures, replacing only those handler bodies. It removes unused speech-cache initialization. The helper is copied into the WebUI image; it does not import Corvus application/storage code.

The existing compiled response component contains a debug statement that prints prepared speech text. The derivative removes that one exact statement, guarded by the full asset hash. It preserves the existing Read Aloud controls and all other asset bytes; no frontend rebuild or new interface is added.

## C. Architecture and Kokoro compatibility

```text
Existing Read Aloud UI
  → existing authenticated WebUI speech route
  → fixed loopback Kokoro synthesis request
  → bounded in-memory WAV finalization/validation
  → private audio/wav response
```

The payload is server-controlled:

```json
{
  "model": "kokoro",
  "voice": "af_mica",
  "lang_code": "z",
  "speed": 0.95,
  "response_format": "wav",
  "stream": false,
  "return_download_link": false,
  "input": "<authenticated displayed text>"
}
```

Only `http://127.0.0.1:8105/v1/audio/speech` is used. Client input cannot select another URL, model, voice, language, format or speed. Input/optional model/voice are validated; unsupported fields, including arbitrary canonical message IDs, are rejected. Existing Corvus presentation-only whitespace preparation is preserved in the isolated adapter without importing its conversation runtime.

Kokoro's voice-list schema differs from WebUI's. The narrow solution returns the one supported installed voice as `{"voices":[{"id":"af_mica","name":"af_mica"}]}`. No voice discovery framework or upstream voice-list request is needed.

### Observed WAV compatibility detail

The installed Kokoro/PyAV writer was run in a separate network-disabled, read-only container using **240 zero-valued samples only**. No TTS service call, model loading or inference occurred. The codec produced 558 bytes, with 480 sample bytes at 24 kHz/16-bit/mono, but RIFF and data lengths were streaming `0xffffffff` sentinels.

Strict finite-header validation alone would reject that real codec behavior. The adapter therefore finalizes only the observed sentinel pair after bounded full receipt, using actual byte length, then validates the resulting PCM WAV. Inconsistent finite lengths, invalid audio, wrong MIME/encoding and oversized responses fail closed. No sample conversion or invented audio is performed. WAV bytes are returned as `audio/wav`, never mislabeled MP3.

This codec-only experiment is not live synthesis or a listening test. Full Kokoro output remains subject to separately authorized acceptance.

## D. Privacy and authentication protections

- Native verified-user authentication is retained. Missing/unverified synthetic users cannot reach the adapter in tests; existing user/admin role behavior is preserved.
- TTS uses the text supplied through the authenticated displayed-text interface. It does not assert that arbitrary client text is a verified canonical assistant message and does not fetch message IDs.
- No shared persistent audio cache, request-text JSON, temporary file or canonical database access exists in the new adapter. The old speech-cache creation/handler path is removed in the derivative.
- Kokoro download links are explicitly disabled. Inspection of the installed non-streaming route found its download-file writer conditional on that option.
- Success and adapter error responses use `Cache-Control: private, no-store`; audio uses `nosniff` and a fixed WAV MIME type.
- The adapter has no logging calls. Upstream bodies and exception text are not returned or logged. The private-text browser debug statement is removed. Audio-producing task results are Response objects, preventing asyncio debug task representations from printing returned audio bytes.
- Environment proxies, redirects and automatic retries are disabled; no client authorization/cookie/user-profile headers are forwarded to Kokoro.
- All processing is memory-only and bounded. Tests deny file and SQLite access during synthesis handling and capture logs using synthetic sentinel text.

This establishes the adapter's tested behavior, not a universal guarantee about the existing Kokoro service or all dependencies. Existing upstream operational logging was not reconfigured; a bounded live privacy review is still required before private use. No historical cache files were inspected, deleted or migrated.

The compiled asset filename is unchanged. Existing devices must close old clients and hard-reload/clear cached application assets before acceptance can assert the old browser debug call is absent. Previously loaded JavaScript is not remotely erased by an image build.

## E. Limits, cancellation and persistence

| Boundary | Implemented limit/behavior |
| --- | --- |
| Input | JSON only; 24 KiB body; 1–4000 characters before whitespace preparation |
| Input deadline | 5 seconds |
| Connection timeout | 3 seconds |
| Total synthesis/response deadline | 60 seconds |
| Audio response | At most 8 MiB; 24 kHz, 16-bit PCM, mono/stereo WAV |
| Provider/network/format failure | Sanitized HTTP 502 |
| Upstream/total timeout | Sanitized HTTP 504 |
| Input timeout | HTTP 408 |
| Client disconnect | Cancel local request/watch tasks and close upstream transport; HTTP 499 where a response remains possible |
| Automatic retries | None |

Closing the request does not prove that Kokoro stops computation it already admitted. WebUI's existing Stop button behavior is preserved; offline ASGI disconnect tests do not prove that every browser playback action aborts an in-flight fetch. Device behavior remains an acceptance requirement.

The adapter creates no user/assistant message, rewrites no existing message, triggers no Hindsight retain and changes no Arena result. The retained native authentication layer may perform its usual WebUI user-activity maintenance; this is distinct from canonical Corvus conversation persistence. Offline fixtures use isolated synthetic storage; no deployed database was read or written by the tests.

## F. Executed checks and actual results

| Check | Result |
| --- | --- |
| Final focused TTS suite in built derivative | **22 passed; zero failures/errors/skips** |
| Existing Pipe regression under isolated data/network-denial guard | **24 passed, one explicitly skipped; 25 discovered** |
| Existing Corvus TTS adapter script entry point | **Passed**, five function contracts |
| Existing Corvus TTS API script entry point | **Passed**, six function contracts |
| Broader branding/Arena suite | **Not green:** 19 test methods ran; 18 passed, one method error plus three class-setup errors |
| Five-file Compose merged configuration | **Passed**; only image/build and four TTS settings differ |
| Python compilation | **Passed** for new Python and patched backend, compiled in memory |
| Patched compiled JavaScript `node --check` | **Passed** |
| Offline local derivative image build | **Passed**, existing local base, no pulls/dependency installs, build network disabled |
| Built image payload verification | **Passed**: exact patched audio source, adapter and one-call frontend difference; version remains 0.6.5 |
| Git staged whitespace and six-file code scope | **Passed** |

The final focused suite ran with the pinned WebUI dependency versions in a network-disabled container: read-only root, unprivileged user, capabilities dropped, no new privileges, temporary empty data, and read-only mounts of integration code and public fixtures. It never started WebUI or mounted deployed data. Kokoro responses were mocked.

Coverage includes authenticated/unauthorized native routes, exact Chinese parameters, voice format, disabled-engine behavior, MIME/WAV limits and finalization, raw input/Unicode rejection, fixed destination, redirects, timeout/network failure sanitization, deadlines, disconnect/cancellation cleanup, private cache headers, no storage/logged sentinel, unchanged Pipe/Arena patch hashes and narrow image inheritance. Native verified-role dependency code is executed with synthetic user lookup; real JWT lookup/login is not tested or claimed.

The existing Pipe suite's fresh-subprocess test is skipped by its guard and is not counted as passed. The two legacy TTS files contain script-driven function tests: an initial unittest import reported zero tests for them; their actual `__main__` entry points were subsequently executed under the same isolated-data/network-denial guard and passed. No guard violations were reported.

The first focused run had a test-fixture encoding error: the client could not encode an unpaired surrogate before dispatch. The fixture was corrected to send escaped JSON so the adapter's rejection is actually exercised. Final results above refer to the completed corrected suite, not that earlier failed run.

### Pre-existing baseline regression blocker

`deploy/open-webui/branding/upstream.lock.json` retains Pipe hash `cc5299b32fedb0f10ee2a37c7466121049a2837c09dc0ec0c7d6f8bd157ec890`, while the verified Lab/W2.1 Pipe hash is `68967bd0ed499aaf2ecce38bc6afc80c3fc3cdeb805aab6a57182a2e907af861`.

Consequently, `artifact_checks()` raises **`Corvus Pipe changed`**. It causes one branding artifact test error and prevents setup for pinned branding-source, Arena overlay and Arena UI-2 Action test classes. The current Pipe, lock and verifier were checked byte-for-byte against the starting commit, and the same error was reproduced on the unchanged Lab checkout. This is not introduced by TTS-1. No lock refresh, guard bypass or unrelated fix was made.

The image derivative builds from the exact active image and validates its own exact input hashes; it does not regenerate the old branding tree or weaken its verifier. However, **full-source branding/Arena regeneration and UI-2 Action tests are not claimed passed**. This unresolved packaging baseline is why the verdict is constrained.

## G. Local build and unchanged deployed state

Prepared image: `corvus-open-webui:0.6.5-arena-ui2.1-https-tts1`.

Local image ID: `sha256:72252f095805fa8aebb6ed17e7fb44c3746e9d2a289ec3ff395769aad0c44e3b`.

The build used only the existing pinned local base and the narrow `deploy/lab/tts` context. No newer Open WebUI or new dependency/model was obtained. Existing license notices are inherited unchanged. Test containers were temporary; this image was not started as a service.

Postflight confirmed the deployed Lab WebUI still uses its original `453f9f...` image, unchanged start time, and healthy state. Its TTS engine/model/voice environment settings remain unset and `USER_PERMISSIONS_CHAT_TTS=false`. The prepared override was not added to the active stack. No persistent user setting was modified.

No deployed WebUI/API/model/FoxGate/Production/Demo/Hindsight service was restarted or reconfigured. No live synthesis, search, chat or Qwen inference was submitted. A local build artifact and ephemeral offline tests are the only Docker additions; they are not deployment acceptance.

## H. Deployment prerequisites and rollback

Before any activation, separately authorize a controlled Lab-only deployment and acceptance stage. Required preparation:

1. Review the implementation commit and the existing baseline checksum discrepancy; reconcile that packaging issue before claiming a fully green regeneration baseline. Do not silently update hashes without source review.
2. Recheck actual runtime drift, exact original image, installed Function and effective settings. Create and verify a protected consistent WebUI backup; preserve the original image/stack/volume.
3. Use or verify the prepared local derivative. Merge order is WebUI → boot → Arena UI-2 → HTTPS → TTS. The new override changes only image/build plus `AUDIO_TTS_ENGINE`, `AUDIO_TTS_MODEL`, `AUDIO_TTS_VOICE` and `USER_PERMISSIONS_CHAT_TTS`; auth, secret, volume, HTTPS and bindings were unchanged in offline merge comparison.
4. Only after approval, recreate **Lab WebUI only**. This adapter requires no Lab API, Kokoro, Qwen, Hindsight, FoxGate, Production or Demo restart and no public port/network change.
5. Start with manual Read Aloud, fixed Chinese configuration and refreshed browser assets. Do not select browser-Kokoro, another TTS model, auto-play or call mode as a shortcut.

Rollback, if separately required: return to the saved original four-file HTTPS stack/image and recreate only Lab WebUI while retaining the same volume, credentials and installed Function. No schema migration exists. Do not restore whole databases, delete messages or roll back canonical Corvus data for a presentation-only failure.

## I. Next proposed acceptance and remaining limitations

The next useful stage is a small controlled Lab TTS activation/acceptance after the documented baseline issue is reviewed. Separately authorize bounded synthetic Kokoro calls and Mac/iPhone checks: authentication, Chinese listening, audio MIME/header playback, stop/replay/cancel behavior, safe timeout/failure, no new persistent audio/text cache, effective logging privacy and unchanged chat/Arena behavior.

Remaining limitations:

- No live voice/model quality, synthesis latency, shared CPU contention or browser/PWA acceptance was measured.
- English and mixed-language behavior is not established by fixed `lang_code=z` or historical Chinese acceptance.
- The 4000-character, 60-second and 8-MiB limits may reject long Read Aloud segments; tune only from later bounded evidence.
- Cancellation releases local resources but cannot guarantee upstream compute cancellation; no retry is authorized automatically.
- Existing caches and old browser assets are not purged; global upstream logging privacy is not certified by mocked adapter tests.
- Native authentication wiring is preserved, but real login, per-user preferences and end-to-end remote authentication were not exercised.
- The broader branding/Arena baseline remains blocked as documented; UI-2 Action behavior is not newly accepted by this checkpoint.

**Operational result: IMPLEMENTED_LOCAL_ONLY; IMAGE_BUILT_OFFLINE; TTS_NOT_ENABLED; LIVE_ACCEPTANCE_PENDING.**

Only this sanitized report and its multimodal index entry are published to `reports/web-validation`. Code branches remain local. No private messages/media, credentials, account-specific host paths, database contents or raw test transcripts are included.
