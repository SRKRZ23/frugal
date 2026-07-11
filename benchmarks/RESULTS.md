# Frugal benchmark results

_Measured 2026-07-12 on the offline deterministic MockProvider + labelled synthetic datasets (`benchmarks/data.py`). Reproducible: `python benchmarks/run_all.py`._

> **What this proves:** cost arithmetic, routing/escalation accuracy, privacy-leak safety, guard precision/recall, eval/RAG gate accuracy, and metering overhead — all exact.
>
> **What it does NOT prove:** real-model answer quality (mock text is synthetic). Run `benchmarks/bench_cluster.py` against real models for quality retention.

## 1. Cost-aware routing (meter + route)

| metric | value |
|---|---|
| prompts | 26 |
| cascade_cost_usd | 0.001714 |
| frontier_only_cost_usd | 0.021715 |
| cheap_only_cost_usd | 0.000302 |
| cost_saved_vs_frontier_pct | 92.1 |
| escalation_precision | 1.0 |
| escalation_recall | 0.4 |
| escalation_f1 | 0.571 |
| calls_cascade | 31 |
| calls_frontier_only | 26 |

## 2. Local↔cloud routing + privacy (local)

| metric | value |
|---|---|
| prompts | 26 |
| routed_local | 25 |
| routed_cloud | 1 |
| local_share_pct | 96.2 |
| private_prompts | 6 |
| private_leaked_to_cloud | 0 |
| cloud_cost_avoided_by_local | 25 calls kept off the paid tier |

## 3. Eval gates (eval)

| metric | value |
|---|---|
| semantic_pairs | 10 |
| semantic_best_threshold | 0.2 |
| semantic_accuracy | 0.8 |
| groundedness_examples | 6 |
| groundedness_accuracy | 1.0 |
| hallucination_flag_precision | 1.0 |
| hallucination_flag_recall | 1.0 |

## 4. RAG checks (rag)

| metric | value |
|---|---|
| examples | 5 |
| gate_accuracy_vs_label | 1.0 |
| retrieval_hit_rate | 0.6 |
| faithfulness | 0.6 |
| citation_coverage | 0.6 |

## 5. Guardrails (mcp.guard)

| metric | value |
|---|---|
| samples | 10 |
| pii_precision | 1.0 |
| pii_recall | 1.0 |
| pii_f1 | 1.0 |
| injection_precision | 1.0 |
| injection_recall | 1.0 |
| injection_f1 | 1.0 |

## 6. Metering overhead (meter)

| metric | value |
|---|---|
| calls | 5000 |
| total_s | 0.027 |
| calls_per_sec | 185292.7 |
| overhead_ms_per_call | 0.0054 |

## 7. Cost projection at scale (meter + route)

| metric | value |
|---|---|
| per_request_cascade_usd | 6.594e-05 |
| per_request_frontier_usd | 0.00083519 |
| at_100k_requests | {'cascade_usd': 6.59, 'frontier_only_usd': 83.52, 'saved_usd': 76.93} |
| at_1M_requests | {'cascade_usd': 65.94, 'frontier_only_usd': 835.19, 'saved_usd': 769.25} |
| at_10M_requests | {'cascade_usd': 659.4, 'frontier_only_usd': 8351.92, 'saved_usd': 7692.52} |
| monthly_saved_usd_at_50k_per_day | 1153.88 |

## 8. Escalation-threshold sweep (route)

| metric | value |
|---|---|
| sweep | {'min_confidence': 0.3, 'esc_precision': 1.0, 'esc_recall': 0.0, 'esc_f1': 0.0, 'cost_usd': 0.000302}<br>{'min_confidence': 0.5, 'esc_precision': 1.0, 'esc_recall': 0.4, 'esc_f1': 0.571, 'cost_usd': 0.001714}<br>{'min_confidence': 0.6, 'esc_precision': 1.0, 'esc_recall': 0.4, 'esc_f1': 0.571, 'cost_usd': 0.001714}<br>{'min_confidence': 0.7, 'esc_precision': 1.0, 'esc_recall': 0.4, 'esc_f1': 0.571, 'cost_usd': 0.001714}<br>{'min_confidence': 0.8, 'esc_precision': 1.0, 'esc_recall': 0.4, 'esc_f1': 0.571, 'cost_usd': 0.001714}<br>{'min_confidence': 0.9, 'esc_precision': 1.0, 'esc_recall': 0.4, 'esc_f1': 0.571, 'cost_usd': 0.001714} |
| note | higher min_confidence => more escalation (higher recall) => higher cost; pick the knee |

