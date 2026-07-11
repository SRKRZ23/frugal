"""Scenario: a drop-in gateway that enforces a hard spend cap.

Value proven: point any OpenAI client at frugal.gateway and spend is metered +
routed automatically; when the budget is hit you get an HTTP 402, not a surprise
invoice. Runs offline (no keys).

    python examples/scenarios/scenario_gateway_budget.py
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from frugal import Meter, MockProvider
from frugal.gateway import handle_chat

provider = MockProvider()
meter = Meter(budget_usd=0.00005)   # a tiny cap so we hit it quickly

def call(text):
    body = {"messages": [{"role": "user", "content": text}]}
    resp, status = handle_chat(body, provider, meter)
    if status == 200:
        print(f"200  spent=${resp['frugal']['spent_usd']:.6f}  :: {text[:40]}")
    else:
        print(f"{status}  {resp['error']['type']}  :: {text[:40]}")
    return status

prompts = ["say hi", "what is 2+2", "list three fruits",
           "Analyze and prove the optimal design step by step", "another request", "and another"]
for p in prompts:
    if call(p) == 402:
        print("→ budget hit; gateway stops the spend (no surprise bill).")
        break
