#!/bin/bash
export OLLAMA_HOST=127.0.0.1:11434
export OLLAMA_MODELS=/shared/ollama_shared
pkill -9 -f "ollama serve" 2>/dev/null; sleep 2
nohup /shared/bin/ollama serve > /tmp/ollama_c20.log 2>&1 &
sleep 8
echo "--- models ---"; /shared/bin/ollama list
echo "--- GPU latency benchmark ---"; /shared/mathenv/bin/python /shared/frugal/bench_gpu/gpu_latency.py
echo "--- GPU offload proof (log) ---"; grep -iE "offloaded|layers|CUDA0" /tmp/ollama_c20.log | tail -3
echo "--- gpu state ---"; nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader
