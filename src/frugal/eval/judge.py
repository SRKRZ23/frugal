"""LLM-as-judge (P3) — a real quality signal instead of crude token overlap.

Used to answer "is the cheap model's answer as good as the strong model's?" with
an actual model on your cluster, not a Jaccard heuristic. Deliberately small and
parseable; the judge model is your choice (a fast 7B is usually enough).

    from frugal.eval.judge import LLMJudge
    j = LLMJudge(provider, model="qwen2.5:7b")
    j.equivalent(question, answer_cheap, answer_strong)   # -> True/False
    j.score(question, answer)                             # -> 0..1
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_THINK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


def strip_reasoning(text: str) -> str:
    """Drop <think>…</think> traces (deepseek-r1 etc.) so we judge the final answer."""
    return _THINK.sub("", text).strip()


@dataclass
class LLMJudge:
    provider: object
    model: str = "qwen2.5:7b"
    num_predict: int = 16  # judge only needs a token or two

    def _ask(self, prompt: str) -> str:
        try:
            r = self.provider.complete(prompt, model=self.model,
                                       num_predict=self.num_predict, temperature=0.0)
            return strip_reasoning(r.text)
        except Exception:  # noqa: BLE001
            return ""

    def equivalent(self, question: str, answer_a: str, answer_b: str) -> bool:
        """Is answer_a at least as correct/complete as answer_b for the question?"""
        a, b = strip_reasoning(answer_a)[:800], strip_reasoning(answer_b)[:800]
        prompt = (
            "You are grading two answers to a question. Is Answer A at least as correct "
            "and complete as Answer B? Reply with exactly one word: YES or NO.\n\n"
            f"Question: {question}\n\nAnswer A: {a}\n\nAnswer B: {b}\n\nVerdict (YES/NO):"
        )
        out = self._ask(prompt).upper()
        return "YES" in out and "NO" not in out.split("YES")[0]

    def score(self, question: str, answer: str) -> float:
        """Rate answer quality 0..1 (parsed from a 0-10 judge score)."""
        ans = strip_reasoning(answer)[:800]
        prompt = (
            "Rate how well this answer addresses the question on a scale of 0 to 10 "
            "(10 = perfect). Reply with only the number.\n\n"
            f"Question: {question}\n\nAnswer: {ans}\n\nScore (0-10):"
        )
        m = re.search(r"\b(10|\d)(?:\.\d+)?\b", self._ask(prompt))
        return round(float(m.group()) / 10.0, 3) if m else 0.0


class JudgePanel:
    """A panel of judge models that VOTE — more robust than one lenient judge.
    Still LLM-judged (not human), but majority agreement reduces single-model bias.

        panel = JudgePanel(provider, models=["qwen2.5:7b", "phi4:14b"])
        panel.equivalent(q, cheap_answer, strong_answer)   # -> (verdict, votes)
    """

    def __init__(self, provider, models):
        self.judges = [LLMJudge(provider, model=m) for m in models]
        self.models = list(models)

    def equivalent(self, question: str, answer_a: str, answer_b: str):
        votes = []
        for j in self.judges:
            try:
                votes.append(bool(j.equivalent(question, answer_a, answer_b)))
            except Exception:  # noqa: BLE001
                votes.append(False)
        yes = sum(votes)
        return (yes * 2 >= len(votes)), votes   # majority (ties count as agreement)
