# Experiment A — No-Memory Baseline

## Goal

Establish a reproducible local inference baseline with no long-term memory.

## Hardware

- GPU: NVIDIA GeForce RTX 2080 Ti
- VRAM: 11264 MiB
- Compute Capability: 7.5
- CPU: AMD Ryzen 7 3700X
- CPU cores / threads: 8 / 16
- RAM: 31 GiB
- OS: Linux Mint 22.3
- Kernel: 7.0.0-30-generic

## NVIDIA / CUDA

- NVIDIA Driver: 580.173.02
- Driver-reported CUDA capability: 13.0
- CUDA Toolkit / nvcc: not installed
- NVIDIA Container Runtime: available

## Model

- Model: Qwen3.5-9B
- Quantization: Q5_K_M
- Format: GGUF
- File: Qwen_Qwen3.5-9B-Q5_K_M.gguf
- File size reported by ls: 6.7G
- SHA256:

  a686d88ec1e6881f9bf161526826cd6d6874b7f0e80e0f79acf6144a132c5d7e

## Runtime

- Runtime: llama.cpp
- Build: 10630
- Commit: d222767c7
- Docker image:

  ghcr.io/ggml-org/llama.cpp:server-cuda12-b10630

- Docker digest:

  sha256:c50a38601c8bbb6dcb2fdbe60ee336faea7c7c7e11a1d5a6396993783617d911

## Baseline Parameters

- Context size: 8192
- GPU layers: 99
- Threads: 8
- Batch size: 512
- UBatch size: 512
- Parallel slots: 1
- Temperature: 0
- Top-p: 1.0
- Seed: 42
- Thinking: disabled
- Speculative decoding / MTP: disabled

## Functional Validation

The model successfully loaded on the RTX 2080 Ti without OOM and returned:

SMALL VRAM BASELINE OK

Observed llama-server GPU memory usage:

- approximately 6460–6462 MiB

Observed total GPU usage during inference:

- approximately 8.3 GiB including desktop graphics processes

## Cold-Start Observation

The first inference after a fresh server start showed a large one-time prompt-processing delay.

Example:

- Prompt tokens: 24
- Prompt processing time: 36.24 s
- Prompt throughput: 0.66 tok/s
- Decode throughput: 68.95 tok/s

After warm-up, with prompt cache disabled:

- Prompt tokens: 24
- Prompt processing time: 62.17 ms
- Prompt throughput: 386.04 tok/s
- Decode throughput: 71.42 tok/s

The exact source of the cold-start overhead has not yet been decomposed.

## Warm Prefill Scaling

Prompt cache disabled. Warm server.

| Actual Prompt Tokens | Prompt Time | Prefill Throughput |
|---:|---:|---:|
| 146 | 127.91 ms | 1141.40 tok/s |
| 530 | 291.63 ms | 1817.40 tok/s |
| 2066 | 923.10 ms | 2238.12 tok/s |
| 4114 | 1798.57 ms | 2287.37 tok/s |

During the largest test:

- GPU utilization: 100%
- Power: 255 W / 260 W
- llama-server VRAM: 6462 MiB

## Decode Throughput

Initial short-generation tests showed approximately:

- 67–71 tok/s

## Reproducibility Test

Three independent fresh server starts were tested.

Each run:

- loaded successfully
- completed warm-up
- produced the exact expected response
- did not OOM

| Run | Prompt Tokens | Prompt Time | Prefill tok/s | Decode tok/s | Output |
|---:|---:|---:|---:|---:|---|
| 1 | 533 | 325.13 ms | 1639.32 | 67.48 | BASELINE STABLE |
| 2 | 533 | 322.21 ms | 1654.21 | 66.89 | BASELINE STABLE |
| 3 | 533 | 308.79 ms | 1726.08 | 67.36 | BASELINE STABLE |

Approximate averages:

- Prompt time: 318.71 ms
- Prefill throughput: 1673 tok/s
- Decode throughput: 67.24 tok/s

## No-Memory Chat Validation

The CLI chat loop stores the current conversation only in process memory.

Test:

1. User: My codename is Fox Seven.
2. Same session: model correctly recalled Fox Seven.
3. Program exited.
4. New session started.
5. User asked whether the model knew the codename.
6. Model correctly stated that it did not know.

Result:

- current-session context: working
- persistent long-term memory: none

This is the control condition for future memory experiments.

## Initial Engineering Observations

- Qwen3.5-9B Q5_K_M fits comfortably within the 11GB VRAM constraint.
- Warm inference performance is sufficient for interactive use.
- Long active contexts increase prefill latency, reinforcing the need to separate archive size from active context size.
- Shared persistent inference service is likely preferable to repeatedly starting the model because fresh-start cold inference has a large one-time cost.
- Future memory architecture should be compared against this exact baseline without changing the base model or runtime unless explicitly testing those variables.
