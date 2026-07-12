# Frugal for the enterprise — the token-tax is real money now

**[🇷🇺 Русский](ENTERPRISE.ru.md)**

If you run agents at scale, inference isn't a line item any more — it's the bill. Frugal is the
control layer that routes most of it to a cheaper/local model, proves quality didn't drop, and caps
the spend. Here's the case, with real, cited numbers.

## Who's burning it — the 2026 roster

| Company | The 2026 fact | Source |
|---|---|---|
| **Meta** | AI capex raised to **$125–145B**; ~$25B/qtr already going to short-lived **inference** silicon | [Krasa](https://www.krasa.ai/news/meta-2026-ai-capex-145-billion-infrastructure-bet) |
| **Amazon** | ~**$200B** AI capex 2026; Bedrock now hosts Anthropic + Grok inference | [ValueAdd](https://valueaddvc.com/ai-spending) |
| **Google** | Gemini serving **1.3 quadrillion tokens / month** | [Krasa/Statista](https://www.krasa.ai/news/meta-2026-ai-capex-145-billion-infrastructure-bet) |
| **Microsoft** | ~$120B capex; **GitHub Copilot moved to token-metered billing** (June 2026 "meter shock") | [Windows Forum](https://windowsforum.com/threads/copilot-to-usage-billing-june-1-2026-ai-credits-token-costs-and-meter-shock.420900/) |
| **xAI** | Anthropic pays xAI **$1.25B/month** for Colossus compute; **>1M API calls/day** | [Enterprise DNA](https://enterprisedna.co/resources/news/anthropic-xai-colossus-1-25-billion-compute-economics-2026/) |
| **Palantir** | CEO: token pricing is **"completely broken"** → Palantir+Nvidia ship **air-gapped, no-hosted-API** AI | [TechTimes](https://www.techtimes.com/articles/319702/20260704/palantir-nvidia-launch-air-gapped-ai-stack-token-billing-cracks-enterprise-budgets.htm) |
| **Oracle** | OCI Enterprise AI; hosts Palantir Foundry/AIP inference | [Oracle](https://docs.oracle.com/en/solutions/palantir-foundry-ai-platform-on-oci/index.html) |
| **Salesforce** | Token costs forced a rethink → Agentforce **resolution-based** pricing, credits at $0.10/action | [BigGo](https://finance.biggo.com/news/d50e3253-faf4-4f76-b5f9-18134d747e5e) |
| **Uber** | **Burned its entire 2026 AI-coding budget by April** (dev usage 32% → 84% in 3 months) | [CNBC](https://www.cnbc.com/2026/06/26/openai-anthropic-new-ai-spending-reality-as-users-shift-to-efficiency.html) |
| **Klarna** | AI assistant: **2.3M conversations/month**, work of ~850 agents | [Klarna](https://www.klarna.com/international/press/klarna-ai-assistant-handles-two-thirds-of-customer-service-chats-in-its-first-month/) |
| **A Fortune-500 firm** | **$500M on Claude in a single month** — no spending caps | [Optimum](https://optimumpartners.com/insight/ai-token-costs-and-how-they-might-wreck-your-budget/) |
| **Industry** | Enterprise LLM spend **$8.4B → doubling**; **inference = 85% of the AI budget**; market $66B→$292B by 2029 | [Oplexa](https://oplexa.com/ai-inference-cost-crisis-2026/) |

Token *prices* fell ~280× in two years, yet total spend **rose ~320%** — because agentic volume
exploded (10–20 calls per task, RAG inflating context 3–5×, always-on agents). **Cheaper tokens don't
save you. Routing what doesn't need the big model does.** Palantir's CEO is already saying it out loud
— and pushing the exact local-first / on-prem direction Frugal is built for.

## What Frugal saves, by monthly inference spend

Frugal routes calls that don't need the frontier model to a cheap/local one and escalates only when a
real check fails — saving **~50–75% of routable spend** (we *measure* 75–91% on the cheap-tier
fraction; this range is deliberately conservative for a blended enterprise load). Modeled at published
2026 API prices — reproduce with `python benchmarks/cost_model.py`:

| Monthly inference spend | Frugal saves / month | Frugal saves / year |
|---|---|---|
| $100,000 | **$50k – $75k** | $0.6M – $0.9M |
| $1,000,000 | **$0.5M – $0.75M** | $6M – $9M |
| $10,000,000 | **$5M – $7.5M** | $60M – $90M |
| $50,000,000 (Fortune-500 tier) | **$25M – $37.5M** | $300M – $450M |

## The situations Frugal is built for

- **"Uber burned its budget by April."** Thread-safe **hard budget cap** + `reserve()` (refuse before
  spending) → the budget can't be blown silently; routing stretches it 2–4×.
- **"$500M on Claude in a month, no caps."** Exactly what the budget gateway prevents — every
  key/tenant gets a cap and a live $/token view (MCP server).
- **Palantir's "air-gapped, no hosted API" push.** Frugal's **local-first routing** keeps private/simple
  work on your own GPUs (0 leaks, tested) and only escalates to a hosted frontier when truly needed.
- **Klarna-scale support (2.3M chats/mo ≈ 6.9M calls).** Most turns are simple → cheap tier; hard ones
  escalate. Modeled token saving ≈ **$210k/yr** on that volume alone.
- **Coding agents (the Uber/Copilot pattern).** Trivial edits → cheap/local; real reasoning → frontier.

## Why it's safe to route (not just cheap)

We **measured** it: an LLM judge rated a 3B model *as good as* a 14B on **83% of hard tasks (100% of
easy)**, and Frugal escalates the rest. We also publish where routing **doesn't** pay off. Full math +
caveats: [BUSINESS_CASE.md](BUSINESS_CASE.md) · [WEAKNESSES.md](WEAKNESSES.md).

## For a pilot

Point one workload's OpenAI base-url at the Frugal gateway, set a budget, keep your models. Measure the
drop for a week. → **razikovsardor1@gmail.com** · [github.com/SRKRZ23/frugal](https://github.com/SRKRZ23/frugal)

*Savings figures are modeled at published 2026 API prices and a conservative routable-share assumption;
your actual mix determines the result. Company facts are cited public reports; Frugal is not affiliated
with, or endorsed by, any company named.*
