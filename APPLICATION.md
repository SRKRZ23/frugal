# Claude for Open Source — application draft (Frugal)

> Honest draft. Uses the program's **catch-all** lane ("if you maintain something the
> ecosystem quietly depends on, apply anyway and tell us"). Frugal is new — it does not
> yet meet the download/dependent thresholds, and this draft says so plainly. Fill the
> live numbers before sending; do not overstate. Submit yourself.

**First name:** Sardor
**Last name:** Razikov
**Email:** *(the email on your Claude account)*
**GitHub repo:** github.com/SRKRZ23/frugal  *(select at OAuth step)*

---

**Tell us about the project's reach and impact:**

Frugal is a new, Apache-2.0 LLM-ops toolkit: one Python package that makes any agent
cheaper (cost metering + cascade routing), local (route work to on-prem Ollama/vLLM,
incl. AMD ROCm), and verifiable (offline eval asserts, drift, RAG checks), plus an MCP
server that lets an agent read its own $/token spend. It runs fully offline on a
deterministic mock provider, so it installs and tests with zero setup.

I'm being straight: it's early and does **not** yet clear the 200k-download / 500-dependent
bars. What I can show today is substance, not vanity metrics — 19/19 tests, a measured
benchmark suite (`benchmarks/RESULTS.md`, reproducible) that proves the cost math and
routing/privacy behaviour exactly, and a design aimed squarely at the two things that
generate real dependents: pytest-style eval assertions (`frugal.eval`) that other test
suites import, and an MCP cost server for the fastest-growing tool ecosystem of the year.

*(Before sending, insert live numbers: GitHub stars/forks, PyPI downloads if published,
any external contributors — do not estimate; use the real figures or omit.)*

**How will you use the subscription for your project?**

To build and maintain Frugal at a pace a solo maintainer otherwise can't: expand the
eval/RAG assertion library and provider adapters, harden the MCP server against the
official spec, write docs and examples, and triage issues/PRs. Claude Code is my main
development tool; the Max plan directly translates into more shipped, tested releases and
faster response to contributors.

**Other info:**

Independent builder from Tashkent, Uzbekistan. Related work: REPOMIND (open-source
repo-scale coding agent + LLM cost-router, AMD hackathon winner) — Frugal productizes its
cost-routing layer as a standalone library. I care about the token-tax and on-prem/
sovereign-AI problems Frugal targets, and I maintain it in the open.
