#!/bin/bash
pkill -9 -f k135_thermal 2>/dev/null
pkill -9 -f rckangaroo 2>/dev/null
sleep 5
echo "loop=$(ps -eo args | grep -c '[k]135_thermal')"
echo "miner=$(pgrep -c rckangaroo)"
nvidia-smi --query-gpu=memory.used,utilization.gpu,temperature.gpu --format=csv,noheader
