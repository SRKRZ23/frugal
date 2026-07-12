# Frugal cross-model benchmark

_Measured 2026-07-13 02:07 on **carlito4** (real Ollama models, CPU inference). Judge: qwen2.5:7b. Reference: phi4:14b._

| model | p50 s | p95 s | tok/s | avg out tok | judge quality 0-1 | retention vs ref |
|---|---|---|---|---|---|---|
| qwen2.5:7b | 62.29 | 76.55 | 3.1 | 190.8 | 0.75 | 5/6 (83%) |
| phi4:14b | 122.78 | 162.29 | 1.6 | 191.5 | 0.767 | ref |

**Routing takeaway:** best judged quality = 0.767; models within 10% of it: ['qwen2.5:7b', 'phi4:14b']. Cheapest of those = **qwen2.5:7b** (~2.0× faster p50 than the reference phi4:14b) — route there first, escalate only when confidence is low.
