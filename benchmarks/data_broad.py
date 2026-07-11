"""Broader, categorized prompt set for a more honest eval. Spans coding, multi-step
reasoning, factual recall, extraction, summarization, and long-context retrieval —
so retention can be reported per category (where the cheap tier holds vs breaks),
not as one saturated number.
"""

_CTX = (
    "Release notes v4.1: billing retries failed charges 3x with 400ms backoff; the flag "
    "`ledger_v2` defaults OFF; reconciliation runs 03:30 UTC (analytics export ends 03:10 UTC); "
    "a duplicate-invoice bug in the EU fired when ledger_v2 was ON and retries exceeded 2, fixed by "
    "idempotency-key dedup; /v1/charge rejects amounts over 10,000 USD without a manager token; "
    "P0 SLA 15 min, P1 2 hours, P2 1 business day."
)

BROAD = [
    ("coding", "Write a Python function `dedupe(xs)` that removes duplicates but keeps first-seen order. Handle empty input."),
    ("coding", "Fix this: `def avg(x): return sum(x)/len(x)` — what breaks and how do you fix it safely?"),
    ("reasoning", "A tank fills in 6h with pipe A and 4h with pipe B. Both open, how long to fill? Show the steps."),
    ("reasoning", "If all Bloops are Razzies and some Razzies are Lazzies, does it follow that some Bloops are Lazzies? Explain."),
    ("factual", "What is the time complexity of binary search and why? One paragraph."),
    ("factual", "Name three ACID properties of a database transaction and define one."),
    ("extraction", _CTX + "\nExtract: what amount triggers a manager-token requirement on /v1/charge?"),
    ("extraction", _CTX + "\nExtract exactly: the P1 SLA and the reconciliation time."),
    ("summarization", "Summarize in one sentence: " + _CTX),
    ("long_context", _CTX + "\nUnder exactly what two conditions did the EU duplicate-invoice bug fire, and what fixed it?"),
    ("long_context", _CTX + "\nAnalytics slips 25 min. Does it overlap reconciliation? By how much? Use the times given."),
    ("creative", "Write a two-line changelog entry announcing that `ledger_v2` is now GA and on by default."),
]
