"""pytest-style assertions for LLM output — the part that grows *dependents*
(every test suite that imports it). Offline heuristics by default; pass a
`provider` to upgrade to an LLM judge.

    from frugal.eval import assert_semantic, assert_no_hallucination, assert_tone

    def test_answer():
        out = my_agent("capital of France?")
        assert_semantic(out, "Paris is the capital of France", threshold=0.5)
        assert_no_hallucination(out, context=retrieved_docs)

These are *cheap gates*, not ground truth — they catch obvious regressions in CI
without a model in the loop. Documented as heuristics on purpose.
"""
from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Iterable, List, Optional

_WORD = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> List[str]:
    return _WORD.findall(text.lower())


def semantic_similarity(a: str, b: str, provider=None) -> float:
    """0..1. Default = blend of token-Jaccard and sequence ratio (offline).
    If `provider` is given, asks it to score 0..1 (best-effort parse)."""
    if provider is not None:
        return _judge_similarity(a, b, provider)
    ta, tb = set(_tokens(a)), set(_tokens(b))
    jacc = len(ta & tb) / len(ta | tb) if (ta or tb) else 1.0
    seq = SequenceMatcher(None, a.lower(), b.lower()).ratio()
    return round(0.5 * jacc + 0.5 * seq, 4)


def _judge_similarity(a: str, b: str, provider) -> float:
    prompt = (
        "Rate how semantically equivalent these two texts are, 0.0 to 1.0. "
        "Reply with only the number.\n\nA: " + a + "\n\nB: " + b
    )
    resp = provider.complete(prompt)
    m = re.search(r"[01](?:\.\d+)?", resp.text)
    return float(m.group()) if m else 0.0


def assert_semantic(output: str, expected: str, threshold: float = 0.6, provider=None) -> float:
    score = semantic_similarity(output, expected, provider)
    if score < threshold:
        raise AssertionError(
            f"semantic similarity {score:.3f} < {threshold} "
            f"\n  output:   {output[:120]!r}\n  expected: {expected[:120]!r}"
        )
    return score


def find_unsupported(output: str, context: str) -> List[str]:
    """Return 'facts' in output (numbers + Capitalized/ALLCAPS terms) absent from context."""
    ctx = context.lower()
    facts = set(re.findall(r"\b\d[\d,.\-]*\b", output))
    facts |= set(re.findall(r"\b[A-Z][a-zA-Z]{2,}\b", output))
    unsupported = [f for f in facts if f.lower() not in ctx]
    return sorted(unsupported)


def assert_no_hallucination(output: str, context: "str | Iterable[str]") -> List[str]:
    """Heuristic groundedness gate: every number/proper-noun in `output` should
    appear somewhere in `context`. Raises listing anything unsupported."""
    if not isinstance(context, str):
        context = "\n".join(context)
    unsupported = find_unsupported(output, context)
    # allow trivial function words that slipped through the Capitalized regex at sentence start
    unsupported = [u for u in unsupported if len(u) > 2]
    if unsupported:
        raise AssertionError(f"unsupported by context (possible hallucination): {unsupported}")
    return unsupported


_TONE_LEXICON = {
    "formal": ("therefore", "regarding", "furthermore", "accordingly", "please", "kindly"),
    "friendly": ("hey", "thanks", "awesome", "happy", "glad", "sure"),
    "apologetic": ("sorry", "apolog", "unfortunately", "regret"),
    "concise": (),  # judged by length below
}


def assert_tone(output: str, tone: str) -> bool:
    tone = tone.lower()
    if tone == "concise":
        if len(output.split()) > 60:
            raise AssertionError(f"expected concise tone but got {len(output.split())} words")
        return True
    lex = _TONE_LEXICON.get(tone)
    if lex is None:
        raise ValueError(f"unknown tone {tone!r}; known: {list(_TONE_LEXICON)}")
    low = output.lower()
    if not any(w in low for w in lex):
        raise AssertionError(f"output does not read as {tone!r}: {output[:120]!r}")
    return True
