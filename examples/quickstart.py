"""Frugal in 20 lines — runs offline, no API keys.

    python examples/quickstart.py
"""
from frugal import Meter, MockProvider, cascade
from frugal.eval import assert_semantic
from frugal.mcp import FrugalMCP

provider = MockProvider()
meter = Meter(budget_usd=0.50)

# 1. cost-aware routing: cheap prompt stays cheap, hard prompt escalates
for prompt in ["say hi", "analyze the trade-offs and prove the design, step by step"]:
    r = cascade(prompt, provider, meter)
    print(f"{prompt[:35]:35s} -> {r.model_used:22s} escalated={r.escalated}")

# 2. verify an answer offline
assert_semantic("Paris is the capital of France", "The capital of France is Paris", threshold=0.4)
print("semantic assert: OK")

# 3. what did it cost? (also exposed to agents via MCP)
print("cost summary:", FrugalMCP(meter).call("get_cost_summary"))
print(f"total: ${meter.total_cost:.6f}")
