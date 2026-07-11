"""Developer-persona swarm (MiroFish-style) — spin up a crowd of distinct developer
'minds', have each react to Frugal's pitch, then aggregate the collective opinion:
who'd star it, who'd adopt, the shared concerns, and the objections to fix before launch.

This is the MiroFish idea (a swarm of persona-agents -> emergent collective read)
applied to one question: 'would developers & enterprises adopt Frugal?'. Real models
on the cluster. Same honest caveat MiroFish itself notes: LLM personas over-polarize
and herd, so treat this as idea-generation / objection-mining, NOT a real forecast.

Run on a node with ollama:  /shared/mathenv/bin/python dev_swarm.py
Env: FRUGAL_SWARM_MODEL (default qwen2.5:7b), FRUGAL_OLLAMA_HOST (default localhost).
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
    "Frugal — an open-source Python toolkit that makes AI agents cheap, local, and verified. "
    "It meters every LLM call's cost, then cascade-routes: a cheap/local model first, escalating "
    "to a strong model only when a real confidence check (self-consistency) fails. Measured on a "
    "real cluster: a 3B model matched a 14B model on 83% of HARD tasks (100% of easy ones) at ~4.7x "
    "the speed -> route down, cut ~80% of cost. Also ships an OpenAI-compatible budget gateway with a "
    "thread-safe hard spend cap, offline eval asserts + RAG checks for CI, and an MCP server that lets "
    "an agent read its own $/token spend. Runs fully offline on a mock provider (no API keys). "
    "Apache-2.0, 22 tests, honest caveats published."
)

PERSONAS = [
    ("Indie hacker", "a solo indie developer who ships side-projects on a tiny budget and hates complexity"),
    ("Vibecoder", "a 'vibecoder' who builds by prompting AI, wants things that work out-of-the-box with a cool demo and near-zero setup"),
    ("Senior backend engineer", "a senior backend engineer who is skeptical of magic, cares about correctness, thread-safety, and real tests"),
    ("Enterprise architect", "an enterprise architect who cares about on-prem/private deployment, compliance, vendor lock-in, and support"),
    ("DevOps / SRE", "a DevOps/SRE who cares about observability, hard budget caps, reliability under concurrency, and ops burden"),
    ("Skeptical HN commenter", "a cynical Hacker News commenter who asks 'isn't this just a wrapper around LiteLLM?' and distrusts benchmarks"),
    ("Big-tech infra engineer", "an infra engineer at a big tech company who cares about scale, whether it beats existing tools, and why they'd adopt it"),
    ("Startup CTO", "a startup CTO who cares about cost-savings ROI, time-to-integrate, and not betting on an abandoned repo"),
]

FMT = (
    "React honestly IN CHARACTER. Reply in EXACTLY this format, one item per line:\n"
    "STAR: yes or no\nADOPT: yes or maybe or no\nCONCERN: <your single biggest concern, one line>\n"
    "WIN: <one thing that would make you adopt or star it>\nQUOTE: <one sentence you'd actually post>"
)


def ask(prov, model, persona_desc):
    prompt = f"You are {persona_desc}.\n\nA new open-source project:\n{PITCH}\n\n{FMT}"
    r = prov.complete(prompt, model=model, num_predict=220, temperature=0.4)
    return strip_reasoning(r.text)


def field(text, key):
    m = re.search(rf"{key}\s*:\s*(.+)", text, re.IGNORECASE)
    return m.group(1).strip() if m else ""


def main():
    host = os.environ.get("FRUGAL_OLLAMA_HOST", "http://localhost:11434")
    model = os.environ.get("FRUGAL_SWARM_MODEL", "qwen2.5:7b")
    prov = get_ollama(host=host)
    print(f"swarm model={model} host={host}  personas={len(PERSONAS)}\n", flush=True)

    stars = adopts = 0
    concerns, wins, quotes = [], [], []
    for name, desc in PERSONAS:
        try:
            out = ask(prov, model, desc)
        except Exception as e:  # noqa: BLE001
            print(f"[{name}] FAILED: {e}", flush=True)
            continue
        star = field(out, "STAR").lower()
        adopt = field(out, "ADOPT").lower()
        c, w, q = field(out, "CONCERN"), field(out, "WIN"), field(out, "QUOTE")
        if star.startswith("y"): stars += 1
        if adopt.startswith("y") or adopt.startswith("m"): adopts += 1
        if c: concerns.append(f"[{name}] {c}")
        if w: wins.append(f"[{name}] {w}")
        if q: quotes.append(f"[{name}] {q}")
        print(f"[{name}] STAR={star} ADOPT={adopt}\n   concern: {c}\n   win: {w}\n   quote: {q}\n", flush=True)

    n = len(PERSONAS)
    print("=== COLLECTIVE READ ===")
    print(f"would STAR: {stars}/{n} ({round(100*stars/n)}%)")
    print(f"would ADOPT (yes/maybe): {adopts}/{n} ({round(100*adopts/n)}%)")
    print("\nTop concerns to fix before launch:")
    for c in concerns:
        print("  -", c)
    print("\nWhat would win them:")
    for w in wins:
        print("  -", w)

    d = os.path.dirname(__file__)
    with open(os.path.join(d, "SWARM_OPINIONS.md"), "w", encoding="utf-8") as fh:
        fh.write(f"# Frugal — developer-persona swarm opinions (MiroFish-style)\n\n")
        fh.write(f"_Persona brain: {model}. {n} personas. Caveat: LLM personas over-polarize/herd — "
                 f"objection-mining, not a forecast._\n\n")
        fh.write(f"**Would star:** {stars}/{n} ({round(100*stars/n)}%)  ·  "
                 f"**Would adopt (yes/maybe):** {adopts}/{n} ({round(100*adopts/n)}%)\n\n")
        fh.write("## Concerns to fix\n" + "\n".join(f"- {c}" for c in concerns) + "\n\n")
        fh.write("## What would win them\n" + "\n".join(f"- {w}" for w in wins) + "\n\n")
        fh.write("## Quotes\n" + "\n".join(f"- {q}" for q in quotes) + "\n")
    print(f"\n✅ wrote {d}/SWARM_OPINIONS.md")


if __name__ == "__main__":
    main()
