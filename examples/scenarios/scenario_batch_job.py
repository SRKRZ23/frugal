"""Scenario: a large batch job that must stay under budget AND under memory.

Value proven: process thousands of items with cost-routing, a hard budget cap, and
`max_history` so a long-running job never leaks memory — totals stay exact. Offline.

    python examples/scenarios/scenario_batch_job.py
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from frugal import Meter, MockProvider, cascade
from frugal.meter import BudgetExceeded

prov = MockProvider()
meter = Meter(budget_usd=0.05, max_history=500)   # bounded memory + hard cap

processed = 0
try:
    for i in range(100_000):
        prompt = "summarise item %d" % i if i % 5 else "Analyze and prove item %d in depth" % i
        cascade(prompt, prov, meter)
        processed += 1
except BudgetExceeded as e:
    print("budget hit — job paused cleanly:", e)

s = meter.summary()
print(f"processed {processed} items")
print(f"spent ${s['total_cost_usd']} of ${meter.budget_usd} cap")
print(f"calls tracked (exact): {s['calls']}  |  Call objects in memory (bounded): {len(meter.calls)}")
print("→ ran a huge batch with exact accounting and bounded memory.")
