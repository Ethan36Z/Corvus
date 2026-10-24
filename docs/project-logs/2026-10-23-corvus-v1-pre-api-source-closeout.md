# Corvus v1 — Pre-API source closeout

Date: 2026-10-23 (America/Los_Angeles)
Scope: existing-source preservation and GitHub synchronization; no development,
deployment, service restart, private-data export or memory recovery operation.

## Source and branch relationship

API v1 should start from **integration/corvus-v1**, created in a new clean
worktree from the accepted Voice seal `2bdd7ff379aa78a4a41f8b16792131c9a7ee3512`.
No merge/cherry-pick of main, duplicate personality system or repeated closure
merge was needed. All feature refs below are already ancestors of that seal.

| Module | Final source |
| --- | --- |
| Core/Evidence/RAG and H1 memory/admission | Existing Lab/closure ancestry; H1 patch ecb692d and seal 98693f6 |
| Personality | Original main P0.3 8b863ec; equivalent integration port 236b79b, reconciliation dcc2e8a, P0.4 b99a5d5 |
| Web W1/W1.1/Plan C/W2 | 6b3e430 / 35dd9c9 / b796650 / cc95d3d; integration 9331541 |
| Vision, single storage, preview and resize | multimodal closure 01797c5, including da3d9c3 through 98ae271 |
| STT transport/Bridge/persistent mounts | multimodal ancestry, API refactor 688a8bb, boot fix 75e3cf9 |
| Kokoro/TTS | privacy implementation 7c0b5d0; runtime closure 0406e2d |
| Voice/Open WebUI | f6d94ff implementation, b415ac9 preparation, 45a70cf full-build proof, 2bdd7ff user acceptance seal |
| Lab HTTPS/FoxGate | 7dc2478; external FoxGate main a8aea86 contains deployed Auth source 1009bba |
| Production foreground publisher | main f240896/c315d0e; shared registry/activity code byte-identical in integration |

Main's four unpublished commits (f240896, c315d0e, 14b6cf8, 8b863ec) remain on
main. The running Production/Demo source checkout is not switched. Only its
missing publisher unit's three environment directives and existing compatibility
test are brought into the new integration tree. The test explicitly permits
only the existing nullable Lab `historical_recall_elapsed_ms` diagnostic while
comparing all original return fields, model/persistence events and exceptions.
Production's original exact-equivalence test remains unchanged on main.

## Minimal additions

- Non-secret, opt-in persistent Lab personality 85 drop-in example and recovery
  instructions alongside existing systemd checkpoints. Module defaults remain
  OFF; installed Lab config is not edited. Profile 0.1.1 and its prompt unchanged.
- Two byte-identical Corvus-only private gateway Nginx files and scoped recovery
  instructions. No private Compose, account credentials or Tunnel config copied.
- Persistent Hindsight container/image references and an availability warning in
  the historical runtime README; no new backup/recovery framework or data copy.
- This source/deployment handoff and the Production compatibility material above.

## Final integration contracts

Existing tests only, fake model calls and synthetic temporary data:
**21 selected checks passed**: 282 Python unittest cases (280 passed, 2 existing
subprocess-only offline skips), four module-level assertion scripts, and 17 Node
Voice Call cases. Coverage includes profile versions/default-off/fallback,
PERS-A and final assembly, Arena consistency, Web citations/security/boundaries,
attachments/Vision, STT transport, native STT/TTS, voice persistence/API, async
retain/reconciliation, Pipe and foreground activity/publication. All three
Production compatibility cases passed, including isolated mixed publisher
processes with crash/restart semantics. No live fault injection occurred.

The publication suite uses the existing bwrap-only isolation rather than the
Web Python audit hook, which cannot handle that suite's dir-fd writes and child
processes. Network is unshared; active data, /run and protected STT configuration
are hidden; repository and Python environment are readonly. No application fix
was needed for that harness limitation. Two Pipe subprocess cases remain skipped
by the original stricter guard, explicitly not counted as passes.

Full Vite/client/SSR and accepted-image evidence is reused from 45a70cf and the
Voice seal. No frontend code changed and no rebuild or broad benchmark ran.
`git diff --check` and explicit staged checks are required before commit. Review
of unpublished blobs and new material found no secret-pattern hits, private
DB/key files or new binary captures; the scan is not a universal security audit.

## Existing deployment remains the acceptance target

| Environment/component | Observed baseline |
| --- | --- |
| Production API | PID 6052, main checkout; installed publisher unit matches committed main |
| Demo API | PID 1006708, same checkout, independent demo data |
| Lab API | PID 2460016, lab/ow2e-console 4f8013a + preserved 28 changes |
| Lab personality | persistent 85 drop-in, TRUE / corvus-companion / 0.1.1 |
| Lab WebUI | corvus-lab-webui:voice-v1-f6d94ff-candidate; image sha256:5058ab1bdfd1112c38dda284f67c76717c0d6faf5eb425e59a0229f980c3ec6d |
| Hindsight | sha256:36a59577d7bdabe7525a114f8baa9bd26bac195df99e1999c807a3301be284f8; both prior containers retained |
| Kokoro | sha256:94d19bad32ccb34df77cccc2f5c9bc4ebd1a225878be2522d27b16edc5ae3c44 |

Lab memory/personality source matches Voice seal. App source differs only in
STT: live `app/transcription.py` remains the pre-688a8bb adapter, and the API has
not deployed the three new stt_active/stt_bridge/stt_protocol modules. The
separate accepted STT Bridge container is already using its own committed code.
Do not deploy the new API adapter merely to make these trees appear identical.
For exact current API-source recovery, use that adapter from Lab HEAD 4f8013a
with the accepted closure source, not an automatic upgrade. Production/Demo's
old React images are preserved but lack exact historical build-revision
manifests; immutable image identity alone cannot prove their source commit.

Normal text, editable/manual Dictation, Kokoro Read Aloud and half-duplex Call
have user-confirmed Lab basic acceptance. Existing P0.4 normal chat, Arena and
restoration/persistent activation evidence is reused; no new private chat was
read or submitted. This is not a new all-device, language, cancellation or
long-session acceptance. HTTPS automated-client 403 is a known access-policy
boundary, not proof of human browser failure.

## Explicit remaining limits

- Voice Call requires manual transcript confirmation/send; speech begins after
  the full response. VAD, automatic submit/turn switching and token streaming
  are future optional work. Shared Qwen/Hindsight inference still causes waits.
- BackgroundTasks -> durable retain-intent handoff and automatic recovery gaps
  remain. Post-intent H1 guarantees do not prove end-to-end memory integrity.
- P0.2 personality quality BLOCK remains; daily Lab opt-in is not quality release.
- Hindsight's old /tmp snapshots are missing. Retained images/containers and
  guarded source recipes survive, but no unsafe reconstruction or complete
  database disaster-recovery claim is made. See the new RECOVERY.md.
- Credentials, private consistent backups, model/voice weights, local images,
  private Compose packets and Cloudflare account routes need separate protected
  provisioning. GitHub source alone cannot restore these assets.
- Lab's 28 changes and W1's two untracked author drafts remain untouched. Their
  status need not be clean for the separate integration worktree to be clean.

## Publication and final verification

Only main, feature/voice-v1-half-duplex and integration/corvus-v1 are authorized
Push targets, with ordinary fast-forward/new-branch pushes only. Other closure
branches already on origin are dependencies, not additional Push targets.
Fetch and compare exact remote SHAs, then check out integration from GitHub in a
separate /tmp clone. Final SHAs, remote checkout verification, unchanged-worktree
fingerprints and minimal read-only health results belong to the accompanying
source-closeout report. Source publication changes neither the current deployment
nor the above acceptance limits. API v1 is not implemented by this closeout.
