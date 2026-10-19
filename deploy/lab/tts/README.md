# TTS-1 — prepared Lab Read Aloud adapter

Status: implementation/offline validation only. A local offline image build is
permitted; activation and service recreation are not authorized.

The existing Open WebUI 0.6.5 Read Aloud controls call their existing authenticated
`/api/v1/audio/speech` route. A pinned build-time patch retains its exact native
`Depends(get_verified_user)` signature/decorator, replaces only its body and the
voice-list body, and removes unused speech-cache initialization. All other
handlers, authentication, UI controls, chat Pipe and Arena files stay unchanged.

`kokoro.py` is copied into the WebUI image, not into Corvus's conversation runtime.
It does not import Corvus storage or expose canonical message IDs. Input is the
displayed text supplied by an authenticated user, not an ownership assertion
about a canonical message. The native authentication layer may maintain normal
WebUI user activity metadata; the adapter never writes canonical conversation
data or submits chat requests.

## Fixed contract and limits

- Destination: only `http://127.0.0.1:8105/v1/audio/speech`.
- Model `kokoro`, voice `af_mica`, language `z`, speed `0.95`.
- Request WAV with `stream=false` and `return_download_link=false`. The inspected
  installed Kokoro non-streaming branch uses its download-file writer only when
  a download link is requested. Do not enable it.
- Return validated, complete PCM WAV as `audio/wav`; do not label WAV as MP3.
- The installed PyAV writer was exercised offline with zero-valued samples only,
  without a model: it emits `0xffffffff` RIFF/data lengths even in the complete
  response path. After bounded full receipt, finalize that observed sentinel pair
  from actual byte length before validating PCM. Inconsistent finite headers are
  rejected, not guessed. This is a fixed-format repair, not a media converter.
- One supported voice is returned in WebUI's `{id, name}` format. No upstream
  voice discovery, additional model or voice-management system.
- Maximum JSON body 24 KiB, maximum input 4000 characters, input deadline 5 s.
- Upstream connection timeout 3 s, total synthesis/receive deadline 60 s,
  maximum returned audio 8 MiB. Expected WAV is 24 kHz, 16-bit PCM, mono/stereo.
- No redirects, environment proxies, client-selected destinations or retries.
- `private, no-store` and `nosniff`; no files, persistent text JSON or audio cache.
- Errors have fixed safe descriptions; no upstream body/exception is returned or
  logged. The adapter has no logging calls. Request cancellation/disconnect closes
  local upstream transport and releases tasks; this does not guarantee that the
  shared Kokoro process stops computation already admitted.

The derivative removes exactly one private-text `console.debug` call in the
pinned compiled response component. It retains all UI control behavior and needs
no frontend rebuild. The asset filename is unchanged: deployment acceptance must
close existing clients and hard-reload/clear the cached application assets before
claiming the old debug call is gone on devices. Previously cached browser assets
and historical server audio caches are not deleted by this implementation.

## Offline checks

The focused tests use actual pinned route signatures and native verified-role
dependency code with synthetic user lookup, mocked Kokoro responses and public
source fixtures. No JWT/private-user lookup or deployed storage is imported.
They do not prove live login, synthesis, listening quality or browser acceptance.

Existing full-source branding/Arena regeneration tests are currently blocked on
the unchanged Lab baseline: `upstream.lock.json` retains an older Pipe checksum
and `artifact_checks()` raises `Corvus Pipe changed`. TTS-1 does not modify that
lock, Pipe or verifier or bypass the guard. The direct derivative instead pins
the exact active image and exact audio/frontend inputs. Reconcile this separate
baseline packaging issue before claiming a fully green regeneration suite.

Local fixtures required:

- `CORVUS_TTS1_SOURCE`: cached branded 0.6.5 source tree; defaults to the existing
  temporary source fixture. Its audio source hash must match the installed image.
- `CORVUS_TTS1_FRONTEND`: cached public `DN99fuHl.js` from the exact base image;
  defaults to the temporary file captured during implementation. Hash mismatch is
  a hard failure, not permission to download/update the source.

Run `python -B -m unittest discover -s tests -p test_lab_webui_tts.py -v` using
existing dependencies. Prefer the pinned base image with `--network none`, a
read-only filesystem, unprivileged user, temporary empty data and read-only mounts
of code/public fixtures. Never mount deployed WebUI or Corvus data.

## Proposed deployment, separately authorized

1. Review the local implementation commit and privacy findings. Verify the exact
   existing HTTPS/UI-2.1 image digest and unchanged Lab runtime. Keep that image
   and the original four-file stack for rollback.
2. Make and verify a protected consistent WebUI backup. Do not inspect private
   messages or delete existing volumes/caches as part of this code checkpoint.
3. Build only the new derivative from its existing local pinned base with no
   dependency downloads or frontend build. Verify both exact-source patches.
4. Preview the merged Compose configuration using the existing secret file
   without printing it. Required order is `compose.webui.yml`, `compose.boot.yml`,
   `compose.arena-ui2.yml`, `compose.https.yml`, then `compose.tts.yml`. The final
   override changes only image/build and four TTS environment settings.
5. After separate approval, recreate only Lab WebUI, retaining its volume,
   installed Function, secret, HTTPS settings and authentication. No API, model,
   Hindsight, FoxGate, Production or Demo restart is needed by this adapter.
6. Verify effective TTS permission/settings. Native browser/OS speech and
   browser-Kokoro are different choices; do not select or load another model.
   Use manual Read Aloud rather than auto-play/call mode for initial acceptance.
7. Separately authorize bounded synthetic live synthesis and Mac/iPhone testing:
   authentication, Chinese output, exact MIME, stopping/replay, failure/cancel,
   cache/log privacy, no duplicate turns and existing chat/Arena regression.

The fixed Chinese language configuration preserves existing Corvus behavior;
English/mixed-language voice quality and device playback remain unverified.
Existing Kokoro logging/dependency behavior is not globally reconfigured or
certified by mocked WebUI tests. Review operational logging before private live
acceptance; do not infer end-to-end privacy from this adapter alone.

Rollback: return to the original four-file Compose stack and exact saved HTTPS
image, recreating only Lab WebUI under operator authorization. Retain the same
volume/credentials; do not restore whole databases, delete messages, roll back
canonical Corvus data or change unrelated services. No data migration is added.
