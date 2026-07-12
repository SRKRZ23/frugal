"""frugal diagnose — a read-only savings PROJECTION on a customer's OWN prompt log.

The wedge: a prospective user drops in a log of their real prompts and instantly sees what
Frugal's cost-aware routing would do to their bill — what share stays on the cheap/local
model, what escalates to a frontier model, and the projected $ vs the model they run today.

Two honesty rules are baked in:
  1. Nothing leaves the machine and NO model is called — it reads the log locally and scores
     each prompt with a complexity heuristic. Safe to run on sensitive/on-prem logs.
  2. It is clearly labelled a PROJECTION, not a measurement. The complexity heuristic decides
     the routing split; the dollar figures use editable list prices. For measured cost AND
     quality numbers you must run the live diagnostic against your own models on your traffic.

For the MEASURED version use `diagnose_live()` / `frugal diagnose --live`: it actually routes
every prompt through the cascade against real models and observes cost, latency and escalation
(no heuristic). Point it at a local/on-prem Ollama to keep data in-house.
"""
import json
from dataclasses import dataclass, field
from typing import List, Union

from .providers.mock import prompt_complexity
from .meter.pricing import cost_of
from .meter import count_tokens


@dataclass
class DiagnosisRow:
    prompt_preview: str
    complexity: float
    route: str  # "cheap" or "escalate"


@dataclass
class Diagnosis:
    n: int
    escalate_frac: float
    cheap_frac: float
    current_cost_usd: float
    frugal_cost_usd: float
    saved_frac: float          # vs the current model (CAN be negative on a small price gap)
    saved_per_1m_usd: float
    current_model: str
    cheap_model: str
    frontier_model: str
    threshold: float
    rows: List[DiagnosisRow] = field(default_factory=list)

    def summary(self) -> str:
        pct = lambda f: f"{100 * f:.1f}%"
        sign = "+" if self.saved_frac >= 0 else "−"
        lines = [
            "frugal diagnose — PROJECTION (heuristic; no model called; nothing left this machine)",
            f"  prompts analysed      : {self.n}",
            f"  stay on cheap/local   : {pct(self.cheap_frac):>7}   ({self.cheap_model})",
            f"  escalate to frontier  : {pct(self.escalate_frac):>7}   ({self.frontier_model})",
            f"  cost today            : ${self.current_cost_usd:.6f}   (all on {self.current_model})",
            f"  cost with Frugal      : ${self.frugal_cost_usd:.6f}",
            f"  projected savings     : {sign}{pct(abs(self.saved_frac))}   "
            f"(${self.saved_per_1m_usd:,.0f} / 1M requests) vs your current model",
        ]
        if self.saved_frac < 0:
            lines.append("  ⚠ NEGATIVE: your current model is already close in price to the cheap "
                         "tier — cascading costs more than it saves here. Frugal would WARN you and "
                         "recommend a bigger price gap or a local tier.")
        else:
            lines.append(f"  quality note          : the {pct(self.escalate_frac)} flagged as hard "
                         "get the frontier model; the rest stay cheap. The heuristic can misjudge — "
                         "the escalation is the insurance.")
        lines.append("  ⚠ PROJECTION ONLY — complexity-scored, list prices. Run the live diagnostic on "
                     "your own models/traffic for MEASURED cost + quality.")
        return "\n".join(lines)


def diagnose_prompts(
    prompts: List[Union[str, dict]],
    current_model: str,
    cheap_model: str,
    frontier_model: str,
    threshold: float = 0.6,
    out_tokens: int = 300,
) -> Diagnosis:
    """Project Frugal's routing over `prompts` vs running everything on `current_model`.

    No model is called; each prompt is complexity-scored and routed cheap (<=threshold) or
    escalated (>threshold). Frugal's per-prompt cost = cheap call + (frontier call iff escalated).
    """
    rows: List[DiagnosisRow] = []
    esc = 0
    cur = frug = 0.0
    for p in prompts:
        text = p if isinstance(p, str) else str(p)
        tin = count_tokens(text)
        c = prompt_complexity(text)
        escalate = c > threshold
        esc += 1 if escalate else 0
        cur += cost_of(current_model, tin, out_tokens)
        frug += cost_of(cheap_model, tin, out_tokens)
        if escalate:
            frug += cost_of(frontier_model, tin, out_tokens)
        preview = text[:60].replace("\n", " ")
        rows.append(DiagnosisRow(preview, round(c, 3), "escalate" if escalate else "cheap"))

    n = len(prompts)
    denom = n or 1
    saved = (1 - frug / cur) if cur else 0.0
    return Diagnosis(
        n=n,
        escalate_frac=esc / denom,
        cheap_frac=1 - esc / denom,
        current_cost_usd=round(cur, 6),
        frugal_cost_usd=round(frug, 6),
        saved_frac=saved,
        saved_per_1m_usd=(cur - frug) / denom * 1e6 if n else 0.0,
        current_model=current_model,
        cheap_model=cheap_model,
        frontier_model=frontier_model,
        threshold=threshold,
        rows=rows,
    )


@dataclass
class LiveRow:
    prompt_preview: str
    model_used: str
    escalated: bool
    cost_usd: float
    latency_s: float


@dataclass
class LiveDiagnosis:
    """A MEASURED diagnosis: every prompt was actually sent through the cascade against
    real models. Nothing here is a heuristic guess — cost, latency and the escalation
    decision are observed, not projected."""
    n: int
    escalate_frac: float
    cheap_frac: float
    frugal_cost_usd: float              # measured total actually spent by the cascade
    baseline_frontier_cost_usd: float   # measured cost of the same prompts, all on frontier
    saved_vs_frontier_frac: float       # can be negative
    p50_latency_s: float
    cheap_model: str
    frontier_model: str
    confidence: str
    min_confidence: float
    rows: List["LiveRow"] = field(default_factory=list)

    def summary(self) -> str:
        pct = lambda f: f"{100 * f:.1f}%"
        priced = self.baseline_frontier_cost_usd > 0
        lines = [
            "frugal diagnose --live — MEASURED (every prompt actually routed through real models)",
            f"  prompts routed        : {self.n}",
            f"  confidence signal     : {self.confidence} (escalate below {self.min_confidence})",
            f"  stayed on cheap/local : {pct(self.cheap_frac):>7}   ({self.cheap_model})",
            f"  escalated to frontier : {pct(self.escalate_frac):>7}   ({self.frontier_model})",
            f"  median latency        : {self.p50_latency_s:.2f}s / prompt",
        ]
        if priced:
            sign = "+" if self.saved_vs_frontier_frac >= 0 else "−"
            lines += [
                f"  measured spend        : ${self.frugal_cost_usd:.6f}",
                f"  all-on-frontier spend : ${self.baseline_frontier_cost_usd:.6f}",
                f"  measured savings      : {sign}{pct(abs(self.saved_vs_frontier_frac))} vs all-on-frontier",
            ]
        else:
            lines.append("  measured spend        : $0 (local models are free) — the win here is "
                         "LATENCY/throughput, not dollars. Map to API list prices for a $ figure.")
        return "\n".join(lines)


def diagnose_live(
    prompts: List[Union[str, dict]],
    cheap_model: str,
    frontier_model: str,
    *,
    provider=None,
    backend: str = "ollama",
    host: str = "http://localhost:11434",
    base_url: str = None,
    api_key: str = None,
    min_confidence: float = 0.6,
    confidence: str = "verifier",
    out_tokens: int = 300,
) -> LiveDiagnosis:
    """Actually route every prompt through the cascade against REAL models and measure
    what happens. Unlike `diagnose_prompts`, nothing is a heuristic — cost, latency and
    escalation are observed. Pass `provider=` to inject a stub (used in tests).

    NOTE: this DOES call models, so prompts leave the machine iff the backend is remote.
    Point `--backend ollama --host` at a local/on-prem server to keep data in-house.
    """
    import time

    from .meter import Meter
    from .meter.pricing import cost_of
    from .route import cascade
    from .route.confidence import (
        make_logprob_confidence,
        make_self_consistency,
        make_verifier_confidence,
    )

    if provider is None:
        if backend == "ollama":
            from .providers import get_ollama
            provider = get_ollama(model=cheap_model, host=host)
        else:
            from .providers import get_openai
            provider = get_openai(model=cheap_model, base_url=base_url, api_key=api_key)

    conf_fn = {
        "verifier": make_verifier_confidence,
        "self-consistency": make_self_consistency,
        "logprob": make_logprob_confidence,
        "hedge": lambda: None,
    }.get(confidence, make_verifier_confidence)()

    ladder = (cheap_model, frontier_model)
    rows: List[LiveRow] = []
    esc = 0
    frug_cost = base_cost = 0.0
    latencies: List[float] = []
    for p in prompts:
        text = p if isinstance(p, str) else str(p)
        meter = Meter()
        t0 = time.perf_counter()
        r = cascade(text, provider, meter, ladder=ladder, min_confidence=min_confidence,
                    confidence_fn=conf_fn, warn_economics=False, max_tokens=out_tokens)
        dt = time.perf_counter() - t0
        latencies.append(dt)
        esc += 1 if r.escalated else 0
        frug_cost += meter.total_cost
        out_tok = r.response.output_tokens if r.response else out_tokens
        base_cost += cost_of(frontier_model, count_tokens(text), out_tok)
        rows.append(LiveRow(text[:60].replace("\n", " "), r.model_used, r.escalated,
                            round(meter.total_cost, 6), round(dt, 3)))

    n = len(prompts)
    denom = n or 1
    saved = (1 - frug_cost / base_cost) if base_cost else 0.0
    ordered = sorted(latencies)
    p50 = ordered[len(ordered) // 2] if ordered else 0.0
    return LiveDiagnosis(
        n=n,
        escalate_frac=esc / denom,
        cheap_frac=1 - esc / denom,
        frugal_cost_usd=round(frug_cost, 6),
        baseline_frontier_cost_usd=round(base_cost, 6),
        saved_vs_frontier_frac=saved,
        p50_latency_s=round(p50, 3),
        cheap_model=cheap_model,
        frontier_model=frontier_model,
        confidence=confidence,
        min_confidence=min_confidence,
        rows=rows,
    )


def load_prompts(path: str) -> List[str]:
    """Load prompts from a .jsonl (obj with `prompt` or OpenAI-style `messages`) or a plain
    text file (one prompt per line). Robust to malformed lines (kept as raw text)."""
    prompts: List[str] = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            if line[0] in "{[":
                try:
                    obj = json.loads(line)
                except Exception:
                    prompts.append(line)
                    continue
                if isinstance(obj, dict):
                    if "prompt" in obj:
                        prompts.append(str(obj["prompt"]))
                    elif obj.get("messages"):
                        prompts.append(str(obj["messages"][-1].get("content", "")))
                    else:
                        prompts.append(json.dumps(obj))
                else:
                    prompts.append(str(obj))
            else:
                prompts.append(line)
    return prompts
