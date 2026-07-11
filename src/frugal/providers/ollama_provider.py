"""Optional local Ollama backend (http://localhost:11434). Uses only urllib —
no extra dependency. Enables the local<->cloud routing story in frugal.local.
"""
from __future__ import annotations

import json
import urllib.request

from .base import LLMResponse, count_tokens


class OllamaProvider:
    name = "ollama"

    def __init__(self, model: str = "llama3", host: str = "http://localhost:11434"):
        self._default_model = model
        self._host = host.rstrip("/")

    def complete(self, prompt: str, model: str | None = None, **kwargs) -> LLMResponse:
        model = model or self._default_model
        body = {"model": model, "prompt": prompt, "stream": False}
        options = dict(kwargs.get("options", {}))
        if "num_predict" in kwargs:      # cap output length (keeps CPU/reasoning models bounded)
            options["num_predict"] = kwargs["num_predict"]
        if "temperature" in kwargs:
            options["temperature"] = kwargs["temperature"]
        if options:
            body["options"] = options
        payload = json.dumps(body).encode()
        req = urllib.request.Request(
            f"{self._host}/api/generate", data=payload, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=kwargs.get("timeout", 600)) as r:  # noqa: S310
            data = json.loads(r.read())
        text = data.get("response", "")
        in_tok = data.get("prompt_eval_count") or count_tokens(prompt)
        out_tok = data.get("eval_count") or count_tokens(text)
        return LLMResponse(text=text, input_tokens=in_tok, output_tokens=out_tok, model=model)
