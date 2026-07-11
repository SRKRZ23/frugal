from frugal import Meter, MockProvider
from frugal.meter import BudgetExceeded


def test_meter_records_cost_and_tokens():
    meter = Meter()
    provider = MockProvider()
    with meter.track("frugal-mock-mid") as call:
        call.set(provider.complete("hello world", model="frugal-mock-mid"))
    assert len(meter.calls) == 1
    c = meter.calls[0]
    assert c.input_tokens > 0 and c.output_tokens > 0
    assert c.cost_usd > 0
    assert meter.total_cost == c.cost_usd


def test_meter_summary_breaks_down_by_model():
    meter = Meter()
    provider = MockProvider()
    for model in ("frugal-mock-cheap", "frugal-mock-frontier"):
        with meter.track(model) as call:
            call.set(provider.complete("hi", model=model))
    s = meter.summary()
    assert s["calls"] == 2
    assert set(s["by_model"]) == {"frugal-mock-cheap", "frugal-mock-frontier"}
    # frontier must cost more than cheap for identical work
    assert s["by_model"]["frugal-mock-frontier"]["cost_usd"] > s["by_model"]["frugal-mock-cheap"]["cost_usd"]


def test_meter_thread_safe_ledger():
    """Concurrent tracking must not corrupt the ledger and must bound overspend
    (regression for the stress-test finding: unlocked meter blew the cap ~2000x)."""
    import threading

    meter = Meter(budget_usd=0.01)
    prov = MockProvider()

    def worker():
        for _ in range(200):
            try:
                with meter.track("frugal-mock-frontier") as c:
                    c.set(prov.complete("x " * 5, model="frugal-mock-frontier"))
            except BudgetExceeded:
                return

    ts = [threading.Thread(target=worker) for _ in range(20)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    per_call = max(c.cost_usd for c in meter.calls)
    # ledger integrity: total_cost equals the sum of recorded calls (no lost/torn writes)
    assert abs(meter.total_cost - sum(c.cost_usd for c in meter.calls)) < 1e-12
    # bounded overshoot: at most one in-flight call per thread beyond budget
    assert meter.total_cost <= meter.budget_usd + 20 * per_call


def test_budget_enforced_with_max_history():
    """Regression: with a ring buffer, the budget must still fire on the TRUE total
    (a batch scenario once spent 18x the cap because the check saw only the window)."""
    prov = MockProvider()
    meter = Meter(budget_usd=0.01, max_history=50)
    hit = False
    for _ in range(100_000):
        try:
            with meter.track("frugal-mock-frontier") as c:
                c.set(prov.complete("pay " * 5, model="frugal-mock-frontier"))
        except BudgetExceeded:
            hit = True
            break
    assert hit, "budget never fired under max_history"
    assert meter.total_cost <= meter.budget_usd * 1.05  # stopped right at the cap


def test_max_history_bounds_memory_but_keeps_totals():
    """Ring buffer caps stored Call objects (no unbounded memory on long runs)
    while total cost/tokens/summary stay exact via aggregates."""
    prov = MockProvider()
    meter = Meter(max_history=10)
    exact = Meter()  # unbounded reference
    for _ in range(1000):
        for m in (meter, exact):
            with m.track("frugal-mock-cheap") as c:
                c.set(prov.complete("x", model="frugal-mock-cheap"))
    assert len(meter.calls) == 10                      # memory bounded
    assert meter.summary()["calls"] == 1000            # count still exact
    assert abs(meter.total_cost - exact.total_cost) < 1e-9   # totals still exact
    assert meter.total_input_tokens == exact.total_input_tokens


def test_metering_is_O1_not_quadratic():
    """Regression: metering must be O(1) per call, not O(n) (once it summed every
    prior call on each track() -> O(n^2)). 40k calls on one meter must be quick and exact."""
    from time import perf_counter
    prov, meter = MockProvider(), Meter()
    n = 40_000
    t0 = perf_counter()
    for _ in range(n):
        with meter.track("frugal-mock-cheap") as c:
            c.set(prov.complete("x", model="frugal-mock-cheap"))
    dt = perf_counter() - t0
    assert len(meter.calls) == n
    assert dt < 3.0, f"metering too slow ({dt:.1f}s for {n}) — O(n^2) regression?"
    # exactness preserved by the running aggregate
    assert abs(meter.total_cost - sum(c.cost_usd for c in meter.calls)) < 1e-9


def test_budget_enforced():
    meter = Meter(budget_usd=1e-9)  # basically zero
    provider = MockProvider()
    try:
        with meter.track("frugal-mock-frontier") as call:
            call.set(provider.complete("expensive prompt " * 50, model="frugal-mock-frontier"))
    except BudgetExceeded:
        return
    assert False, "expected BudgetExceeded"
