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

## Future entries

Follow the [archive conventions](../README.md). Use
`YYYY-MM-DD-<experiment-id>-<short-description>.md`, one report per checkpoint,
and append a row ordered by date and experiment sequence. Record the objective,
exact verdict, limitations and verified baseline. Preserve earlier verdicts;
publish later integration or acceptance as separate reports.

Only reviewed documentation belongs on this reporting branch. Baseline hashes
may refer to unpublished local code; report publication does not publish code or
authorize deployment.
