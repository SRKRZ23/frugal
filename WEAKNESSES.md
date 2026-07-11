# Frugal — honest weakness analysis

Infra earns trust by naming its own limits. Here's where Frugal is weak today, what
we've already hardened, and what's still open. (Skeptics: this is the doc to read.)

> Our own pressure / property / concurrency tests have found & fixed **7 real bugs** this cycle:
> budget thread-safety, budget hidden by `max_history`, an O(n²) metering regression, a cascade
> crash on a hostile confidence function, a gateway crash on malformed bodies, a cache crash on lone
> Unicode surrogates, and a **broken FastAPI HTTP layer** (every request 422'd — annotation
> stringification). The deep, fuzz, and FastAPI-concurrency suites now pass clean.

## Already found & fixed (via `benchmarks/stress_test.py` + `stress_deep.py`)
| Weakness | Status |
|---|---|
| Budget cap **not thread-safe** — 50 threads blew a $0.01 cap to $19.6 | **FIXED** — locked ledger; overshoot now bounded to ≤1 in-flight call/thread (test: `test_meter_thread_safe_ledger`) |
| **Unbounded memory** — `Meter.calls` grew forever (leak for long-running gateways) | **FIXED** — `max_history` ring buffer; totals stay exact via aggregates (test: `test_max_history_bounds_memory_but_keeps_totals`) |
| Guard **ReDoS** risk on pathological input | **VERIFIED SAFE** — worst 0.039s on 500KB adversarial strings |
| Router crash on garbage input | **VERIFIED** — 3000 fuzzed prompts, 0 crashes |
| Cache/mock crash on lone Unicode **surrogates** | **FIXED** — `encode(..., "surrogatepass")` (found by `test_fuzz.py`) |
| **FastAPI gateway 422'd every request** (annotation stringification) | **FIXED** — dropped `from __future__ import annotations`; verified with a real `TestClient` concurrency suite |

## Open weaknesses (stated plainly)
1. **Benchmark scope is still modest.** *Improved:* `bench_broad.py` adds a **judge PANEL**
   (multiple models vote) over a **categorized** set (coding/reasoning/factual/extraction/…).
   Measured: 3B↔7B saturates at 100% retention (small gap) — the informative <100% (83%) needs
   3B↔14B, which RAM-thrashes on our 15 GB CPU node. Still **LLM-judged, not human** — human eval
   remains the gold standard we haven't done. Everything is one command; re-run on your models.
2. **The confidence signal costs extra.** `self_consistency` re-samples 2×. *Closed:*
   `make_logprob_confidence` uses the model's own token log-probs — **no extra call (free)** — so
   routing saves the most; `make_verifier_confidence` is a 1-call middle option; `ResponseCache`
   removes repeats entirely. Use logprob confidence on any provider that returns log-probs.
3. **Budget overshoot.** The default meter is post-hoc (bounded overshoot under concurrency).
   *Improved:* `Meter.reserve()` / `can_afford()` give a pre-flight, **zero-overshoot** hard cap —
   refuse the call before spending. (Needs a token estimate up front.)
4. **The eval asserts are heuristics**, not ground truth — cheap CI gates, documented as such.
   The LLM-judge upgrade helps but inherits the judge model's biases.
5. **No real-world adoption yet.** It's new; no production users, no external contributors. The
   "would devs adopt it" signal so far is a persona-swarm simulation (optimistic by construction).
6. **Live bake-off vs a proxy — done (local).** `benchmarks/compare_litellm_live.py` ran on the
   cluster: same models/prompts, proxy (all→strong) vs Frugal (routed). Frugal made **6/12** strong
   calls instead of 12 → **−53.9% modelled cost, −32.5% latency**. Honest caveats: the baseline is a
   proxy pass-through (the `litellm` package wouldn't finish installing on the CPU-starved node —
   the mechanism is identical), and a **cloud-key run** (real $ vs OpenAI/Anthropic) still needs
   keys you provide.
7. **The guard is a first-line heuristic**, not a security product. Regex PII/injection detection
   catches the obvious, misses the clever. Don't rely on it as your only control.
8. **Solo maintainer.** Longevity is the #1 concern real devs raise — addressed by a public roadmap
   + responsive support, not yet by a community.

## What this means
Frugal's *engineering* is solid and stress-tested; its *evidence* is early and its *community* is
zero. The honest pitch is "a well-built, stress-tested cost/routing/eval layer with reproducible
(if small) benchmarks — verify it yourself in 10 seconds" — not "the definitive proven solution."
Overclaiming would fail exactly the scrutiny the skeptics apply.
