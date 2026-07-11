# Frugal

**🇬🇧 English · [🇷🇺 Русский](README.ru.md)**

[![CI](https://github.com/SRKRZ23/frugal/actions/workflows/ci.yml/badge.svg)](https://github.com/SRKRZ23/frugal/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9%E2%80%933.12-blue.svg)](pyproject.toml)
![Tests](https://img.shields.io/badge/tests-56%20passing-brightgreen.svg)
![Deps](https://img.shields.io/badge/runtime%20deps-0-brightgreen.svg)

**Run AI agents cheap, local, and verified.**

Frugal is a drop-in ops layer for LLM apps and agents. It makes any workload:

- 💸 **cheaper** — meter every call, cascade-route cheap→frontier, enforce a hard budget
- 🏠 **local** — route private/simple work to on-device models (Ollama / vLLM / AMD ROCm)
- ✅ **verified** — offline semantic asserts, drift detection, and RAG checks for CI
- 🔎 **self-aware** — an MCP server that lets the agent read its own `$/token` spend

One package, nine modules, **zero API keys required** — everything runs offline out of the
box on a deterministic mock provider, so you can try it, test it, and demo it immediately.

```bash
pip install -e .
frugal demo          # end-to-end showcase, fully offline
```

## Why

Agentic AI sends the bill soaring — every token has a price, and most agents burn frontier
tokens on trivial work, leak private prompts to the cloud, and fail *silently* at the
semantic level. Frugal is the thin layer that fixes all four in one place, built around a
single shared cost **Meter**.

## Watch the bill

```text
  FRUGAL — live cost   (gpt-4o-mini cheap → gpt-4o escalate, real prices)

  requests processed :  2400
  frontier-only      : $ 10.2000  ██████████████████████████████████
  frugal             : $  0.8262  ██
  saved  91.9%  ($9.3738 kept in your pocket)
```

`python examples/live_cost_demo.py` (animated) or `--cast` to make an
[asciinema](https://asciinema.org) recording (`examples/demo.cast`). Real prices;
the exact savings depend on your workload and confidence signal — see [BUSINESS_CASE.md](BUSINESS_CASE.md).

## Verify it yourself in 10 seconds

Don't trust the numbers — reproduce them. No API keys needed:

```bash
pip install -e . && frugal demo        # end-to-end, offline, ~2s
python benchmarks/run_all.py           # the offline benchmark table
python benchmarks/stress_test.py       # 8 dims: thread-safety, ReDoS, fuzz, memory
python benchmarks/stress_deep.py       # 6 adversarial dims: hostile inputs, races (diamond)
python benchmarks/cost_model.py        # real-price savings math (see BUSINESS_CASE.md)
```

Have models on a cluster/Ollama? Re-run the exact model comparison on **your** models and
dispute it: `FRUGAL_MODELS=... python benchmarks/bench_models.py`. Every claim here is one
command away from being checked. (See [WEAKNESSES.md](WEAKNESSES.md) for what the numbers do
and don't prove.)

## Modules

| Module | What it does | Import |
|---|---|---|
| `frugal.meter` | per-call cost/token/latency accounting + budget guard | `from frugal import Meter` |
| `frugal.route` | cascade routing: cheap model first, escalate only when needed | `from frugal import cascade` |
| `frugal.local` | route local↔cloud by cost/privacy/complexity; AMD quickstart | `from frugal.local import LocalRouter` |
| `frugal.eval` | `assert_semantic` / `assert_no_hallucination` / `assert_tone` + drift | `from frugal.eval import assert_semantic` |
| `frugal.rag` | `ragcheck`: retrieval hit-rate, faithfulness, citation coverage | `from frugal.rag import ragcheck` |
| `frugal.mcp` | MCP server exposing live cost telemetry + PII/injection guard | `from frugal.mcp import FrugalMCP` |
| `frugal.gateway` | OpenAI-compatible proxy: meter + budget + route (`[gateway]`) | `from frugal.gateway import create_app` |
| `frugal.cache` | response cache — the second cost lever; a hit costs $0 | `from frugal import ResponseCache` |
| `frugal.economics` | warns when a cheap/frontier pair can't cover the routing overhead | `from frugal.economics import routing_savings` |

## Quickstart

```python
from frugal import Meter, MockProvider, cascade
from frugal.eval import assert_semantic
from frugal.mcp import FrugalMCP

provider = MockProvider()          # swap for get_openai(...) / get_ollama(...)
meter = Meter(budget_usd=0.50)

r = cascade("say hi", provider, meter)          # -> stays on the cheap model
r = cascade("prove this design, step by step", provider, meter)  # -> escalates

assert_semantic("Paris is the capital", "The capital is Paris", threshold=0.4)
print(FrugalMCP(meter).call("get_cost_summary"))
```

## CLI

```bash
frugal demo                     # offline end-to-end showcase
frugal route "explain this bug" # cascade-route one prompt, print cost
frugal rag check examples/rag_example.json
frugal mcp                      # list the MCP cost-telemetry tools
frugal gateway --budget 5.00    # OpenAI-compatible budget gateway  (needs frugal[gateway])
```

## Real providers

```python
from frugal.providers import get_openai, get_ollama
cloud = get_openai(base_url="https://api.openai.com/v1")   # or any OpenAI-compatible endpoint
local = get_ollama(model="llama3")                         # http://localhost:11434
```

Serve a local model on **AMD ROCm** (MI300X / Radeon) in one command:

```bash
MODEL=meta-llama/Llama-3.1-8B-Instruct src/frugal/local/amd_quickstart.sh
# -> OpenAI-compatible endpoint at http://localhost:8000/v1
```

## Tests

```bash
pip install -e '.[dev]'
pytest -q
```

## Benchmarks (measured)

Every number is produced by running the code on a labelled synthetic workload —
reproduce with `python benchmarks/run_all.py` (writes [`benchmarks/RESULTS.md`](benchmarks/RESULTS.md)).

| What | Result | Notes |
|---|---|---|
| **Cost saved by routing** vs frontier-only | **−92.1%** on a 26-prompt mix (⚠️ **demo prices**) | exact cost math on the mock price table. **Real-price savings are ~75–91% (cloud) / up to ~97% (local)** — and it can even *lose* money on small price gaps. Full honest numbers: [BUSINESS_CASE.md](BUSINESS_CASE.md) |
| **Private-prompt leaks** to cloud | **0 / 6** | privacy invariant: `private`-tagged prompts always stay local |
| Local share of a mixed workload | **96.2%** kept off the paid tier | complexity heuristic favours the cheap tier (tunable) |
| Hallucination-flag precision / recall | **1.0 / 1.0** on the labelled set | heuristic gate; small set |
| PII + injection guard | **F1 1.0** | 10-sample labelled set |
| RAG gate accuracy vs label | **1.0** (5 ex) | aggregate hit/faith 0.6 reflects the 2 planted bad cases |
| Metering overhead | **~0.005 ms/call** (~185k calls/s; varies with load) | negligible next to any network call |

> **Honest scope:** these prove the **cost arithmetic, routing/escalation logic,
> privacy safety, guard accuracy, and overhead** — exactly, offline. They do **not**
> prove real-model *answer quality* (the mock's text is synthetic). For quality
> retention on real models, run [`benchmarks/bench_cluster.py`](benchmarks/bench_cluster.py)
> against your cluster.

### Real-model results (measured on a real cluster node)

Run on a **cluster node** (carlito4, an i7-8700 CPU node in a 12-node Tailscale fleet)
via `benchmarks/bench_cluster.py`, using that node's own Ollama models —
**`qwen2.5-coder:3b` (cheap) + `qwen2.5:7b` (strong)**, CPU inference, self-consistency
confidence, 6 prompts. Single-run, real numbers (model sampling is nondeterministic):

| metric | value |
|---|---|
| cheap-tier latency p50 / p95 | **1.56s / 13.1s** |
| strong-tier latency p50 / p95 | **3.70s / 69.1s** (7B on CPU — the tail is why you don't send easy work here) |
| cheap≈strong agreement | **4 / 6 (67%)** — with a capable cheap model, most answers already match the strong one |
| escalations (self-consistency) | **2 / 6** — only the uncertain prompts escalate |
| local token cost | **$0** (on-prem); modelled cloud ≈ $55 / 1M requests at $0.90/1M |

Earlier laptop stand-in run (`qwen2.5:0.5b` + `qwen2.5:3b`) showed the **confidence-signal
finding** starkly: **hedging** confidence escalated **0/12** (real models don't self-hedge —
useless signal), while **self-consistency** escalated **9/12**.

**Finding (honest):** the routing *mechanism* works; the *confidence signal* decides
quality. Default hedging-word confidence is fine for demos but inadequate on real models —
use `frugal.route.make_self_consistency(...)` (or logprobs / a verifier). A bigger cheap
model raises the cheap≈strong rate (17% with 0.5b → 67% with 3b-coder), so more traffic
safely stays cheap. This is what the benchmark surfaces instead of hiding.

### Cross-model comparison (real cluster, LLM-judged)

`benchmarks/bench_models.py` on cluster node **carlito4** — five real Ollama models,
CPU inference, quality graded by an **LLM judge** (`qwen2.5:7b`) against reference
`phi4:14b` (5 prompts, `num_predict=220`):

| model | p50 s | p95 s | tok/s | judge quality 0-1 | as-good-as 14B ref |
|---|---|---|---|---|---|
| **qwen2.5-coder:3b** | **12.7** | 27.6 | 6.5 | 0.80 | **5/5** |
| qwen2.5:7b | 20.2 | 59.4 | 3.2 | 0.82 | 5/5 |
| deepseek-r1:7b | 59.3 | 70.9 | 3.6 | 0.64 | 5/5 |
| phi4:14b (ref) | 60.1 | 116.8 | 1.5 | 0.86 | — |
| deepseek-r1:14b | 113.8 | 115.2 | 1.8 | 0.80 | 5/5 |

**What this proves (real numbers):**
1. **The cheap tier is enough here.** `qwen2.5-coder:3b` is **~4.7× faster** than `phi4:14b`
   and the judge rated its answers *as good as* the 14B on **5/5** prompts — so routing there
   first and escalating rarely cuts latency/cost ~80% at ~no quality loss on this workload.
2. **Reasoning models are a bad default for simple work.** `deepseek-r1:7b` scored the
   *lowest* quality (0.64) while emitting the *most* tokens (verbose `<think>`), and
   `deepseek-r1:14b` was the slowest (113s) with no quality gain — exactly the "token tsunami"
   Frugal exists to route around.
3. **Honest caveats:** N=5, relatively easy prompts → retention saturates at 100%; the 7B
   judge is lenient; CPU-only (GPU nodes were busy mining). Reproduce: `FRUGAL_MODELS=...
   FRUGAL_BENCH_N=... python benchmarks/bench_models.py`.

#### Harder prompts break the 100% saturation

Re-run on a **hard** set (coding with edge cases, multi-step reasoning, long-context
retrieval — `benchmarks/data_hard.py`, `FRUGAL_PROMPTSET=hard`, N=6):

| model | p50 s | judge quality 0-1 | as-good-as 14B ref |
|---|---|---|---|
| qwen2.5-coder:3b | 34.1 | 0.733 | **5/6 (83%)** |
| qwen2.5:7b | 89.0 | 0.75 | 5/6 (83%) |
| phi4:14b (ref) | 149.8 | 0.75 | — |

On hard tasks the cheap tier's retention drops from **100% → 83%**: it genuinely fails ~1
prompt in 6, which is **exactly the traffic escalation should catch**. It's still 4.4× faster
and good enough on 83% — so the routing thesis holds *and* now has a measured escalation
rate instead of a saturated 100%.

### GPU vs CPU for the cheap tier (real GTX 1650)

Ran `qwen2.5-coder:3b` on a **GTX 1650 (4GB)** GPU node (`benchmarks/bench_gpu/`), CUDA
confirmed (partial offload — a 3B model doesn't fully fit 4GB):

| cheap tier `coder:3b` | p50 | tok/s |
|---|---|---|
| CPU (i7-8700, carlito4) | 12.7s | 6.5 |
| **GPU (GTX 1650, carlito20)** | **1.13s** | 11.5 |

**~11× faster on a modest GPU.** That's the routing thesis's punchline: on any GPU the
cheap tier is near-instant, so you route almost everything to it and escalate the ~17% of
hard prompts a real confidence check flags. (A bigger card than a 4GB 1650 would fit the
model fully and go faster still.)

### Live bake-off vs a plain proxy

`benchmarks/compare_litellm_live.py` on the cluster — same models (`qwen2.5-coder:3b` /
`qwen2.5:7b`), same 12 prompts. A proxy (LiteLLM-style) sends every prompt to the strong
model; Frugal routes by complexity:

| metric | proxy (all→strong) | Frugal (routed) | Frugal saves |
|---|---|---|---|
| strong-model calls | 12 | **6** | half |
| total latency | 373.9s | 252.3s | **−32.5%** |
| modelled cost (cloud prices) | $0.01568 | $0.00723 | **−53.9%** |

Honest caveats: the baseline is a proxy pass-through (the `litellm` package wouldn't finish
installing on the CPU-starved node — the behaviour is identical); a cloud-key run needs your
keys. Also `benchmarks/bench_broad.py` adds a **judge panel** (multiple models vote) over a
categorized set — on a small model gap (3B↔7B) retention saturates at 100%; still LLM-judged,
not human.

## Running on a cluster (models off-box)

Frugal is the control layer; the GPUs live on your cluster. Point it there with env
vars — no code changes — and the same script that runs offline on the mock now drives
real Ollama / vLLM endpoints. See [`docs/CLUSTER.md`](docs/CLUSTER.md).

```bash
export FRUGAL_LOCAL_BASE_URL=http://cpu-node:11434   FRUGAL_LOCAL_MODEL=llama3
export FRUGAL_CLOUD_BASE_URL=http://gpu-node:8000/v1 FRUGAL_CLOUD_MODEL=Llama-3.1-70B-Instruct
python benchmarks/bench_cluster.py   # real latency, tokens, $, quality-retention
```

### Multi-node distributed routing (two physical machines)

`benchmarks/bench_multinode.py` — cheap tier on **node A** (laptop, `qwen2.5:3b`), strong
tier on **node B** (cluster node `carlito4`, `qwen2.5:7b`, reached over an SSH tunnel — no
config change on the cluster). LocalRouter decides per prompt; 8-prompt balanced mix:

| metric | value |
|---|---|
| routed to node A (local) / node B (cluster) | **7 / 1** |
| node A latency p50 | **0.53s** |
| node B latency (the one hard prompt) | **50.5s** (7B on a busy CPU node) |
| private prompts | 2 |
| **private leaked across the network** | **0** |

**Proves:** routing genuinely spans machines, keeps p50 low by sending only the hard prompt
to the heavy tier, and the **privacy invariant holds over a real network hop** — every
`private` prompt stayed on node A. (Threshold is tunable via `FRUGAL_COMPLEXITY_THRESHOLD`.)

## Scenarios

Runnable stories under [`examples/scenarios/`](examples/scenarios/), each proving one value:
`scenario_coding_agent.py` (budget-capped agent), `scenario_private_data.py` (0 leaks),
`scenario_ci_eval.py` (catch a silent regression in CI).

## Also in this repo

- [`rules/AGENTS.md`](rules/AGENTS.md) — 10 copy-paste rules to make any coding agent cost-aware.
- [`awesome-onprem-ai.md`](awesome-onprem-ai.md) — curated list of local-first / on-prem AI tooling.

## Notes on honesty

Price figures in `frugal/meter/pricing.py` are **approximate public list prices** and
user-editable — verify against your provider before relying on the dollar values. The eval
asserts are **cheap heuristic gates** for CI, not ground-truth judges; pass a `provider=` to
upgrade them to an LLM judge.

## How Frugal differs (it's not "just a LiteLLM wrapper")

Proxies like LiteLLM / Portkey / Helicone route and log across providers. Frugal overlaps there
but its point is the **decision + verification loop**, not the proxy:

| | LiteLLM / gateways | **Frugal** |
|---|---|---|
| Multi-provider proxy | ✅ | ✅ (gateway) |
| **Cost-aware cascade** (cheap→escalate on a real confidence check) | mostly manual | ✅ measured, with self-consistency |
| **Offline eval asserts + RAG checks for CI** | ✕ | ✅ |
| **MCP server** exposing the agent's own $/token | ✕ | ✅ |
| **Local-first** routing by privacy/complexity | partial | ✅ (0 private leaks, tested) |
| **Reproducible model-vs-model benchmark** built in | ✕ | ✅ (`bench_models.py`) |
| Zero-dep, runs fully offline (mock) | ✕ | ✅ |

If all you need is a provider proxy, use LiteLLM. Frugal is for *deciding what to run and proving
it was good enough* — cheaply, locally, in CI.

## Roadmap & maintenance

Longevity is the #1 thing developers ask about a new repo, so plainly: this is actively
maintained, Apache-2.0, and issues/PRs get triaged. Near-term roadmap:
- broader, human-graded, multi-workload evals (retire the "small N" caveat)
- logprob/verifier confidence (cheaper than self-consistency)
- pre-reservation budget mode (zero-overshoot hard cap)
- head-to-head bake-off vs LiteLLM/Portkey
- more provider adapters + a persistent metrics store

Not promising a foundation — promising honest, responsive upkeep and a public roadmap.

## Security

The `frugal.mcp.guard` PII/injection checks are a **first-line heuristic**, not a security
product — they catch the obvious and miss the clever; don't make them your only control. Report
vulnerabilities via a private issue. See [WEAKNESSES.md](WEAKNESSES.md) for the full honest audit.

## License

Apache-2.0.
