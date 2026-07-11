# Awesome On-Prem / Local-First AI [![Awesome](https://awesome.re/badge.svg)](https://awesome.re)

A curated list of tools for running AI **on your own hardware** — for cost, privacy,
sovereignty, and regulated/air-gapped environments. PRs welcome.

## Local inference engines
- **[Ollama](https://github.com/ollama/ollama)** — one-command local LLM runner (Llama, Mistral, Gemma, DeepSeek).
- **[vLLM](https://github.com/vllm-project/vllm)** — high-throughput serving; ROCm build runs on AMD MI300X/Radeon.
- **[llama.cpp](https://github.com/ggml-org/llama.cpp)** — CPU/GPU inference in C/C++, GGUF quantization.
- **[LM Studio](https://lmstudio.ai/)** — desktop local-model runner with an OpenAI-compatible server.

## UIs & gateways
- **[Open WebUI](https://github.com/open-webui/open-webui)** — self-hosted, offline-capable ChatGPT-style UI.
- **[LiteLLM](https://github.com/BerriAI/litellm)** — proxy across 100+ providers, incl. local.
- **frugal** (this project) — metering + budget gateway + cost routing + eval for local/cloud.

## AMD / ROCm specifics
- **[ROCm](https://github.com/ROCm/ROCm)** — AMD's open GPU compute stack.
- **[rocm/vllm image](https://hub.docker.com/r/rocm/vllm)** — prebuilt vLLM for AMD (see `frugal local` quickstart).

## Quantization & efficiency
- **[GGUF](https://github.com/ggml-org/ggml)**, **[AWQ](https://github.com/mit-han-lab/llm-awq)**, **[GPTQ](https://github.com/AutoGPTQ/AutoGPTQ)** — run big models on small hardware.

## Eval & observability (local-first)
- **frugal.eval** — offline semantic asserts + drift, no SaaS.
- **[MLflow](https://github.com/mlflow/mlflow)** — OTel tracing for local LLMs.

## Why on-prem?
Cost predictability · data never leaves the building · works with bad/no network ·
compliance (regulated, sovereign, air-gapped) · no per-token vendor tax.

---
*Maintained as part of [frugal](https://github.com/frugal-ai/frugal). Contributions from
anyone building the local-first AI stack are welcome.*
