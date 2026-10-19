# Multimodal experiment and decision reports

Chronological, sanitized reports for speech input, speech output and Vision in
Corvus. A decision report records inspected evidence and proposed integration;
it does not imply deployment, new test execution or browser acceptance.

| Experiment / decision ID | Date | Objective | Verdict | Report | Important limitations | Related Lab baseline |
| --- | --- | --- | --- | --- | --- | --- |
| Multimodal reuse decision | 2026-10-18 | Select existing engines, UI and minimum adapters for the next daily-use MVP | `MULTIMODAL_REUSE_DECISION` | [Multimodal reuse decision](2026-10-18-multimodal-reuse-decision.md) | Read-only audit; no inference or fresh tests; audio-cache privacy, ownership and protocol gaps remain; Mac/iPhone acceptance pending | `50a63850f83506724aaff4c2af4f50811d00d646` |
| TTS-1 | 2026-10-18 | Prepare private Read Aloud integration with existing Kokoro and WebUI controls | `TTS1_IMPLEMENTED_WITH_CONSTRAINTS` | [Kokoro offline integration](2026-10-18-tts1-kokoro-offline-integration.md) | 22 focused tests passed; local image built, not deployed; existing branding/Arena lock mismatch; live audio/browser/privacy acceptance pending | `50a63850f83506724aaff4c2af4f50811d00d646` |
| TTS-1.1 | 2026-10-19 | Verify W2.1 Pipe ancestry and correct stale packaging pins without weakening checks | `TTS1_DEPLOYMENT_BASELINE_READY` | [Packaging baseline review](2026-10-19-tts1-packaging-baseline-review.md) | Two local pin corrections; 41 affected and 22 TTS tests passed; no deployment/live acceptance; code remains unpushed | `3793b13d1f6855d5df7a3b139d47036b1879e4e0` |
| TTS-2 | 2026-10-19 | Verify current runtime and prepare protected backup, activation, rollback and acceptance plans | `TTS2_BLOCKED` | [Deployment preflight](2026-10-19-tts2-deployment-preflight.md) | Git/images/health/merge match; shared Kokoro DEBUG and warning/error text logging persists to Docker logs; no backup, activation or synthesis performed | `4f8013af2c8e73774fcef91c2510e5808c1fd2c2` |
| TTS-2.1 | 2026-10-19 | Prepare pinned Kokoro logging privacy derivative without changing synthesis | `TTS2_1_LOGGING_HARDENED_OFFLINE` | [Logging hardening](2026-10-19-tts2-1-kokoro-logging-hardening.md) | 19 privacy/API and 22 TTS-1 tests pass; 11 legacy contract groups pass; image prepared only; shared-service activation and live acceptance require approval | `4f8013af2c8e73774fcef91c2510e5808c1fd2c2` |
| TTS-2.2 | 2026-10-19 | Activate hardened shared Kokoro with retained rollback and one synthetic speech request | `KOKORO_ACTIVATED_LOCAL_ACCEPTED_WITH_CONSTRAINTS` | [Controlled Kokoro activation](2026-10-19-tts2-2-kokoro-activation.md) | One HTTP speech call, zero retries; WAV/privacy/health/canonical metadata pass; four metadata-only warnings; temporary Compose ownership; WebUI TTS remains disabled | `7c0b5d0bbbfe993d4cd4910f1e9c1306de9e3b51` |
| TTS-2.3 | 2026-10-19 | Activate prepared Lab WebUI Read Aloud after verified volume backup | `TTS23_LAB_ACTIVATED_WITH_CONSTRAINTS` | [Lab WebUI activation](2026-10-19-tts2-3-webui-activation.md) | One authenticated synthesis succeeds; WAV/no-store/cache/canonical checks pass; initial native 403 expectation corrected before any synthesis; Mac/iPhone/HTTPS browser acceptance pending | `4f8013af2c8e73774fcef91c2510e5808c1fd2c2` |
| STT-1 | 2026-10-19 | Prepare private Whisper-backed reviewed-text dictation | `STT1_BLOCKED` | [Whisper offline integration blocker](2026-10-19-stt1-whisper-offline-integration.md) | Shared --convert writes audio to persistent container layer and misses failure cleanup; three existing A3 scripts pass; no STT code/image/live request | `4f8013af2c8e73774fcef91c2510e5808c1fd2c2` |
| STT-1a | 2026-10-19 | Prepare bounded private Whisper conversion cleanup | `STT1A_BLOCKED` | [Whisper conversion privacy](2026-10-19-stt1a-whisper-conversion-privacy.md) | Docker rejects noswap tmpfs option; draft uncommitted, no conversion tests or image; shared service unchanged | `4f8013af2c8e73774fcef91c2510e5808c1fd2c2` |
| STT-1a recovery | 2026-10-19 | Select minimum private volatile-storage and build path | `STT1A_CONFIGURATION_ONLY_CANDIDATE_REQUIRES_VALIDATION` | [Recovery feasibility gate](2026-10-19-stt1a-recovery-feasibility.md) | Local-driver noswap tmpfs candidate untested; active host swap; RAM leftovers differ from disk persistence; draft preserved, no build or deployment | `4f8013af2c8e73774fcef91c2510e5808c1fd2c2` |
| STT-1a.1 | 2026-10-19 | Test private bounded Docker local-driver noswap tmpfs | `NOSWAP_PROBE_PASS` | [Noswap storage probe](2026-10-19-stt1a-noswap-storage-probe.md) | Actual noswap/permissions/ENOSPC/swap.max=0 verified; named files survive SIGKILL; all temporary Docker resources removed; core/hibernation and Whisper acceptance unresolved | `4f8013af2c8e73774fcef91c2510e5808c1fd2c2` |

## Future entries

Follow the [archive conventions](../README.md). Use
`YYYY-MM-DD-<experiment-id>-<short-description>.md`, one report per checkpoint,
and append a row ordered by date and experiment sequence. Record the objective,
exact verdict, limitations and verified baseline. Preserve earlier verdicts;
publish later integration or acceptance as separate reports.

Only reviewed documentation belongs on this reporting branch. Baseline hashes
may refer to unpublished local code; report publication does not publish code or
authorize deployment.
