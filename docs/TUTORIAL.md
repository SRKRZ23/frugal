# Frugal tutorial — from zero to cost-routed in 10 minutes

Every step runs offline first (mock provider), then shows the real-provider swap.

## 0. Install
```bash
git clone https://github.com/SRKRZ23/frugal && cd frugal
pip install -e .
frugal demo            # offline end-to-end, ~2s, no keys
```

## 1. Meter a call (know what you spent)
```python
from frugal import Meter, MockProvider
meter, prov = Meter(), MockProvider()
with meter.track("gpt-4o-mini") as call:
    call.set(prov.complete("summarise this", model="gpt-4o-mini"))
print(meter.summary())          # cost, tokens, per-model breakdown
```

## 2. Cost-route (cheap first, escalate only when needed)
```python
from frugal import cascade
r = cascade("say hi", prov, meter)                       # stays cheap
r = cascade("prove this design step by step", prov, meter)  # escalates
print(r.model_used, r.escalated)
```

## 3. Use a real confidence signal (works on real models)
```python
from frugal.route import make_self_consistency
conf = make_self_consistency(n=2)
r = cascade(prompt, prov, meter, ladder=["gpt-4o-mini", "gpt-4o"], confidence_fn=conf)
# Frugal auto-warns if this cheap/frontier pair can't cover the probing cost.
```

## 4. Put a hard budget on it
```python
from frugal.meter import BudgetExceeded
meter = Meter(budget_usd=5.00, max_history=1000)   # hard cap + bounded memory
try:
    for job in jobs:
        cascade(job, prov, meter)
except BudgetExceeded:
    print("stopped at the cap — no surprise bill")
```

## 5. Gate quality in CI (catch silent regressions)
```python
# tests/test_agent.py
from frugal.eval import assert_semantic, assert_no_hallucination
def test_answer():
    out = my_agent("capital of France?")
    assert_semantic(out, "Paris is the capital of France", threshold=0.4)
    assert_no_hallucination(out, context=retrieved_docs)
```

## 6. Go real (cloud or local)
```python
from frugal.providers import get_openai, get_ollama
cloud = get_openai(base_url="https://api.openai.com/v1")     # any OpenAI-compatible
local = get_ollama(model="llama3")                           # http://localhost:11434
```

## 7. Run the OpenAI-compatible budget gateway
```bash
pip install 'frugal[gateway]'
frugal gateway --budget 5.00          # point any OpenAI SDK at http://localhost:8080
```

## 8. On a cluster (models off-box)
See [CLUSTER.md](CLUSTER.md) — set `FRUGAL_*` env vars, run the same code against real nodes.

## 9. Prove the savings for YOUR setup
```bash
python benchmarks/cost_model.py       # edit PRICES / tokens / mix -> your $ savings
python benchmarks/bench_models.py      # compare your models (needs Ollama/cluster)
```

That's the whole loop: **meter → route → verify → (budget) → deploy**, cheap and local by default.
