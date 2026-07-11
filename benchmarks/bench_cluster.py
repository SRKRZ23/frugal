"""Real-model benchmark. Runs against a CLUSTER (Ollama / vLLM) — or, with no
FRUGAL_* env set, against a local Ollama as a *stand-in* so you still get REAL
numbers (real latency, real tokens, real quality-retention) instead of synthetic
mock text. It never fabricates: if no real endpoint answers, it says so and exits.

What it measures (all real):
  • per-tier latency p50/p95 and token usage
  • quality-retention: how often the cheap model's answer already matches the
    strong model's (== how often escalation was genuinely avoidable)
  • cascade escalation behaviour with the default confidence signal (+ its limits)
  • modelled $ at scale: local ($0/token) vs a cloud-frontier reference price

Config (env; see docs/CLUSTER.md). Defaults target a local ollama stand-in:
    FRUGAL_LOCAL_BASE_URL   (default http://localhost:11434)
    FRUGAL_LOCAL_MODEL      cheap tier   (default qwen2.5:0.5b)
    FRUGAL_CLOUD_BASE_URL   strong tier endpoint (optional; else local ollama)
    FRUGAL_CLOUD_MODEL      strong tier  (default qwen2.5:3b on the local ollama)
    FRUGAL_CLOUD_REF_PRICE  $/1M tokens used ONLY to model cloud cost (default 5.0)
"""
from __future__ import annotations

import os
import sys
from statistics import median
from time import perf_counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from frugal import Meter, cascade  # noqa: E402
from frugal.eval import semantic_similarity  # noqa: E402
from frugal.meter import register_price  # noqa: E402
from frugal.providers import get_ollama  # noqa: E402

from data import WORKLOAD  # noqa: E402


def _pct(xs, p):
    if not xs:
        return 0.0
    xs = sorted(xs)
    k = min(len(xs) - 1, int(round((p / 100) * (len(xs) - 1))))
    return xs[k]


def _resolve_providers():
    """Return (cheap_provider, cheap_model, strong_provider, strong_model, mode)."""
    local_host = os.environ.get("FRUGAL_LOCAL_BASE_URL", "http://localhost:11434")
    cheap_model = os.environ.get("FRUGAL_LOCAL_MODEL", "qwen2.5:0.5b")
    cloud_url = os.environ.get("FRUGAL_CLOUD_BASE_URL")
    strong_model = os.environ.get("FRUGAL_CLOUD_MODEL", "qwen2.5:3b")

    cheap = get_ollama(model=cheap_model, host=local_host)
    if cloud_url:
        from frugal.providers import get_openai
        strong = get_openai(model=strong_model, base_url=cloud_url,
                            api_key=os.environ.get("FRUGAL_CLOUD_API_KEY", "x"))
        mode = "cluster (local ollama + remote cloud)"
    else:
        import socket
        strong = get_ollama(model=strong_model, host=local_host)
        mode = f"single-host ollama on '{socket.gethostname()}' (both tiers @ {local_host})"
    return cheap, cheap_model, strong, strong_model, mode


def _probe(provider, model):
    try:
        r = provider.complete("ping", model=model)
        return r is not None
    except Exception as e:  # noqa: BLE001
        print(f"   ✗ {model} unreachable: {e}")
        return False


def main():
    cheap, cheap_m, strong, strong_m, mode = _resolve_providers()
    ref_price = float(os.environ.get("FRUGAL_CLOUD_REF_PRICE", "5.0"))  # $/1M tok, modelled

    print(f"mode: {mode}")
    print(f"cheap tier : {cheap_m}\nstrong tier: {strong_m}\n")
    print("probing endpoints...")
    if not _probe(cheap, cheap_m):
        print("⚠️  cheap tier unreachable — start ollama / set FRUGAL_* (no numbers fabricated).")
        return 0
    strong_ok = _probe(strong, strong_m)
    if not strong_ok:
        print("   (strong tier unreachable — running cheap-tier-only measurements)")

    # local models are $0/token; model the cloud tier at the reference price
    register_price(cheap_m, 0.0, 0.0)
    if strong_ok:
        register_price(strong_m, ref_price, ref_price)

    n = int(os.environ.get("FRUGAL_BENCH_N", "12"))
    prompts = [r["prompt"] for r in WORKLOAD[:n]]
    cheap_lat, strong_lat, cheap_tok, strong_tok = [], [], [], []
    retained = comparable = 0
    cheap_meter = Meter()

    print(f"\nrunning {len(prompts)} prompts through real models...")
    for p in prompts:
        t0 = perf_counter()
        with cheap_meter.track(cheap_m) as c:
            rc = c.set(cheap.complete(p, model=cheap_m))
        cheap_lat.append(perf_counter() - t0)
        cheap_tok.append(rc.total_tokens)

        if strong_ok:
            t1 = perf_counter()
            rs = strong.complete(p, model=strong_m)
            strong_lat.append(perf_counter() - t1)
            strong_tok.append(rs.total_tokens)
            comparable += 1
            if semantic_similarity(rc.text, rs.text) >= 0.6:
                retained += 1

    # cascade over real models (real ladder). Choose the confidence signal via env:
    #   FRUGAL_CONFIDENCE=self_consistency  -> re-sample & measure agreement (works on real models)
    #   (default)                           -> hedging words (weak on real models)
    conf_mode = os.environ.get("FRUGAL_CONFIDENCE", "hedging")
    conf_fn = None
    if conf_mode == "self_consistency":
        from frugal.route import make_self_consistency
        conf_fn = make_self_consistency(n=2, sim_threshold=0.6)
    cas_meter = Meter()
    escalations = 0
    ladder = [cheap_m] + ([strong_m] if strong_ok else [])  # one ollama host serves both
    for p in prompts:
        r = cascade(p, cheap, cas_meter, ladder=ladder, confidence_fn=conf_fn)
        if r.escalated:
            escalations += 1

    # modelled cost at scale: cloud-frontier vs this cluster
    avg_tok = (sum(cheap_tok) / len(cheap_tok)) if cheap_tok else 0
    cloud_cost_per_req = (avg_tok / 1_000_000) * ref_price
    lines = {
        "mode": mode,
        "prompts_run": len(prompts),
        "cheap_model": cheap_m,
        "strong_model": strong_m if strong_ok else "(unreachable)",
        "cheap_latency_p50_s": round(median(cheap_lat), 3),
        "cheap_latency_p95_s": round(_pct(cheap_lat, 95), 3),
        "cheap_avg_tokens": round(avg_tok, 1),
        "strong_latency_p50_s": round(median(strong_lat), 3) if strong_lat else None,
        "strong_latency_p95_s": round(_pct(strong_lat, 95), 3) if strong_lat else None,
        "quality_retention_cheap≈strong": (f"{retained}/{comparable} ({round(100*retained/comparable)}%)" if comparable else "n/a"),
        "confidence_mode": conf_mode,
        "cascade_escalations": f"{escalations}/{len(prompts)}",
        "local_cost_usd_total": round(cheap_meter.total_cost, 6),
        "modelled_cloud_$_per_1k_requests": round(cloud_cost_per_req * 1000, 4),
        "modelled_cloud_$_per_1M_requests": round(cloud_cost_per_req * 1_000_000, 2),
    }
    print("\n=== REAL-MODEL RESULTS ===")
    for k, v in lines.items():
        print(f"  {k}: {v}")

    import datetime
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    out = os.path.join(os.path.dirname(__file__), "RESULTS_CLUSTER.md")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(f"# Frugal real-model benchmark\n\n_Measured {stamp} — mode: **{mode}**._\n\n")
        fh.write("> Real models, real latency/tokens. Local tokens cost $0 (on-prem); the "
                 "cloud $ column is **modelled** at the reference price to show the savings "
                 "of keeping work on the cluster.\n\n")
        fh.write("| metric | value |\n|---|---|\n")
        for k, v in lines.items():
            fh.write(f"| {k} | {v} |\n")
        fh.write("\n**Honest note:** cascade escalation uses a hedging-word confidence signal; "
                 "real models rarely self-hedge, so on real endpoints wire a logprob/verifier "
                 "confidence (or `LocalRouter` by cost/privacy) rather than relying on it.\n")
    print(f"\n✅ wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
