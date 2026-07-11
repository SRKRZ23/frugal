"""Scenario: catch a silent quality regression in CI.

Value proven: frugal.eval turns 'the model quietly got worse' into a failing test.
A good answer passes the gate; a drifted/hallucinated one fails it — deterministically,
offline, no judge model needed. This is the file you'd wire into pytest.

    python examples/scenarios/scenario_ci_eval.py
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from frugal.eval import DriftMonitor, assert_no_hallucination, assert_semantic

CONTEXT = "The Eiffel Tower is a wrought-iron tower in Paris, France, 330 metres tall."

def check(answer):
    assert_semantic(answer, "The Eiffel Tower is in Paris and is 330 metres tall", threshold=0.3)
    assert_no_hallucination(answer, CONTEXT)

good = "The Eiffel Tower is in Paris, France and stands 330 metres tall."
bad = "The Eiffel Tower is in Berlin and is 1083 metres tall."   # wrong city + number

print("good answer:", end=" ")
try:
    check(good); print("PASS ✅")
except AssertionError as e:
    print("FAIL", e)

print("regressed answer:", end=" ")
try:
    check(bad); print("PASS (❌ should have failed!)")
except AssertionError as e:
    print(f"FAIL ✅ (caught) -> {e}")

# drift monitor over a rolling window of production outputs
dm = DriftMonitor().fit(["all systems normal", "ok", "looks correct", "fine"])
print("\ndrift on a normal output   :", dm.drift("all systems normal")["drift"])
print("drift on a garbage output  :", dm.drift("ERROR ERROR total meltdown everywhere xyzzy")["drift"])
