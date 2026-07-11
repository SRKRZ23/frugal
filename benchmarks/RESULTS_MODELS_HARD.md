# Frugal cross-model benchmark

_Measured 2026-07-11 18:59 on **carlito4** (real Ollama models, CPU inference). Judge: qwen2.5:7b. Reference: phi4:14b._

| model | p50 s | p95 s | tok/s | avg out tok | judge quality 0-1 | retention vs ref |
|---|---|---|---|---|---|---|
| qwen2.5-coder:3b | 34.12 | 58.83 | 6.6 | 224 | 0.733 | 5/6 (83%) |
| qwen2.5:7b | 88.96 | 90.41 | 3.3 | 271 | 0.75 | 5/6 (83%) |
| phi4:14b | 149.79 | 211.42 | 1.7 | 242 | 0.75 | ref |

**Routing takeaway:** best judged quality = 0.750; models within 10% of it: ['qwen2.5-coder:3b', 'qwen2.5:7b', 'phi4:14b']. Cheapest of those = **qwen2.5-coder:3b** (~4.4× faster p50 than the reference phi4:14b) — route there first, escalate only when confidence is low.
