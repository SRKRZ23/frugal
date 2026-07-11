"""The hub. Every LLM call flows through a Meter so you always know what you spent.

    meter = Meter(budget_usd=1.00)
    with meter.track("gpt-4o-mini") as call:
        call.set(provider.complete(prompt, model="gpt-4o-mini"))
    print(meter.summary())

route / local / gateway / mcp all read the same Meter — that shared ledger is
what turns six tools into one product.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, List, Optional

from ..providers.base import LLMResponse
from .pricing import cost_of


class BudgetExceeded(RuntimeError):
    """Raised by a budget-enforcing Meter when a call would blow the cap."""


@dataclass
class Call:
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    latency_s: float = 0.0
    tier: Optional[str] = None
    response: Optional[LLMResponse] = None

    def set(self, response: LLMResponse) -> LLMResponse:
        """Attach the provider response; tokens/cost are finalised on context exit."""
        self.response = response
        return response


@dataclass
class Meter:
    budget_usd: Optional[float] = None
    calls: List[Call] = field(default_factory=list)
    max_history: Optional[int] = None  # cap stored Call objects (bounded memory for long runs)
    _lock: Any = field(default_factory=threading.Lock, repr=False, compare=False)
    # aggregates for calls dropped by the ring buffer (so totals stay exact)
    _drop: dict = field(default_factory=lambda: {"cost": 0.0, "in": 0, "out": 0, "n": 0, "by_model": {}},
                        repr=False, compare=False)
    # running aggregate of the LIVE calls -> O(1) total_cost / budget checks (no per-call summation)
    _live: dict = field(default_factory=lambda: {"cost": 0.0, "in": 0, "out": 0},
                        repr=False, compare=False)

    class _Tracker:
        def __init__(self, meter: "Meter", model: str, tier: Optional[str]):
            self._meter, self._call, self._start = meter, Call(model=model, tier=tier), 0.0

        def __enter__(self) -> Call:
            self._start = perf_counter()
            return self._call

        def __exit__(self, exc_type, exc, tb) -> bool:
            c = self._call
            c.latency_s = perf_counter() - self._start
            if c.response is not None:
                c.input_tokens = c.response.input_tokens
                c.output_tokens = c.response.output_tokens
            c.cost_usd = cost_of(c.model, c.input_tokens, c.output_tokens)
            # atomic append + O(1) budget check via running aggregates (no per-call summation)
            with self._meter._lock:
                m = self._meter
                m.calls.append(c)
                lv = m._live
                lv["cost"] += c.cost_usd; lv["in"] += c.input_tokens; lv["out"] += c.output_tokens
                mh = m.max_history
                if mh is not None and len(m.calls) > mh:
                    old = m.calls.pop(0)   # ring buffer: fold oldest into the dropped aggregates
                    lv["cost"] -= old.cost_usd; lv["in"] -= old.input_tokens; lv["out"] -= old.output_tokens
                    d = m._drop
                    d["cost"] += old.cost_usd; d["in"] += old.input_tokens
                    d["out"] += old.output_tokens; d["n"] += 1
                    bm = d["by_model"].setdefault(old.model, {"calls": 0, "cost_usd": 0.0, "tokens": 0})
                    bm["calls"] += 1; bm["cost_usd"] += old.cost_usd
                    bm["tokens"] += old.input_tokens + old.output_tokens
                # true total = dropped + live, both O(1); catches overspend even with max_history
                true_total = m._drop["cost"] + m._live["cost"]
                over = (m.budget_usd is not None and true_total > m.budget_usd)
                spent = m.budget_usd
            if exc_type is None and over:
                raise BudgetExceeded(
                    f"budget ${spent:.4f} exceeded (spent ${true_total:.4f})"
                )
            return False  # never swallow exceptions

    def track(self, model: str, tier: Optional[str] = None) -> "Meter._Tracker":
        return Meter._Tracker(self, model, tier)

    def would_exceed(self, projected_usd: float = 0.0) -> bool:
        if self.budget_usd is None:
            return False
        return (self.total_cost + projected_usd) > self.budget_usd

    def can_afford(self, model: str, input_tokens: int, output_tokens: int) -> bool:
        """Pre-flight check: would this call fit the budget? Enables zero-overshoot
        enforcement (reserve before you spend) instead of catching it after."""
        if self.budget_usd is None:
            return True
        return not self.would_exceed(cost_of(model, input_tokens, output_tokens))

    def reserve(self, model: str, input_tokens: int, output_tokens: int) -> None:
        """Raise BEFORE a call if it can't fit the budget (true hard cap, no overshoot)."""
        if not self.can_afford(model, input_tokens, output_tokens):
            raise BudgetExceeded(
                f"budget ${self.budget_usd:.4f} would be exceeded by this call "
                f"(spent ${self.total_cost:.4f}); refused before spending."
            )

    # --- aggregates ----------------------------------------------------------
    @property
    def total_cost(self) -> float:
        return self._drop["cost"] + self._live["cost"]

    @property
    def total_input_tokens(self) -> int:
        return self._drop["in"] + self._live["in"]

    @property
    def total_output_tokens(self) -> int:
        return self._drop["out"] + self._live["out"]

    def summary(self) -> dict:
        # start from ring-buffer-dropped aggregates so totals stay exact after trimming
        by_model: dict = {k: dict(v) for k, v in self._drop["by_model"].items()}
        with self._lock:                       # snapshot the live calls so a concurrent
            live = list(self.calls)            # append() can't tear the iteration
        for c in live:
            m = by_model.setdefault(c.model, {"calls": 0, "cost_usd": 0.0, "tokens": 0})
            m["calls"] += 1
            m["cost_usd"] += c.cost_usd
            m["tokens"] += c.input_tokens + c.output_tokens
        return {
            "calls": self._drop["n"] + len(live),
            "total_cost_usd": round(self.total_cost, 6),
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "budget_usd": self.budget_usd,
            "budget_remaining_usd": (
                None if self.budget_usd is None else round(self.budget_usd - self.total_cost, 6)
            ),
            "by_model": {k: {**v, "cost_usd": round(v["cost_usd"], 6)} for k, v in by_model.items()},
        }
