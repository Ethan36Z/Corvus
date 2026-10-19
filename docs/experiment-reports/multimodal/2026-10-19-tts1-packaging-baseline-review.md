# TTS-1.1 — Packaging baseline review

Date: **2026-10-19**

Verdict: **TTS1_DEPLOYMENT_BASELINE_READY**

**The Pipe mismatch was a stale packaging baseline following reviewed W2.1 integration.** Two exact hash literals were corrected locally: the branding lock and its independent HTTPS regression assertion. The verifier and all runtime behavior remain unchanged. Affected offline checks now pass. No deployment, service restart or live inference occurred.

This follows [TTS-1](2026-10-18-tts1-kokoro-offline-integration.md); that report and its original constrained verdict are preserved.

## 1. Verified baseline and source identity

- Lab remained clean on `lab/ow2e-console` at `50a63850f83506724aaff4c2af4f50811d00d646`.
- The existing isolated worktree was clean on `integration/tts1-kokoro-webui` at TTS-1 commit `3793b13d1f6855d5df7a3b139d47036b1879e4e0`. It was reused without repeating the TTS implementation or image build.
- Reporting started clean at `3000e724ab3dff9719fcc2a3d5babb09e2d44b76` on `reports/web-validation`; origin matched that tip.
- Exact ancestry was verified: Arena UI-1 checkpoint `680b626732360e3e2f731b535d3160c022e9dcb8` → Lab milestone `975645963291ec992d64df0474a3ee9d0ba33dcd` → W2 `9b374cf2ef46ea08399b124e0c2a725d96c92a38` → W2.1 `50a63850f83506724aaff4c2af4f50811d00d646` → TTS-1 `3793b13d1f6855d5df7a3b139d47036b1879e4e0`.

| Source | Actual Pipe SHA256 | Previously recorded lock |
| --- | --- | --- |
| Arena UI-1 checkpoint, Lab milestone and W2 | `cc5299b32fedb0f10ee2a37c7466121049a2837c09dc0ec0c7d6f8bd157ec890` | Same; correct for those revisions |
| Reviewed W2.1 and TTS-1 | `68967bd0ed499aaf2ecce38bc6afc80c3fc3cdeb805aab6a57182a2e907af861` | Still the older `cc5299…` value |

The current Pipe was byte-identical to reviewed W2.1. The full [W2.1 report](../web/2026-10-18-w2-1-web-mvp-integration.md) and exact Pipe diff were reviewed: W2.1 added acceptance of confirmed deterministic Web fallback replies, retaining session/persistence checks and excluding Arena fallback acceptance. It did not replace the transport, authentication/session mapping or media guards. TTS-1 did not change the Pipe.

The lock and verifier were unchanged from the pre-W2 Lab milestone. This proves the mismatch came from the reviewed integration leaving its packaging baseline stale, rather than an unexplained source change.

## 2. Verifier semantics and minimal correction

`artifact_checks()` separately verifies the upstream commit/version, images, branding patch scope/checksum, asset hashes/dimensions, license notices and exact repository Pipe hash. `prepare_source()` calls that gate before extracting and patching the checksum-verified cached upstream source. Arena layers retain their own pins and source checks.

The Pipe field is an exact pin for the packaged repository input; it is not the upstream WebUI source checksum, an authentication secret or a signature over historical deployment state. Updating it to a separately verified reviewed source is a baseline correction, not removal of a check.

Only these two literals changed, each from the old full hash to the new full hash:

1. `deploy/open-webui/branding/upstream.lock.json`: `corvus_pipe_sha256`.
2. `tests/test_lab_webui_https.py`: the independent exact current-Pipe assertion in `test_manifest_patch_changes_no_other_function_and_rejects_drift`.

The first test run after correcting the lock passed branding/Arena setup but exposed the same stale hash in the HTTPS test. That assertion was updated to another fixed literal; it was not deleted or made to accept whatever the lock contains. The final run passed.

JSON comparison confirmed no other lock field changed. Byte comparisons confirmed the verifier, Pipe and TTS implementation/build patch were unchanged. No guard was disabled or bypassed. The old hash in the R0.3 HTTPS README remains intact because it explicitly records that historical baseline.

Local correction commit: **`4f8013af2c8e73774fcef91c2510e5808c1fd2c2`**, `Align packaging Pipe pins with reviewed Web MVP`, directly following TTS-1 on the same local integration branch. Scope: two files, two literal replacements. Neither code commit was pushed.

## 3. Offline validation

| Check | Observed result |
| --- | --- |
| Branding, Arena UI-1, Arena UI-2, HTTPS/task/Socket suites | **41 passed; zero failures/errors/skips** in the final run |
| Existing focused TTS suite | **22 passed; zero failures/errors/skips** in its existing network-disabled derivative image |
| Built TTS image payload comparison | Passed; backend, adapter, one-call frontend patch and version 0.6.5 still match TTS-1 |
| Corrected verifier with exact reviewed Pipe | Accepted |
| Isolated fixture with one unreviewed appended byte | Rejected: `Corvus Pipe changed` |
| Isolated fixture with the previous Pipe | Rejected: `Corvus Pipe changed` |
| Exact diff/JSON and unchanged-code checks | Passed |
| Git whitespace/staged scope | Passed |

The affected suites were `test_open_webui_branding`, `test_open_webui_arena_ui1`, `test_open_webui_arena_ui2` and `test_lab_webui_https`. They used the existing checksum-verified cached upstream archive and synthetic fixtures; no source download or dependency installation was needed. Tests include rejected asset/archive drift, unchanged conversation/auth code, Arena ownership and vote behavior, secure cookies, manifest handling and task/Socket identity/no-resubmission contracts.

The TTS suite reused the already-built image with networking disabled, a read-only filesystem, unprivileged user and read-only code/public fixtures. No deployed data was mounted and WebUI was not started. Kokoro responses remained mocked. The pin correction does not enter the TTS Docker build context or alter its parent image; no rebuild was required.

The intermediate affected-suite run had 40 passing methods and one failing stale HTTPS pin assertion. That incomplete result is not presented as a pass; the final 41-method run above followed the second literal correction. No live inference, synthesis, search or chat was submitted. Existing historical test results are not recounted as new executions.

## 4. Does this block the prepared derivative?

**Before correction:** the stale lock blocked full branding/Arena source regeneration and its regression evidence. It did not mechanically prevent building the prepared TTS derivative: that Dockerfile inherits the exact active HTTPS/UI-2.1 image and checks its own exact audio/frontend inputs. TTS-1's local build had already passed without changing the verifier.

**After correction:** that packaging gate and the independent current-Pipe regression agree with reviewed W2.1, and all affected checks pass. No unexplained source drift or packaging blocker remains within this review scope. The prepared integration baseline is ready for a separately authorized controlled Lab deployment procedure.

This is not blanket deployment or private remote-use acceptance. It does not establish live audio quality, browser behavior, upstream logging privacy or current host-wide runtime health. No running service was reconfigured or restarted; this stage checked Git/source/packaging and offline fixtures, not a fresh deployment preflight.

## 5. Remaining constraints and next step

Before activation, retain TTS-1's protected WebUI backup, exact original image/stack/volume, runtime-drift preflight and rollback requirements. Separately authorize recreation of Lab WebUI only and bounded synthetic acceptance. Do not change Production/Demo, Corvus API, model configuration, Hindsight, Arena behavior, canonical data, authentication, FoxGate or Cloudflare.

Live checks still need to establish Chinese playback, correct MIME, stop/cancel/replay, effective authentication/settings, no new private text/audio caches, appropriate upstream logging and Mac/iPhone behavior. Old browser assets need refresh; historical caches are not purged by this patch. Local cancellation does not guarantee upstream compute cancellation. No automatic retry is introduced.

The running Lab checkout remains untouched at its original baseline. The metadata correction and TTS implementation remain local. Only this sanitized report and its chronological index entry are published on `reports/web-validation`; previous reports/verdicts remain unchanged.

**Decision: TTS1_DEPLOYMENT_BASELINE_READY — packaging cleared for controlled deployment planning; not deployed, not live-accepted.**
