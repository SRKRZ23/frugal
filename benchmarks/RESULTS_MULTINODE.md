# Frugal multi-node routing (2026-07-11 14:07, orchestrated from macbook)

node A (cheap): qwen2.5:3b @ http://localhost:11434  ·  node B (strong): qwen2.5:7b @ http://localhost:11435

| metric | value |
|---|---|
| prompts | 8 |
| routed_local_nodeA | 7 |
| routed_cloud_nodeB | 1 |
| local_share_pct | 87.5 |
| private_prompts | 2 |
| private_leaked_to_nodeB | 0 |
| nodeA_latency_p50_s | 0.53 |
| nodeB_latency_p50_s | 50.49 |
| speedup_local_vs_cloud | 95.8 |
