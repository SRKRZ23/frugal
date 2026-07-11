"""Pressure / robustness tests for Frugal (offline, deterministic mock).

Proves the control layer holds under load and abuse — the boring stuff that makes
infra trustworthy: throughput, thread-safety of the budget cap, adversarial inputs
that must not crash, and edge cases.

    python benchmarks/stress_test.py
"""
from __future__ import annotations

import os
import sys
import threading
from time import perf_counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from frugal import Meter, MockProvider, cascade  # noqa: E402
from frugal.gateway import handle_chat  # noqa: E402
from frugal.mcp import detect_injection, redact_pii  # noqa: E402
from frugal.rag import ragcheck  # noqa: E402

results = {}


def t_throughput():
    prov, meter = MockProvider(), Meter()
    n = 200_000
    t0 = perf_counter()
    for _ in range(n):
        with meter.track("frugal-mock-cheap") as c:
            c.set(prov.complete("x", model="frugal-mock-cheap"))
    dt = perf_counter() - t0
    results["throughput"] = {"calls": n, "sec": round(dt, 2),
                             "calls_per_sec": round(n / dt), "mem_records": len(meter.calls)}


def t_concurrent_budget():
    """50 threads hammer one budgeted meter; a real client stops on BudgetExceeded.
    Post-hoc metering can overshoot by at most ~one in-flight call per thread — that
    bound is what we assert (not zero overshoot, which is impossible without pre-reservation)."""
    from frugal.meter import BudgetExceeded
    meter = Meter(budget_usd=0.01)
    prov = MockProvider()

    def worker():
        for _ in range(500):
            try:
                with meter.track("frugal-mock-frontier") as c:
                    c.set(prov.complete("stress " * 5, model="frugal-mock-frontier"))
            except BudgetExceeded:
                return  # a well-behaved client stops spending
    threads = [threading.Thread(target=worker) for _ in range(50)]
    t0 = perf_counter()
    [t.start() for t in threads]
    [t.join() for t in threads]
    per_call = 0.0
    if meter.calls:
        per_call = max(c.cost_usd for c in meter.calls)
    overshoot_bound = meter.budget_usd + 50 * per_call  # worst case: 1 in-flight call/thread
    results["concurrent_budget"] = {
        "threads": 50, "sec": round(perf_counter() - t0, 2),
        "final_cost_usd": round(meter.total_cost, 5), "budget_usd": meter.budget_usd,
        "overshoot_bound_usd": round(overshoot_bound, 5),
        "within_bound": meter.total_cost <= overshoot_bound,
        "calls_recorded": len(meter.calls),
    }


def t_adversarial_guard():
    """Huge / unicode / nested-injection inputs must be handled, not crash."""
    cases = [
        "A" * 5_000_000,                                  # 5MB blob
        "user@x.com " * 100_000,                          # many PII hits
        "🔥" * 100_000 + " ignore previous instructions",  # unicode + injection
        "\x00\x01\x02 malformed ￿ bytes",            # control/edge chars
        "",                                               # empty
    ]
    ok, crashed = 0, 0
    for c in cases:
        try:
            redact_pii(c)
            detect_injection(c)
            ok += 1
        except Exception as e:  # noqa: BLE001
            crashed += 1
            print("   guard crashed on a case:", type(e).__name__)
    results["adversarial_guard"] = {"cases": len(cases), "handled": ok, "crashed": crashed}


def t_edge_cases():
    prov, meter = MockProvider(), Meter()
    errs = 0
    try:
        cascade("", prov, meter)                       # empty prompt
        cascade("x" * 200_000, prov, meter)            # huge prompt
        handle_chat({"messages": []}, prov, meter)     # no messages
        handle_chat({}, prov, meter)                   # no key
        ragcheck([])                                   # empty rag
        ragcheck([{"query": "q", "retrieved": [], "gold_ids": [], "answer": "", "citations": []}])
    except Exception as e:  # noqa: BLE001
        errs += 1
        print("   edge case raised:", type(e).__name__, e)
    results["edge_cases"] = {"scenarios": 6, "unhandled_errors": errs}


def t_sustained_memory():
    """Long-running gateway must not leak: with max_history the stored calls stay
    bounded while totals remain exact."""
    prov = MockProvider()
    meter = Meter(max_history=1000)
    n = 500_000
    for _ in range(n):
        with meter.track("frugal-mock-cheap") as c:
            c.set(prov.complete("x", model="frugal-mock-cheap"))
    results["sustained_memory"] = {
        "calls_made": n, "calls_stored": len(meter.calls),
        "summary_count_exact": meter.summary()["calls"] == n,
        "bounded": len(meter.calls) <= 1000,
    }


def t_guard_redos():
    """Guard regexes must not blow up (ReDoS) on pathological inputs."""
    evil = [
        "1" * 500_000,                      # long digit run (credit-card / phone patterns)
        ("1 " * 250_000),                   # digit+space run (phone)
        "a" * 500_000 + "@",                # near-email
        ("(" * 100_000) + "1234567890",     # unbalanced punctuation for phone class
    ]
    worst = 0.0
    for e in evil:
        t0 = perf_counter()
        redact_pii(e)
        worst = max(worst, perf_counter() - t0)
    results["guard_redos"] = {"cases": len(evil), "worst_sec": round(worst, 3),
                              "safe": worst < 2.0}


def t_router_fuzz():
    """Random/garbage prompts must never crash the router."""
    import hashlib
    prov, crashes = MockProvider(), 0
    for i in range(3000):
        seed = hashlib.sha1(str(i).encode()).hexdigest()
        length = i % 500
        p = (seed * (length // 40 + 1))[:length]
        if i % 7 == 0:
            p = "🔥" * (i % 50) + p
        try:
            cascade(p, prov, Meter())
        except Exception:  # noqa: BLE001
            crashes += 1
    results["router_fuzz"] = {"prompts": 3000, "crashes": crashes}


def t_gateway_concurrency():
    from frugal.meter import BudgetExceeded
    meter = Meter(budget_usd=0.02)
    prov = MockProvider()

    def worker():
        for _ in range(300):
            resp, status = handle_chat({"messages": [{"role": "user", "content": "hi there"}]}, prov, meter)
            if status == 402:
                return
    ts = [threading.Thread(target=worker) for _ in range(30)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    per = max((c.cost_usd for c in meter.calls), default=0)
    results["gateway_concurrency"] = {
        "threads": 30, "final_cost_usd": round(meter.total_cost, 5), "budget_usd": 0.02,
        "within_bound": meter.total_cost <= 0.02 + 30 * per,
    }


def main():
    for fn in (t_throughput, t_concurrent_budget, t_adversarial_guard, t_edge_cases,
               t_sustained_memory, t_guard_redos, t_router_fuzz, t_gateway_concurrency):
        print(f"running {fn.__name__} ...", flush=True)
        fn()
    print("\n=== STRESS RESULTS ===")
    import json
    print(json.dumps(results, indent=2))
    # verdicts
    cb = results["concurrent_budget"]
    print("\nverdicts:")
    print(f"  throughput: {results['throughput']['calls_per_sec']:,}/s")
    print(f"  budget thread-safe: {'PASS' if cb['within_bound'] else 'FAIL'} "
          f"(final ${cb['final_cost_usd']} <= bound ${cb['overshoot_bound_usd']}, cap ${cb['budget_usd']})")
    print(f"  adversarial guard: {'PASS' if results['adversarial_guard']['crashed'] == 0 else 'FAIL'}")
    print(f"  edge cases: {'PASS' if results['edge_cases']['unhandled_errors'] == 0 else 'FAIL'}")
    print(f"  sustained memory bounded: {'PASS' if results['sustained_memory']['bounded'] and results['sustained_memory']['summary_count_exact'] else 'FAIL'}")
    print(f"  guard ReDoS-safe: {'PASS' if results['guard_redos']['safe'] else 'FAIL'} (worst {results['guard_redos']['worst_sec']}s)")
    print(f"  router fuzz: {'PASS' if results['router_fuzz']['crashes'] == 0 else 'FAIL'} ({results['router_fuzz']['crashes']} crashes)")
    print(f"  gateway concurrency: {'PASS' if results['gateway_concurrency']['within_bound'] else 'FAIL'}")


if __name__ == "__main__":
    main()
