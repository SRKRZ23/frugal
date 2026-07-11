# Running Frugal against a cluster (models off-box)

Frugal is the thin control layer; the GPUs live on your cluster. You never run a
model on the machine that runs Frugal — you point it at cluster endpoints.

## 1. Bring up models on the cluster

**Frontier / cloud tier** — any OpenAI-compatible server. On an AMD MI300X node:

```bash
# on the GPU node (see src/frugal/local/amd_quickstart.sh)
docker run --rm -it --device /dev/kfd --device /dev/dri --group-add video --ipc host \
  -p 8000:8000 rocm/vllm:latest \
  --model meta-llama/Llama-3.1-70B-Instruct --dtype float16
# -> OpenAI-compatible at http://<gpu-node>:8000/v1
```

**Local / cheap tier** — Ollama on a CPU/small-GPU node:

```bash
# on the cheap node
OLLAMA_HOST=0.0.0.0:11434 ollama serve
ollama pull llama3
# -> http://<cpu-node>:11434
```

## 2. Point Frugal at them (env only — no code changes)

```bash
export FRUGAL_CLOUD_BASE_URL="http://gpu-node-0.cluster:8000/v1"
export FRUGAL_CLOUD_MODEL="meta-llama/Llama-3.1-70B-Instruct"
export FRUGAL_CLOUD_API_KEY="x"                 # vLLM ignores it, but the SDK wants one
export FRUGAL_LOCAL_BASE_URL="http://cpu-node-3.cluster:11434"
export FRUGAL_LOCAL_MODEL="llama3"
export FRUGAL_BUDGET_USD="5.00"
```

```python
from frugal.config import providers_from_env
from frugal import Meter, cascade

local, cloud, cfg = providers_from_env()   # real cluster providers
meter = Meter(budget_usd=cfg.budget_usd)
# route cheap(local) -> frontier(cloud), escalating only when needed:
r = cascade("refactor this module", cloud or local, meter)
```

The **same** script, with none of these env vars set, runs fully offline on the
deterministic MockProvider. That's the point: develop/CI on mock, deploy on cluster.

## 3. Prove real-model value on the cluster

The offline benchmarks (`benchmarks/`) measure the **cost math and routing logic**
exactly. To measure **real-model quality retention** (does the cheap tier's answer
actually hold up so escalation was unnecessary?), run the cluster harness:

```bash
python benchmarks/bench_cluster.py     # needs the FRUGAL_* env vars above
```

It records real latency, real token usage, real $ (from your price table), and a
quality-retention check comparing cheap-tier vs frontier-tier answers on a labelled
set. Without the env vars it prints a clear "cluster not configured" and skips —
it never fabricates numbers.

## Pricing

Edit `src/frugal/meter/pricing.py` (or call `register_price(model, in, out)`) so the
dollar figures match your account / your amortized on-prem cost per 1M tokens. Local
models default to `$0` per token (you paid for the hardware).
