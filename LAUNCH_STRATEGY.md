# Frugal — honest launch strategy (how to earn attention without pretending)

> Straight talk first: **you cannot manufacture a MiroFish overnight.** 33k stars +
> $4M in 24h is an outlier driven by a jaw-dropping "predict the future" demo, a bold
> (unvalidated) claim, funding-news flywheel, and Chinese dev-community amplification.
> Frugal is *infrastructure* — it wins slowly by being depended-on, not by one viral day.
> This doc maximizes the odds of both: a strong launch spike **and** durable growth.

## 1. What actually makes the hyped repos blow up

| Repo | Why it went viral | Transferable lesson |
|---|---|---|
| **MiroFish** (33k★, $4M/24h) | a *screenshot-able* "spin up 1000 agents, predict the future" demo + a bold claim + funding news + CN community | one **jaw-dropping demo** + a **bold, contrarian narrative** |
| **OpenClaw** (210k★) | local-first personal AI that connects to WhatsApp/Slack/etc; famous founder; rode a moment | **local-first + "connects to your life"** + founder reach |
| **MCP servers** (97M dl) | rode Anthropic's standard as a platform tailwind | **ride a platform wave**, don't fight it |
| **Karpathy CLAUDE.md** (156k★) | one tiny file, zero deps, answered a famous person's public complaint the same day | **tiny + timely**, solve a shared pain instantly |
| **Ollama / Open WebUI** | became the *default tool* of the local-AI movement | **be the default utility** for a movement |

Common thread: **a demo you can screenshot, a narrative you can argue about, and timing.**
Infra tools (Frugal) rarely get the demo-wow — so we lean on **narrative + numbers + being depended-on.**

## 2. Frugal's honest position

- Frugal is **not** a wow-demo product; it's a **cost/routing/eval utility.** That means the
  realistic growth engine is **dependents + downloads** (pytest asserts other suites import,
  an MCP server, a drop-in gateway) — slower than a viral day, but durable, and it's exactly
  what the **Claude-for-OSS** program rewards.
- We DO have one genuinely shareable, contrarian hook, and it's **backed by measured numbers**:

  > **"Your AI agents are overpaying. Measured: a 3B model matched a 14B on 83% of hard tasks
  > (100% of easy ones) at ~4.7× the speed. Route down, escalate the rest — **~75–91% cheaper on
  > cloud, up to ~97% with a local tier** (real prices, `BUSINESS_CASE.md`)."**

  That's a debate-worthy claim with a reproducible benchmark behind it (`benchmarks/RESULTS_MODELS*.md`).
  It rides the #1 tailwind of 2026 — the **token tax / "agentic AI is sending the bill soaring."**

## 3. The plan (concrete, in order)

**A. Sharpen to ONE flagship message.** Lead with cost-routing (`meter` + `route`), not the whole
kitchen sink. The other five modules are "and it also…". One sentence: *"Frugal proves your agents
are overpaying and routes around it — cheap/local first, escalate only when a real check says so."*

**B. Make it screenshot-able (the infra version of a wow-demo):**
- a 30-second **asciinema** of `frugal demo` (cost drops in real time, MCP shows the bill)
- the **benchmark table** as a clean image (3B ≈ 14B on 83%, 4.7× faster) — that's the shareable artifact
- one diagram: prompt → meter → cheap/local → (low confidence?) → escalate.

**C. README that converts** (README is the product for a repo): hook in the first two lines,
GIF, "why", copy-paste quickstart that runs offline in 10s, the honest benchmark, the caveats
(honesty *is* a trust signal for infra).

**D. Launch, Tue–Thu 10:00–13:00 ET, first 2 hours matter:**
- **Show HN:** *"Show HN: Frugal – measure (and cut) what your AI agents overspend"* — HN rewards
  measured, contrarian, honest infra with real numbers and visible caveats.
- **r/LocalLLaMA + r/selfhosted:** they love local-first + cost + on-prem — lead with the 3B≈14B
  result and the cluster/Ollama story.
- **X/LinkedIn:** the one benchmark image + the one-line claim. Tag the token-tax conversation.
- Ride the **platform tailwind**: it's an **MCP server** (hot ecosystem) and an **on-prem/AMD**
  story (your existing AMD orbit) — mention both.

**E. Convert stars → dependents (the durable engine):** land `frugal.eval` asserts and the MCP
server as things people *install into their pipeline*. Answer every issue/PR fast for two weeks.
That's what turns a spike into the Claude-for-OSS-qualifying metrics.

## 4. Honest odds & targets (no hype)

- **Most infra repos** get hundreds→low-thousands of stars, not tens of thousands. MiroFish-level
  is a lottery outcome; don't bank on it.
- **Realistic good outcome** with strong execution: an HN front-page spike (≈ few hundred → couple
  thousand stars if it lands), then steady dependent/download growth. That's a *win* and it's what
  the OSS program actually cares about.
- **What would break the ceiling:** a genuinely novel, screenshot-able artifact (e.g. a live
  "watch your agent's bill" dashboard) or a well-known dev quoting the 3B≈14B result. Engineer for
  the shareable artifact; you can't engineer the luck.

**Bottom line:** don't chase MiroFish's fireworks. Ship the honest cost-truth with a reproducible
benchmark, make it trivially installable, launch it well, and support it hard for two weeks. That
earns real developers — and real developers are what big tech actually notices.
