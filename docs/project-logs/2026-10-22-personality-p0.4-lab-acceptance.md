# Corvus Personality P0.4 — Controlled Lab Acceptance and Restoration

Date: 2026-10-22 (America/Los_Angeles)

Engineering result: **controlled Lab activation PASS; restoration VERIFIED**.
Repository closeout: **COMMIT BLOCKED by uncommitted prerequisite changes**.
Personality quality: **P0.2 BLOCK remains unchanged**. This is a module integration
acceptance record, not approval of the blocked experimental prompts or a general
claim about conversational quality.

## Scope and version provenance

Lab branch: `lab/ow2e-console`, base HEAD
`4f8013af2c8e73774fcef91c2510e5808c1fd2c2`.
Production branch: `main`, HEAD
`8b863ec95b8c133951e166c8b60d6335b764f7db` (P0.3).
P0.3 is not an ancestor of the Lab HEAD; their merge base is
`f453ed161994c8131bf8d9ed7c43cc15914176cf`.
No merge, cherry-pick, branch switch, fetch, push, or service operation was
performed during final closeout.

The Lab preparation reuses the same P0.3 personality package. Byte comparisons
against P0.3 pass for `personality/__init__.py`, `personality/runtime.py`,
`personality/profiles.py`, `personality/profiles/corvus-companion/0.1.0.json`,
and `tests/test_personality_profiles.py`. This is explicit file-level provenance,
not a claim that the Lab branch contains the P0.3 commit history.

Only `corvus-companion@0.1.1` was activated. Relative to immutable `0.1.0`, its
first core instruction is “Put long-term companionship first.” rather than a
second “You are Corvus” identity declaration; the remaining instructions are
unchanged and `expression` is empty. P0.2 experimental prompts are not runtime
profiles. The sample stays disabled; there is no automatic activation.

## Actual activation and API results

The operator installed a temporary runtime drop-in for **only**
`corvus-lab-api.service` and restarted Lab once. Live PID `513013` had the three
exact variables `TRUE`, `corvus-companion`, `0.1.1`, cwd
`/home/ethan/srv/apps/corvus-lab`, and data root `/home/ethan/srv/data/corvus/lab`.
Health before and after requests was HTTP 200, with overall/service/model/dense
recovery all OK. Preflight snapshots were IDLE with no API TCP connections.

Two synthetic API requests were sent sequentially, once each, without retries.
Web was off; no attachment, STT, Vision, TTS, or voice request was sent.

| Request | HTTP / elapsed | Result |
| --- | --- | --- |
| `POST /api/chat` | 200 / 1.926 s | All normal statuses OK; persistence NORMAL; canonical IDs 194/195 |
| `POST /api/arena/chat` | 200 / 6.576 s | Main and Shadow OK; recall OK; evaluation STORED and votable; canonical IDs 196/197 |

Normal reply: “测试通过，心情不错，这感觉确实挺踏实的。”
Arena main and Shadow replies: “今天的小测试完成了。”
Arena trial: `4d9b6048-2b92-4585-b4ea-491ed44db090`.
Shadow generation took 1883.057 ms with 2776 input tokens.
The canonical API paths and existing Lab comparison/retain scheduling were left
intact. Synthetic session/trial records were created by those existing paths;
no direct database editing or cleanup was performed.

The live Arena `personality_sha256` exactly matched locally rendered `0.1.1`:
`2ace63774e575cbe181ac949f20476b08ab9cfd22617e2dc4dfdba4b71c66731`.
The original PERS-A prefix was preserved verbatim, its instruction lines appeared
once, the identity declaration appeared once, and the safety-precedence notice
remained. The reviewed Arena path compiles once and reuses the main arm's full
system instructions, including date context, for Shadow. Offline tests compare
the exact shared system prefix and recent history, including a config change
between arms. The live API exposes one personality hash, not separate full
per-arm prompt hashes; no model-request wire interception was performed.

## Operator restoration and independent read-only verification

The operator removed only the temporary
`/run/systemd/system/corvus-lab-api.service.d/80-personality-acceptance.conf`,
reloaded systemd and restarted Lab once more. These were the two authorized Lab
restarts. Codex performed no restart or runtime configuration mutation.

Final Lab PID: `525160`, active. All three `CORVUS_PERSONALITY_*` variables are
absent in `/proc/525160/environ`. The temporary file is absent and the loaded
unit lists only the original Web and Vision drop-ins. Original unit-file hashes
match the pre-activation baseline. Health is HTTP 200, with status/service/model/
dense recovery all OK.

Rendering with the actual restored process environment disables the profile and
returns the original PERS-A byte-for-byte, SHA-256:
`1c146488ec8fc5a5993e66f2c33f130d06b747aecf75c5e4a5417b36882110e9`.
This verifies environment plus deterministic assembly; no additional model
conversation was run after restoration. Existing date/safety context remains.

Production retains PID `6052`, its complete process-environment hash, original
unit hashes, clean worktree and all 270 tracked-file hashes. Lab verified all
399 tracked hashes against its expected staged snapshot. Relevant other service
PIDs/start times/states and running container identities/states are unchanged
except for the authorized Lab restart. This is isolation/state evidence, not a
new functional regression of every other service or a private database audit.
No private memory evidence or credentials are included in this log.

## Protected work and commit blocker

The following ten pre-existing dirty files still match the saved backups
byte-for-byte and must not be staged, restored, or folded into P0.4:

- `app/arena.py`
- `app/conversation_runtime.py`
- `app/playground_api.py`
- `app/runtime_config.py`
- `app/vision_input.py`
- `app/web_evidence_prompt.py`
- `app/web_intent_gate.py`
- `app/web_mvp.py`
- `deploy/lab/foxgate/nginx/nginx.conf`
- `memory/attachments.py`

P0.4's integration tests depend on `current_date_note` and `now_fn` in the
uncommitted conversation runtime, and on the uncommitted Arena change that
captures/reuses the full effective system prompt. Lab HEAD lacks these changes.
To check commit isolation, an isolated `/tmp` checkout of Lab HEAD received only
the 11 prepared P0.4 files. Its integration script ran 8 tests and failed with
10 errors, including missing `current_date_note` and unsupported `now_fn`.
This is a prerequisite/reproducibility failure, not a failure of the restored
running Lab or of the already tested staged snapshot.

Therefore no commit or staging operation is performed. A complete independent
P0.4 commit would otherwise contain tests that fail on its committed source.
The prerequisite owners must first record their changes separately; a later
P0.4 closeout may then recheck the exact base and stage only the P0.4 paths.
No dependency was merged, cherry-picked, rewritten, or claimed as P0.4 work.

## Offline verification and limits

Final offline rerun on the actual staged snapshot passed four existing scripts:
Profile 15, Lab integration 8, Arena 22 unittest cases (45 total), plus the
original personality runtime's module-level assertions. No skips and no guarded
network/private-data access violations occurred in this rerun.
The earlier eight-script regression recorded 89 unittest cases plus module-level
assertions. Its two existing skip reasons were the guarded Pipe subprocess case
and missing `CORVUS_OW2D_ARCHIVE` for pinned-source Arena UI integration.
Date assertion changes only match the already-existing runtime/date behavior;
no date implementation was changed by P0.4.

Evidence, local to this host and not guaranteed durable across `/tmp` cleanup:

- `/tmp/corvus-p04-live-acceptance-_k_ksirb/preflight.json`
- `/tmp/corvus-p04-live-acceptance-_k_ksirb/live-results.json`
- `/tmp/corvus-p04-live-acceptance-_k_ksirb/restoration-verification.json`
- `/tmp/corvus-p04-live-acceptance-_k_ksirb/closeout-test-logs/`
- `/tmp/corvus-p04-live-acceptance-_k_ksirb/clean-head-test-logs/`
- Backup: `/tmp/corvus-p04-lab-staged-yds1zurg/`

The smoke is intentionally small and does not prove stable multi-turn persona
behavior, every base-model response, or long-term memory quality. P0.2 BLOCK is
not lifted. `0.1.0` remains historical and is outside the single-identity live
acceptance scope. Invalid-profile fallback was covered offline, not by another
live configuration change. API success statuses are not an independent audit
of exact underlying model-call or database-write counts.

Recommendation: accept and archive the controlled activation/restoration
engineering result. Keep the profile disabled. Defer source-release sealing
until the prerequisite commits make the Lab tree reproducible; do not declare
unqualified “Personality v1.0 SEALED” or full personality-quality approval.
