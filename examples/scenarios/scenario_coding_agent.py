"""Scenario: a coding agent under a hard budget.

Value proven: cost-aware routing keeps a multi-step agent cheap — trivial steps
run on the cheap tier, only genuinely hard steps escalate — and the budget is a
hard stop, not a suggestion. Runs offline.

    python examples/scenarios/scenario_coding_agent.py
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from frugal import Meter, MockProvider, cascade
from frugal.mcp import FrugalMCP

steps = [
    "list the files in this module",              # trivial
    "rename the variable `x` to `count`",         # trivial
    "Analyze the race condition and prove the fix step by step.",  # hard -> escalates
    "add a docstring to this function",           # trivial
    "Design a retry policy and justify the trade-offs.",           # hard -> escalates
]

provider = MockProvider()
meter = Meter(budget_usd=1.00)

for s in steps:
    r = cascade(s, provider, meter)
    print(f"[{'ESCALATED' if r.escalated else 'cheap    '}] {r.model_used:22s} :: {s[:48]}")

mcp = FrugalMCP(meter)
print("\nagent's own cost view (via MCP):", mcp.call("get_budget_status"))
print(f"total: ${meter.total_cost:.6f} across {len(meter.calls)} calls "
      f"(a frontier-only agent would call the expensive model {len(steps)} times)")
