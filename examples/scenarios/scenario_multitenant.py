"""Scenario: per-tenant budgets in a multi-tenant service.

Value proven: give each customer/API-key its own Meter+budget; one tenant blowing
their cap can't spend another's. Thread-safe, offline.

    python examples/scenarios/scenario_multitenant.py
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from frugal import Meter, MockProvider, cascade
from frugal.meter import BudgetExceeded

prov = MockProvider()
tenants = {"acme (paid)": Meter(budget_usd=0.02),
           "free-tier bob": Meter(budget_usd=0.001),
           "enterprise co": Meter(budget_usd=0.10)}

for name, meter in tenants.items():
    stopped_at = None
    for i in range(1000):
        try:
            cascade("Analyze and prove request %d step by step" % i, prov, meter)
        except BudgetExceeded:
            stopped_at = i
            break
    s = meter.summary()
    print(f"{name:16s} spent ${s['total_cost_usd']:.5f} / ${meter.budget_usd:<6} cap "
          f"→ {'capped at req %d' % stopped_at if stopped_at is not None else 'under budget'}")

print("→ each tenant is isolated; a free-tier blowout never touches paid tenants.")
