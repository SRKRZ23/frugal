"""Zero-dependency local tracing for LLM/agent steps. Records spans in-process so
you can inspect a run offline; if opentelemetry is installed it also emits real
OTel spans (the gap MLflow flagged for local Ollama/vLLM setups).

    tr = Tracer()
    with tr.span("retrieve", k=5):
        ...
    with tr.span("generate", model="frugal-mock-mid"):
        ...
    tr.spans  # -> list of finished spans with durations
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, Dict, List


@dataclass
class Span:
    name: str
    attrs: Dict[str, Any]
    duration_s: float = 0.0


@dataclass
class Tracer:
    spans: List[Span] = field(default_factory=list)
    emit_otel: bool = False

    def __post_init__(self):
        self._otel = None
        if self.emit_otel:
            try:  # pragma: no cover - optional
                from opentelemetry import trace

                self._otel = trace.get_tracer("frugal")
            except ImportError:
                self._otel = None

    @contextmanager
    def span(self, name: str, **attrs):
        start = perf_counter()
        otel_cm = self._otel.start_as_current_span(name) if self._otel else None
        if otel_cm:  # pragma: no cover - optional
            otel_cm.__enter__()
        try:
            yield
        finally:
            dur = perf_counter() - start
            self.spans.append(Span(name=name, attrs=dict(attrs), duration_s=dur))
            if otel_cm:  # pragma: no cover - optional
                otel_cm.__exit__(None, None, None)

    def summary(self) -> List[Dict[str, Any]]:
        return [{"name": s.name, "duration_s": round(s.duration_s, 6), **s.attrs} for s in self.spans]
