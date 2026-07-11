# Frugal real-model benchmark

_Measured 2026-07-11 17:19 — mode: **local-ollama stand-in (both tiers on localhost)**._

> Real models, real latency/tokens. Local tokens cost $0 (on-prem); the cloud $ column is **modelled** at the reference price to show the savings of keeping work on the cluster.

| metric | value |
|---|---|
| mode | local-ollama stand-in (both tiers on localhost) |
| prompts_run | 6 |
| cheap_model | qwen2.5-coder:3b |
| strong_model | qwen2.5:7b |
| cheap_latency_p50_s | 1.561 |
| cheap_latency_p95_s | 13.112 |
| cheap_avg_tokens | 61.2 |
| strong_latency_p50_s | 3.699 |
| strong_latency_p95_s | 69.121 |
| quality_retention_cheap≈strong | 4/6 (67%) |
| confidence_mode | self_consistency |
| cascade_escalations | 2/6 |
| local_cost_usd_total | 0.0 |
| modelled_cloud_$_per_1k_requests | 0.055 |
| modelled_cloud_$_per_1M_requests | 55.05 |

**Honest note:** cascade escalation uses a hedging-word confidence signal; real models rarely self-hedge, so on real endpoints wire a logprob/verifier confidence (or `LocalRouter` by cost/privacy) rather than relying on it.
