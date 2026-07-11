# Frugal real-model benchmark

_Measured 2026-07-11 13:08 — mode: **local-ollama stand-in (both tiers on localhost)**._

> Real models, real latency/tokens. Local tokens cost $0 (on-prem); the cloud $ column is **modelled** at the reference price to show the savings of keeping work on the cluster.

| metric | value |
|---|---|
| mode | local-ollama stand-in (both tiers on localhost) |
| prompts_run | 12 |
| cheap_model | qwen2.5:0.5b |
| strong_model | qwen2.5:3b |
| cheap_latency_p50_s | 0.249 |
| cheap_latency_p95_s | 1.491 |
| cheap_avg_tokens | 116.1 |
| strong_latency_p50_s | 0.358 |
| strong_latency_p95_s | 2.248 |
| quality_retention_cheap≈strong | 2/12 (17%) |
| confidence_mode | self_consistency |
| cascade_escalations | 9/12 |
| local_cost_usd_total | 0.0 |
| modelled_cloud_$_per_1k_requests | 0.5804 |
| modelled_cloud_$_per_1M_requests | 580.42 |

**Honest note:** cascade escalation uses a hedging-word confidence signal; real models rarely self-hedge, so on real endpoints wire a logprob/verifier confidence (or `LocalRouter` by cost/privacy) rather than relying on it.
