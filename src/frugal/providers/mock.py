"""Deterministic, offline provider — the reason the whole stack runs with no API keys.

It fakes a three-tier model family (cheap / mid / frontier). Cheap tiers give
terse answers and "hedge" on hard prompts; the frontier tier answers fully.
That lets frugal.route demonstrate real cascade behaviour deterministically.
"""
from __future__ import annotations

import hashlib

from .base import LLMResponse, count_tokens

# tier -> canonical model id used across the demo + pricing table
TIER_MODELS = {
    "cheap": "frugal-mock-cheap",
    "mid": "frugal-mock-mid",
    "frontier": "frugal-mock-frontier",
}
_MODEL_TIER = {v: k for k, v in TIER_MODELS.items()}

_HARD_SIGNALS = (
    "prove", "analyze", "architecture", "refactor", "step by step",
    "why", "trade-off", "tradeoff", "design", "optimize", "derive",
)


def prompt_complexity(prompt: str) -> float:
    """0..1 heuristic used by both the mock and the router. Pure + deterministic."""
    p = prompt.lower()
    length_term = min(1.0, len(prompt) / 400.0)
    signal_term = min(1.0, sum(s in p for s in _HARD_SIGNALS) / 3.0)
    q_term = 0.2 if "?" in prompt else 0.0
    return min(1.0, 0.5 * length_term + 0.4 * signal_term + q_term)


class MockProvider:
    name = "mock"

    def complete(self, prompt: str, model: str | None = None, **kwargs) -> LLMResponse:
        model = model or TIER_MODELS["mid"]
        tier = _MODEL_TIER.get(model, "mid")
        text = self._reply(prompt, tier)
        cx = prompt_complexity(prompt)
        # synthetic mean log-prob: strong models stay confident; a cheap model on a hard
        # prompt gets a low (very negative) log-prob -> logprob-confidence will escalate it.
        base = {"frontier": -0.04, "mid": -0.10, "cheap": -0.14}.get(tier, -0.10)
        slope = {"frontier": 0.15, "mid": 0.55, "cheap": 1.25}.get(tier, 0.55)
        avg_lp = base - slope * cx
        return LLMResponse(
            text=text,
            input_tokens=count_tokens(prompt),
            output_tokens=count_tokens(text),
            model=model,
            avg_logprob=round(avg_lp, 4),
        )

    # --- deterministic pseudo-generation -------------------------------------
    def _reply(self, prompt: str, tier: str) -> str:
        cx = prompt_complexity(prompt)
        tag = hashlib.sha1(prompt.encode("utf-8", "surrogatepass")).hexdigest()[:6]
        head = (prompt.strip().split("\n", 1)[0])[:80]
        if tier == "frontier":
            return (
                f"[frontier:{tag}] {head} — full answer: here is a complete, "
                f"reasoned response covering the key points and edge cases."
            )
        if tier == "mid":
            if cx > 0.6:
                return f"[mid:{tag}] {head} — partial answer; this may need review."
            return f"[mid:{tag}] {head} — answer: a solid, direct response."
        # cheap
        if cx > 0.45:
            return f"[cheap:{tag}] not sure, this looks complex."  # hedges -> low confidence
        return f"[cheap:{tag}] {head} — short answer."

    def confidence(self, response: LLMResponse) -> float:
        """Stand-in for logprob/verifier confidence: hedging phrases => low."""
        t = response.text.lower()
        if any(h in t for h in ("not sure", "may need review", "looks complex", "partial answer")):
            return 0.35
        return 0.9
