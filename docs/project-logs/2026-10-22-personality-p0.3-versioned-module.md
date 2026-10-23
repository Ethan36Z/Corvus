# Corvus Personality P0.3 — Versioned Module, Offline Implementation

**Status: P0.3_IMPLEMENTED_OFFLINE**

## Existing implementation and decision

The repository already had a sealed PERS-A specification and `personality/runtime.py`, integrated through the existing `system_prompt_fn` callback. P0.1 was a separately archived design/API experiment, not an independent runtime module. P0.3 extends the existing package and callback rather than creating another personality system.

Added exact-version JSON profiles, immutable identity/expression records, a deterministic renderer, explicit opt-in configuration and safe fallback. The version selector defaults off. Disabled or invalid selections preserve the legacy PERS-A prompt byte-for-byte; active system and safety instructions are retained before any profile supplement. No application runtime, context assembly, model transport or memory code was changed.

The new profile `corvus-companion@0.1.0` records the specified companion-first, naturally distinctive, curious, warm, independent, aesthetically interested and gender-neutral core identity; voice remains separately configurable. It is an offline candidate pending P0.4 review, not an approved behavioral solution or a repackaged P0.2 prompt.

## P0.2 evidence preserved

Both temporary result sets existed. Their prompts and all 12 visible answers/metrics per run were copied into compact experimental archives under `docs/personality/experiments/p0.2/`, preserving original evaluations and source hashes. First run: REVISE. Final run: BLOCK. No experiment was repeated or revised. These files remain experimental / not approved and are outside the runtime profile directory.

## Validation

`tests/test_personality_profiles.py` adds small offline stdlib contracts. `tests/test_personality_runtime.py` keeps its original contract and adds opt-in, disabled and invalid-selection integration checks using existing stubs. Existing context/Web/Voice/Vision contracts are regression targets. The unchanged legacy policy's SHA-256 is pinned in the compatibility test.

All tests run through the existing offline guard copied to `/tmp` with only the target checkout path changed. No new repository framework, real model calls, network requests or deployed data access are permitted. Final run: 15 Profile unit tests passed, plus all six scripts:

- `test_personality_profiles.py`
- `test_personality_runtime.py`
- `test_web_working_context.py`
- `test_web_conversation_runtime.py`
- `test_voice_conversation_runtime.py`
- `test_vision_conversation_runtime.py`

The five pre-existing script contracts execute module-level assertions rather than unittest cases; they are not counted as additional unit tests. No skips or network/private-access violations. The legacy prompt SHA-256 remains `1c146488ec8fc5a5993e66f2c33f130d06b747aecf75c5e4a5417b36882110e9`. Version switching, disabled/invalid selection, malformed/unreadable files and unresolved profile paths preserve the existing conversation contract.

## Minimal review fix

Final review found all seven profile expression rules already present verbatim in PERS-A. Directly appending the profile therefore sent each rule twice. The shipped incremental profile now has an empty expression list; the loader permits it and the renderer omits the empty section. Core identity and the compiler's legacy/disabled/fallback paths are unchanged. No generic deduplication framework or personality tuning was added.

The new combined-prompt regression pins those seven historical rules independently of the profile and checks each occurs exactly once in the actual enabled compiler output. Existing legacy-hash compatibility remains enforced, and non-empty future expressions retain rendering coverage. The tradeoff is explicit: this profile supplements PERS-A rather than copying a standalone full behavior policy. Profile file/version/model independence is preserved.

## Operational scope and next step

No active Production/Lab configuration, database, service, model parameters, other worktree or Git branch was modified. No deployment, restart, commit or push. The sample config is not auto-loaded.

After human review, P0.4 may validate controlled Lab configuration, token budget and runtime behavior. The module is ready for that integration preparation; personality behavior has not been accepted, and P0.2 remains BLOCK. Stop here.

See [module interfaces and config](../personality/personality-module-p0.3.md) and [P0.2 archive](../personality/experiments/p0.2/README.md).
