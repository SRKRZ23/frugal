"""ragcheck — offline evaluation for RAG pipelines. No LLM needed for the core
metrics, so it runs in CI on every commit.

Each example:
    {
      "query": "...",
      "retrieved": [{"id": "d1", "text": "..."}, ...],
      "gold_ids": ["d1"],           # which docs SHOULD have been retrieved
      "answer": "the model's answer",
      "citations": ["d1"]           # which retrieved ids the answer cited
    }

Metrics:
  • retrieval_hit_rate   — did we retrieve at least one gold doc?
  • faithfulness         — is the answer's content supported by retrieved text?
  • citation_coverage    — are the answer's citations valid (in retrieved set)?
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List

_WORD = re.compile(r"[a-z0-9]+")


def _tokens(text: str):
    return set(_WORD.findall(text.lower()))


def _supported(answer: str, retrieved_text: str, threshold: float = 0.35) -> float:
    a, r = _tokens(answer), _tokens(retrieved_text)
    if not a:
        return 1.0
    overlap = len(a & r) / len(a)
    return overlap


@dataclass
class RagReport:
    n: int
    retrieval_hit_rate: float
    faithfulness: float
    citation_coverage: float
    per_example: List[Dict]

    def as_dict(self) -> Dict:
        return {
            "n": self.n,
            "retrieval_hit_rate": round(self.retrieval_hit_rate, 4),
            "faithfulness": round(self.faithfulness, 4),
            "citation_coverage": round(self.citation_coverage, 4),
        }


def ragcheck(examples: List[Dict], faithfulness_threshold: float = 0.35) -> RagReport:
    hits, faiths, cites, rows = [], [], [], []
    for ex in examples:
        retrieved = ex.get("retrieved", [])
        rids = [d.get("id") for d in retrieved]
        gold = set(ex.get("gold_ids", []))
        # retrieval hit
        hit = 1.0 if (gold & set(rids)) else 0.0
        # faithfulness: answer overlap vs the union of retrieved text
        rtext = " ".join(d.get("text", "") for d in retrieved)
        support = _supported(ex.get("answer", ""), rtext)
        faith = 1.0 if support >= faithfulness_threshold else 0.0
        # citation coverage: cited ids that actually exist in retrieved
        citations = ex.get("citations", [])
        valid = [c for c in citations if c in rids]
        cov = (len(valid) / len(citations)) if citations else (1.0 if not gold else 0.0)
        hits.append(hit)
        faiths.append(faith)
        cites.append(cov)
        rows.append(
            {
                "query": ex.get("query", "")[:60],
                "hit": hit,
                "support": round(support, 3),
                "faithful": faith,
                "citation_coverage": round(cov, 3),
            }
        )
    n = len(examples) or 1
    return RagReport(
        n=len(examples),
        retrieval_hit_rate=sum(hits) / n,
        faithfulness=sum(faiths) / n,
        citation_coverage=sum(cites) / n,
        per_example=rows,
    )
