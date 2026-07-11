"""Response cache — the second cost lever besides routing. A cache hit costs $0.

Routing makes each call cheaper; caching removes calls entirely. Exact-match by
default; `normalize=True` folds whitespace/case so trivially-different prompts share
an entry. Bounded (LRU-ish ring) so it can't leak memory.

    cache = ResponseCache(normalize=True)
    r = cascade(prompt, provider, meter, cache=cache)   # 2nd identical prompt -> $0 hit
    cache.hit_rate  # -> 0.5
"""
from __future__ import annotations

import hashlib
import re
import threading
from collections import OrderedDict
from typing import Optional

from .providers.base import LLMResponse

_WS = re.compile(r"\s+")


class ResponseCache:
    def __init__(self, normalize: bool = False, max_size: int = 10_000):
        self.normalize = normalize
        self.max_size = max_size
        self._d: "OrderedDict[str, LLMResponse]" = OrderedDict()
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0

    def key(self, prompt: str, model: Optional[str] = None) -> str:
        p = prompt
        if self.normalize:
            p = _WS.sub(" ", prompt.strip().lower())
        # surrogatepass: lone surrogates (from bad decoding / hostile input) must not crash keying
        return hashlib.sha1(((model or "") + "\x00" + p).encode("utf-8", "surrogatepass")).hexdigest()

    def get(self, prompt: str, model: Optional[str] = None) -> Optional[LLMResponse]:
        k = self.key(prompt, model)
        with self._lock:
            r = self._d.get(k)
            if r is not None:
                self._d.move_to_end(k)   # LRU touch
                self.hits += 1
                return r
            self.misses += 1
            return None

    def put(self, prompt: str, response: LLMResponse, model: Optional[str] = None) -> None:
        k = self.key(prompt, model)
        with self._lock:
            self._d[k] = response
            self._d.move_to_end(k)
            while len(self._d) > self.max_size:
                self._d.popitem(last=False)  # evict oldest

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return round(self.hits / total, 4) if total else 0.0

    def stats(self) -> dict:
        return {"entries": len(self._d), "hits": self.hits, "misses": self.misses,
                "hit_rate": self.hit_rate}
