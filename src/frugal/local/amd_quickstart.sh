#!/usr/bin/env bash
# frugal local: one-command vLLM serving on AMD ROCm (MI300X / Radeon).
# Brings up an OpenAI-compatible endpoint you can point Frugal's OpenAIProvider at:
#   provider = frugal.providers.get_openai(base_url="http://localhost:8000/v1", api_key="x")
#
# Usage:  MODEL=meta-llama/Llama-3.1-8B-Instruct ./amd_quickstart.sh
set -euo pipefail

MODEL="${MODEL:-meta-llama/Llama-3.1-8B-Instruct}"
PORT="${PORT:-8000}"
IMAGE="${IMAGE:-rocm/vllm:latest}"   # AMD's ROCm+vLLM image

echo "▶ Frugal AMD quickstart"
echo "  model : $MODEL"
echo "  port  : $PORT   (OpenAI-compatible /v1)"
echo "  image : $IMAGE"

if ! command -v docker >/dev/null 2>&1; then
  echo "✗ docker not found. Install Docker + ROCm drivers first (see README)." >&2
  exit 1
fi

exec docker run --rm -it \
  --device /dev/kfd --device /dev/dri \
  --group-add video --ipc host \
  -p "${PORT}:8000" \
  "$IMAGE" \
  --model "$MODEL" \
  --dtype float16
