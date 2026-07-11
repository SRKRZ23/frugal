"""Provider protocol + the shared response/token primitives every module builds on."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol, runtime_checkable


def count_tokens(text: str) -> int:
    """Cheap, dependency-free token estimate (~4 chars/token, the common heuristic).

    Deliberately approximate: swap in tiktoken/the provider's real usage numbers
    when you have them. Good enough for routing decisions and offline demos.
    """
    if not text:
        return 0
    return max(1, (len(text) + 3) // 4)


@dataclass
class LLMResponse:
    text: str
    input_tokens: int
    output_tokens: int
    model: str
    avg_logprob: Optional[float] = None   # mean token log-prob if the backend returns it

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@runtime_checkable
class Provider(Protocol):
    """Minimal surface Frugal needs from any LLM backend."""

    name: str

    def complete(self, prompt: str, model: str | None = None, **kwargs) -> LLMResponse:
        ...
