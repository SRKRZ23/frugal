# Frugal FAQ

**🇬🇧 English · [🇷🇺 Русский](FAQ.ru.md)**

**Isn't this just LiteLLM / a proxy with a router?**
No — the proxy is one of nine pieces. Frugal's point is the *decide + verify* loop: a
cost-aware cascade with a real confidence check, offline eval/RAG asserts for CI, an MCP
server exposing the agent's own spend, local-first routing, and a reproducible model-vs-model
benchmark. If you only need a provider proxy, use LiteLLM. See the comparison in the README.

**Are the benchmarks real or cherry-picked?**
Real and reproducible — `python benchmarks/run_all.py` / `bench_models.py`. They're also
**small** (N=5–6, a 7B judge, mostly CPU) and we say so in [WEAKNESSES.md](../WEAKNESSES.md).
Re-run them on your models and dispute the numbers; that's the point.

**How much will it actually save me?**
Depends on the price gap and confidence signal. Real prices: ~**75–91%** cloud (GPT-4o-mini→4o),
up to ~**97%** with a local cheap tier. It can even **lose** money on a small price gap
(Haiku→Sonnet) with self-consistency — Frugal warns you when that's the case. Full math:
[BUSINESS_CASE.md](../BUSINESS_CASE.md).

**When does Frugal NOT save money?**
When the cheap tier isn't much cheaper (<~10×) *and* you use a re-sampling confidence signal —
the probing eats the margin. Fix: use logprob/free confidence, a local ($0/token) cheap tier, or
don't cascade that pair. Frugal computes this and emits a warning.

**Does it work with my provider?**
Anything OpenAI-compatible (OpenAI, vLLM, Fireworks, Together, local llama.cpp) via `get_openai`,
and Ollama via `get_ollama`. Prices are user-editable in `frugal/meter/pricing.py`.

**Is my data safe with local routing?**
`private`-tagged prompts always stay on the local model (tested: 0 leaks, incl. across a network
hop). The `guard` PII/injection checks are a **first-line heuristic**, not a security product —
don't make them your only control. See [WEAKNESSES.md](../WEAKNESSES.md).

**How is "confidence" decided for escalation?**
Pluggable. `hedging` (cheap, weak on real models), `self_consistency` (re-sample & compare —
works on real models, costs extra), or bring your own (logprobs / a verifier). Default is
hedging; use `make_self_consistency` for real models.

**Will this be maintained, or is it abandonware in 3 months?**
Actively maintained, Apache-2.0, issues/PRs triaged. Roadmap in the README (broader evals,
logprob confidence, pre-reservation budget, LiteLLM bake-off). No foundation promised — honest,
responsive upkeep.

**Is it thread-safe / production-safe?**
The metered ledger is locked; the budget cap is thread-safe (bounded overshoot); memory is
bounded via `max_history`; guards are ReDoS-checked; the router survived 3000 fuzzed prompts.
See `benchmarks/stress_test.py`.

**Do I need a GPU / a cluster?**
No. Everything runs offline on the mock provider. Local models (Ollama) and clusters are
optional and make the cheap tier faster/cheaper (≈11× faster on a modest GPU in our test).

**What's the fastest way to see value?**
`frugal demo`, then `python examples/live_cost_demo.py`, then `python benchmarks/cost_model.py`
with your own prices.
