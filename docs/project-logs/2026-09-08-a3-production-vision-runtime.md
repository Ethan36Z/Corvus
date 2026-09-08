# A3.2a Production Vision Runtime

Date: 2026-09-08

## Goal

Enable Qwen3.5 multimodal inference in the existing production llama.cpp
runtime without creating a second Corvus model service or materially reducing
the daily-use text runtime.

## Baseline

Production model:

`Qwen_Qwen3.5-9B-Q5_K_M.gguf`

Matching multimodal projector:

`mmproj-Qwen_Qwen3.5-9B-bf16.gguf`

Verified SHA-256 values:

Model:

`a686d88ec1e6881f9bf161526826cd6d6874b7f0e80e0f79acf6144a132c5d7e`

Projector:

`d89c4bc142d02ed64aeed5c0a358bdead9109f21f4ada03a6b2df17a1aa94d9e`

Pinned llama.cpp image:

`ghcr.io/ggml-org/llama.cpp:server-cuda12-b10630`

## Runtime configuration

The existing production model remains GPU offloaded with:

`-ngl 99`

The multimodal projector is enabled with:

`--mmproj /models/mmproj-Qwen_Qwen3.5-9B-bf16.gguf`

and kept off the GPU with:

`--no-mmproj-offload`

This preserves GPU headroom for the language model, KV cache, and runtime
working memory.

## Production vision acceptance

A deterministic image was generated containing:

- red square on the left
- blue circle on the right
- white background

The real production llama.cpp endpoint responded:

`The red square is on the left, and the blue circle is on the right.`

Measured vision request latency:

`1.945 seconds`

Result:

`PRODUCTION_QWEN_VISION: PASS`

## GPU behavior

Before enabling multimodal runtime:

- GPU used: 8006 MiB
- GPU free: 2813 MiB

After real vision inference:

- GPU used: 7994 MiB
- GPU free: 2825 MiB

No meaningful persistent VRAM increase was observed.

System RAM remained healthy with approximately 24 GiB available after the
vision smoke.

## Text regression

The first text inference immediately after recreating the llama.cpp container
took:

`35.237 seconds`

A subsequent warm-runtime test produced:

- request 1: 0.258 s
- request 2: 0.155 s
- request 3: 0.158 s
- average: 0.190 s

Therefore the 35-second result is classified as first-inference cold-start
behavior rather than persistent multimodal text regression.

Future deployment polish may issue a small warm-up request after llama.cpp
startup, but this is not an A3.2 blocker.

## Service compatibility

After multimodal enablement:

- llama.cpp health: OK
- Private Corvus API: OK
- Demo Corvus API: OK
- Private dense recovery: caught up
- Demo dense recovery: caught up

## Result

`A3_PRODUCTION_VISION_RUNTIME: PASS`

`A3_VISION_WARM_TEXT_REGRESSION: PASS`

A3.2a Production Vision Runtime is complete.

Next:

A3.2b should integrate a stored image attachment into the existing
`process_turn()` authority while preserving SQLite-first canonical evidence,
text retrieval, and the single Corvus conversation runtime.
