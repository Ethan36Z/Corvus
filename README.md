# Small-VRAM Personal Companion

A research project exploring how much persistent companion intelligence can be achieved on fixed consumer hardware without increasing the base model size.

## Research Question

How much persistent companion intelligence can be extracted from a fixed consumer hardware budget through:

- long-term memory
- adaptive retrieval
- context construction
- CPU / RAM / SSD orchestration
- background consolidation
- specialist models
- personal adaptation

Reference machine:

- NVIDIA RTX 2080 Ti
- 11GB VRAM
- 32GB RAM
- AMD Ryzen 7 3700X
- Linux Mint 22.3

## Project Principle

The project does not assume that a larger model automatically means a better personal AI.

Instead, it studies the whole system around the model:

Small Model + Long-Term Memory + Context Engine + CPU / RAM / SSD + Background Processing = Stronger Personal AI System

A core hypothesis is that memory retention and memory activation should be separate.

The archive may grow very large, while only a small amount of relevant memory should enter the active prompt.

## Current Status

### Phase 0 — Experiment A: No-Memory Baseline

Baseline:

- Model: Qwen3.5-9B
- Quantization: Q5_K_M GGUF
- Runtime: llama.cpp
- GPU backend: CUDA
- Context size: 8192
- Thinking: disabled
- Persistent memory: none

Current-session conversation context works, but restarting the chat process removes all conversation memory.

This provides the control condition for future long-term memory experiments.

## Baseline Performance

On the RTX 2080 Ti:

- llama-server VRAM usage: approximately 6.46 GiB
- warm decode throughput: approximately 67–71 tok/s
- 146-token warm prefill: approximately 1141 tok/s
- 530-token warm prefill: approximately 1817 tok/s
- 2066-token warm prefill: approximately 2238 tok/s
- 4114-token warm prefill: approximately 2287 tok/s

Three independent fresh-server reproducibility runs completed successfully without OOM.

See benchmarks/experiment-a.md for the complete benchmark record.

## Current Architecture

User -> CLI Chat Loop -> Current-Session Messages in RAM -> llama.cpp -> Qwen3.5-9B

There is currently no persistent memory layer.

## Planned Experimental Path

1. No Memory
2. Vanilla RAG
3. Full Archive + Adaptive Recall
4. Hierarchical Memory
5. Background Consolidation
6. Personal Model Adaptation
7. Multi-Agent experiments

Each stage should be compared using the same base model and hardware whenever possible.

## Repository Structure

- app/chat.py
- benchmarks/experiment-a.md
- .gitignore
- README.md

## Philosophy

Architecture is guilty until benchmarked.

Do not assume a more complex memory system is better.

Measure:

- recall quality
- retrieval latency
- TTFT
- prefill cost
- decode speed
- VRAM usage
- RAM usage
- long-horizon consistency
- false recall
- provenance accuracy
