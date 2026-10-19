# Multimodal experiment and decision reports

Chronological, sanitized reports for speech input, speech output and Vision in
Corvus. A decision report records inspected evidence and proposed integration;
it does not imply deployment, new test execution or browser acceptance.

| Experiment / decision ID | Date | Objective | Verdict | Report | Important limitations | Related Lab baseline |
| --- | --- | --- | --- | --- | --- | --- |
| Multimodal reuse decision | 2026-10-18 | Select existing engines, UI and minimum adapters for the next daily-use MVP | `MULTIMODAL_REUSE_DECISION` | [Multimodal reuse decision](2026-10-18-multimodal-reuse-decision.md) | Read-only audit; no inference or fresh tests; audio-cache privacy, ownership and protocol gaps remain; Mac/iPhone acceptance pending | `50a63850f83506724aaff4c2af4f50811d00d646` |
| TTS-1 | 2026-10-18 | Prepare private Read Aloud integration with existing Kokoro and WebUI controls | `TTS1_IMPLEMENTED_WITH_CONSTRAINTS` | [Kokoro offline integration](2026-10-18-tts1-kokoro-offline-integration.md) | 22 focused tests passed; local image built, not deployed; existing branding/Arena lock mismatch; live audio/browser/privacy acceptance pending | `50a63850f83506724aaff4c2af4f50811d00d646` |

## Future entries

Follow the [archive conventions](../README.md). Use
`YYYY-MM-DD-<experiment-id>-<short-description>.md`, one report per checkpoint,
and append a row ordered by date and experiment sequence. Record the objective,
exact verdict, limitations and verified baseline. Preserve earlier verdicts;
publish later integration or acceptance as separate reports.

Only reviewed documentation belongs on this reporting branch. Baseline hashes
may refer to unpublished local code; report publication does not publish code or
authorize deployment.
