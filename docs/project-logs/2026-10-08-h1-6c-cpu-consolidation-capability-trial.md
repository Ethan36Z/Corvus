# H1.6c — CPU consolidation capability trial

Date: 2026-10-08

Baseline: `lab/ow2e-console` at `530d877759523f6fa3e3392f73d8331938705579`

Trial verdict: **PASS WITH CONSTRAINTS**. Capability judgment: **USABLE for this
single frozen fixture**. One real consolidation task produced a justified,
schema-valid update on an isolated CPU model. General consolidation quality,
conflict-handling quality, and production readiness remain unestablished.

This documentation seal records the completed experiment from saved artifacts
under `/tmp/corvus-h16c-4/`; it does not rerun inference. The repository baseline
was verified clean before creating this file.

## Model and isolated runtime

- Model: **Qwen3-1.7B Q8_0**, alias `corvus-h16c-cpu`.
- Official artifact: `Qwen/Qwen3-1.7B-GGUF`, revision
  `90862c4b9d2787eaed51d12237eafdfe7c5f6077`, `Qwen3-1.7B-Q8_0.gguf`.
- Local model:
  `/home/ethan/srv/shared/models/qwen3-1.7b/Qwen3-1.7B-Q8_0.gguf`.
- Endpoint: `http://127.0.0.1:8106/v1/chat/completions`.
- Container: `corvus-h16c-cpu-trial`, using the cached llama.cpp **b10630**
  (`d222767c7`) image pinned to
  `sha256:c50a38601c8bbb6dcb2fdbe60ee336faea7c7c7e11a1d5a6396993783617d911`.
- CPU settings: **4 threads**, **8192-token context**, **parallel 1**;
  `runc`, `--device none`, zero GPU layers, no KV or operation offload.
- Generation settings: temperature **0**, seed **42**, reasoning **off**,
  no context shift. The model directory was mounted read-only.

## Frozen fixture and preflight

The real failed consolidation trace was
`454bf090-99eb-4f9f-8171-4a47b4a5672e`. Its complete recorded system and user
messages were recovered from saved audit-session evidence without calling
Hindsight. The system message contained **11742 characters** and the user
message **2111 characters**; neither was simplified or rewritten.

The fixture contained one new source fact,
`e48a7eec-a27f-4214-86e9-1c5e87b644d3`, and three recalled observations with
their supporting facts: the H1.4/library memory-testing event, Corvus GPU
hardware, and Ethan's Corvus project. The matching library observation was
`673b03bb-4980-4fa5-a96c-f24e3e6cbf05`.

The incident's `_ConsolidationBatchResponse` and create/update/delete class
definitions, validators, and strict-schema serializer were reconstructed
offline from the matching installed Hindsight source snapshot at
`/tmp/corvus-h16a-source/`. The request used the real strict structured-output
contract, rather than a relaxed substitute.

The CPU endpoint's `/apply-template` and `/tokenize` paths measured the complete
rendered chat input, including the chat template and disabled-thinking prefix:

- Exact rendered input: **4038 tokens**.
- Available context headroom: **4154 tokens**.
- Completion budget: **4090 tokens**, leaving a **64-token safety margin**.

The per-request limit overrode the old 1024-token server trial default. The
original failed 9B call reported 4129 input tokens; this trial used its own
model/tokenizer/template measurement without changing the frozen messages.

## Single-request result

Exactly **ONE** completion request was sent to the CPU endpoint, with
**zero retries** and a **300-second client timeout**. Monotonic elapsed time was
**68903.404 ms**, reported as **68,903 ms**. The response returned HTTP 200:

- Prompt tokens: **4038**; completion tokens: **189**; total: **4227**.
- `finish_reason`: **stop**; server log: `truncated = 0`.
- Schema validation: **PASS**, against both the actual incident Pydantic
  definitions and their generated strict JSON schema.
- Source-ID validation: **PASS**; every referenced source and observation ID
  belonged to the frozen fixture.

The raw structured response was:

```json
{
  "creates": [],
  "updates": [
    {
      "text": "Memory testing for H1.4 live retain is being performed at the library, involving the user.",
      "observation_id": "673b03bb-4980-4fa5-a96c-f24e3e6cbf05",
      "source_fact_ids": ["e48a7eec-a27f-4214-86e9-1c5e87b644d3"],
      "reason": "The new fact restates the same memory testing event already captured by obs 673b03bb-4980-4fa5-a96c-f24e3e6cbf05 — merged as evidence rather than creating siblings."
    }
  ],
  "deletes": []
}
```

This was **one justified UPDATE**: it recognized the recurring canonical event
and attached the new fact as evidence, avoiding a duplicate CREATE. It proposed
no CREATE or DELETE and left unrelated architecture observations untouched.
There were no invented facts or source IDs, no rambling, and no truncation.
The wording remained grounded in the new fact and existing user involvement,
but dropped the explicit name "Corvus" from the prior observation prose: a
minor loss of specificity. The proposal was safe enough for this fixture;
**no returned operations were applied**. There was no conflict in the fixture,
so conflict handling was not tested.

## Resource and isolation evidence

Peak sampled RSS and process high-water RSS were **2790812 KiB**, approximately
**2.66 GiB**. The cgroup memory peak was **1028423680 bytes**, approximately
**981 MiB**; these are different accounting measures. Server timing attributed
about **52.03 seconds** to prompt evaluation and **16.86 seconds** to generation.

The test container had no GPU device nodes or device requests, used `runc`,
and retained zero GPU offload. Startup logs reported no usable GPU. The CPU
container's identity and configuration remained unchanged during the trial.

Corvus foreground `:8095` remained healthy. Its container identity, PID, start
time, restart count, image, arguments, mounts, and host configuration were
unchanged before and after. Only health/metadata checks were performed there;
no foreground completion or overlap-latency test was submitted.

## Architecture interpretation and limits

The experiment establishes that a **1.7B CPU-resident generative model can
perform at least one real Hindsight consolidation task correctly without
occupying the Corvus foreground GPU inference slot**. It does not establish
general consolidation quality, conflict-handling quality, or production
readiness. The approximately 69-second latency is an observed result for this
fixture, not a throughput guarantee; shared CPU and memory-bandwidth contention
remain possible.

Hindsight was not invoked or reconfigured, and no bank was mutated. Its global
LLM semaphore remains configured at concurrency **1**, so background
throughput/serialization remains a possible constraint even with endpoint
isolation. Corvus foreground is outside that semaphore. This direct endpoint
trial did not exercise Hindsight's scheduling or apply native routing changes;
redirecting consolidation alone would still leave extraction on the shared
foreground server.

Saved evidence includes `frozen-trace.json`, `response-schema.json`,
`preflight-result.json`, `request.json`, `rendered-prompt.txt`,
`input-token-ids.json`, `response.raw.json`, `structured-response.json`,
`trial-result.json`, `validation-result.json`, `resource-samples.json`,
`isolation-result.json`, and `cpu-server-after.log` in `/tmp/corvus-h16c-4/`.

This seal changes only this project log. No additional inference, application
code/configuration changes, bank operations, service restarts, CPU-endpoint
stop/start, host reboot/shutdown, or push were performed during sealing.
