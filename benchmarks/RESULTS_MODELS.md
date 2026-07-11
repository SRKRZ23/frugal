# Frugal cross-model benchmark

_Measured 2026-07-11 17:58 on **carlito4** (real Ollama models, CPU inference). Judge: qwen2.5:7b. Reference: phi4:14b._

| model | p50 s | p95 s | tok/s | avg out tok | judge quality 0-1 | retention vs ref |
|---|---|---|---|---|---|---|
| qwen2.5-coder:3b | 12.71 | 27.57 | 6.5 | 113.2 | 0.8 | 5/5 (100%) |
| qwen2.5:7b | 20.17 | 59.42 | 3.2 | 112 | 0.82 | 5/5 (100%) |
| deepseek-r1:7b | 59.25 | 70.93 | 3.6 | 220 | 0.64 | 5/5 (100%) |
| phi4:14b | 60.13 | 116.75 | 1.5 | 129.2 | 0.86 | ref |
| deepseek-r1:14b | 113.78 | 115.24 | 1.8 | 205 | 0.8 | 5/5 (100%) |

**Routing takeaway:** best judged quality = 0.860; models within 10% of it: ['qwen2.5-coder:3b', 'qwen2.5:7b', 'phi4:14b', 'deepseek-r1:14b']. Cheapest of those = **qwen2.5-coder:3b** (~4.7× faster p50 than the reference phi4:14b) — route there first, escalate only when confidence is low.
