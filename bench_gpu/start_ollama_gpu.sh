#!/bin/bash
# userspace ollama on GPU. Check whether CUDA runners exist; report GPU offload.
export OLLAMA_HOST=127.0.0.1:11434
export OLLAMA_MODELS=$HOME/.ollama/models
pkill -9 -f "ollama serve" 2>/dev/null; sleep 1
echo "--- runner libs on master copied? check /shared/lib/ollama ---"
ls /shared/lib/ollama 2>/dev/null | head -3 || echo "(no shared runner libs)"
nohup /shared/bin/ollama serve > /tmp/ollama_c20.log 2>&1 &
sleep 8
echo "--- serve log (GPU detection) ---"
grep -iE "gpu|cuda|library|inference compute|no compatible" /tmp/ollama_c20.log | head -8
echo "--- pull qwen2.5:3b ---"
/shared/bin/ollama pull qwen2.5:3b 2>&1 | tail -2
/shared/bin/ollama list 2>/dev/null
