# Launch posts (honest, ready to send — Sardor's voice)

> Rule: real numbers, visible caveats, no hype. The hook is the honest cost truth + a
> reproducible benchmark. Send once the repo is public and CI is green.
> **Timing:** Tue–Thu, 10:00–13:00 ET. First 2 hours matter most — be around to reply.

---

## Show HN
**Title:** Show HN: Frugal – prove (and cut) what your AI agents overpay

**Body:**
I kept watching agents burn frontier-model tokens on trivial steps, so I built Frugal — a
small Python layer that meters every call, routes a cheap/local model first, and escalates to a
strong model only when a real confidence check fails.

On a real cluster an LLM judge rated a 3B model *as good as* a 14B on 83% of hard tasks (100% of
easy ones), at ~4.7×–11× the speed. On real prices that's ~75–91% cheaper (up to ~97% with a
local tier).

The honest part: it can also *lose* money — cascade + a re-sampling confidence signal costs more
than it saves when the cheap model is only ~3× cheaper (e.g. Haiku→Sonnet). Frugal computes this
and warns you. I published where it doesn't work (WEAKNESSES.md) and the full math (BUSINESS_CASE.md).

Everything runs offline on a mock provider (no keys). 56 tests, found and fixed 7 real bugs). Reproduce any claim in ~10s:

    pip install -e . && frugal demo
    python benchmarks/cost_model.py

Repo: https://github.com/SRKRZ23/frugal — feedback very welcome, especially on the eval scope
(it's small and I say so).

---

## r/LocalLLaMA
**Title:** I benchmarked a 3B vs a 14B with an LLM judge — the 3B matched it on 83% of hard tasks. So I built a router around it.

**Body:**
Local-first tool: keep cheap/private work on your own model (Ollama/vLLM, incl. AMD ROCm),
escalate to a big model only when a self-consistency check says the cheap answer isn't trustworthy.
Measured on my cluster (qwen2.5-coder:3b vs phi4:14b, judged by qwen2.5:7b): 3B was "as good as"
the 14B on 83% of hard prompts, ~11× faster on a GTX 1650. Private prompts never leave the box
(tested, 0 leaks). Fully offline demo, no keys. It's early and the eval set is small — numbers are
one command to reproduce. https://github.com/SRKRZ23/frugal

---

## X / Twitter (thread, 2 posts)
1/ Your AI agents are overpaying.

I measured it: a 3B model matched a 14B on 83% of hard tasks (100% of easy), ~4.7–11× faster.
Route the cheap model first, escalate only when a real check fails → 75–97% cheaper.

Open-source, runs offline, reproduce in 10s 👇
https://github.com/SRKRZ23/frugal

2/ The honest bit most tools won't tell you: cascading can *lose* money when the cheap tier isn't
much cheaper (Haiku→Sonnet). Frugal computes that and warns you. I published where it doesn't
work, not just where it does. 56 tests, 0 deps, Apache-2.0.

---

## LinkedIn
Independent builder note: I open-sourced **Frugal** — a drop-in layer that makes AI agents cheaper,
local, and verifiable.

Measured on a real cluster: a 3B model was judged as good as a 14B on 83% of hard tasks (100% of
easy), ~4.7–11× faster → ~75–97% lower inference cost depending on setup. It also ships the
uncomfortable truth: on a small price gap, cascading with a re-sampling check can cost more than it
saves — so the tool warns you instead of quietly overcharging.

56 tests, an 8-dimension stress suite, reproducible benchmarks, and an honest weakness audit.
Runs offline, no API keys. Apache-2.0.

Would love feedback from people running agents in production — what would make you trust (or not
trust) a cost router? https://github.com/SRKRZ23/frugal

#opensource #LLM #AIinfrastructure #localAI

---

## Repo metadata (set on GitHub)
- **Description:** Run AI agents cheap, local, and verified — cost metering + cascade routing +
  eval + an MCP cost server. Offline, zero-dep, Apache-2.0.
- **Topics:** `llm`, `llmops`, `cost-optimization`, `local-llm`, `ollama`, `mcp`, `ai-agents`,
  `openai`, `inference`, `on-prem`
- Pin the repo on your profile; enable Discussions; add the demo GIF to the top of the README.
