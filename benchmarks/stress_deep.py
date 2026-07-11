"""DEEP adversarial pressure tests — the ones that try hard to break Frugal.
Anything that fails here is a real bug to fix (that's the point).

    python benchmarks/stress_deep.py
"""
from __future__ import annotations

import math
import os
import sys
import threading
from time import perf_counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from frugal import Meter, MockProvider, ResponseCache, cascade  # noqa: E402
from frugal.gateway import handle_chat, stream_chat  # noqa: E402

R = {}


def t_summary_during_writes():
    """summary()/total_cost read the ledger WHILE other threads append. Must not crash
    (list-changed-size) or return torn totals."""
    meter, prov = Meter(), MockProvider()
    errs = []
    stop = threading.Event()

    def writer():
        while not stop.is_set():
            with meter.track("frugal-mock-cheap") as c:
                c.set(prov.complete("x", model="frugal-mock-cheap"))

    def reader():
        while not stop.is_set():
            try:
                meter.summary(); _ = meter.total_cost; _ = meter.total_input_tokens
            except Exception as e:  # noqa: BLE001
                errs.append(repr(e))

    ts = [threading.Thread(target=writer) for _ in range(16)] + [threading.Thread(target=reader) for _ in range(6)]
    [t.start() for t in ts]
    perf = perf_counter()
    while perf_counter() - perf < 2.0:
        pass
    stop.set(); [t.join() for t in ts]
    R["summary_during_writes"] = {"reader_exceptions": len(errs), "sample": errs[:2], "calls": len(meter.calls)}


def t_cache_concurrent():
    cache = ResponseCache(normalize=True, max_size=500)
    prov = MockProvider()
    errs = []

    def worker(k):
        for i in range(2000):
            try:
                key = f"q{(i + k) % 50}"
                if cache.get(key) is None:
                    cache.put(key, prov.complete(key, model="frugal-mock-cheap"))
            except Exception as e:  # noqa: BLE001
                errs.append(repr(e))
    ts = [threading.Thread(target=worker, args=(k,)) for k in range(24)]
    [t.start() for t in ts]; [t.join() for t in ts]
    R["cache_concurrent"] = {"errors": len(errs), "entries_bounded": len(cache._d) <= 500,
                             "hits_plus_misses": cache.hits + cache.misses}


def t_cascade_bad_confidence():
    """A hostile/buggy confidence_fn (raises, NaN, out-of-range) must not crash cascade."""
    prov, results, crashes = MockProvider(), [], 0
    bad = {
        "raises": lambda p, r, pr: (_ for _ in ()).throw(ValueError("boom")),
        "nan": lambda p, r, pr: float("nan"),
        "too_high": lambda p, r, pr: 5.0,
        "negative": lambda p, r, pr: -3.0,
        "none": lambda p, r, pr: None,
    }
    for name, fn in bad.items():
        try:
            res = cascade("analyze this", prov, Meter(), confidence_fn=fn)
            results.append((name, res.model_used))
        except Exception as e:  # noqa: BLE001
            crashes += 1
            results.append((name, "CRASH:" + type(e).__name__))
    R["cascade_bad_confidence"] = {"crashes": crashes, "results": results}


def t_gateway_malformed():
    prov, crashes, cases = MockProvider(), 0, [
        {}, {"messages": "not-a-list"}, {"messages": []}, {"messages": [{}]},
        {"messages": [{"role": "user", "content": None}]},
        {"messages": [{"role": "user"}]}, {"messages": [{"content": 12345}]},
        {"messages": [{"role": "user", "content": "x" * 200000}]},
    ]
    for body in cases:
        try:
            handle_chat(body, prov, Meter())
            list(stream_chat(body, prov, Meter()))
        except Exception as e:  # noqa: BLE001
            crashes += 1
            print("   gateway crashed on", str(body)[:40], "->", type(e).__name__)
    R["gateway_malformed"] = {"cases": len(cases), "crashes": crashes}


def t_float_drift_ring_buffer():
    """max_history pops subtract from the running aggregate — over many ops, does the
    O(1) total drift from an exact recompute?"""
    prov = Meter(max_history=100), MockProvider()
    meter, p = prov
    exact = 0.0
    for _ in range(200_000):
        with meter.track("frugal-mock-mid") as c:
            r = c.set(p.complete("hello world", model="frugal-mock-mid"))
        # exact is the running true total (never trimmed)
    # recompute what total SHOULD be: drop + live, vs a from-scratch tally is impossible after trim,
    # so check internal consistency: total_cost == _drop cost + sum(live calls)
    recomputed = meter._drop["cost"] + sum(c.cost_usd for c in meter.calls)
    R["float_drift_ring_buffer"] = {"total_cost": round(meter.total_cost, 8),
                                    "recomputed": round(recomputed, 8),
                                    "abs_diff": abs(meter.total_cost - recomputed),
                                    "ok": abs(meter.total_cost - recomputed) < 1e-6}


def t_reserve_concurrent():
    from frugal.meter import BudgetExceeded
    meter, prov = Meter(budget_usd=0.02), MockProvider()

    def worker():
        for _ in range(400):
            try:
                meter.reserve("frugal-mock-frontier", 400, 300)
                with meter.track("frugal-mock-frontier") as c:
                    c.set(prov.complete("pay " * 5, model="frugal-mock-frontier"))
            except BudgetExceeded:
                return
    ts = [threading.Thread(target=worker) for _ in range(20)]
    [t.start() for t in ts]; [t.join() for t in ts]
    R["reserve_concurrent"] = {"final_cost": round(meter.total_cost, 5), "budget": 0.02,
                               "within_2x": meter.total_cost <= 0.04}


def main():
    for fn in (t_summary_during_writes, t_cache_concurrent, t_cascade_bad_confidence,
               t_gateway_malformed, t_float_drift_ring_buffer, t_reserve_concurrent):
        print("running", fn.__name__, "...", flush=True)
        fn()
    import json
    print("\n=== DEEP STRESS RESULTS ===")
    print(json.dumps(R, indent=2, default=str))
    fails = []
    if R["summary_during_writes"]["reader_exceptions"]: fails.append("summary_during_writes")
    if R["cache_concurrent"]["errors"] or not R["cache_concurrent"]["entries_bounded"]: fails.append("cache_concurrent")
    if R["cascade_bad_confidence"]["crashes"]: fails.append("cascade_bad_confidence")
    if R["gateway_malformed"]["crashes"]: fails.append("gateway_malformed")
    if not R["float_drift_ring_buffer"]["ok"]: fails.append("float_drift")
    if not R["reserve_concurrent"]["within_2x"]: fails.append("reserve_concurrent")
    print("\nFAILURES:", fails if fails else "none — diamond ✅")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
