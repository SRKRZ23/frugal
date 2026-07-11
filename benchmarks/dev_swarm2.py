"""Two-round debate swarm (MiroFish-faithful): stricter personas react, SEE the
crowd's concerns, then revise — so we watch opinions shift/herd and find which
objections SURVIVE a debate. Stricter brain (phi4:14b) + the 5 most critical minds.

Run on a node with ollama:  /shared/mathenv/bin/python dev_swarm2.py
Env: FRUGAL_SWARM_MODEL (default phi4:14b), FRUGAL_OLLAMA_HOST, FRUGAL_NUM_PREDICT.
"""
from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, "/shared/frugal/src")

from frugal.eval import strip_reasoning  # noqa: E402
from frugal.providers import get_ollama  # noqa: E402

PITCH = (
    "Frugal — open-source Python toolkit making AI agents cheap, local, and verified. Meters every "
    "LLM call's cost, then cascade-routes: cheap/local model first, escalate to a strong model only "
    "when a self-consistency confidence check fails. Measured on a real cluster: a 3B model matched a "
    "14B on 83% of HARD tasks (100% easy) at ~4.7x speed and ~11x faster on GPU -> cut ~80% cost. "
    "Ships an OpenAI-compatible budget gateway with a thread-safe hard cap, offline eval asserts + RAG "
    "checks for CI, and an MCP server exposing an agent's own $/token spend. Fully offline mock provider, "
    "Apache-2.0, 22 tests, honest caveats published."
)

# the 5 hardest-to-please minds
PERSONAS = [
    ("Senior backend engineer", "a senior backend engineer, skeptical of magic; cares about correctness, thread-safety, real tests, and whether this is just a thin wrapper"),
    ("Enterprise architect", "an enterprise architect; cares about on-prem/privacy, compliance, vendor lock-in, and long-term support"),
    ("Skeptical HN commenter", "a cynical Hacker News commenter who distrusts benchmarks and asks 'isn't this just LiteLLM + a router?'"),
    ("Big-tech infra engineer", "a big-tech infra engineer; cares about scale, whether it beats existing tools, and maintenance longevity"),
    ("Startup CTO", "a startup CTO; cares about ROI, time-to-integrate, and not betting on an abandoned repo"),
]

R1 = ("React IN CHARACTER. Reply EXACTLY:\nSTAR: yes/no\nADOPT: yes/maybe/no\n"
      "CONCERN: <your single biggest concern, one line>")
R2 = ("Give your FINAL verdict after the debate. Reply EXACTLY:\nSTAR: yes/no\nADOPT: yes/maybe/no\n"
      "SURVIVES: <the one objection that still stands even if the project addresses the rest>\n"
      "FIXABLE: yes/no  (can they realistically fix it before launch?)")


def field(t, k):
    m = re.search(rf"{k}\s*:\s*(.+)", t, re.IGNORECASE)
    return m.group(1).strip() if m else ""


def main():
    host = os.environ.get("FRUGAL_OLLAMA_HOST", "http://localhost:11434")
    model = os.environ.get("FRUGAL_SWARM_MODEL", "phi4:14b")
    npr = int(os.environ.get("FRUGAL_NUM_PREDICT", "150"))
    prov = get_ollama(host=host)
    print(f"debate swarm model={model} personas={len(PERSONAS)} rounds=2\n", flush=True)

    # ---- round 1: independent ----
    r1 = {}
    for name, desc in PERSONAS:
        out = strip_reasoning(prov.complete(f"You are {desc}.\n\nProject:\n{PITCH}\n\n{R1}",
                                            model=model, num_predict=npr, temperature=0.4).text)
        r1[name] = {"star": field(out, "STAR").lower(), "adopt": field(out, "ADOPT").lower(),
                    "concern": field(out, "CONCERN")}
        print(f"[R1 {name}] STAR={r1[name]['star']} ADOPT={r1[name]['adopt']} :: {r1[name]['concern']}", flush=True)

    town_square = "\n".join(f"- {n}: {v['concern']}" for n, v in r1.items() if v["concern"])

    # ---- round 2: after seeing the crowd ----
    r2 = {}
    for name, desc in PERSONAS:
        prompt = (f"You are {desc}.\n\nProject:\n{PITCH}\n\n"
                  f"The community raised these concerns in debate:\n{town_square}\n\n{R2}")
        out = strip_reasoning(prov.complete(prompt, model=model, num_predict=npr, temperature=0.4).text)
        r2[name] = {"star": field(out, "STAR").lower(), "adopt": field(out, "ADOPT").lower(),
                    "survives": field(out, "SURVIVES"), "fixable": field(out, "FIXABLE").lower()}
        print(f"[R2 {name}] STAR={r2[name]['star']} ADOPT={r2[name]['adopt']} "
              f"SURVIVES={r2[name]['survives']} FIXABLE={r2[name]['fixable']}", flush=True)

    def stars(r): return sum(1 for v in r.values() if v["star"].startswith("y"))
    shifts = sum(1 for n in r1 if r1[n]["star"] != r2[n]["star"])
    surviving = [f"[{n}] {v['survives']} (fixable={v['fixable']})" for n, v in r2.items() if v["survives"]]

    print("\n=== DEBATE OUTCOME ===")
    print(f"STAR round1: {stars(r1)}/{len(PERSONAS)}  ->  round2: {stars(r2)}/{len(PERSONAS)}  "
          f"(minds changed: {shifts})")
    print("Surviving objections (after debate):")
    for s in surviving:
        print("  -", s)

    d = os.path.dirname(__file__)
    with open(os.path.join(d, "SWARM_DEBATE.md"), "w", encoding="utf-8") as fh:
        fh.write(f"# Frugal — 2-round debate swarm ({model}, 5 strict personas)\n\n")
        fh.write(f"_MiroFish-style: round 2 sees the crowd's concerns and revises. Caveat: LLM personas "
                 f"herd/over-polarize — objection-mining, not a forecast._\n\n")
        fh.write(f"**STAR:** round1 {stars(r1)}/5 → round2 {stars(r2)}/5 (minds changed: {shifts})\n\n")
        fh.write("## Objections that SURVIVE the debate (fix these first)\n")
        for s in surviving:
            fh.write(f"- {s}\n")
    print(f"\n✅ wrote {d}/SWARM_DEBATE.md")


if __name__ == "__main__":
    main()
