"""Scenario: routing + caching stacked on a repetitive workload.

Value proven: routing makes each call cheaper; the cache removes repeat calls
entirely ($0). Together they cut far more than either alone. Offline.

    python examples/scenarios/scenario_cache_savings.py
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from frugal import Meter, MockProvider, ResponseCache, cascade

prov = MockProvider()
# a realistic support/agent workload: lots of repeated & near-repeated questions
prompts = (["what are your hours?", "how do i reset my password?", "what is your refund policy?"] * 300
           + ["Analyze and prove the optimal retry design step by step"] * 30)

no_cache = Meter()
with_cache, cache = Meter(), ResponseCache(normalize=True)
for p in prompts:
    cascade(p, prov, no_cache)
    cascade(p, prov, with_cache, cache=cache)

saved = 1 - with_cache.total_cost / no_cache.total_cost
print(f"requests            : {len(prompts)}")
print(f"routing only        : ${no_cache.total_cost:.6f}")
print(f"routing + cache     : ${with_cache.total_cost:.6f}")
print(f"cache hit-rate      : {cache.hit_rate*100:.0f}%")
print(f"extra saved by cache: {saved*100:.1f}%  (on top of routing)")
