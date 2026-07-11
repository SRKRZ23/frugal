"""Optional OpenAI-compatible backend. Import stays cheap; the SDK is only
touched when you actually construct/use it, so the rest of Frugal never needs it.

Works with any OpenAI-compatible endpoint (OpenAI, vLLM, Together, Fireworks,
local llama.cpp servers) via base_url.
"""
from __future__ import annotations

from .base import LLMResponse, count_tokens


class OpenAIProvider:
    name = "openai"

    def __init__(self, model: str = "gpt-4o-mini", base_url: str | None = None, api_key: str | None = None):
        try:
            from openai import OpenAI  # noqa: WPS433
        except ImportError as e:  # pragma: no cover - env dependent
            raise ImportError("Install extras:  pip install 'frugal[openai]'") from e
        self._default_model = model
        self._client = OpenAI(base_url=base_url, api_key=api_key)

    def complete(self, prompt: str, model: str | None = None, **kwargs) -> LLMResponse:
        model = model or self._default_model
        kwargs.setdefault("logprobs", True)   # near-free confidence signal
        resp = self._client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            **kwargs,
        )
        choice = resp.choices[0]
        text = choice.message.content or ""
        usage = getattr(resp, "usage", None)
        in_tok = getattr(usage, "prompt_tokens", None) or count_tokens(prompt)
        out_tok = getattr(usage, "completion_tokens", None) or count_tokens(text)
        avg_lp = None
        try:  # pragma: no cover - shape depends on the endpoint
            toks = choice.logprobs.content
            lps = [t.logprob for t in toks if t.logprob is not None]
            avg_lp = sum(lps) / len(lps) if lps else None
        except Exception:  # noqa: BLE001
            avg_lp = None
        return LLMResponse(text=text, input_tokens=in_tok, output_tokens=out_tok,
                           model=model, avg_logprob=avg_lp)
