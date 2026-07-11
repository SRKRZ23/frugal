#!/bin/bash
pkill -9 -f ollama 2>/dev/null
sleep 4
echo "ollama_procs=$(pgrep -c ollama)"
echo "loop=$(ps -eo args | grep -c '[k]135_thermal')"
echo "miner=$(pgrep -c rckangaroo)"
nvidia-smi --query-gpu=memory.used,utilization.gpu,temperature.gpu --format=csv,noheader
