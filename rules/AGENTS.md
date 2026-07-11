# Cost-Aware Agent Rules (`AGENTS.md` / `CLAUDE.md`)

Drop this into a repo to make any coding agent spend fewer tokens without getting
dumber. Ten rules, in priority order.

1. **Read before you write.** Grep/inspect the exact file and lines first; never
   regenerate context you can retrieve. Retrieval is cheaper than generation.
2. **Cheapest model that can do the job.** Start on a small/local model; escalate
   to a frontier model only when the small one hedges or fails a check
   (see `frugal.route.cascade`).
3. **Keep private/short work local.** If a prompt is tagged private or is short and
   simple, run it on-device (Ollama/vLLM), not the cloud API.
4. **No speculative fan-out.** Don't spawn parallel agents "just in case." Fan out
   only when the work is genuinely independent and each branch pays for itself.
5. **Bounded context.** Send the minimal slice — the relevant function, not the
   whole file; the whole file, not the whole repo.
6. **Cache and reuse.** Memoize tool results and sub-answers within a task; don't
   re-ask what you already know.
7. **Stop when done.** No victory-lap re-summaries, no re-reading files you just
   edited — the edit tool already confirmed success.
8. **Verify cheaply.** Gate outputs with offline checks first (`frugal.eval`
   asserts, schema validation) before paying a model to judge.
9. **Meter everything.** Every call goes through a cost meter; surface `$ spent`
   so humans can see the bill (`frugal.mcp` exposes it to the agent itself).
10. **Budget is a hard cap.** When the budget is hit, stop and report — don't
    silently keep spending.

> These pair with the `frugal` toolkit, but they stand alone — copy them into your
> agent's system prompt or repo root as-is.
