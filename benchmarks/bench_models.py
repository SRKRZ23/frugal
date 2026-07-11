"""Cross-model benchmark on a real cluster node.

For each model: latency p50/p95, avg output tokens, throughput (tok/s).
Then an LLM-judged quality matrix: how often each model's answer is 'as good as'
the strong reference (retention), plus an absolute judge quality score. This is
the honest version of quality-retention (a real judge model, not token overlap).

Env:
    FRUGAL_MODELS       comma list (default: the 5 cluster models)
    FRUGAL_STRONG_REF   reference 'best' model (default: last in FRUGAL_MODELS)
    FRUGAL_JUDGE_MODEL  judge (default: qwen2.5:7b)
    FRUGAL_BENCH_N      prompts (default: 5)
    FRUGAL_NUM_PREDICT  output cap per generation (default: 220)
    FRUGAL_OLLAMA_HOST  (default http://localhost:11434)

Writes benchmarks/RESULTS_MODELS.md + .json. Prints progress as it goes.
"""
from __future__ import annotations

import json
import os
import sys
from statistics import mean, median
from time import perf_counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from frugal.eval import strip_reasoning  # noqa: E402
from frugal.eval.judge import LLMJudge  # noqa: E402
from frugal.providers import get_ollama  # noqa: E402

PROMPTS = [
    "What is the capital of France? Answer in one sentence.",
    "A train travels 60 km in 45 minutes. What is its average speed in km/h? Show the calculation.",
    "Explain in 2-3 sentences why binary search is O(log n).",
    "List three trade-offs between microservices and a monolith.",
    "Write a one-line Python function that returns the factorial of n.",
    "What causes a deadlock in concurrent programming? Answer briefly.",
]


def _pct(xs, p):
    if not xs:
        return 0.0
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round((p / 100) * (len(xs) - 1))))]


def main():
    host = os.environ.get("FRUGAL_OLLAMA_HOST", "http://localhost:11434")
    models = os.environ.get(
        "FRUGAL_MODELS",
        "qwen2.5-coder:3b,qwen2.5:7b,deepseek-r1:7b,phi4:14b,deepseek-r1:14b",
    ).split(",")
    models = [m.strip() for m in models if m.strip()]
    strong_ref = os.environ.get("FRUGAL_STRONG_REF", models[-1])
    judge_model = os.environ.get("FRUGAL_JUDGE_MODEL", "qwen2.5:7b")
    n = int(os.environ.get("FRUGAL_BENCH_N", "5"))
    num_predict = int(os.environ.get("FRUGAL_NUM_PREDICT", "220"))
    if os.environ.get("FRUGAL_PROMPTSET", "easy").lower() == "hard":
        from data_hard import HARD_PROMPTS
        prompts = HARD_PROMPTS[:n]
    else:
        prompts = PROMPTS[:n]

    prov = get_ollama(host=host)
    judge = LLMJudge(prov, model=judge_model)

    print(f"host={host}\nmodels={models}\nstrong_ref={strong_ref} judge={judge_model} "
          f"N={len(prompts)} num_predict={num_predict}\n", flush=True)

    per_model = {}
    answers = {m: [] for m in models}
    for m in models:
        lat, toks = [], []
        print(f"[{m}] generating {len(prompts)} answers...", flush=True)
        for i, p in enumerate(prompts):
            try:
                t0 = perf_counter()
                r = prov.complete(p, model=m, num_predict=num_predict, temperature=0.0)
                dt = perf_counter() - t0
                lat.append(dt)
                toks.append(r.output_tokens)
                answers[m].append(strip_reasoning(r.text))
                print(f"   [{m}] {i+1}/{len(prompts)}  {dt:.1f}s  {r.output_tokens}tok", flush=True)
            except Exception as e:  # noqa: BLE001
                print(f"   [{m}] prompt {i} FAILED: {e}", flush=True)
                answers[m].append("")
                lat.append(0.0)
                toks.append(0)
        tps = mean([t / l for t, l in zip(toks, lat) if l > 0]) if any(lat) else 0
        per_model[m] = {
            "latency_p50_s": round(median([x for x in lat if x > 0] or [0]), 2),
            "latency_p95_s": round(_pct([x for x in lat if x > 0], 95), 2),
            "avg_output_tokens": round(mean(toks), 1),
            "throughput_tok_s": round(tps, 1),
        }
        print(f"[{m}] p50={per_model[m]['latency_p50_s']}s "
              f"p95={per_model[m]['latency_p95_s']}s tok/s={per_model[m]['throughput_tok_s']}\n", flush=True)

    # --- LLM-judged quality: absolute score + retention vs strong_ref ---
    print("judging quality (LLM-as-judge)...", flush=True)
    for m in models:
        qscores, retained = [], 0
        for i, p in enumerate(prompts):
            qscores.append(judge.score(p, answers[m][i]))
            if m != strong_ref:
                if judge.equivalent(p, answers[m][i], answers[strong_ref][i]):
                    retained += 1
        per_model[m]["judge_quality_0_1"] = round(mean(qscores), 3)
        per_model[m]["retention_vs_strong"] = (
            "ref" if m == strong_ref else f"{retained}/{len(prompts)} ({round(100*retained/len(prompts))}%)"
        )
        print(f"[{m}] quality={per_model[m]['judge_quality_0_1']} "
              f"retention={per_model[m]['retention_vs_strong']}", flush=True)

    # --- routing insight: cheapest model whose quality is within 10% of the best ---
    best_q = max(v["judge_quality_0_1"] for v in per_model.values())
    good_enough = [m for m in models if per_model[m]["judge_quality_0_1"] >= best_q * 0.9]
    fastest_good = min(good_enough, key=lambda m: per_model[m]["latency_p50_s"]) if good_enough else models[0]

    out = {
        "host_models": per_model,
        "strong_ref": strong_ref,
        "judge_model": judge_model,
        "best_quality_0_1": round(best_q, 3),
        "within_10pct_of_best": good_enough,
        "recommended_cheap_tier": fastest_good,
        "speedup_vs_ref_p50": (round(per_model[strong_ref]["latency_p50_s"] /
                                     max(0.01, per_model[fastest_good]["latency_p50_s"]), 1)),
    }
    print("\n=== SUMMARY ===")
    print(json.dumps(out, indent=2))

    import datetime
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    import socket
    d = os.path.dirname(__file__)
    with open(os.path.join(d, "RESULTS_MODELS.json"), "w") as fh:
        json.dump(out, fh, indent=2)
    with open(os.path.join(d, "RESULTS_MODELS.md"), "w", encoding="utf-8") as fh:
        fh.write(f"# Frugal cross-model benchmark\n\n_Measured {stamp} on **{socket.gethostname()}** "
                 f"(real Ollama models, CPU inference). Judge: {judge_model}. Reference: {strong_ref}._\n\n")
        fh.write("| model | p50 s | p95 s | tok/s | avg out tok | judge quality 0-1 | retention vs ref |\n")
        fh.write("|---|---|---|---|---|---|---|\n")
        for m in models:
            v = per_model[m]
            fh.write(f"| {m} | {v['latency_p50_s']} | {v['latency_p95_s']} | {v['throughput_tok_s']} | "
                     f"{v['avg_output_tokens']} | {v['judge_quality_0_1']} | {v['retention_vs_strong']} |\n")
        fh.write(f"\n**Routing takeaway:** best judged quality = {best_q:.3f}; models within 10% of it: "
                 f"{good_enough}. Cheapest of those = **{fastest_good}** "
                 f"(~{out['speedup_vs_ref_p50']}× faster p50 than the reference {strong_ref}) — "
                 f"route there first, escalate only when confidence is low.\n")
    print(f"\n✅ wrote {d}/RESULTS_MODELS.md")


if __name__ == "__main__":
    main()
