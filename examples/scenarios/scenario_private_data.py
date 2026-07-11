"""Scenario: sensitive data must never leave the building.

Value proven: LocalRouter keeps every `private`-tagged prompt on the on-prem model
regardless of how hard it is, while still sending public/heavy work to the cluster
frontier. Zero private prompts leak to the cloud. Runs offline.

    python examples/scenarios/scenario_private_data.py
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from frugal import MockProvider
from frugal.local import LocalRouter

lr = LocalRouter(local=MockProvider(), cloud=MockProvider(),
                 local_model="on-prem-llama", cloud_model="cluster-frontier")

jobs = [
    ("summarise this patient record", {"private"}),
    ("Analyze our confidential churn data and derive root causes", {"private"}),
    ("what is the capital of France", set()),
    ("Design a distributed queue and justify the trade-offs", set()),
]

leaks = 0
for prompt, tags in jobs:
    where = lr.decide(prompt, tags)
    if "private" in tags and where != "local":
        leaks += 1
    print(f"{where.upper():6s}  ({'PRIVATE' if tags else 'public '})  {prompt[:46]}")

print(f"\nprivate prompts leaked to cloud: {leaks}  (must be 0)")
assert leaks == 0, "privacy violation!"
print("✅ privacy invariant holds")
