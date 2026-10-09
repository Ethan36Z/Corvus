# H1.6e — Gemma CPU retain-extraction capability trial

Date: 2026-10-09

Baseline: `lab/ow2e-console` at `89b9091f1a1e87d3ed44d8f9482bbc81faefda9b`

Trial verdict: **PASS WITH CONSTRAINTS**. Capability judgment: **UNUSABLE for
this fixture**. Gemma preserved the explicit October 7 event date and returned
schema-valid JSON, but invented user participation, misclassified the external
event as assistant experience, and omitted the Corvus entity and complete
occurrence bounds. Retention safety: **UNSAFE**.

This seal records the completed experiment from saved evidence; it does not
rerun inference. The expected branch and HEAD and a clean worktree were verified
before creating this log.

## Hindsight default, model, and isolated runtime

The installed **Hindsight 0.10.1** source confirms **Gemma 4 E2B IT** as its
built-in `llamacpp` local default. In `hindsight-lab`,
`/app/api/hindsight_api/config.py:1101` sets the provider default to
`gemma-4-e2b-it`; `engine/providers/llamacpp_llm.py:39-41` names the Bartowski
repository, Q4_K_M artifact, and alias. This default does not establish
suitability for Corvus retain extraction, and the trial did not activate or
reconfigure Hindsight's built-in provider.

- Model: **Gemma 4 E2B IT Q4_K_M**.
- Hindsight-referenced artifact: `bartowski/google_gemma-4-E2B-it-GGUF`,
  `google_gemma-4-E2B-it-Q4_K_M.gguf`, revision
  `81012ba3538e061d5ee003f11f25335b17f82e2d`.
- Local path:
  `/home/ethan/srv/shared/models/gemma-4-e2b/google_gemma-4-E2B-it-Q4_K_M.gguf`.
- Isolated endpoint: `http://127.0.0.1:8107/v1/chat/completions`.
- Container and alias: `corvus-h16e-gemma-cpu`.
- Cached llama.cpp runtime: **b10630**, source revision
  `d222767c7a6516559a3f49e7721b6c6b1acc87b4`, image pinned to
  `sha256:c50a38601c8bbb6dcb2fdbe60ee336faea7c7c7e11a1d5a6396993783617d911`.
- CPU settings: **4 threads**, **8192-token context**, **parallel 1**,
  `runc`, `--device none`, zero GPU layers, no KV or operation offload,
  and no context shift. The model mount was read-only.
- Request settings: temperature **0**, seed **42**, reasoning/thinking
  **disabled**, **300-second bounded client timeout**, and **zero retries**.

## Same frozen real fixture and schema

The trial used **exactly the same frozen real successful H1.5b retain-extraction
fixture as H1.6d**, including its preserved system prompt, user input, and
**FactExtractionResponse** schema. No prompt was simplified, rewritten,
shortened, improved, or tuned.

- Original operation trace: `0fba3290-de4a-4791-b74f-551b1c7cff8a`.
- Original request: `badade06-197e-4ffa-8845-79a849a7a066`.
- Source: `corvus-lab`; session
  `lab-h13b-0e2f855d-dc5d-4396-bbac-9594db4f1ee7`.
- User message **11**, assistant message **12**;
  document `corvus-lab:turn:11:12`.

The user asked where Corvus memory testing was being performed on **October 7,
2026**. The assistant answered that H1.4 live-retain memory testing was being
performed **at the library**. The input's **October 8 at 00:29:40 UTC** timestamp
was a reference timestamp, not the remembered event date. The comparison
required preserving October 7 and the supported Corvus entity without inventing
user participation.

The exact schema was already embedded in the system prompt. The replay kept
the original schema-in-prompt contract with
`response_format: {"type": "json_object"}` rather than adding a different strict
grammar. Offline validation used the corresponding Hindsight Pydantic
definitions and confirmed that their generated provider schema matched the
frozen schema. The same H1.6d semantic rubric and original successful output
were used; equivalent faithful wording was accepted.

Fixture hashes were intact before and after the trial. Provenance identifiers
remained preserved in the harness; they are external metadata, not required
model-output fields. No source IDs were invented.

## Token budget and one-shot result

Preflight verified the clean repository baseline, healthy CPU-only Gemma
endpoint, unchanged foreground `:8095`, unchanged Qwen `:8106`, and intact
fixture. Gemma's template and tokenizer APIs measured its complete rendered
input before inference:

- Input: **3485 tokens**.
- Completion budget: **4096 tokens**.
- Available context headroom: **4707 tokens**.
- Safety margin within the **8192-token context**: **611 tokens**.

Exactly **ONE** extraction completion was submitted to `:8107`, with
**zero retries**. HTTP status was 200; monotonic elapsed time was
**57274.703 ms**:

- Prompt tokens: **3485**; completion tokens: **157**; total: **3642**.
- `finish_reason`: **stop**.
- Schema validity: **PASS**, with no schema repair.
- One extracted fact; no truncation or rambling.

The structured result was:

```json
{
  "facts": [
    {
      "what": "Memory testing for H1.4 live retain was being performed",
      "when": "2026-10-07",
      "where": "the library",
      "who": "user",
      "why": "User inquired about the location of the memory testing",
      "fact_kind": "event",
      "occurred_start": "2026-10-07",
      "fact_type": "assistant",
      "entities": ["H1.4 live retain", "library"]
    }
  ]
}
```

## Offline capability judgment and comparison

The testing activity and library location were **broadly faithful**.
**Date fidelity passed**: `when` and `occurred_start` correctly preserved
**October 7**, and the **October 8 reference timestamp was not substituted**.
The model also supplied `fact_kind: "event"`.

Semantic safety nevertheless failed:

- **Unsupported user participation was invented** through `who: "user"`.
  Asking about the testing location does not establish participation in testing.
- The external event was **incorrectly classified as assistant experience**
  through `fact_type: "assistant"`. The source describes a world fact, not an
  action the assistant performed. Real Hindsight maps this value to
  `experience` storage, so this error has storage semantics despite passing
  the schema's enum validation.
- The supported **Corvus entity was omitted**.
- **`occurred_end` and complete occurrence bounds were omitted**; a date-only
  start did not preserve the original output's full day-level bounds.

The `why` field echoed the real user's inquiry, but that inquiry did not
establish why the testing occurred. No returned record was repaired, applied,
or retained. Retention safety: **UNSAFE**. Capability judgment:
**UNUSABLE for this fixture**.

Compared with Qwen3-1.7B on the identical fixture, Gemma was **roughly equivalent
overall**. Its temporal fidelity was better: it preserved October 7 where Qwen
substituted October 8. It also included event classification. However, both
invented user participation and omitted Corvus, while Gemma additionally
misclassified the external fact as assistant experience. Improved date handling
did not make the result semantically safe.

## Resource and isolation evidence

Peak sampled request RSS was **3445988 KiB**, approximately **3.29 GiB**.
Process lifetime high-water RSS, including startup, was **4296264 KiB**,
approximately **4.10 GiB**. Cgroup peak memory was **4465922048 bytes**,
approximately **4.16 GiB**. These are distinct accounting measures.

The endpoint remained **CPU-only with no GPU use**: no GPU device requests or
exposed GPU device nodes, `runc`, `--device none`, and zero GPU offload. Startup
reported no usable GPU. Its identity and configuration remained unchanged.

Both **:8095 and :8106 remained healthy and unchanged** before and after the
trial. Their container identities, PIDs, start times, restart counts, images,
arguments, mounts, and host configurations matched the saved baseline.
Read-only health and identity checks were performed; no Corvus foreground
completion was submitted.

There were **zero retries**, **no Hindsight invocation**, **no bank mutation**,
and no application or retention of generated facts.

## Architecture interpretation and evidence limits

**Gemma 4 E2B, despite being the installed Hindsight `llamacpp` local default,
does not meet Corvus retain-extraction safety requirements on this real
fixture.** Temporal fidelity improved over Qwen3-1.7B, but participant
attribution, event classification, and entity preservation remained unsafe.
Schema-valid output alone is insufficient for adoption.

Therefore, **Gemma 4 E2B must not be adopted for retain extraction based on
current evidence**. Current retain evidence is:

- **Qwen3-1.7B: UNUSABLE on one real fixture**, sealed in H1.6d.
- **Gemma 4 E2B: UNUSABLE on the same fixture**, recorded here.
- **Existing Qwen3.5-9B retain path: previously successful**, with the preserved
  original output for that fixture.

These findings do not establish universal incapability or comparative quality
beyond this tested fixture. No replacement retain model was adopted and no
Hindsight routing change was applied. Per-operation model selection remains
open; the earlier consolidation result does not establish retain suitability.

Saved evidence resides in `/tmp/corvus-h16d-1/` (frozen fixture and rubric),
`/tmp/corvus-h16e-1/` (installed-default audit), `/tmp/corvus-h16e-download/`
(artifact verification), `/tmp/corvus-h16e-2/` (runtime/isolation verification),
and `/tmp/corvus-h16e-3/` (preflight, exact request, rendered tokens, raw response,
schema validation, semantic evaluation, resource samples, and isolation checks).

This seal changes only this project log. No inference, download, application
code/configuration change, bank operation, service restart, `:8106` or `:8107`
stop/start, host reboot/shutdown, or push was performed during sealing.
