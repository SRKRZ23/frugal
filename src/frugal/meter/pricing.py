"""Price table in USD per 1M tokens (input, output).

⚠️ APPROXIMATE, user-editable. These are ballpark public list prices meant as
sane defaults — verify against your provider's current pricing before you rely
on the dollar figures. Add your own models with `register_price()` or a YAML/env
override. Local models are $0 (you pay in hardware, not per token).
"""
from __future__ import annotations

from typing import Dict, Tuple

# model_id -> (usd_per_1M_input, usd_per_1M_output)
PRICES: Dict[str, Tuple[float, float]] = {
    # --- Frugal mock tiers (for offline demos) ---
    "frugal-mock-cheap": (0.15, 0.60),
    "frugal-mock-mid": (0.60, 2.40),
    "frugal-mock-frontier": (5.00, 20.00),
    # --- real-ish list prices (approximate, 2026-07; edit to match your account) ---
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
    "claude-haiku": (1.00, 5.00),
    "claude-sonnet": (3.00, 15.00),
    "llama-8b": (0.20, 0.20),
    "llama-70b": (0.90, 0.90),
    "llama3": (0.0, 0.0),        # local via Ollama
    "local": (0.0, 0.0),
}

_DEFAULT = (1.00, 3.00)  # used for unknown models so accounting never crashes


def register_price(model: str, input_per_1m: float, output_per_1m: float) -> None:
    PRICES[model] = (float(input_per_1m), float(output_per_1m))


def cost_of(model: str, input_tokens: int, output_tokens: int) -> float:
    p_in, p_out = PRICES.get(model, _DEFAULT)
    return (input_tokens / 1_000_000.0) * p_in + (output_tokens / 1_000_000.0) * p_out
