"""Broader eval with a JUDGE PANEL — retention by category, majority vote of >1 judge.

Honest scope: this is still LLM-judged, NOT human. A panel (2+ models voting) reduces
single-judge bias and a categorized set shows WHERE the cheap tier holds vs breaks — the
closest honest approximation to a broad eval short of paying human raters (still the gold
standard, still owed).

Env: FRUGAL_CHEAP (default qwen2.5-coder:3b), FRUGAL_STRONG (default phi4:14b),
     FRUGAL_JUDGES (comma list, default "qwen2.5:7b,phi4:14b"),
     FRUGAL_OLLAMA_HOST (default localhost), FRUGAL_NUM_PREDICT (default 260).
"""
from __future__ import annotations

import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, "/shared/frugal/src")

from frugal.eval import strip_reasoning  # noqa: E402
from frugal.eval.judge import JudgePanel  # noqa: E402
from frugal.providers import get_ollama  # noqa: E402

from data_broad import BROAD  # noqa: E402


def main():
    host = os.environ.get("FRUGAL_OLLAMA_HOST", "http://localhost:11434")
    cheap = os.environ.get("FRUGAL_CHEAP", "qwen2.5-coder:3b")
    strong = os.environ.get("FRUGAL_STRONG", "phi4:14b")
    judges = [m.strip() for m in os.environ.get("FRUGAL_JUDGES", "qwen2.5:7b,phi4:14b").split(",") if m.strip()]
    npr = int(os.environ.get("FRUGAL_NUM_PREDICT", "260"))
    prov = get_ollama(host=host)
    panel = JudgePanel(prov, judges)

    print(f"cheap={cheap} strong={strong} judges={judges} N={len(BROAD)}\n", flush=True)

    by_cat = defaultdict(lambda: [0, 0])   # category -> [retained, total]
    rows = []
    for i, (cat, q) in enumerate(BROAD):
        ca = strip_reasoning(prov.complete(q, model=cheap, num_predict=npr, temperature=0.0).text)
        sa = strip_reasoning(prov.complete(q, model=strong, num_predict=npr, temperature=0.0).text)
        verdict, votes = panel.equivalent(q, ca, sa)
        by_cat[cat][1] += 1
        by_cat[cat][0] += 1 if verdict else 0
        rows.append({"cat": cat, "retained": verdict, "votes": votes})
        print(f"[{i+1}/{len(BROAD)}] {cat:13s} cheap≈strong={verdict}  votes={votes}", flush=True)

    total_ret = sum(r["retained"] for r in rows)
    overall = round(100 * total_ret / len(rows), 1)
    cats = {c: {"retention_pct": round(100 * a / b, 1), "n": b} for c, (a, b) in by_cat.items()}

    print("\n=== BROAD EVAL (judge panel) ===")
    print(f"overall retention (cheap as-good-as strong): {total_ret}/{len(rows)} ({overall}%)")
    for c, v in sorted(cats.items(), key=lambda x: x[1]["retention_pct"]):
        print(f"  {c:13s} {v['retention_pct']:5}%  (n={v['n']})")

    import datetime, socket
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    out = {"host": socket.gethostname(), "cheap": cheap, "strong": strong, "judges": judges,
           "N": len(rows), "overall_retention_pct": overall, "by_category": cats}
    d = os.path.dirname(__file__)
    with open(os.path.join(d, "RESULTS_BROAD.json"), "w") as fh:
        json.dump(out, fh, indent=2)
    with open(os.path.join(d, "RESULTS_BROAD.md"), "w", encoding="utf-8") as fh:
        fh.write(f"# Frugal broad eval — judge panel ({stamp}, {socket.gethostname()})\n\n")
        fh.write(f"_Cheap **{cheap}** vs strong **{strong}**, judged by a PANEL {judges} (majority vote). "
                 f"Still LLM-judged, NOT human — a panel + categories reduce bias; human eval is still owed._\n\n")
        fh.write(f"**Overall retention (cheap as-good-as strong): {overall}%** on {len(rows)} prompts.\n\n")
        fh.write("| category | retention | n |\n|---|---|---|\n")
        for c, v in sorted(cats.items(), key=lambda x: x[1]["retention_pct"]):
            fh.write(f"| {c} | {v['retention_pct']}% | {v['n']} |\n")
    print(f"\nwrote {d}/RESULTS_BROAD.md")


if __name__ == "__main__":
    main()
