"""Multi-node distributed routing benchmark (P2).

Two PHYSICAL machines:
  • cheap/local tier  -> Ollama on THIS box            (node A)
  • strong/cloud tier -> Ollama on a cluster node      (node B, reached however)

Frugal's LocalRouter decides per prompt (private->local always; hard public->strong;
easy public->local) and we measure: the routing split, per-node latency, and that
NO private prompt ever left node A. Real models, real network hop.

Env:
    FRUGAL_LOCAL_BASE_URL   node A ollama  (default http://localhost:11434)
    FRUGAL_LOCAL_MODEL      cheap model    (default qwen2.5:3b)
    FRUGAL_CLOUD_BASE_URL   node B ollama  (default http://localhost:11435  e.g. ssh tunnel)
    FRUGAL_CLOUD_MODEL      strong model   (default qwen2.5:7b)
    FRUGAL_BENCH_N          prompts        (default 8)
    FRUGAL_NUM_PREDICT      output cap     (default 160)
"""
from __future__ import annotations

import os
import sys
from statistics import median
from time import perf_counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from frugal import Meter  # noqa: E402
from frugal.local import LocalRouter  # noqa: E402
from frugal.providers import get_ollama  # noqa: E402

from data import WORKLOAD  # noqa: E402


def main():
    a_host = os.environ.get("FRUGAL_LOCAL_BASE_URL", "http://localhost:11434")
    a_model = os.environ.get("FRUGAL_LOCAL_MODEL", "qwen2.5:3b")
    b_host = os.environ.get("FRUGAL_CLOUD_BASE_URL", "http://localhost:11435")
    b_model = os.environ.get("FRUGAL_CLOUD_MODEL", "qwen2.5:7b")
    n = int(os.environ.get("FRUGAL_BENCH_N", "8"))
    num_predict = int(os.environ.get("FRUGAL_NUM_PREDICT", "160"))

    local = get_ollama(model=a_model, host=a_host)
    cloud = get_ollama(model=b_model, host=b_host)
    meter = Meter()
    thr = float(os.environ.get("FRUGAL_COMPLEXITY_THRESHOLD", "0.4"))
    lr = LocalRouter(local=local, cloud=cloud, meter=meter,
                     local_model=a_model, cloud_model=b_model, complexity_threshold=thr)

    print(f"node A (cheap/local) : {a_model} @ {a_host}")
    print(f"node B (strong/cloud): {b_model} @ {b_host}")
    print(f"N={min(n,len(WORKLOAD))} num_predict={num_predict}\n", flush=True)

    # balanced sample so BOTH nodes + the privacy path get exercised
    easy = [r for r in WORKLOAD if not r["hard"] and not r["private"]][:3]
    hard = [r for r in WORKLOAD if r["hard"] and not r["private"]][:3]
    priv = [r for r in WORKLOAD if r["private"]][:2]
    rows = (easy + hard + priv)[:n] if n >= 8 else WORKLOAD[:n]
    a_lat, b_lat = [], []
    routed = {"local": 0, "cloud": 0}
    leaks = 0
    for row in rows:
        tags = {"private"} if row["private"] else set()
        where = lr.decide(row["prompt"], tags)
        routed[where] += 1
        if row["private"] and where != "local":
            leaks += 1
        t0 = perf_counter()
        lr.complete(row["prompt"], tags=tags, num_predict=num_predict, temperature=0.0)
        dt = perf_counter() - t0
        (a_lat if where == "local" else b_lat).append(dt)
        print(f"  [{where.upper():5s} {'A' if where=='local' else 'B'}] "
              f"{dt:5.1f}s  {'PRIVATE' if tags else 'public '}  {row['prompt'][:44]}", flush=True)

    print("\n=== MULTI-NODE RESULTS ===")
    out = {
        "prompts": len(rows),
        "routed_local_nodeA": routed["local"],
        "routed_cloud_nodeB": routed["cloud"],
        "local_share_pct": round(100 * routed["local"] / len(rows), 1),
        "private_prompts": sum(r["private"] for r in rows),
        "private_leaked_to_nodeB": leaks,
        "nodeA_latency_p50_s": round(median(a_lat), 2) if a_lat else None,
        "nodeB_latency_p50_s": round(median(b_lat), 2) if b_lat else None,
        "speedup_local_vs_cloud": (round(median(b_lat) / median(a_lat), 1)
                                   if a_lat and b_lat else None),
    }
    for k, v in out.items():
        print(f"  {k}: {v}")
    assert leaks == 0, "PRIVACY VIOLATION — a private prompt crossed the network!"
    print("\n✅ privacy invariant held across the network; routing distributed over 2 nodes")

    import datetime, socket
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    d = os.path.dirname(__file__)
    with open(os.path.join(d, "RESULTS_MULTINODE.md"), "w", encoding="utf-8") as fh:
        fh.write(f"# Frugal multi-node routing ({stamp}, orchestrated from {socket.gethostname()})\n\n")
        fh.write(f"node A (cheap): {a_model} @ {a_host}  ·  node B (strong): {b_model} @ {b_host}\n\n")
        fh.write("| metric | value |\n|---|---|\n")
        for k, v in out.items():
            fh.write(f"| {k} | {v} |\n")
    print(f"✅ wrote {d}/RESULTS_MULTINODE.md")


if __name__ == "__main__":
    main()
