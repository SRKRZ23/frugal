import sys, os, time, statistics
sys.path.insert(0, '/shared/frugal/src')
from frugal.providers import get_ollama
M = "qwen2.5-coder:3b"
prov = get_ollama(host='http://127.0.0.1:11434')
prompts = ["say hello","what is 2+2?","capital of France?","list three fruits","spell banana","define apple"]
prov.complete("hi", model=M, num_predict=16)  # warm (loads to GPU)
lat, tok = [], []
for p in prompts:
    t=time.perf_counter(); r=prov.complete(p, model=M, num_predict=140, temperature=0.0); dt=time.perf_counter()-t
    lat.append(dt); tok.append(r.output_tokens)
    print(f"  {dt:5.2f}s  {r.output_tokens}tok :: {p}")
print(f"GPU {M}: p50={statistics.median(lat):.2f}s  p95={sorted(lat)[-1]:.2f}s  tok/s={sum(tok)/sum(lat):.1f}")
