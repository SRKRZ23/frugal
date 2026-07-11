import pytest

from frugal.eval import (
    DriftMonitor,
    assert_no_hallucination,
    assert_semantic,
    assert_tone,
)


def test_semantic_pass_and_fail():
    assert assert_semantic("Paris is the capital of France",
                           "The capital of France is Paris", threshold=0.4) > 0.4
    with pytest.raises(AssertionError):
        assert_semantic("bananas are yellow", "quantum chromodynamics", threshold=0.5)


def test_no_hallucination_flags_unsupported_number():
    context = "The Eiffel Tower is in Paris."
    # supported
    assert_no_hallucination("The Eiffel Tower is in Paris", context)
    # unsupported number should raise
    with pytest.raises(AssertionError):
        assert_no_hallucination("The tower is 1083 metres tall in Berlin", context)


def test_tone_concise():
    assert_tone("Yes.", "concise")
    with pytest.raises(AssertionError):
        assert_tone("word " * 100, "concise")


def test_drift_detects_shift():
    dm = DriftMonitor().fit(["all good", "looks correct", "fine", "ok"])
    low = dm.drift("all good")["drift"]
    high = dm.drift("catastrophic total meltdown across every subsystem imaginable")["drift"]
    assert high > low
