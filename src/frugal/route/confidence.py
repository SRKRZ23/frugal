"""Confidence strategies for cascade routing.

`cascade` escalates when confidence in the cheap answer is low. WHICH signal you
use matters a lot on real models:

  • hedging_confidence      — looks for "not sure / unclear" phrases. Cheap (no extra
                              calls) but weak: real models rarely self-hedge.
  • self_consistency_confidence — re-samples the cheap model a few times and measures
                              agreement. Low agreement => low confidence => escalate.
                              Costs extra cheap-tier calls but works on real models.

All strategies share the signature (provider, response, prompt) -> float in [0,1].
"""
from __future__ import annotations

from ..eval.asserts import semantic_similarity
from ..providers.base import LLMResponse, Provider

_HEDGES = ("not sure", "i think", "might be", "unclear", "cannot", "no idea",
           "may need review", "looks complex", "partial answer")


def hedging_confidence(provider: Provider, response: LLMResponse, prompt: str) -> float:
    fn = getattr(provider, "confidence", None)
    if callable(fn):
        try:
            return float(fn(response))
        except TypeError:
            pass
    t = response.text.lower()
    return 0.35 if any(h in t for h in _HEDGES) else 0.85


def make_self_consistency(n: int = 2, sim_threshold: float = 0.6):
    """Return a confidence_fn that samples the cheap model `n` extra times and
    reports mean agreement with the first answer as confidence."""
    def _conf(provider: Provider, response: LLMResponse, prompt: str) -> float:
        sims = []
        for _ in range(n):
            try:
                other = provider.complete(prompt, model=response.model)
            except Exception:  # noqa: BLE001
                return 0.5  # can't verify -> neutral
            sims.append(semantic_similarity(response.text, other.text))
        return sum(sims) / len(sims) if sims else 0.5
    _conf._is_resampling = True   # lets cascade run the economics guard
    _conf._probes = n
    return _conf


def make_logprob_confidence(neutral: float = 0.7):
    """The near-FREE confidence signal: use the model's own mean token log-prob
    (no extra call). confidence = exp(avg_logprob) in (0,1]; high log-prob = confident.
    Falls back to `neutral` if the backend didn't return log-probs.

    This is the cheapest signal — probe_mult = 1, so it saves the most."""
    import math

    def _conf(provider: Provider, response: LLMResponse, prompt: str) -> float:
        lp = getattr(response, "avg_logprob", None)
        if lp is None:
            return neutral
        return max(0.0, min(1.0, math.exp(lp)))
    # NOT tagged _is_resampling — no extra calls, so no economics penalty.
    return _conf


def make_verifier_confidence(sim_threshold: float = 0.6):
    """Cheaper than self-consistency: ONE extra cheap call that asks the model to
    self-check its answer (0..1). Costs 2x cheap/request (vs 3x for self-consistency),
    so it breaks even at a ~2x price gap instead of ~3x."""
    import re

    def _conf(provider: Provider, response: LLMResponse, prompt: str) -> float:
        q = (f"Is this answer correct and complete for the question? "
             f"Reply with only a number 0.0-1.0.\nQuestion: {prompt}\nAnswer: {response.text}")
        try:
            r = provider.complete(q, model=response.model)
        except Exception:  # noqa: BLE001
            return 0.5
        m = re.search(r"[01](?:\.\d+)?", r.text)
        return float(m.group()) if m else 0.5
    _conf._is_resampling = True
    _conf._probes = 1     # one extra call
    return _conf
