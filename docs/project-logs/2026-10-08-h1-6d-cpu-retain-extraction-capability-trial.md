# H1.6d — CPU retain-extraction capability trial

Date: 2026-10-08

Baseline: `lab/ow2e-console` at `74caefdb8d6264556b112bf721d5f78560869f78`

Trial verdict: **PASS WITH CONSTRAINTS**. Capability judgment: **UNUSABLE for
this fixture**. The single CPU extraction completion was schema-valid but
semantically unsafe: it replaced the explicit event date with the reference
timestamp and introduced unsupported user participation. **Qwen3-1.7B must not
be adopted for retain extraction based on current evidence.**

This seal documents the completed experiment from saved evidence in
`/tmp/corvus-h16d-1/` and `/tmp/corvus-h16d-2/`. It does not rerun inference.
The expected branch and HEAD and a clean worktree were verified before writing
this log.

## Model and isolation

- Model: **Qwen3-1.7B Q8_0**, alias `corvus-h16c-cpu`.
- Isolated endpoint: `http://127.0.0.1:8106/v1/chat/completions`.
- Existing container: `corvus-h16c-cpu-trial`, using the pinned llama.cpp
  runtime recorded in the H1.6c project log.
- CPU runtime: **4 threads**, **8192-token context**, **parallel 1**,
  `--device none`, zero GPU layers, no KV or operation offload, and `runc`.
- Request: temperature **0**, seed **42**, reasoning **disabled**, no context
  shift, **300-second bounded client timeout**, and **zero retries**.

## Frozen real fixture and contract

The fixture came from a **real successful Hindsight retain-extraction call in
H1.5b**, with these identifiers:

- Operation trace: `0fba3290-de4a-4791-b74f-551b1c7cff8a`.
- Request: `badade06-197e-4ffa-8845-79a849a7a066`.
- Source: `corvus-lab`.
- Session: `lab-h13b-0e2f855d-dc5d-4396-bbac-9594db4f1ee7`.
- User message **11**, assistant message **12**;
  document `corvus-lab:turn:11:12`.

The input exchange was:

> User: Where was Corvus memory testing being performed on October 7, 2026?
>
> Assistant: The memory testing for H1.4 live retain was being performed at the library.

The chunk's reference timestamp was **October 8, 2026 at 00:29:40 UTC**.
The remembered event explicitly happened on **October 7**; the reference
timestamp must not replace that date. The original successful output preserved
`when: "2026-10-07"`, `fact_kind: "event"`, and day-level occurrence timestamps,
used `who: "N/A"`, and included the Corvus entity.

The replay used the exact frozen system and user messages without rewriting,
shortening, or tuning them. The actual **FactExtractionResponse** schema was
already embedded in the system prompt. The original provider contract used
`response_format: {"type": "json_object"}`; the schema was neither appended
again nor replaced by a different strict grammar. Offline validation used the
corresponding Hindsight Pydantic definitions and verified that their generated
provider schema matched the frozen schema.

Fixture hashes were verified before and after the trial. Source/session/message
identifiers remained preserved in the evaluation harness; they are provenance
metadata, not required model-output fields. The trial made no Hindsight calls.

## Token budget and single-request result

Before inference, the CPU endpoint's template and tokenizer APIs remeasured
the complete rendered chat input, including the chat template and disabled
thinking prefix:

- Input: **3536 tokens**, matching fixture preparation.
- Completion budget: **4096 tokens**.
- Context: **8192 tokens**; safety margin: **560 tokens**.

Exactly **ONE** extraction completion was submitted. Monotonic elapsed time
was **53242.089 ms**, reported as **53242 ms**. The response returned HTTP 200:

- Prompt tokens: **3536**; completion tokens: **119**; total: **3655**.
- `finish_reason`: **stop**.
- Schema validity: **PASS** against the real FactExtractionResponse contract.
- One extracted fact; no truncation or rambling.

The raw structured result was:

```json
{
  "facts": [
    {
      "what": "The memory testing for H1.4 live retain was being performed at the library",
      "when": "2026-10-08T00:29:40+00:00",
      "where": "library",
      "who": "user",
      "why": "N/A",
      "fact_type": "world",
      "entities": ["H1.4 live retain", "library"],
      "causal_relations": []
    }
  ]
}
```

## Offline semantic evaluation

The result captured one meaningful fact and was broadly faithful to the testing
activity and library location. Its `world` classification was appropriate.
Equivalent wording was accepted; matching the original output verbatim was
not required.

However, **date fidelity failed**: the output used the October 8 reference
timestamp instead of the explicit October 7 event date. It also introduced
`who: "user"`, attributing participation that the question and answer did not
establish. This is an unsupported actor attribution, even though the original
output included a generic user entity. The original output was a comparison
artifact, not a reason to accept unsupported participation.

The output omitted the **Corvus entity**, **event classification**, and
**occurrence timestamps**. Omitting `fact_kind` is allowed by the schema but
defaults to `conversation` in the real model, losing the event semantics.
There were no invented source IDs, attachment references, or causal links.
External provenance was preserved, but the remembered date and participant
attribution were not faithful to the source.

Retention safety: **UNSAFE**. Capability judgment: **UNUSABLE for this real
fixture**. No extracted result was applied or retained, and no repair, prompt
tuning, or second attempt was performed.

## Resource and isolation evidence

Peak sampled RSS and process high-water RSS were **3267208 KiB**, approximately
**3.12 GiB**. The cgroup memory peak was **1517400064 bytes**, approximately
**1.41 GiB**; these are distinct accounting measures.

The endpoint remained **CPU-only with no GPU use**: zero GPU offload,
`--device none`, `runc`, no GPU device requests or exposed GPU device nodes,
and unchanged CPU-container identity and configuration.

Corvus foreground **:8095 remained healthy and unchanged** before and after
the request. Its container identity, PID, start time, restart count, image,
arguments, mounts, and host configuration matched the saved baseline. Only
read-only health and identity checks were performed; no foreground completion
was sent.

There was **no Hindsight invocation**, **no bank mutation**, and **zero retries**.

## Architecture interpretation

**Schema-valid output is not sufficient for retain extraction.** Qwen3-1.7B
produced a syntactically valid but semantically unsafe memory record on this
real fixture, failing temporal fidelity, entity completeness, and faithful
attribution to the source conversation.

Therefore, **Qwen3-1.7B must not be adopted for retain extraction based on
current evidence**. This does not prove universal incapability; it establishes
failure on one real fixture and blocks adoption without further evidence.

The operation-specific evidence differs:

- **Consolidation: USABLE on one real fixture**, as sealed in H1.6c.
- **Retain extraction: UNUSABLE on one real fixture**, as recorded here.

This supports keeping **per-operation model selection open**. Neither result
establishes general quality or production readiness, and no routing or Hindsight
configuration change was selected or applied by this trial.

The frozen fixture directory preserves exact messages, schema, original output,
provenance manifest, hashes, rendered tokens, and evaluation rubric. The trial
directory preserves `preflight-result.json`, `request.json`,
`response.raw.json`, `structured-response.json`, `trial-result.json`,
`validation-result.json`, `evaluation-result.json`, `resource-samples.json`,
container identity snapshots, `isolation-result.json`, and server logs.

This seal changes only this project log. No inference, model download,
application code/configuration change, bank operation, service restart,
CPU-endpoint stop/start, host reboot/shutdown, or push was performed during
sealing.
