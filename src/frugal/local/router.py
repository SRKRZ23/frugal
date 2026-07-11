"""Local <-> cloud routing — the "Agent Computers" two-tier pattern:
keep cheap/private/short work on a local model (Ollama/vLLM/AMD), send only the
heavy or explicitly-cloud work to a frontier API. Decide by cost, privacy tag,
and prompt complexity — never leak a `private` prompt off-box.

    lr = LocalRouter(local=ollama, cloud=openai, meter=meter)
    out = lr.complete("summarise this file", tags={"private"})   # stays local
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Set

from ..meter import Meter
from ..providers.base import LLMResponse, Provider
from ..providers.mock import prompt_complexity


@dataclass
class LocalRouter:
    local: Provider
    cloud: Optional[Provider] = None
    meter: Meter = field(default_factory=Meter)
    complexity_threshold: float = 0.6   # above this, prefer cloud (unless private)
    local_model: Optional[str] = None
    cloud_model: Optional[str] = None

    def decide(self, prompt: str, tags: Optional[Set[str]] = None) -> str:
        tags = tags or set()
        if "private" in tags or "local" in tags:
            return "local"
        if self.cloud is None:
            return "local"
        if "cloud" in tags:
            return "cloud"
        return "cloud" if prompt_complexity(prompt) > self.complexity_threshold else "local"

    def complete(self, prompt: str, tags: Optional[Set[str]] = None, **kwargs) -> LLMResponse:
        where = self.decide(prompt, tags)
        provider = self.local if where == "local" else self.cloud
        model = self.local_model if where == "local" else self.cloud_model
        with self.meter.track(model or getattr(provider, "name", where), tier=where) as call:
            return call.set(provider.complete(prompt, model=model, **kwargs))
