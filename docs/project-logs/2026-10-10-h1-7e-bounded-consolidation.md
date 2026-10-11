# H1.7e-1 — Bounded consolidation

Date: 2026-10-10 local time. Verdict: PASS WITH CONSTRAINTS — bounded runtime deployed and one frozen real consolidation replay passed; oversized singleton work can remain durably deferred, and per-attempt bounds do not certify general memory quality or total job latency.

## Safe baseline and known failure

Lab was clean on `lab/ow2e-console` at `ecb692d6f5747d4b5997253f097b48e0290c9a83`; Production was clean on `main` at `c315d0e767e31fde3c82ba4dfb08659a268c267a`. Hindsight 0.10.1 was healthy on the validated admission image `sha256:344abefa75512314309102e9d0391a0a346a6258d538bbbd881620cc5da69689`, container `d10028ca1b99d0ae02d4bd43cd2a81b8bdd65248600948481bd58a8485949f99`. All eleven then-guarded source/dependency hashes matched. Lab durable async retain remained enabled, its ledger had zero unresolved intents, both foreground publishers were healthy/idle, and the registry read-only mount and 30-second admission configuration were active.

The bank `corvus-hindsight-lab-v1` had nine documents, nine memories and thirteen completed operations. :8095 remained Qwen3.5-9B Q5_K_M, alias `corvus`, one 8192-token slot; its process and runtime properties were captured read-only. Lab PID 13671, Production PID 2831871 and foreground model PID 2867 were preserved.

The frozen incident `454bf090-99eb-4f9f-8171-4a47b4a5672e` previously consumed approximately 4038 input and 4063 generated tokens, exhausted the 8192 context, raised OutputTooLongError and occupied the shared model for approximately 64 seconds. Retained facts remained valid. This was a context/output budget failure; it did not establish semantic incapability of the trusted 9B model. No model-selection research was reopened.

## Exact generation contract and narrow patch

Installed `engine/consolidation/consolidator.py::_consolidate_batch_with_llm` constructs the system instructions and user facts/pooled observations, selects the real `_ConsolidationBatchResponse`, then calls the LLM wrapper with scope `consolidation`. Its completion argument is omitted when `consolidation_max_completion_tokens` is unset. Existing `CONSOLIDATION_MAX_TOKENS=512` limits retrieved input, **not generated output**. Source-fact retrieval budgets remain 4096 overall and 256 per observation; configured parallelism remains four and global LLM concurrency remains one.

The actual custom OpenAI-compatible provider is `openai`, base `http://corvus-llama:8080/v1`, model alias `corvus`. `engine/providers/openai_compatible_llm.py::OpenAICompatibleLLM.call` adds schema text/JSON hints or grammar, merges provider options and enters per-attempt permits before sending. This deployment emits **`max_tokens`**; the native `llamacpp` transport uses `max_completion_tokens`. Bounding only the earlier unwrapped prompt would miss provider-added input.

The existing guarded patch now introduces `engine/consolidation_budget.py` and inserts its preflight immediately before the SDK create call in both structured and free-form branches of the existing retry loop. Only scopes `consolidation` and `consolidation_dedup` are affected. Existing admission/defer source bytes are unchanged; retain/foreground behavior, schema/action semantics, worker SQL and ordinary error classification were not redesigned. No tool/Reflect functionality was added.

## Budget, counting and reasoning

Deployed settings:

```text
CORVUS_CONSOLIDATION_CONTEXT_LIMIT=8192
CORVUS_CONSOLIDATION_SAFETY_MARGIN_TOKENS=256
HINDSIGHT_API_CONSOLIDATION_MAX_COMPLETION_TOKENS=1024
HINDSIGHT_API_CONSOLIDATION_LLM_BATCH_SIZE=1
HINDSIGHT_API_CONSOLIDATION_LLM_REASONING_EFFORT=none
HINDSIGHT_API_CONSOLIDATION_LLM_EXTRA_BODY={"chat_template_kwargs":{"enable_thinking":false}}
```

The new budget feature is disabled when its context-limit setting is absent. When enabled, counting uses the provider's own server origin, verifies `/props` model alias/context, renders the **final wrapped request** through `/apply-template`, and tokenizes that rendered prompt through `/tokenize` with special-token parsing/insertion. No character-count or foreign-tokenizer estimate is used. Counting is bounded by a five-second overall deadline, with no generation, sleep or HTTP retry.

For each provider attempt:

```text
available = 8192 - rendered_input_tokens - 256
allowed_completion = min(1024, explicit requested cap if supplied, available)
allow only if allowed_completion >= 512
rendered_input_tokens + allowed_completion + 256 <= 8192
```

The 1024 cap is defensible for a one-source-fact structured maintenance response: the old CPU fixture needed 189 tokens, and this real 9B replay needed 161. It is a separate completion control, not reuse of retrieval budget. The explicit 256-token margin reserves template/wrapping/control-token/counting headroom; actual server input usage agreed exactly with preflight in the replay. At the tight boundary, a 7424-token input receives 512 output tokens; 7425 or more cannot meet this minimum and defers. No source text or provenance is shortened.

For these consolidation scopes only, the final request independently forces `reasoning_effort=none` and `chat_template_kwargs.enable_thinking=false`; counting uses the same template options. These do not change foreground or retain reasoning. Extra-body overrides of model/messages/token limits are rejected as untrustworthy rather than allowing a different request to bypass the measured cap. Unsupported/missing tokenizer, model/context mismatch, malformed responses/configuration or insufficient space raises DeferOperation, not an ordinary provider failure.

## Existing batching, durable oversize handling and foreground priority

Existing batching is reduced from eight to **one source fact** before budget preflight. The read-only effective bank config confirmed batch size one and no bank overrides. Static cap/reasoning defaults were verified separately, and the actual outgoing SDK request proves the effective cap. Static fields absent from the bank-config API are not interpreted as unset.

If a singleton plus its recalled observations is still oversized, the preflight raises DeferOperation before generation. The already-patched consolidator propagates it before normal retries/bisection/failure marking; the existing durable worker leaves pending work eligible with next_retry_at and no normal retry consumption. Prior committed batches remain committed. There is no blind truncation, failed-fact stamp from budget alone, new queue/framework, or recursive splitting of an unsplittable fact. Persistent oversize may need operator attention and is not promised automatic resolution.

Ordering is preserved and strengthened:

```text
operation/global permits
→ existing foreground admission
→ exact budget preflight
→ foreground admission recheck immediately before send
→ capped provider request
→ permit release
```

BUSY, UNKNOWN and recovery/idle grace still raise DeferOperation; counting does not bypass foreground priority. Foreground arrival during counting is caught by the second check. The remaining arrival-after-final-check race is unchanged: there is no preemption or perfect arbitration. Reflect remains deferred.

## Offline validation

- **14** new budget tests: known 4038/4090 failure cannot receive unsafe output; exhaustive 0–8192 input-count invariant; small/useful and boundary budgets; oversize/unknown/invalid configuration deferral; no extra-body bypass; final soft-schema input counted; actual SDK request capped inside permits; repeated provider errors recheck each attempt; BUSY prevents counting/send; permits release; deferred consolidator produces no failed batch; exact server template/tokenization contract; disabled/non-consolidation behavior unchanged.
- **28** existing reader/admission tests passed, including BUSY/UNKNOWN/grace, liveness/crash, retry ordering and no send on defer.
- **27** existing defer/control-flow/guard tests passed, including no bisection/failed-fact marking on intentional defer, durable pending/no retry consumption, partial committed work and no false COMPLETED/FAILED.
- **10** ordinary-error regressions also passed against pristine upstream.
- **7** deployment preservation/upgrade tests passed, including unchanged admission bind/settings, exact budget-only additions, immutable original recipe, and rejection of model/security/resource/mount/admission drift.
- The preserved H1.6c schema/source-ID validation passed again offline; no real request was involved in that check.

The final derived image itself passed all **69** focused patch tests (14 + 28 + 27), not merely the host edits. Syntax checks and git diff --check passed. No new unbounded provider retry/bisection loop is introduced; deliberate worker deferral uses its existing scheduling behavior.

## Guarded build, rollout and rollback

The existing `deploy/hindsight-patches/0.10.1/` combined diff/manifest/application guard was extended, not replaced. All ten guarded upstream/dependency hashes, distribution/version and introduced-file absence must match before application; all twelve output/dependency hashes are checked afterward. No full upstream source tree was vendored. Previously validated admission/defer hashes remained identical; only the OpenAI-compatible provider request seam and the new budget module add behavior.

The existing builder used immutable cached upstream base `sha256:b4d3b76f363aa40cf348450e7f8f52a50653008731b99824b14623a196182e73` and the extended combined patch. It used `--pull=false`, network-disabled build steps and installed/downloaded no models or packages. Prior validated images were retained.

Derived tag: `corvus-hindsight:0.10.1-h17e1-ecb692d`.

Derived image: `sha256:36a59577d7bdabe7525a114f8baa9bd26bac195df99e1999c807a3301be284f8`.

Current container: `271da9e5744daf97b14005294dc384fb139054daae310ec095b4fe391006c1b9`, PID 517830, started `2026-10-11T03:15:43.425388303Z` (October 10 locally).

The runtime recipe gained an explicit bounded upgrade option. Its strict validator confirmed that only image and six consolidation settings changed relative to the prior admission runtime. Existing read-only registry bind/admission settings, persistent/cache volumes, bank/model routing, environment, user, command/entrypoint, localhost ports, network, restart policy, security/capability/resource settings and labels were preserved. No Corvus or model service was restarted. Docker was available to the normal operator account; no sudo password bypass was used.

The first bounded-upgrade startup validation accessed a bank-configurable field through Hindsight's protected static config proxy. Validation failed and the helper automatically restored the exact prior admission container/image/config/volumes, with unchanged bank/operations. The helper was corrected to inspect raw deployment defaults; effective bank batch configuration was separately checked read-only. This did not alter the patch or derived image. Retrying that same image passed guarded source verification, cap/batch/reasoning checks, reader UNKNOWN → IDLE after **30.030188 seconds**, and EROFS read-only verification. The observation horizon remains 75 seconds; admission grace remains 30 seconds. Bank and all thirteen operation records stayed unchanged at startup. Existing provider verification probes are not retain/consolidation work.

Rollback is ready to the previous **admission-enabled** runtime, retained stopped at `hindsight-lab-h17d3c-rollback-d10028ca1b99`; its exact Config/HostConfig/image/mounts were reverified. The private mode-0600 snapshot is `/tmp/corvus-h17e-1/before.json`.

```sh
python3 -B deploy/hindsight-runtime/0.10.1/runtime.py --snapshot /tmp/corvus-h17e-1/before.json --image sha256:36a59577d7bdabe7525a114f8baa9bd26bac195df99e1999c807a3301be284f8 --bounded-consolidation --rollback
```

Rollback deletes no persistent volume or bank evidence. It was not performed after successful acceptance. Private full environment/inspection snapshots are not committed.

## One real frozen consolidation acceptance

The same saved trace `454bf090-99eb-4f9f-8171-4a47b4a5672e` was reconstructed in an isolated Python process inside the new Hindsight container. Its one source fact and three observations/source-memory serializations were fed to the **installed** `_consolidate_batch_with_llm`, real `_ConsolidationBatchResponse`, wrapper and actual provider. Before any model send, the generated system/user messages were asserted byte-for-byte equal to the saved real fixture. Local lookup indices only reconstruct the frozen source-memory serialization; they are not provenance UUIDs and are never rendered. The original source/observation IDs and task semantics were unchanged.

This process never initialized a MemoryEngine, submitted a bank operation or applied returned actions. It respected its own reader's full 30-second recovery grace before calling the real admission/budget path. Exactly one provider completion was allowed, with SDK/provider/outer retries disabled for this acceptance and an exclusive one-shot marker preventing accidental resubmission. Capturing outgoing SDK parameters/response did not rewrite the request. No chat/retain/replay or extra completion was sent.

Observed preflight:

```text
[CONSOLIDATION_BUDGET] scope=consolidation input_tokens=4131 completion_tokens=1024 safety_margin=256 context_limit=8192 total_reserved=5411 request_parameter=max_tokens reasoning=none thinking=false
```

The new exact count includes current provider/schema/template wrapping and disabled-thinking rendering; the approximate earlier 4038 count is not substituted for it. Actual provider request carried `max_tokens=1024`, `reasoning_effort=none`, `enable_thinking=false`. Server usage was **4131 prompt + 161 completion = 4292 total tokens**, finish_reason **stop**. Elapsed LLM/consolidator time was **4321.221 ms**, excluding the mandatory observer recovery grace. There was no OutputTooLongError, retry, bisection or failed batch.

The real response schema validated and source-ID checks passed. It proposed **one UPDATE**, no CREATE/DELETE:

- Observation: `673b03bb-4980-4fa5-a96c-f24e3e6cbf05`.
- Source fact: `e48a7eec-a27f-4214-86e9-1c5e87b644d3`.
- Text: “Memory testing for H1.4 live retain was being performed at the library on October 7, 2026.”
- Reason: merge the same existing testing event as additional evidence instead of creating a duplicate.

The date/activity/location are faithful and no source ID was invented. Wording omits the existing observation's Corvus/user qualifiers; no operations were applied, and this bounds acceptance is not a general semantic-safety certification. The actual consolidator returned normally with failed=false. No durable bank operation is claimed completed by this replay: it tested the real generation path without storage side effects.

## Final isolation and limitations

Bank remained **9 documents / 9 memories**, with the same **13 completed operations** before restart, after startup and after replay. No new bank data/operations or canonical/private records were created. Corvus's live retain ledger/hash and zero-unresolved state remained unchanged. Host aggregate/publishers returned healthy IDLE; registry bytes/inodes remained unchanged. Production HEAD/worktree, PID, configuration and private SQLite/dense state were unchanged. Lab PID/config/canonical evidence were unchanged; :8095 properties, process/container identity and one-slot/context settings were unchanged. :8106/:8107 were untouched. No Reflect, model routing change/download, automatic reconciliation, unrelated restart, reboot or push occurred.

Bounds apply per attempt, not to the entire multi-batch job; existing finite ordinary-error retries can still lengthen work. A response needing more than the cap can still truncate and follow existing model/schema-error behavior. Oversized singletons defer and can need operator attention; continuous foreground use can starve background work. The exact counting path adds bounded read-only server calls and requires compatible tokenizer/template endpoints. The accepted admission race remains without preemption. One frozen fixture proves the invariant/request cap and a normal real response, not universal consolidation quality or production readiness.

Next engineering objective: **H1 final daily-use acceptance and seal**, preserving these constraints and the frozen model choices. No new architecture work was started here.
