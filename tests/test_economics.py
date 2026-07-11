import warnings

import pytest

from frugal import Meter, MockProvider, cascade
from frugal.economics import routing_savings
from frugal.route import make_self_consistency


def test_big_gap_pays_off():
    r = routing_savings("gpt-4o-mini", "gpt-4o", confidence="self_consistency")
    assert r["will_save"] is True
    assert r["price_ratio"] >= 10


def test_small_gap_loses_with_self_consistency():
    r = routing_savings("claude-haiku", "claude-sonnet", confidence="self_consistency")
    assert r["will_save"] is False          # 3x gap can't cover 3x probing
    assert r["saved_pct"] <= 5


def test_small_gap_ok_with_free_confidence():
    r = routing_savings("claude-haiku", "claude-sonnet", confidence="free")
    assert r["will_save"] is True           # no probing overhead -> still saves


def test_cascade_warns_on_uneconomical_selfconsistency():
    """Using self-consistency across a small price gap must emit a warning."""
    meter = Meter()
    conf = make_self_consistency(n=2)
    with pytest.warns(UserWarning, match="economics"):
        cascade("hi", MockProvider(), meter,
                ladder=["claude-haiku", "claude-sonnet"], confidence_fn=conf)


def test_cascade_silent_when_economical():
    meter = Meter()
    conf = make_self_consistency(n=2)
    with warnings.catch_warnings():
        warnings.simplefilter("error")      # any warning would fail the test
        cascade("hi", MockProvider(), meter,
                ladder=["gpt-4o-mini", "gpt-4o"], confidence_fn=conf)
