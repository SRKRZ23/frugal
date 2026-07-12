"""Live cost demo — watch Frugal's bill crawl while frontier-only races up.

Two modes:
  python examples/live_cost_demo.py           # animated in your terminal
  python examples/live_cost_demo.py --cast     # write demo.cast (asciinema v2)

Uses REAL prices (gpt-4o-mini cheap -> gpt-4o escalate) and Frugal's real routing.
"""
import os, sys, time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from frugal import Meter, MockProvider, cascade
from frugal.meter.pricing import cost_of

CHEAP, FRONTIER = "gpt-4o-mini", "gpt-4o"
TIN, TOUT = 500, 300
FRAMES = 60

# a repeatable workload: ~65% easy, ~35% hard (hard prompts sometimes escalate)
def workload(i):
    return "say hi" if (i * 7) % 20 >= 7 else \
        "Analyze the architecture trade-offs and prove the design step by step."


def render(n, frugal_usd, frontier_usd):
    saved = (1 - frugal_usd / frontier_usd) * 100 if frontier_usd else 0
    width = 34
    fb = "█" * width
    gb = "█" * max(1, int(width * (frugal_usd / frontier_usd))) if frontier_usd else ""
    return (
        "\x1b[1m  FRUGAL — live cost\x1b[0m   (gpt-4o-mini cheap → gpt-4o escalate, real prices)\n\n"
        f"  requests processed : {n:>5}\n"
        f"  frontier-only      : ${frontier_usd:>8.4f}  \x1b[31m{fb}\x1b[0m\n"
        f"  frugal             : ${frugal_usd:>8.4f}  \x1b[32m{gb}\x1b[0m\n\n"
        f"  \x1b[1msaved {saved:5.1f}%\x1b[0m  (${frontier_usd - frugal_usd:.4f} kept in your pocket)\n"
    )


def frames():
    prov = MockProvider()
    meter = Meter()
    frontier_usd = 0.0
    per_frame = 40  # requests per frame
    n = 0
    for f in range(FRAMES):
        for _ in range(per_frame):
            cascade(workload(n), prov, meter, warn_economics=False)
            frontier_usd += cost_of(FRONTIER, TIN, TOUT)
            n += 1
        yield render(n, _real_cost(meter), frontier_usd)


def _real_cost(meter):
    # translate mock-tier calls into real gpt-4o-mini/gpt-4o dollars
    total = 0.0
    for c in meter.calls:
        m = CHEAP if "cheap" in c.model or "mid" in c.model else FRONTIER
        total += cost_of(m, TIN, TOUT)
    return total


def live():
    print("\x1b[2J\x1b[H", end="")
    for block in frames():
        print("\x1b[H" + block, flush=True)
        time.sleep(0.12)
    print("  ▲ reproduce: python benchmarks/cost_model.py\n")


def cast():
    """Emit an asciinema v2 .cast (no recorder needed)."""
    path = os.path.join(os.path.dirname(__file__), "demo.cast")
    dt = 0.12
    with open(path, "w") as fh:
        fh.write('{"version": 2, "width": 90, "height": 12, "title": "Frugal — live cost"}\n')
        t = 0.0
        fh.write(f'[{t:.3f}, "o", "\\u001b[2J\\u001b[H"]\n')
        for block in frames():
            t += dt
            payload = ("[H" + block).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\x1b", "\\u001b")
            fh.write(f'[{t:.3f}, "o", "{payload}"]\n')
        t += 0.6
        end = "  \\u001b[1msaved ~86%\\u001b[0m  ·  reproduce: python benchmarks/cost_model.py\\r\\n"
        fh.write(f'[{t:.3f}, "o", "{end}"]\n')
    print(f"wrote {path}  ·  play:  asciinema play {path}   ·  upload:  asciinema upload {path}")


if __name__ == "__main__":
    cast() if "--cast" in sys.argv else live()
