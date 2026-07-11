"""Frugal vs LiteLLM / gateways — honest comparison.

Two parts:
  1) MEASURED: the overhead Frugal's routing + metering adds per call (offline, real).
  2) FEATURE MATRIX: what Frugal does that a provider proxy doesn't.

Honest scope: a live latency/cost bake-off against LiteLLM needs LiteLLM installed and
real API keys — that's a roadmap item. This measures Frugal's own overhead (which is what
you'd add on top of any client) and states the feature differences plainly.

    python benchmarks/compare_litellm.py
"""
from __future__ import annotations

import os
import sys
from time import perf_counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from frugal import Meter, MockProvider, ResponseCache, cascade  # noqa: E402
from frugal.route import make_logprob_confidence  # noqa: E402


def overhead():
    prov = MockProvider()
    N = 20_000
    # baseline: raw provider call, no Frugal
    t0 = perf_counter()
    for _ in range(N):
        prov.complete("hi", model="frugal-mock-cheap")
    raw = perf_counter() - t0
    # with Frugal: meter + cascade + logprob confidence (free signal)
    conf = make_logprob_confidence()
    meter = Meter()
    t1 = perf_counter()
    for _ in range(N):
        cascade("hi", prov, meter, confidence_fn=conf, ladder=["frugal-mock-cheap"])
    frug = perf_counter() - t1
    add = (frug - raw) / N * 1e6  # microseconds/call added
    return {"calls": N, "raw_s": round(raw, 3), "frugal_s": round(frug, 3),
            "overhead_us_per_call": round(add, 2)}


FEATURES = [
    ("Multi-provider proxy",                 "LiteLLM/Portkey/Helicone", "Frugal (gateway)"),
    ("Cost-aware cascade (cheap→escalate)",  "manual / plugin",          "built-in, measured"),
    ("Confidence signal (logprob/verifier)", "no",                       "yes (logprob = free)"),
    ("Response cache ($0 on repeat)",        "some (exact)",             "yes (exact/normalized)"),
    ("Offline eval asserts + RAG for CI",    "no",                       "yes"),
    ("MCP server (agent reads own spend)",   "no",                       "yes"),
    ("Local-first privacy routing (tested)", "partial",                  "yes (0 leaks)"),
    ("Economics guard (won't-save warning)", "no",                       "yes"),
    ("Reproducible model-vs-model bench",    "no",                       "yes"),
    ("Zero runtime deps / offline demo",     "no",                       "yes"),
    ("Streaming gateway",                    "yes",                      "yes"),
]


def main():
    o = overhead()
    print("== MEASURED overhead (what Frugal adds on top of any client) ==")
    for k, v in o.items():
        print(f"  {k}: {v}")
    print(f"\n  → Frugal adds ~{o['overhead_us_per_call']} µs/call for routing + metering + a "
          f"free confidence signal. Negligible next to any network call.\n")

    print("== FEATURE COMPARISON (honest; not a live LiteLLM bake-off) ==")
    w = max(len(f[0]) for f in FEATURES)
    print(f"  {'capability'.ljust(w)}   proxy            frugal")
    for name, proxy, frug in FEATURES:
        print(f"  {name.ljust(w)}   {proxy:<15}  {frug}")
    print("\n  If you only need a provider proxy, use LiteLLM. Frugal is the decide-and-verify "
          "layer on top: it chooses what to run and proves it was good enough.")
    print("  Roadmap: a live latency/cost bake-off vs LiteLLM with real keys.")


if __name__ == "__main__":
    main()
