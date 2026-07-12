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
