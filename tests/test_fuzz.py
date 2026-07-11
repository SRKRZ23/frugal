"""Property/encoding fuzzing (stdlib random, fixed seed -> reproducible).

Throws nasty Unicode (lone surrogates, RTL/zero-width, combining marks, control chars,
astral emoji, nulls, huge repeats) at every text surface and asserts INVARIANTS hold
and nothing crashes. Property tests, not example tests.
"""
import math
import random

from frugal import Meter, MockProvider, ResponseCache, cascade
from frugal.economics import routing_savings
from frugal.eval import assert_semantic, semantic_similarity
from frugal.mcp import detect_injection, guard_prompt, redact_pii
from frugal.meter import cost_of
from frugal.providers.base import count_tokens

NASTY = [0x00, 0x09, 0x0a, 0x1b, 0x7f, 0x200b, 0x200e, 0x202e, 0xFEFF, 0x0301,
         0xD800, 0xDFFF, 0x1F600, 0x4E2D, 0xFFFF, 0x10FFFF,
         ord("a"), ord(" "), ord("@"), ord("4"), ord("."), ord("-")]


def _rand_str(rng):
    n = rng.randint(0, 240)
    s = "".join(chr(rng.choice(NASTY)) for _ in range(n))
    if rng.random() < 0.05:
        s = "a" * rng.randint(0, 20000)   # occasional huge input
    return s


def test_fuzz_all_text_surfaces():
    rng = random.Random(1337)
    prov = MockProvider()
    for _ in range(2500):
        s = _rand_str(rng)

        # count_tokens / cost invariants
        assert count_tokens(s) >= 0
        c = cost_of("some-model", count_tokens(s), count_tokens(s))
        assert c >= 0 and not math.isnan(c)

        # cache: key deterministic, put/get round-trips, never crashes on any unicode
        cache = ResponseCache(normalize=bool(rng.getrandbits(1)))
        assert cache.key(s) == cache.key(s)
        r = prov.complete(s or "x", model="frugal-mock-cheap")
        cache.put(s, r)
        assert cache.get(s) is r

        # guard never crashes; returns the right shapes
        red = redact_pii(s)
        assert isinstance(red["redacted"], str)
        assert isinstance(detect_injection(s), list)
        g = guard_prompt(s)
        assert set(g) >= {"safe", "redacted_prompt", "pii_found", "injection_signals"}

        # semantic_similarity always in [0,1]; identical strings score high-ish
        sim = semantic_similarity(s, s)
        assert 0.0 <= sim <= 1.0
        sim2 = semantic_similarity(s, _rand_str(rng))
        assert 0.0 <= sim2 <= 1.0

        # assert_semantic must ONLY raise AssertionError (never a crash)
        try:
            assert_semantic(s, s, threshold=0.0)   # threshold 0 -> should pass
        except AssertionError:
            pass


def test_fuzz_cascade_never_crashes():
    rng = random.Random(7)
    prov = MockProvider()
    for _ in range(1500):
        s = _rand_str(rng)
        meter = Meter(budget_usd=rng.choice([None, 1.0, 1e-9]))
        try:
            res = cascade(s, prov, meter, cache=ResponseCache())
            assert res.response is not None
        except Exception as e:  # noqa: BLE001
            from frugal.meter import BudgetExceeded
            assert isinstance(e, BudgetExceeded), f"cascade crashed on {s!r}: {e!r}"
        # ledger invariant: total == dropped + live, never NaN/negative
        assert meter.total_cost >= 0 and not math.isnan(meter.total_cost)
        assert abs(meter.total_cost - (meter._drop["cost"] + meter._live["cost"])) < 1e-9


def test_fuzz_economics_no_div0_or_nan():
    rng = random.Random(99)
    models = ["gpt-4o-mini", "gpt-4o", "claude-haiku", "claude-sonnet", "local", "llama-8b"]
    for _ in range(500):
        r = routing_savings(rng.choice(models), rng.choice(models),
                            confidence=rng.choice(["free", "self_consistency"]),
                            easy_frac=rng.random())
        assert not math.isnan(r["saved_pct"])
        assert isinstance(r["will_save"], bool)
