from frugal import Meter, MockProvider, cascade


def test_easy_prompt_stays_on_cheap_model():
    meter = Meter()
    r = cascade("say hi", MockProvider(), meter)
    assert r.model_used == "frugal-mock-cheap"
    assert r.escalated is False
    assert r.tiers_tried == ["frugal-mock-cheap"]


def test_hard_prompt_escalates():
    meter = Meter()
    hard = "Analyze the architecture trade-offs and prove why this refactor is optimal, step by step."
    r = cascade(hard, MockProvider(), meter)
    assert r.escalated is True
    assert len(r.tiers_tried) > 1
    # escalation means more than one metered call
    assert len(meter.calls) == len(r.tiers_tried)


def test_cascade_saves_money_vs_frontier_only():
    provider = MockProvider()
    easy = "say hi"
    # cascade
    m1 = Meter()
    cascade(easy, provider, m1)
    # frontier-only baseline
    m2 = Meter()
    with m2.track("frugal-mock-frontier") as call:
        call.set(provider.complete(easy, model="frugal-mock-frontier"))
    assert m1.total_cost < m2.total_cost
