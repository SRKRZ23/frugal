# Benchmark methodology — what Frugal's numbers mean, and what they don't

The point of this document is to make the headline savings number **impossible to
misread**. A savings percentage is meaningless without naming the baseline, so we name it.

## The two baselines (we measure against both)

Frugal's routing is compared against two honest baselines, not a single strawman. The same
response cache is applied to all three, so caching is never counted as Frugal's private win.

| Baseline | What it is | Result (real 2026 prices, `benchmarks/cost_model.py`) |
|---|---|---|
| **frontier-default** | you send *every* request to the frontier model for quality | **~70–79%** cheaper (gpt-4o-mini→gpt-4o), up to **~97%** with a local $0 tier, and **negative (−3 to −12%)** on a small price gap (Haiku→Sonnet) |
| **static-cheap** | you send *every* request to the cheap model, no escalation | Frugal costs **MORE** (roughly +200–400%). Against this baseline Frugal's value is **not** a lower bill — it is recovering frontier-level quality on the ~17% of hard prompts it escalates, plus governance and a measured $/token |

**Honest reading:** the big percentage is real *only* if your alternative was defaulting to a
frontier model (many quality-conscious teams do). If your alternative was defaulting to a cheap
model, Frugal costs more and sells *quality recovery + control*, not raw savings. Both are true;
we quote the baseline every time.

## Where the 17% escalation rate comes from

The routing/escalation behaviour used in the cost model is Frugal's **measured** ~17% hard-prompt
escalation rate from `benchmarks/RESULTS_MODELS_HARD.md`. Honest caveats on that measurement:

- It is **LLM-judged** (an LLM grading the answers), not human-graded.
- It is **small-N** and on a **self-selected** prompt set.
- It was run on a **rented CPU node**, single-run, nondeterministic model sampling.

So it is a **signal, not proof**. It is enough to model cost arithmetic honestly; it is **not**
enough to claim a quality guarantee on someone else's workload.

## Measured: real cross-model run (not mock, not borrowed)

To stop leaning on a mock provider, we ran the cheap→frontier pair on **real Ollama models**
and had an LLM judge grade the answers. This is the actual `benchmarks/RESULTS_MODELS.md`
output, not a hand-typed number.

_Measured 2026-07-13 on **carlito4**, CPU inference. Judge: qwen2.5:7b. Reference: phi4:14b. N=6 prompts._

| model | p50 s | p95 s | tok/s | judge quality 0–1 | agreement with reference |
|---|---|---|---|---|---|
| **qwen2.5:7b** (cheap tier) | **62.3** | 76.6 | 3.1 | 0.750 | **5/6 (83%)** |
| phi4:14b (frontier ref) | 122.8 | 162.3 | 1.6 | 0.767 | ref |

**Reading:** the cheap 7B tier ran **2.0× faster** (p50) at **~98% of the frontier's judged
quality** (0.750 vs 0.767) and agreed with the reference on **5 of 6** prompts. That is the
empirical basis for "route to the cheap tier first, escalate the ~1-in-6 it gets wrong."

Honest caveats, same as below: **LLM-judged** (not human), **N=6** (tiny), **CPU / single-run /
nondeterministic sampling**, and **English** prompts — not the tuned-vLLM, human-graded, Korean
workload that would make it proof. It is a real measurement replacing a mock, not a guarantee.

## What is NOT proven here (and what would prove it)

The following do **not** exist yet, and we do not pretend they do:

- A **human-graded**, held-out, multi-workload quality benchmark.
- A comparison against a **properly-tuned SOTA serving stack** (vLLM continuous batching +
  prefix/KV caching + speculative decoding + an existing router such as RouteLLM), rather than a
  naive always-frontier call. Under that tougher comparison on a real (e.g. Korean-language,
  regulated) workload the cheap-tier quality-match could compress meaningfully.
- Any **real customer traffic** measurement.

**The plan to earn those numbers:** run one design-partner pilot, measure on *their* traffic vs a
tuned baseline, publish both the cost delta and the human-graded quality delta — including the
cases where routing loses money. That requires compute and a signed design partner; it is the
roadmap item, not a shipped claim.

## The one number we refuse to hide

On a price gap below ~10×, cascade + a re-sampling confidence signal can **lose money** (e.g.
Haiku→Sonnet: −3% to −12%). Frugal's `economics` module computes this and warns you. We publish
it because a tool you can only trust when it wins is a tool you cannot trust.

See also [WEAKNESSES.md](WEAKNESSES.md) for the full self-audit.
