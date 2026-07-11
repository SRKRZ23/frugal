"""LIVE bake-off: LiteLLM (plain proxy) vs Frugal (cost routing) — same models, same
prompts, real calls through Ollama on the cluster. No cloud keys needed.

  • LiteLLM path : every prompt -> the strong model (what a proxy does; no routing).
  • Frugal path  : LocalRouter sends easy prompts to the cheap model, only hard ones
                   to the strong model — no extra probe calls.

We measure real latency + strong-model calls, and model the $ at cloud prices to show
the saving. (Local tokens are actually $0; the $ column is modelled for comparison.)

Run with the litellm venv on a node that has Ollama:
  /shared/frugal/.litellmenv/bin/python benchmarks/compare_litellm_live.py
Env: FRUGAL_CHEAP (qwen2.5-coder:3b), FRUGAL_STRONG (qwen2.5:7b), FRUGAL_OLLAMA_HOST.
"""
from __future__ import annotations

import os
import sys
from time import perf_counter

sys.path.insert(0, "/shared/frugal/src")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

try:
    import litellm  # noqa: E402
    litellm.suppress_debug_info = True
    HAVE_LITELLM = True
except Exception:  # noqa: BLE001
    HAVE_LITELLM = False

from frugal import Meter  # noqa: E402
from frugal.local import LocalRouter  # noqa: E402
from frugal.meter.pricing import cost_of, register_price  # noqa: E402
from frugal.providers import get_ollama  # noqa: E402

from data_broad import BROAD  # noqa: E402

HOST = os.environ.get("FRUGAL_OLLAMA_HOST", "http://localhost:11434")
CHEAP = os.environ.get("FRUGAL_CHEAP", "qwen2.5-coder:3b")
STRONG = os.environ.get("FRUGAL_STRONG", "qwen2.5:7b")
NP = int(os.environ.get("FRUGAL_NUM_PREDICT", "150"))
prompts = [q for _, q in BROAD]

# model the $ at cloud prices (cheap ~ gpt-4o-mini, strong ~ gpt-4o) — local tokens are $0
register_price(CHEAP, 0.15, 0.60)
register_price(STRONG, 2.50, 10.00)


def run_proxy():
    """The baseline a plain proxy gives: every prompt -> the strong model (no routing).
    Uses the litellm package if installed; otherwise the same behaviour via Frugal's Ollama
    client (identical: pass-through to one model). Labelled honestly in the output."""
    from frugal.providers import get_ollama
    prov = get_ollama(model=STRONG, host=HOST)
    lat, strong_calls, cost = [], 0, 0.0
    for p in prompts:
        t0 = perf_counter()
        if HAVE_LITELLM:
            r = litellm.completion(model=f"ollama/{STRONG}", messages=[{"role": "user", "content": p}],
                                   api_base=HOST, max_tokens=NP)
            u = r.usage
            it, ot = u.prompt_tokens or 0, u.completion_tokens or 0
        else:
            resp = prov.complete(p, model=STRONG, num_predict=NP)
            it, ot = resp.input_tokens, resp.output_tokens
        lat.append(perf_counter() - t0)
        strong_calls += 1
        cost += cost_of(STRONG, it, ot)
    return {"strong_calls": strong_calls, "total_latency_s": round(sum(lat), 1),
            "modelled_cost_usd": round(cost, 5)}


def run_frugal():
    local, cloud = get_ollama(model=CHEAP, host=HOST), get_ollama(model=STRONG, host=HOST)
    meter = Meter()
    lr = LocalRouter(local=local, cloud=cloud, meter=meter, local_model=CHEAP, cloud_model=STRONG,
                     complexity_threshold=0.4)
    lat, strong_calls = [], 0
    for p in prompts:
        where = lr.decide(p)
        t0 = perf_counter()
        lr.complete(p, num_predict=NP)
        lat.append(perf_counter() - t0)
        if where == "cloud":
            strong_calls += 1
    return {"strong_calls": strong_calls, "total_latency_s": round(sum(lat), 1),
            "modelled_cost_usd": round(meter.total_cost, 5)}


def main():
    baseline = "LiteLLM" if HAVE_LITELLM else "proxy-baseline (litellm not installed — same pass-through)"
    print(f"live bake-off · cheap={CHEAP} strong={STRONG} · {len(prompts)} prompts · host={HOST}")
    print(f"baseline = {baseline}\n", flush=True)
    print("running proxy (all -> strong)...", flush=True)
    ll = run_proxy()
    print(f"  {ll}", flush=True)
    print("running Frugal (route: easy -> cheap, hard -> strong)...", flush=True)
    fr = run_frugal()
    print(f"  {fr}", flush=True)

    saved_cost = round((1 - fr["modelled_cost_usd"] / ll["modelled_cost_usd"]) * 100, 1) if ll["modelled_cost_usd"] else 0
    saved_lat = round((1 - fr["total_latency_s"] / ll["total_latency_s"]) * 100, 1) if ll["total_latency_s"] else 0
    print("\n=== LIVE BAKE-OFF RESULT ===")
    print(f"strong-model calls : LiteLLM {ll['strong_calls']}  vs  Frugal {fr['strong_calls']}")
    print(f"total latency      : LiteLLM {ll['total_latency_s']}s vs Frugal {fr['total_latency_s']}s  ({saved_lat}% less)")
    print(f"modelled $ (cloud) : LiteLLM ${ll['modelled_cost_usd']} vs Frugal ${fr['modelled_cost_usd']}  ({saved_cost}% less)")

    import datetime, socket
    d = os.path.dirname(__file__)
    with open(os.path.join(d, "RESULTS_LITELLM.md"), "w", encoding="utf-8") as fh:
        fh.write(f"# Frugal vs LiteLLM — LIVE bake-off ({datetime.datetime.now():%Y-%m-%d %H:%M}, {socket.gethostname()})\n\n")
        fh.write(f"_Real calls through Ollama ({CHEAP} / {STRONG}), {len(prompts)} prompts. LiteLLM = plain "
                 f"proxy (all→strong); Frugal = LocalRouter (easy→cheap, hard→strong). $ modelled at "
                 f"GPT-4o-mini/4o prices; local tokens are $0. Cloud-key run = when keys provided._\n\n")
        fh.write(f"Baseline: **{baseline}**.\n\n")
        fh.write(f"| metric | proxy (all→strong) | Frugal (routed) | Frugal saves |\n|---|---|---|---|\n")
        fh.write(f"| strong-model calls | {ll['strong_calls']} | {fr['strong_calls']} | — |\n")
        fh.write(f"| total latency (s) | {ll['total_latency_s']} | {fr['total_latency_s']} | {saved_lat}% |\n")
        fh.write(f"| modelled cost (USD) | {ll['modelled_cost_usd']} | {fr['modelled_cost_usd']} | {saved_cost}% |\n")
    print(f"\nwrote {d}/RESULTS_LITELLM.md")


if __name__ == "__main__":
    main()
