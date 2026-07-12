"""Reproducible cost / savings model for Frugal — REAL provider prices, HONEST baselines.

The point of this file is to NOT lie with the headline number. We measure Frugal against TWO
baselines instead of a single strawman:

  1) frontier-default  — a team that sends every request to the frontier model for quality.
     This is the LOOSE bound and the biggest, most-quoted savings. It is honest ONLY if you
     say "vs a frontier-default baseline" (many quality-conscious teams really do this).
  2) static-cheap      — a team that sends every request to the cheap model (no escalation).
     This is the TOUGH bound. Frugal costs MORE than this, because it adds confidence probes
     and escalates ~17% of hard prompts to the frontier. Naming this baseline is the honest
     part: vs static-cheap, Frugal's value is not lower cost — it is recovering frontier-level
     QUALITY on the hard fraction, at a controlled, measured cost.

Both baselines AND Frugal get the SAME response cache (repeats are free for everyone), so the
comparison is fair — Frugal is not allowed to count caching as its own private win.

Numbers use real 2026 list prices (edit PRICES) and Frugal's MEASURED ~17% hard-prompt
escalation rate (benchmarks/RESULTS_MODELS_HARD.md — LLM-judged, small-N; see METHODOLOGY.md
for exactly what that does and does not prove). Real-model, human-graded numbers on a real
workload require compute + a design partner and are NOT produced by this file.

Run:  python benchmarks/cost_model.py
"""

# USD per 1M tokens (input, output). Approximate list prices, 2026-07 — verify before quoting.
PRICES = {
    "gpt-4o":        (2.50, 10.00),
    "gpt-4o-mini":   (0.15, 0.60),
    "claude-sonnet": (3.00, 15.00),
    "claude-haiku":  (1.00, 5.00),
    "llama-70b":     (0.90, 0.90),   # Fireworks/Together, flat-ish
    "llama-8b":      (0.20, 0.20),
    "local":         (0.00, 0.00),   # your own GPU: $0/token, pay hardware instead
}


def per_req(model, tin, tout):
    pin, pout = PRICES[model]
    return (tin / 1e6) * pin + (tout / 1e6) * pout


def costs(cheap, frontier, tin, tout, easy_frac, hard_escalate=0.17,
          confidence="self_consistency", cache_hit=0.0):
    """Per-request cost of Frugal vs TWO honest baselines, all sharing the same cache.

    easy_frac     : share of requests the cheap tier fully handles.
    hard_escalate : share of HARD requests that escalate to frontier (measured ~17%).
    confidence    : 'free' (logprob) or 'self_consistency' (k=2 extra cheap samples => 3x cheap).
    cache_hit     : fraction of requests served from cache at $0 (applied to ALL three equally).
    """
    c_cheap = per_req(cheap, tin, tout)
    c_frontier = per_req(frontier, tin, tout)
    escalate_frac = (1 - easy_frac) * hard_escalate            # fraction of ALL reqs hitting frontier
    probe_mult = 3 if confidence == "self_consistency" else 1  # 1 answer + 2 consistency samples
    live = 1.0 - cache_hit                                     # cache serves the rest at $0 for everyone

    frugal        = live * (probe_mult * c_cheap + escalate_frac * c_frontier)
    base_frontier = live * c_frontier                          # baseline #1: everything -> frontier
    base_cheap    = live * c_cheap                             # baseline #2: everything -> cheap (lower quality)

    vs_frontier = (1 - frugal / base_frontier) if base_frontier else 0.0
    vs_cheap    = (frugal / base_cheap - 1) if base_cheap else float("inf")  # + => Frugal costs MORE (buys quality)
    return {
        "cheap_$/req": round(c_cheap, 6), "frontier_$/req": round(c_frontier, 6),
        "escalate_%": round(100 * escalate_frac, 1), "confidence": confidence,
        "cache_hit_%": round(100 * cache_hit),
        "frugal_$/req": round(frugal, 6),
        "vs_frontier_default_saved_%": round(100 * vs_frontier, 1),
        "vs_static_cheap_costs_%": round(100 * vs_cheap, 1),   # honest: usually POSITIVE (Frugal costs more, buys quality)
        "$/1M_saved_vs_frontier": round((base_frontier - frugal) * 1e6),
    }


def monthly_vs_frontier(scn, reqs_per_day=50_000):
    saved_per_req = scn["frontier_$/req"] * (1 - scn["cache_hit_%"] / 100) - scn["frugal_$/req"]
    return round(saved_per_req * reqs_per_day * 30, 2)


def onprem_breakeven(cheap_cloud="gpt-4o-mini", tin=500, tout=300, node_usd=8600, life_months=36, power_usd_mo=60):
    """When does buying a GPU node (cheap tier local, $0/token) beat paying cloud for the cheap tier?"""
    cheap_req = per_req(cheap_cloud, tin, tout)
    node_mo = node_usd / life_months + power_usd_mo
    reqs_to_break = node_mo / cheap_req if cheap_req else float("inf")
    return {"node_$": node_usd, "amortized_$/mo": round(node_mo, 2),
            "cloud_cheap_$/req": round(cheap_req, 6),
            "reqs/mo_to_breakeven": round(reqs_to_break),
            "reqs/day_to_breakeven": round(reqs_to_break / 30)}


def main():
    TIN, TOUT = 500, 300  # assumed avg agent-step tokens; edit for your workload
    print(f"# assumptions: {TIN} input + {TOUT} output tokens/request; escalation 17% of hard "
          f"prompts (measured, LLM-judged small-N — see METHODOLOGY.md)")
    print("# TWO honest baselines. 'vs frontier-default' = savings if you'd otherwise send all")
    print("# to the frontier model. 'vs static-cheap' = how much MORE Frugal costs than sending")
    print("# all to the cheap model (a POSITIVE number) — that premium buys back quality on the")
    print("# escalated ~17%. Same cache applied to all three.\n")

    combos = [
        ("cheap=gpt-4o-mini vs frontier=gpt-4o", "gpt-4o-mini", "gpt-4o"),
        ("cheap=claude-haiku vs frontier=claude-sonnet", "claude-haiku", "claude-sonnet"),
        ("cheap=llama-8b vs frontier=llama-70b (open hosts)", "llama-8b", "llama-70b"),
        ("cheap=LOCAL($0) vs frontier=gpt-4o", "local", "gpt-4o"),
    ]
    mixes = [("mostly-easy (80/20)", 0.8), ("balanced (60/40)", 0.6), ("mostly-hard (30/70)", 0.3)]

    for title, cheap, frontier in combos:
        print(f"## {title}")
        for mixname, ef in mixes:
            s = costs(cheap, frontier, TIN, TOUT, ef, confidence="self_consistency", cache_hit=0.0)
            print(f"  {mixname:22s} vs-frontier-default saved={s['vs_frontier_default_saved_%']:6}%  "
                  f"| vs-static-cheap Frugal costs {s['vs_static_cheap_costs_%']:+6}% more (buys quality on {s['escalate_%']}% escalated)  "
                  f"| ${s['$/1M_saved_vs_frontier']:>7}/1M saved vs frontier")
        print()

    print("## same, WITH a 30% response-cache hit rate (repeats free for ALL — fair)")
    for title, cheap, frontier in combos[:1]:
        for mixname, ef in mixes:
            s = costs(cheap, frontier, TIN, TOUT, ef, cache_hit=0.30)
            print(f"  {mixname:22s} vs-frontier-default saved={s['vs_frontier_default_saved_%']:6}%  "
                  f"| ${monthly_vs_frontier(s):>10}/mo @50k/day")
    print()

    print("## on-prem break-even (local cheap tier vs paying gpt-4o-mini for it)")
    for node in (8600, 15000):
        b = onprem_breakeven(node_usd=node)
        print(f"  node ${node}: {b['amortized_$/mo']}/mo amortized -> break-even at "
              f"{b['reqs/day_to_breakeven']:,} req/day ({b['reqs/mo_to_breakeven']:,}/mo)")

    print("\n# HONEST BOTTOM LINE: the big % is REAL only against a frontier-default baseline.")
    print("# Against a tuned static-cheap baseline, Frugal costs modestly MORE — its value there")
    print("# is quality recovery on the hard fraction + governance + a measured $/token, NOT a")
    print("# lower bill. Naming the baseline is the whole point. Real-model, human-graded proof")
    print("# on a real workload is the roadmap item that needs compute + a design partner.")


if __name__ == "__main__":
    main()
