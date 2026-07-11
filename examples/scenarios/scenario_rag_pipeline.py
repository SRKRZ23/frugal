"""Scenario: a RAG pipeline that fails the build when retrieval or grounding breaks.

Value proven: frugal.rag turns 'the RAG got worse' into a measurable, gate-able
number — retrieval hit-rate, faithfulness, citation coverage — offline, in CI.

    python examples/scenarios/scenario_rag_pipeline.py
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from frugal.rag import ragcheck

# a healthy RAG run vs a regressed one (bad retrieval + uncited answer)
healthy = [
    {"query": "capital of France?",
     "retrieved": [{"id": "d1", "text": "Paris is the capital of France."}],
     "gold_ids": ["d1"], "answer": "Paris is the capital of France.", "citations": ["d1"]},
    {"query": "who wrote Hamlet?",
     "retrieved": [{"id": "d2", "text": "Hamlet was written by William Shakespeare."}],
     "gold_ids": ["d2"], "answer": "William Shakespeare wrote Hamlet.", "citations": ["d2"]},
]
regressed = [
    {"query": "capital of France?",
     "retrieved": [{"id": "d9", "text": "Penguins are flightless birds."}],   # wrong doc
     "gold_ids": ["d1"], "answer": "Paris.", "citations": []},                 # uncited
]

MIN_HIT, MIN_FAITH = 0.9, 0.9

def gate(name, examples):
    r = ragcheck(examples).as_dict()
    ok = r["retrieval_hit_rate"] >= MIN_HIT and r["faithfulness"] >= MIN_FAITH
    print(f"{name:10s} {r}  -> {'PASS ✅' if ok else 'FAIL ❌ (build should block)'}")
    return ok

print("RAG quality gate (min hit/faith = 0.9):")
gate("healthy", healthy)
gate("regressed", regressed)
