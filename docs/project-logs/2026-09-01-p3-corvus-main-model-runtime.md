# Phase 3 Checkpoint — Permanent Corvus Main-Model Runtime

Date: 2026-09-01

## 1. Context

Corvus Phase 3 requires repeated access to the project's main local model for blind benchmark review and later Gate experiments.

Phase 0 used temporary experimental containers. That was appropriate for controlled benchmarking, but repeatedly reconstructing long docker commands is not appropriate for a model that will become a persistent Corvus runtime dependency.

A separate FoxWords service currently uses Qwen3-8B-Q4_K_M. Corvus itself uses Qwen3.5-9B-Q5_K_M.

## 2. Research / Engineering Question

How should Corvus expose its main 9B model reproducibly on an 11 GB RTX 2080 Ti without requiring the model to remain permanently resident in GPU memory?

## 3. Starting Hypothesis

A permanent runtime configuration should be version-controlled, while the actual model container should remain an on-demand resource.

Temporary containers remain appropriate for experiments.

The production-style Corvus runtime should therefore satisfy:

- stable model identity
- pinned llama.cpp runtime
- stable launch parameters
- localhost-only API exposure
- repeatable start and stop behavior
- complete VRAM release when stopped
- no automatic startup that competes with FoxWords for the same 11 GB GPU

## 4. What We Did

Created:

`compose.corvus.yml`

Configured service:

`corvus-llama`

Pinned runtime image:

`ghcr.io/ggml-org/llama.cpp:server-cuda12-b10630`

Pinned local image ID observed during validation:

`sha256:c50a38601c8bbb6dcb2fdbe60ee336faea7c7c7e11a1d5a6396993783617d911`

Main model:

`/home/ethan/srv/shared/models/qwen3.5-9b/Qwen_Qwen3.5-9B-Q5_K_M.gguf`

Runtime parameters:

- alias: `corvus`
- context: 8192
- GPU layers: 99
- CPU threads: 8
- batch: 512
- micro-batch: 512
- parallel slots: 1
- prompt cache disabled
- API: `127.0.0.1:8095`
- model directory mounted read-only

The Corvus service intentionally has no automatic restart policy.

FoxWords may remain a persistent application service, while Corvus can take control of the GPU only when needed.

## 5. Evidence / Results

Docker Compose configuration validation passed.

The service successfully started and returned:

`{"status":"ok"}`

from the llama.cpp health endpoint.

The model API reported:

- alias: `corvus`
- format: GGUF
- parameters: 9,197,093,888
- context: 8192
- quantization: Q5_K Medium

GPU validation while Corvus was loaded:

- RTX 2080 Ti 11 GB
- llama-server VRAM: approximately 6440 MiB
- total GPU memory usage: approximately 7463 MiB

After stopping Corvus:

- llama-server disappeared from the GPU process list
- total GPU memory usage fell to approximately 1020 MiB
- only desktop graphics processes remained

The same existing container was then started again.

After restart:

- `/health` again returned `{"status":"ok"}`
- Docker health transitioned to `healthy`
- port mapping remained `127.0.0.1:8095 -> 8080`

This demonstrates reproducible on-demand model loading and complete GPU release.

## 6. Interpretation

The runtime configuration and the runtime process should be treated as separate concerns.

Corvus needs a permanent, reproducible definition of how its main model runs, but the model itself does not need to stay loaded continuously.

This is particularly important on the fixed RTX 2080 Ti 11 GB host because FoxWords and Corvus use separate models and should not compete for VRAM unnecessarily.

The Phase 0 temporary-container strategy remains useful for controlled experiments, but it should not be the default operational interface for the Corvus main model.

## 7. Decision

KEEP:

- Qwen3.5-9B-Q5_K_M as the current Corvus main model
- llama.cpp CUDA runtime
- localhost-only model API
- on-demand GPU residency

ADOPT:

- version-controlled Compose configuration for the Corvus main-model runtime
- pinned llama.cpp build for reproducibility

REJECT:

- reconstructing the main Corvus runtime with ad hoc docker commands for normal use
- automatically starting Corvus at boot while FoxWords may already occupy the GPU

DEFER:

- automatic model switching / GPU runtime manager
- shared model scheduler between Corvus and FoxWords

These may become useful later but are not required for Phase 3.

## 8. Architecture Impact

Corvus now has a stable main-model runtime boundary:

Corvus components
→ localhost model API
→ `corvus-llama`
→ Qwen3.5-9B-Q5_K_M
→ RTX 2080 Ti

Future Gate, UI, relation-intelligence, and later memory phases can target the stable local API rather than managing llama.cpp launch commands themselves.

Core operational principle:

**Runtime configuration is persistent; GPU residency is on-demand.**

## 9. Open Questions

- Whether Phase 3 demonstrates a useful role for a smaller specialized relation model.
- Whether future Corvus and FoxWords model switching should be automated.
- Whether context size should remain 8192 outside the established baseline.
- Whether later workloads justify separate runtime profiles.

## 10. Next Step

Use the permanent Corvus 9B runtime for a single blind-review benchmark case.

Validate the reviewer output format before running the complete 96-case blind adversarial review.
