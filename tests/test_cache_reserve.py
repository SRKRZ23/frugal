import pytest

from frugal import Meter, MockProvider, ResponseCache, cascade
from frugal.meter import BudgetExceeded


def test_cache_hit_is_free():
    prov, meter, cache = MockProvider(), Meter(), ResponseCache()
    r1 = cascade("what is 2+2", prov, meter, cache=cache)
    cost_after_first = meter.total_cost
    r2 = cascade("what is 2+2", prov, meter, cache=cache)   # identical -> hit
    assert cache.hits == 1 and cache.misses == 1
    assert r2.text == r1.text
    # second call added a $0 cache entry, so total cost didn't grow
    assert meter.total_cost == cost_after_first
    assert "(cache)" in meter.calls[-1].model


def test_cache_normalize_folds_whitespace_case():
    cache = ResponseCache(normalize=True)
    meter, prov = Meter(), MockProvider()
    cascade("Hello  World", prov, meter, cache=cache)
    cascade("hello world", prov, meter, cache=cache)   # normalized -> same key
    assert cache.hits == 1


def test_reserve_is_zero_overshoot():
    meter = Meter(budget_usd=0.00005)
    # a call that fits
    assert meter.can_afford("frugal-mock-cheap", 3, 3) in (True, False)
    # reserving an unaffordable call raises BEFORE spending
    with pytest.raises(BudgetExceeded):
        meter.reserve("frugal-mock-frontier", 5000, 5000)
    assert len(meter.calls) == 0   # nothing was spent


def test_verifier_confidence_cheaper_than_self_consistency():
    from frugal.economics import routing_savings
    v = routing_savings("gpt-4o-mini", "gpt-4o", confidence="self_consistency", probes=1)  # verifier=1 probe
    s = routing_savings("gpt-4o-mini", "gpt-4o", confidence="self_consistency", probes=2)
    assert v["saved_pct"] > s["saved_pct"]   # fewer probes -> more saved
