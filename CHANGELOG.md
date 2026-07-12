# Changelog

## Unreleased
- `diagnose` — read-only savings **projection** on a customer's own prompt log (offline, no model
  called, nothing leaves the box). Clearly labelled a projection; complexity heuristic broadened
  (reasoning/code signals + code-fence bump) so hard prompts are no longer under-flagged.
- `diagnose --live` / `diagnose.diagnose_live()` — the **measured** counterpart: actually routes
  every prompt through the real cascade (Ollama/OpenAI-compatible) and observes cost, latency, and
  the escalation decision. Point `--host` at a local/on-prem server to keep data in-house.
- `METHODOLOGY.md` — added the real 2026-07-13 cross-model run (`benchmarks/RESULTS_MODELS.md`):
  qwen2.5:7b vs phi4:14b on CPU, LLM-judged, N=6 — cheap tier 2.0× faster p50 at ~98% judged
  quality, 5/6 agreement. Replaces the mock stand-in; caveats retained.

## 0.1.0 — first public release
First open-source release of Frugal — a drop-in cost/routing/eval layer for LLM apps.

**Core**
- `meter` — per-call cost/token/latency accounting, thread-safe budget cap, bounded memory (`max_history`).
- `route` — cost-aware cascade (cheap → escalate), pluggable confidence (`hedging`, `self_consistency`).
- `local` — local↔cloud routing by cost/privacy/complexity; AMD ROCm quickstart.
- `eval` — offline semantic asserts, drift monitor, tracing, and an LLM judge.
- `rag` — retrieval hit-rate / faithfulness / citation-coverage checks.
- `mcp` — MCP server exposing an agent's own $/token spend + PII/injection guard.
- `gateway` — OpenAI-compatible budget-enforcing proxy.
- `economics` — warns when a cheap/frontier pair can't cover the routing overhead.
- `cache` — `ResponseCache` (the second cost lever): a hit costs $0; exact or normalized keys, LRU-bounded.
- `route.make_verifier_confidence` — cheaper confidence (one self-check call vs two re-samples).
- `meter.reserve()` / `can_afford()` — pre-flight, zero-overshoot budget enforcement.
- `route.make_logprob_confidence` — the near-free confidence signal (uses the model's own mean
  token log-prob, no extra call); `LLMResponse.avg_logprob` + OpenAI logprob capture.
- `gateway.stream_chat` — OpenAI-compatible SSE streaming (routes + meters, then streams the answer).
- `benchmarks/compare_litellm.py` — measured Frugal overhead + honest feature comparison vs proxies.
- `eval.JudgePanel` + `benchmarks/bench_broad.py` — multi-judge panel over a categorized prompt set.
- `benchmarks/compare_litellm_live.py` — live routing-vs-proxy bake-off (Frugal cut strong-model
  calls 12→6 on the cluster: −53.9% modelled cost, −32.5% latency).

**Evidence**
- 56 tests; 8-dimension stress suite (throughput, thread-safety, ReDoS, fuzz, memory).
- Reproducible model-vs-model benchmarks (real cluster): 3B matched 14B on 83% of hard tasks
  (100% of easy) at ~4.7×/~11× speed.
- Real-price business case (now on the live site's Savings + Enterprise sections), honest weakness audit (`WEAKNESSES.md`).

**Honesty**
- **Seven** bugs found and fixed by our own pressure / property / concurrency tests: budget
  thread-safety, budget under `max_history`, an O(n²) metering regression, cascade crash on a
  hostile confidence fn, gateway crash on malformed bodies, cache crash on Unicode surrogates, and a
  broken FastAPI layer (every request 422'd). Suites: `stress_test`, `stress_deep`, `test_fuzz`,
  `test_gateway_fastapi`. 56 tests.
- Published where Frugal does *not* save money (small price gap + self-consistency).
