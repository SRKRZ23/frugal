"""Reproducible cost / savings model for Frugal — REAL provider prices, honest math.

Every number in BUSINESS_CASE.md comes from running this. It uses:
  • real list prices (USD / 1M tokens, verified 2026-07 — see PRICES, edit freely)
  • Frugal's MEASURED routing behaviour (easy prompts stay cheap; ~17% of hard prompts
    escalate — from benchmarks/RESULTS_MODELS_HARD.md)
  • the honest cost of the confidence signal (self-consistency re-samples the cheap
    model, so it is NOT free — modelled explicitly)

Run:  python benchmarks/cost_model.py
"""
from __future__ import annotations

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


def scenario(cheap, frontier, tin, tout, easy_frac, hard_escalate=0.17, confidence="self_consistency"):
    """Return dict of per-request costs & savings.
    easy_frac: share of requests that are 'easy' (cheap handles 100%).
    hard_escalate: share of HARD requests that escalate to frontier (measured ~17%).
    confidence: 'free' (logprobs/hedging) or 'self_consistency' (k=2 extra cheap samples)."""
    c_cheap = per_req(cheap, tin, tout)
    c_frontier = per_req(frontier, tin, tout)
    escalate_frac = (1 - easy_frac) * hard_escalate           # fraction of ALL reqs hitting frontier
    probe_mult = 3 if confidence == "self_consistency" else 1  # 1 answer + 2 consistency samples
    # every req pays the cheap probe(s); escalated reqs additionally pay the frontier call
    frugal = probe_mult * c_cheap + escalate_frac * c_frontier
    baseline = c_frontier                                      # naive: everything on frontier
    saved = 1 - frugal / baseline
    return {
        "cheap_$/req": round(c_cheap, 6), "frontier_$/req": round(c_frontier, 6),
        "escalate_%": round(100 * escalate_frac, 1), "confidence": confidence,
        "frugal_$/req": round(frugal, 6), "baseline_$/req": round(baseline, 6),
        "saved_%": round(100 * saved, 1),
        "$/1M_reqs_frugal": round(frugal * 1e6), "$/1M_reqs_baseline": round(baseline * 1e6),
        "$/1M_saved": round((baseline - frugal) * 1e6),
    }


def monthly(scn, reqs_per_day=50_000):
    saved_per_req = scn["baseline_$/req"] - scn["frugal_$/req"]
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
          f"prompts (measured)\n")

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
            for conf in ("free", "self_consistency"):
                s = scenario(cheap, frontier, TIN, TOUT, ef, confidence=conf)
                print(f"  {mixname:22s} conf={conf:16s} "
                      f"saved={s['saved_%']:5}%  ${s['frugal_$/req']:.6f}/req  "
                      f"${s['$/1M_saved']:>6}/1M saved  ${monthly(s):>8}/mo@50k/day")
        print()

    print("## on-prem break-even (local cheap tier vs paying gpt-4o-mini for it)")
    for node in (8600, 15000):
        b = onprem_breakeven(node_usd=node)
        print(f"  node ${node}: {b['amortized_$/mo']}/mo amortized -> break-even at "
              f"{b['reqs/day_to_breakeven']:,} req/day ({b['reqs/mo_to_breakeven']:,}/mo)")


if __name__ == "__main__":
    main()
