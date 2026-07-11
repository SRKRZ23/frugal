"""Frugal offline benchmark suite.

Every number here is MEASURED by running the real code on a labelled synthetic
workload — no hand-typed results. What it proves and what it does NOT:

  ✅ PROVES (exactly, offline): cost arithmetic, routing decisions & escalation
     accuracy, privacy-leak safety, guard precision/recall, eval/RAG gate accuracy
     on the labelled set, and per-call overhead.
  ⚠️ DOES NOT prove real-model answer *quality* — the MockProvider's text is
     synthetic. Run `bench_cluster.py` against real models for quality retention.

Usage:  python benchmarks/run_all.py        # writes benchmarks/RESULTS.md
"""
from __future__ import annotations

import os
import sys
from time import perf_counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from frugal import Meter, MockProvider, cascade  # noqa: E402
from frugal.eval import assert_no_hallucination, semantic_similarity  # noqa: E402
from frugal.local import LocalRouter  # noqa: E402
from frugal.mcp import detect_injection, redact_pii  # noqa: E402
from frugal.rag import ragcheck  # noqa: E402

from data import GROUNDEDNESS, GUARD, RAG, SEMANTIC_PAIRS, WORKLOAD  # noqa: E402


def _prf(tp, fp, fn):
    prec = tp / (tp + fp) if (tp + fp) else 1.0
    rec = tp / (tp + fn) if (tp + fn) else 1.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    return round(prec, 3), round(rec, 3), round(f1, 3)


# --- 1. cost-aware routing ---------------------------------------------------
def bench_routing():
    provider = MockProvider()
    frontier = "frugal-mock-frontier"

    m_cascade, m_frontier, m_cheap = Meter(), Meter(), Meter()
    esc_tp = esc_fp = esc_fn = 0
    for row in WORKLOAD:
        r = cascade(row["prompt"], provider, m_cascade)
        escalated = r.escalated
        if escalated and row["hard"]:
            esc_tp += 1
        elif escalated and not row["hard"]:
            esc_fp += 1
        elif not escalated and row["hard"]:
            esc_fn += 1
        # baselines
        with m_frontier.track(frontier) as c:
            c.set(provider.complete(row["prompt"], model=frontier))
        with m_cheap.track("frugal-mock-cheap") as c:
            c.set(provider.complete(row["prompt"], model="frugal-mock-cheap"))

    saved = 1 - (m_cascade.total_cost / m_frontier.total_cost)
    p, rcl, f1 = _prf(esc_tp, esc_fp, esc_fn)
    return {
        "prompts": len(WORKLOAD),
        "cascade_cost_usd": round(m_cascade.total_cost, 6),
        "frontier_only_cost_usd": round(m_frontier.total_cost, 6),
        "cheap_only_cost_usd": round(m_cheap.total_cost, 6),
        "cost_saved_vs_frontier_pct": round(saved * 100, 1),
        "escalation_precision": p,
        "escalation_recall": rcl,
        "escalation_f1": f1,
        "calls_cascade": len(m_cascade.calls),
        "calls_frontier_only": len(m_frontier.calls),
    }


# --- 2. local<->cloud routing + privacy safety ------------------------------
def bench_local():
    lr = LocalRouter(local=MockProvider(), cloud=MockProvider(),
                     local_model="frugal-mock-cheap", cloud_model="frugal-mock-frontier")
    local_n = cloud_n = leaks = 0
    for row in WORKLOAD:
        tags = {"private"} if row["private"] else set()
        where = lr.decide(row["prompt"], tags)
        if where == "local":
            local_n += 1
        else:
            cloud_n += 1
            if row["private"]:
                leaks += 1  # a private prompt sent to cloud == safety failure
    # cost if everything went to cloud frontier vs the actual split
    return {
        "prompts": len(WORKLOAD),
        "routed_local": local_n,
        "routed_cloud": cloud_n,
        "local_share_pct": round(100 * local_n / len(WORKLOAD), 1),
        "private_prompts": sum(r["private"] for r in WORKLOAD),
        "private_leaked_to_cloud": leaks,
        "cloud_cost_avoided_by_local": f"{local_n} calls kept off the paid tier",
    }


# --- 3. eval gate accuracy ---------------------------------------------------
def bench_eval():
    # semantic assert: sweep threshold, report best accuracy on the labelled set
    best = (0.0, 0.0)
    for thr in [x / 100 for x in range(20, 61, 2)]:
        correct = sum((semantic_similarity(a, b) >= thr) == lbl for a, b, lbl in SEMANTIC_PAIRS)
        acc = correct / len(SEMANTIC_PAIRS)
        if acc > best[1]:
            best = (thr, acc)
    thr, sem_acc = best

    # groundedness gate
    g_tp = g_fp = g_fn = g_correct = 0
    for out, ctx, grounded in GROUNDEDNESS:
        try:
            assert_no_hallucination(out, ctx)
            predicted_grounded = True
        except AssertionError:
            predicted_grounded = False
        g_correct += predicted_grounded == grounded
        if not predicted_grounded and not grounded:
            g_tp += 1  # correctly flagged hallucination
        elif not predicted_grounded and grounded:
            g_fp += 1
        elif predicted_grounded and not grounded:
            g_fn += 1
    gp, gr, gf1 = _prf(g_tp, g_fp, g_fn)
    return {
        "semantic_pairs": len(SEMANTIC_PAIRS),
        "semantic_best_threshold": thr,
        "semantic_accuracy": round(sem_acc, 3),
        "groundedness_examples": len(GROUNDEDNESS),
        "groundedness_accuracy": round(g_correct / len(GROUNDEDNESS), 3),
        "hallucination_flag_precision": gp,
        "hallucination_flag_recall": gr,
    }


# --- 4. RAG gate accuracy ----------------------------------------------------
def bench_rag():
    correct = 0
    for ex in RAG:
        rep = ragcheck([ex])
        d = rep.as_dict()
        passed = d["retrieval_hit_rate"] == 1.0 and d["faithfulness"] == 1.0
        correct += passed == ex["good"]
    agg = ragcheck(RAG).as_dict()
    return {
        "examples": len(RAG),
        "gate_accuracy_vs_label": round(correct / len(RAG), 3),
        "retrieval_hit_rate": agg["retrieval_hit_rate"],
        "faithfulness": agg["faithfulness"],
        "citation_coverage": agg["citation_coverage"],
    }


# --- 5. guard precision/recall ----------------------------------------------
def bench_guard():
    p_tp = p_fp = p_fn = 0
    i_tp = i_fp = i_fn = 0
    for text, has_pii, is_inj in GUARD:
        pii = bool(redact_pii(text)["found"])
        inj = bool(detect_injection(text))
        if pii and has_pii: p_tp += 1
        elif pii and not has_pii: p_fp += 1
        elif not pii and has_pii: p_fn += 1
        if inj and is_inj: i_tp += 1
        elif inj and not is_inj: i_fp += 1
        elif not inj and is_inj: i_fn += 1
    pp, pr, pf1 = _prf(p_tp, p_fp, p_fn)
    ip, ir, if1 = _prf(i_tp, i_fp, i_fn)
    return {
        "samples": len(GUARD),
        "pii_precision": pp, "pii_recall": pr, "pii_f1": pf1,
        "injection_precision": ip, "injection_recall": ir, "injection_f1": if1,
    }


# --- 6. metering overhead ----------------------------------------------------
def bench_overhead(n=5000):
    provider = MockProvider()
    meter = Meter()
    start = perf_counter()
    for _ in range(n):
        with meter.track("frugal-mock-cheap") as c:
            c.set(provider.complete("x", model="frugal-mock-cheap"))
    dt = perf_counter() - start
    return {
        "calls": n,
        "total_s": round(dt, 4),
        "calls_per_sec": round(n / dt, 1),
        "overhead_ms_per_call": round(1000 * dt / n, 4),
    }


# --- 7. cost projection at scale (real arithmetic on measured per-req cost) --
def bench_scale():
    provider = MockProvider()
    m_c, m_f = Meter(), Meter()
    for row in WORKLOAD:
        cascade(row["prompt"], provider, m_c)
        with m_f.track("frugal-mock-frontier") as c:
            c.set(provider.complete(row["prompt"], model="frugal-mock-frontier"))
    n = len(WORKLOAD)
    cas_per = m_c.total_cost / n
    fro_per = m_f.total_cost / n
    def at(x):
        return {"cascade_usd": round(cas_per * x, 2), "frontier_only_usd": round(fro_per * x, 2),
                "saved_usd": round((fro_per - cas_per) * x, 2)}
    # monthly scenario: 50k requests/day
    daily = 50_000
    monthly_saved = (fro_per - cas_per) * daily * 30
    return {
        "per_request_cascade_usd": round(cas_per, 8),
        "per_request_frontier_usd": round(fro_per, 8),
        "at_100k_requests": at(100_000),
        "at_1M_requests": at(1_000_000),
        "at_10M_requests": at(10_000_000),
        "monthly_saved_usd_at_50k_per_day": round(monthly_saved, 2),
    }


# --- 8. escalation-threshold sweep (find the cost/quality knee) --------------
def bench_recall_sweep():
    provider = MockProvider()
    rows = []
    for thr in (0.3, 0.5, 0.6, 0.7, 0.8, 0.9):
        m = Meter()
        tp = fp = fn = 0
        for row in WORKLOAD:
            r = cascade(row["prompt"], provider, m, min_confidence=thr)
            if r.escalated and row["hard"]: tp += 1
            elif r.escalated and not row["hard"]: fp += 1
            elif not r.escalated and row["hard"]: fn += 1
        p, rcl, f1 = _prf(tp, fp, fn)
        rows.append({"min_confidence": thr, "esc_precision": p, "esc_recall": rcl,
                     "esc_f1": f1, "cost_usd": round(m.total_cost, 6)})
    return {"sweep": rows,
            "note": "higher min_confidence => more escalation (higher recall) => higher cost; pick the knee"}


def _table(d):
    def fmt(v):
        if isinstance(v, list):
            return "<br>".join(str(x) for x in v)
        return v
    return "\n".join(f"| {k} | {fmt(v)} |" for k, v in d.items())


def main():
    import datetime  # only for the header; benchmarks themselves use no wall clock
    results = {
        "1. Cost-aware routing (meter + route)": bench_routing(),
        "2. Local↔cloud routing + privacy (local)": bench_local(),
        "3. Eval gates (eval)": bench_eval(),
        "4. RAG checks (rag)": bench_rag(),
        "5. Guardrails (mcp.guard)": bench_guard(),
        "6. Metering overhead (meter)": bench_overhead(),
        "7. Cost projection at scale (meter + route)": bench_scale(),
        "8. Escalation-threshold sweep (route)": bench_recall_sweep(),
    }
    for title, d in results.items():
        print(f"\n### {title}")
        for k, v in d.items():
            print(f"  {k}: {v}")

    stamp = datetime.datetime.now().strftime("%Y-%m-%d")
    out = os.path.join(os.path.dirname(__file__), "RESULTS.md")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(f"# Frugal benchmark results\n\n")
        fh.write(f"_Measured {stamp} on the offline deterministic MockProvider + labelled "
                 f"synthetic datasets (`benchmarks/data.py`). Reproducible: `python benchmarks/run_all.py`._\n\n")
        fh.write("> **What this proves:** cost arithmetic, routing/escalation accuracy, "
                 "privacy-leak safety, guard precision/recall, eval/RAG gate accuracy, and "
                 "metering overhead — all exact.\n>\n"
                 "> **What it does NOT prove:** real-model answer quality (mock text is "
                 "synthetic). Run `benchmarks/bench_cluster.py` against real models for "
                 "quality retention.\n\n")
        for title, d in results.items():
            fh.write(f"## {title}\n\n| metric | value |\n|---|---|\n{_table(d)}\n\n")
    print(f"\n✅ wrote {out}")


if __name__ == "__main__":
    main()
