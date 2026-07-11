"""Harder prompt set — coding (with edge cases), multi-step reasoning, and
long-context retrieval. Designed so a small model plausibly LOSES to a strong one,
i.e. to break the '100% retention' saturation seen on easy prompts and show where
escalation actually pays off.
"""

_LONG_CONTEXT = (
    "Internal release notes (v3.2.1):\n"
    "- The billing service now retries failed charges up to 3 times with exponential backoff "
    "starting at 400ms.\n"
    "- Feature flag `fast_ledger` was renamed to `ledger_v2` and defaults to OFF in production.\n"
    "- The nightly reconciliation job moved from 02:00 UTC to 03:30 UTC to avoid overlap with "
    "the analytics export, which now finishes at 03:10 UTC.\n"
    "- A regression in the EU region caused duplicate invoices when the `ledger_v2` flag was ON "
    "and the retry count exceeded 2; fixed in this release by de-duplicating on idempotency key.\n"
    "- Support tier SLAs: P0 = 15 minutes, P1 = 2 hours, P2 = 1 business day.\n"
    "- The `/v1/charge` endpoint now rejects amounts above 10,000 USD without a manager token.\n"
)

HARD_PROMPTS = [
    # coding with real edge cases
    "Write a Python function `merge_intervals(intervals)` that merges overlapping intervals. "
    "It must handle: empty input, unsorted input, single interval, and touching intervals like "
    "[1,2],[2,3]. Return the merged list. Include the edge-case handling explicitly.",

    # subtle debugging / concurrency reasoning
    "This Python code deadlocks intermittently:\n"
    "  lock_a=Lock(); lock_b=Lock()\n"
    "  def t1():\n    with lock_a:\n      with lock_b: work()\n"
    "  def t2():\n    with lock_b:\n      with lock_a: work()\n"
    "Explain the exact condition that causes the deadlock and give a concrete fix.",

    # multi-step quantitative reasoning
    "A service handles 50,000 requests/day. 80% are simple (cost $0.0001 each) and 20% are "
    "complex (cost $0.002 each). If a router moves 90% of the complex ones to a cheap tier at "
    "$0.0001 with no quality loss, what is the new daily cost and the percent saved vs before? "
    "Show each step.",

    # long-context retrieval (buried detail)
    _LONG_CONTEXT + "\nQuestion: Under exactly what conditions did duplicate invoices occur in "
    "the EU region, and what specific mechanism fixed it? Answer precisely using only the notes.",

    # long-context + reasoning combined
    _LONG_CONTEXT + "\nQuestion: The analytics export finishes at 03:10 UTC and reconciliation "
    "starts at 03:30 UTC. If analytics slips by 25 minutes, do the jobs overlap? By how long? "
    "Explain using the times in the notes.",

    # precise API-contract question from context
    _LONG_CONTEXT + "\nQuestion: A client tries to POST /v1/charge for 12,000 USD without a "
    "manager token. What happens, and which SLA applies if this triggers a P1 incident?",
]
