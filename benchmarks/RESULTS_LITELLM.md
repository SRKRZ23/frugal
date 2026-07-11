# Frugal vs LiteLLM — LIVE bake-off (2026-07-12 05:27, carlito4)

_Real calls through Ollama (qwen2.5-coder:3b / qwen2.5:7b), 12 prompts. LiteLLM = plain proxy (all→strong); Frugal = LocalRouter (easy→cheap, hard→strong). $ modelled at GPT-4o-mini/4o prices; local tokens are $0. Cloud-key run = when keys provided._

Baseline: **proxy-baseline (litellm not installed — same pass-through)**.

| metric | proxy (all→strong) | Frugal (routed) | Frugal saves |
|---|---|---|---|
| strong-model calls | 12 | 6 | — |
| total latency (s) | 373.9 | 252.3 | 32.5% |
| modelled cost (USD) | 0.01568 | 0.00723 | 53.9% |
