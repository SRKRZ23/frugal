"""Cost-aware cascade routing: try the cheap model first, escalate only when the
answer isn't good enough. This is the money-saver — most prompts never reach the
frontier model, but the hard ones still get it.

    result = cascade("explain this bug", provider, meter)
    # result.model_used, result.escalated, result.text, result.tiers_tried

Confidence is pluggable. With MockProvider we use its hedging heuristic; in prod
pass `confidence_fn=` backed by logprobs, a verifier model, or a schema check.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional, Sequence

from ..meter import Meter
from ..providers.base import LLMResponse, Provider
from ..providers.mock import TIER_MODELS

DEFAULT_LADDER: Sequence[str] = (
    TIER_MODELS["cheap"],
    TIER_MODELS["mid"],
    TIER_MODELS["frontier"],
)


@dataclass
class RouteResult:
    text: str
    model_used: str
    tiers_tried: List[str]
    escalated: bool
    response: LLMResponse


def _default_confidence(provider: Provider, response: LLMResponse, prompt: str = "") -> float:
    fn = getattr(provider, "confidence", None)
    if callable(fn):
        return float(fn(response))
    # Generic fallback: hedging language => low confidence.
    t = response.text.lower()
    hedges = ("not sure", "i think", "might be", "unclear", "cannot", "no idea")
    return 0.4 if any(h in t for h in hedges) else 0.85


def _call_confidence(fn, provider: Provider, response: LLMResponse, prompt: str) -> float:
    """Support both (provider, response) and (provider, response, prompt) signatures.
    A broken/hostile confidence function must never crash routing — it fails SAFE
    (confidence 0.0 -> escalate to the stronger model)."""
    try:
        try:
            v = fn(provider, response, prompt)
        except TypeError:
            v = fn(provider, response)      # 2-arg confidence signature
    except Exception:                        # confidence raised -> escalate, don't crash
        return 0.0
    try:
        v = float(v)
    except (TypeError, ValueError):          # None / non-numeric -> escalate
        return 0.0
    return 0.0 if v != v else v              # NaN -> escalate


def cascade(
    prompt: str,
    provider: Provider,
    meter: Meter,
    ladder: Sequence[str] = DEFAULT_LADDER,
    min_confidence: float = 0.6,
    confidence_fn: Optional[Callable[[Provider, LLMResponse], float]] = None,
    warn_economics: bool = True,
    cache=None,
    **complete_kwargs,
) -> RouteResult:
    conf = confidence_fn or _default_confidence
    # If a re-sampling confidence (self-consistency) is used, check it will actually pay off
    # for this ladder's price gap and warn once if not (see frugal.economics).
    if warn_economics and getattr(conf, "_is_resampling", False) and len(ladder) >= 2:
        try:
            from ..economics import check_and_warn
            check_and_warn(ladder[0], ladder[-1], confidence="self_consistency",
                           probes=getattr(conf, "_probes", 2))
        except Exception:  # noqa: BLE001
            pass

    # cache hit = $0, no model call at all
    if cache is not None:
        hit = cache.get(prompt)
        if hit is not None:
            tag = hit.model + " (cache)"
            with meter.track(tag, tier="cache") as call:
                call.set(LLMResponse(hit.text, 0, 0, tag))  # 0 tokens billed -> $0
            return RouteResult(hit.text, tag, [tag], False, hit)

    tried: List[str] = []
    last: Optional[LLMResponse] = None
    result: Optional[RouteResult] = None
    for i, model in enumerate(ladder):
        is_last = i == len(ladder) - 1
        with meter.track(model, tier=model) as call:
            last = call.set(provider.complete(prompt, model=model, **complete_kwargs))
        tried.append(model)
        if is_last or _call_confidence(conf, provider, last, prompt) >= min_confidence:
            result = RouteResult(last.text, model, tried, len(tried) > 1, last)
            break
    if result is None:  # unreachable (loop returns on last rung), keeps type-checkers happy
        result = RouteResult(last.text, tried[-1], tried, len(tried) > 1, last)  # type: ignore[arg-type]
    if cache is not None and result.response is not None:
        cache.put(prompt, result.response)
    return result
