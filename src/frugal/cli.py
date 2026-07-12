"""Unified `frugal` CLI. Everything defaults to the offline MockProvider, so every
command runs with zero setup:

    frugal demo               # end-to-end showcase: meter + route + eval + rag + mcp
    frugal route "..."        # cascade-route one prompt, print cost
    frugal rag check f.json   # score a RAG eval file
    frugal mcp                # print the MCP tool surface (cost telemetry)
    frugal gateway            # run the OpenAI-compatible budget gateway (needs [gateway])
    frugal version
"""
from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .eval import DriftMonitor, assert_semantic
from .mcp import FrugalMCP
from .meter import Meter
from .providers import MockProvider
from .rag import ragcheck
from .route import cascade


def _p(obj):
    print(json.dumps(obj, indent=2, ensure_ascii=False))


def cmd_route(args) -> int:
    meter = Meter(budget_usd=args.budget)
    provider = MockProvider()
    result = cascade(args.prompt, provider, meter, min_confidence=args.min_confidence)
    _p(
        {
            "answer": result.text,
            "model_used": result.model_used,
            "tiers_tried": result.tiers_tried,
            "escalated": result.escalated,
            "cost": meter.summary(),
        }
    )
    return 0


def cmd_rag(args) -> int:
    with open(args.file, "r", encoding="utf-8") as fh:
        examples = json.load(fh)
    report = ragcheck(examples)
    _p({**report.as_dict(), "per_example": report.per_example})
    return 0


def cmd_mcp(args) -> int:
    mcp = FrugalMCP(Meter(budget_usd=1.0))
    print("Frugal MCP tools:", ", ".join(mcp.tools()))
    print("(run `frugal demo` to see them return live cost telemetry)")
    return 0


def cmd_gateway(args) -> int:
    try:
        import uvicorn

        from .gateway import create_app
    except ImportError:
        print("gateway needs extras:  pip install 'frugal[gateway]'", file=sys.stderr)
        return 1
    app = create_app(budget_usd=args.budget)
    uvicorn.run(app, host=args.host, port=args.port)
    return 0


def cmd_demo(args) -> int:
    provider = MockProvider()
    meter = Meter(budget_usd=1.0)

    print("── 1) cost-aware routing (cheap prompt stays cheap) ──")
    easy = cascade("say hello", provider, meter)
    print(f"   '{easy.text[:50]}...'  ->  {easy.model_used}  (escalated={easy.escalated})")

    print("── 2) hard prompt escalates up the ladder ──")
    hard = cascade(
        "Analyze the architecture trade-offs and prove why this refactor is optimal, step by step.",
        provider, meter,
    )
    print(f"   '{hard.text[:50]}...'  ->  {hard.model_used}  (tried {hard.tiers_tried})")

    print("── 3) eval: semantic assert (offline) ──")
    try:
        score = assert_semantic("Paris is the capital of France", "The capital of France is Paris", 0.4)
        print(f"   assert_semantic passed, score={score}")
    except AssertionError as e:
        print(f"   assert failed: {e}")

    print("── 4) drift monitor ──")
    dm = DriftMonitor().fit(["ok", "fine", "all good", "looks correct"])
    print(f"   drift('total failure everywhere') = {dm.drift('catastrophic total failure everywhere')}")

    print("── 5) RAG check ──")
    report = ragcheck([
        {"query": "capital?", "retrieved": [{"id": "d1", "text": "Paris is the capital of France"}],
         "gold_ids": ["d1"], "answer": "Paris is the capital of France", "citations": ["d1"]},
    ])
    print(f"   {report.as_dict()}")

    print("── 6) MCP cost telemetry (what the agent sees about itself) ──")
    mcp = FrugalMCP(meter)
    _p(mcp.call("get_cost_summary"))
    print(f"\n✅ total spent this demo: ${meter.total_cost:.6f} across {len(meter.calls)} calls")
    return 0


def cmd_diagnose(args) -> int:
    from .diagnose import diagnose_live, diagnose_prompts, load_prompts
    prompts = load_prompts(args.file)
    if not prompts:
        print(f"no prompts found in {args.file}")
        return 1
    if args.live:
        d = diagnose_live(prompts, cheap_model=args.cheap, frontier_model=args.frontier,
                          backend=args.backend, host=args.host, base_url=args.base_url,
                          min_confidence=args.threshold, confidence=args.confidence,
                          out_tokens=args.out_tokens)
    else:
        d = diagnose_prompts(prompts, current_model=args.current, cheap_model=args.cheap,
                             frontier_model=args.frontier, threshold=args.threshold,
                             out_tokens=args.out_tokens)
    print(d.summary())
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="frugal", description="Run AI agents cheap, local, and verified.")
    sub = p.add_subparsers(dest="cmd")

    d = sub.add_parser("demo", help="end-to-end offline showcase")
    d.set_defaults(func=cmd_demo)

    r = sub.add_parser("route", help="cascade-route one prompt")
    r.add_argument("prompt")
    r.add_argument("--budget", type=float, default=None)
    r.add_argument("--min-confidence", type=float, default=0.6, dest="min_confidence")
    r.set_defaults(func=cmd_route)

    rc = sub.add_parser("rag", help="RAG eval")
    rc_sub = rc.add_subparsers(dest="rag_cmd")
    check = rc_sub.add_parser("check", help="score a RAG eval json file")
    check.add_argument("file")
    check.set_defaults(func=cmd_rag)

    m = sub.add_parser("mcp", help="show the MCP cost-telemetry tools")
    m.set_defaults(func=cmd_mcp)

    g = sub.add_parser("gateway", help="run the OpenAI-compatible budget gateway")
    g.add_argument("--host", default="127.0.0.1")
    g.add_argument("--port", type=int, default=8080)
    g.add_argument("--budget", type=float, default=None)
    g.set_defaults(func=cmd_gateway)

    dg = sub.add_parser("diagnose", help="project routing savings on YOUR prompt log (offline, no model called, nothing leaves the machine)")
    dg.add_argument("file", help="a .jsonl (prompt/messages) or .txt (one prompt per line) of your prompts")
    dg.add_argument("--current", default="gpt-4o", help="the model you run today (the baseline you're compared against)")
    dg.add_argument("--cheap", default="gpt-4o-mini", help="the cheap/local tier Frugal routes to first")
    dg.add_argument("--frontier", default="gpt-4o", help="the frontier tier Frugal escalates to")
    dg.add_argument("--threshold", type=float, default=0.6, help="offline: complexity to escalate. --live: min confidence to stay cheap")
    dg.add_argument("--out-tokens", type=int, default=300, dest="out_tokens", help="offline: assumed output tokens/request; live: max_tokens cap")
    dg.add_argument("--live", action="store_true", help="MEASURE (not project): actually route every prompt through real models and observe cost/latency/escalation")
    dg.add_argument("--backend", default="ollama", choices=["ollama", "openai"], help="--live backend")
    dg.add_argument("--host", default="http://localhost:11434", help="--live ollama host (point at a local/on-prem server to keep data in-house)")
    dg.add_argument("--base-url", default=None, dest="base_url", help="--live openai-compatible base url")
    dg.add_argument("--confidence", default="verifier", choices=["verifier", "self-consistency", "logprob", "hedge"], help="--live confidence signal for the escalate decision")
    dg.set_defaults(func=cmd_diagnose)

    v = sub.add_parser("version", help="print version")
    v.set_defaults(func=lambda a: (print(__version__), 0)[1])
    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
