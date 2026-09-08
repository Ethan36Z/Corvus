# A3.0 Vision Compatibility Smoke

Date: 2026-09-08

## Context

Corvus Stage A3 adds multimodal, web, and native access to the
existing persistent Corvus runtime.

Before changing the application architecture, the existing local
Qwen3.5 deployment was audited and tested for real image understanding.

## Existing runtime

Language model:

- Qwen3.5-9B
- GGUF: `Qwen_Qwen3.5-9B-Q5_K_M.gguf`
- SHA-256:
  `a686d88ec1e6881f9bf161526826cd6d6874b7f0e80e0f79acf6144a132c5d7e`

Runtime:

- llama.cpp server
- image: `ghcr.io/ggml-org/llama.cpp:server-cuda12-b10630`
- production endpoint: `127.0.0.1:8095`

Hardware:

- NVIDIA GeForce RTX 2080 Ti
- 11 GB VRAM
- Ryzen 7 3700X
- 32 GB system RAM

## Multimodal projector

Matching projector:

`mmproj-Qwen_Qwen3.5-9B-bf16.gguf`

Verified SHA-256:

`d89c4bc142d02ed64aeed5c0a358bdead9109f21f4ada03a6b2df17a1aa94d9e`

The projector is an external model asset and is not stored in Git.

## Compatibility test

An isolated llama.cpp server was started on:

`127.0.0.1:8105`

The test runtime used:

- the existing Q5_K_M language model
- the matching BF16 multimodal projector
- CPU-only language-model execution
- `--no-mmproj-offload`
- no modification to the production `8095` runtime

A deterministic image was generated containing:

- a red square on the left
- a blue circle on the right
- a white background

Qwen correctly described:

- the red square
- the blue circle
- their colors
- their left/right relationship

No OCR pipeline was used.

## Safety result

The production model endpoint remained healthy throughout the test.

The isolated vision container was removed afterward and port 8105 was
confirmed closed.

## Result

`QWEN35_VISION_ON_CORVUS_HARDWARE: VERIFIED`

A3 does not require a replacement language model merely to obtain
image understanding.

The production runtime should not be changed until the application
attachment and multimodal boundaries are ready.
