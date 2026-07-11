"""Economics guard — will cascade + your confidence signal actually SAVE money?

Grounded in BUSINESS_CASE.md: a re-sampling confidence signal (self-consistency)
multiplies the cheap-tier cost, so on a small price gap it can cost MORE than
frontier-only. This module computes that up front and warns — a config that can't
save is one to flag, not ship.

    from frugal.economics import routing_savings, check_and_warn
    routing_savings("claude-haiku", "claude-sonnet", confidence="self_consistency")
    # -> will_save=False (only ~3x price gap can't cover 3x cheap probing)
"""
from __future__ import annotations

import warnings

from .meter.pricing import cost_of


def routing_savings(
    cheap_model: str,
    frontier_model: str,
    confidence: str = "self_consistency",
    probes: int = 2,
    easy_frac: float = 0.6,
    hard_escalate: float = 0.17,
    tin: int = 500,
    tout: int = 300,
) -> dict:
    """Projected savings of cascade vs frontier-only for a (cheap, frontier) pair.
    confidence='self_consistency' costs (1+probes)x cheap per request; 'free' (logprobs) = 1x."""
    cheap = cost_of(cheap_model, tin, tout)
    frontier = cost_of(frontier_model, tin, tout)
    ratio = (frontier / cheap) if cheap > 0 else float("inf")
    escalate = (1 - easy_frac) * hard_escalate
    probe_mult = (1 + probes) if confidence == "self_consistency" else 1
    frugal = probe_mult * cheap + escalate * frontier
    saved = 1 - frugal / frontier if frontier > 0 else 0.0
    return {
        "cheap_model": cheap_model, "frontier_model": frontier_model,
        "cheap_cost_per_req": round(cheap, 6), "frontier_cost_per_req": round(frontier, 6),
        "price_ratio": round(ratio, 1), "confidence": confidence, "probe_mult": probe_mult,
        "escalate_frac": round(escalate, 4),
        "saved_pct": round(100 * saved, 1), "will_save": saved > 0.05,
    }


def check_and_warn(cheap_model: str, frontier_model: str, confidence: str = "self_consistency",
                   probes: int = 2, **kw) -> dict:
    """Compute savings; emit a warning (once) if this config won't meaningfully save."""
    r = routing_savings(cheap_model, frontier_model, confidence, probes, **kw)
    if not r["will_save"]:
        warnings.warn(
            f"Frugal economics: cascading {cheap_model} -> {frontier_model} with "
            f"'{confidence}' (x{r['probe_mult']} cheap probes/request) is projected to save only "
            f"{r['saved_pct']}% (price ratio {r['price_ratio']}x). The probing eats the margin — "
            f"use 'free'/logprob confidence, a LOCAL cheap tier ($0/token → probing is free), or "
            f"don't cascade this pair. See BUSINESS_CASE.md.",
            stacklevel=2,
        )
    return r
