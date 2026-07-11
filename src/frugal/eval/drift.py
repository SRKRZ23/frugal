"""Lightweight, local semantic-drift detector — no SaaS, no vector DB.

Fit a baseline on known-good ("golden") outputs, then score new production
outputs: high drift = the model's answers have moved away from the baseline
distribution (length + vocabulary centroid). Cheap early-warning for silent
quality regressions.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List

_WORD = re.compile(r"[a-z0-9]+")


def _vec(text: str) -> Counter:
    return Counter(_WORD.findall(text.lower()))


def _cosine(a: Counter, b: Counter) -> float:
    keys = set(a) | set(b)
    if not keys:
        return 1.0
    dot = sum(a[k] * b[k] for k in keys)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0


@dataclass
class DriftMonitor:
    centroid: Counter = field(default_factory=Counter)
    avg_len: float = 0.0
    _n: int = 0

    def fit(self, golden_outputs: List[str]) -> "DriftMonitor":
        self.centroid = Counter()
        total_len = 0
        for o in golden_outputs:
            self.centroid.update(_vec(o))
            total_len += len(o.split())
        self._n = len(golden_outputs)
        self.avg_len = total_len / self._n if self._n else 0.0
        return self

    def drift(self, output: str) -> Dict[str, float]:
        """Return {'drift': 0..1, 'similarity':..., 'len_ratio':...}. Higher drift = worse."""
        sim = _cosine(_vec(output), self.centroid)
        cur_len = len(output.split())
        len_ratio = (cur_len / self.avg_len) if self.avg_len else 1.0
        len_penalty = min(1.0, abs(len_ratio - 1.0))
        drift = round(0.7 * (1.0 - sim) + 0.3 * len_penalty, 4)
        return {"drift": drift, "similarity": round(sim, 4), "len_ratio": round(len_ratio, 3)}

    def is_drifted(self, output: str, threshold: float = 0.5) -> bool:
        return self.drift(output)["drift"] >= threshold
