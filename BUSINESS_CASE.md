# Frugal — business case (real prices, honest math)

All figures below are produced by `benchmarks/cost_model.py` (re-run it, change the inputs,
dispute it). Prices are **approximate list prices, 2026-07** — verify before quoting:

| tier | model | $/1M in | $/1M out | source |
|---|---|---|---|---|
| frontier | GPT-4o | 2.50 | 10.00 | OpenAI |
| cheap | GPT-4o-mini | 0.15 | 0.60 | OpenAI (~16× cheaper) |
| frontier | Claude Sonnet 4.6 | 3.00 | 15.00 | Anthropic |
| cheap | Claude Haiku 4.5 | 1.00 | 5.00 | Anthropic (~3× cheaper) |
| frontier | Llama-70B | 0.90 | 0.90 | Fireworks/Together |
| cheap | Llama-8B | 0.20 | 0.20 | Fireworks/Together (~4.5×) |
| cheap | **local (your GPU)** | 0.00 | 0.00 | $0/token, pay hardware |

**Model inputs (measured, not assumed):** easy prompts → cheap handles 100%; ~**17% of hard
prompts escalate** (from `RESULTS_MODELS_HARD.md`). **Assumption:** 500 input + 300 output
tokens/request (edit for your workload). Two confidence signals: `free` (logprobs/hedging) vs
`self_consistency` (re-samples the cheap model 2× — real overhead, so cheap cost ×3).

## Savings by scenario (per request, per 1M, per month @ 50k req/day)

**GPT-4o-mini → GPT-4o (16× price gap — the flagship case):**
| workload | confidence | saved | $/1M saved | $/mo @50k/day |
|---|---|---|---|---|
| mostly-easy 80/20 | free | **90.6%** | $3,850 | $5,776 |
| mostly-easy 80/20 | self-consistency | 78.6% | $3,340 | $5,011 |
| balanced 60/40 | free | 87.2% | $3,706 | $5,559 |
| balanced 60/40 | self-consistency | 75.2% | $3,196 | $4,794 |
| mostly-hard 30/70 | free | 82.1% | $3,489 | $5,233 |
| mostly-hard 30/70 | self-consistency | 70.1% | $2,979 | $4,468 |

**LOCAL ($0) → GPT-4o (on-prem cheap tier — the best case):**
| workload | saved | $/mo @50k/day |
|---|---|---|
| mostly-easy 80/20 | **96.6%** | $6,159 |
| balanced 60/40 | 93.2% | $5,941 |
| mostly-hard 30/70 | 88.1% | $5,616 |

Self-consistency is **free** on a local tier (tokens cost $0), so you get the accuracy of
re-sampling with none of the cost — this is why the local-first path is the strongest.

## ⚠️ The honest catch — where Frugal does NOT pay off

**Claude Haiku → Sonnet (only a 3× price gap) with self-consistency: savings go NEGATIVE
(−3% to −12%).** Why: self-consistency triples the cheap cost (3× Haiku ≈ Sonnet), so the probing
eats the entire margin. **Rule that falls out of the math:**

> Cascade + a re-sampling confidence signal only pays off when the cheap tier is **≥~10× cheaper**
> than frontier (GPT-4o-mini/4o, or local). On a small price gap (Haiku/Sonnet, ~3×), use a
> **near-free confidence signal (logprobs)** or a **local cheap tier**, or don't cascade at all.

Frugal should *tell* you this — `cost_model.scenario()` computes it; a config that can't save is a
config to flag, not ship. Llama-8B→70B (4.5×) is marginal: ~66–74% with free confidence, but only
~21–30% with self-consistency.

## On-prem break-even (buy a GPU node for the cheap tier vs paying GPT-4o-mini for it)

| node | amortized $/mo (36-mo life + power) | break-even |
|---|---|---|
| $8,600 (2×EPYC-class) | $299/mo | **~39,000 req/day** |
| $15,000 | $477/mo | ~62,000 req/day |

Above ~40k cheap-tier requests/day, owning the hardware beats renting the cheap tier — and then
self-consistency is free on top. (This is the REPOMIND / on-prem thesis, costed.)

## Corrections to earlier numbers (honesty)

- Earlier "**92.1% saved / $769 per 1M / $1,154/mo**" used the **mock demo price table** (frontier
  33× the cheap tier — bigger than reality). On **real** GPT-4o-mini→4o prices the honest figure is
  **~75–91%** (mix- and confidence-dependent), **$3,000–3,850 saved per 1M requests**,
  **~$4,500–5,800/mo @50k/day**. The demo number was labelled "modelled" but was optimistic; these
  real-price figures supersede it.
- The blanket "**cut ~80%**" is only true for **large price gaps** (mini/4o, or local). It is
  **false** for small gaps (Haiku/Sonnet) once you pay for a real confidence signal — see above.

## Bottom line

- **Biggest, safest win:** a **local/on-prem cheap tier** (Ollama/vLLM on your GPU) → **~88–97%
  savings**, and the confidence check is free. Frugal's local-first routing is the point.
- **Cloud-only** (mini→4o): **~75–91%** — still large.
- **Don't** cascade with self-consistency across a small price gap — it can cost you money. Frugal
  makes this checkable instead of hiding it.
