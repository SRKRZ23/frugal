"""Regression tests for bugs the deep pressure suite (benchmarks/stress_deep.py) found."""
import pytest

from frugal import Meter, MockProvider, cascade
from frugal.gateway import handle_chat, stream_chat


@pytest.mark.parametrize("bad_fn", [
    lambda p, r, pr: (_ for _ in ()).throw(ValueError("boom")),  # raises
    lambda p, r, pr: None,                                       # returns None
    lambda p, r, pr: float("nan"),                               # NaN
    lambda p, r, pr: "not a number",                             # wrong type
])
def test_cascade_survives_broken_confidence(bad_fn):
    """A hostile/buggy confidence function must not crash routing — it fails safe (escalates)."""
    res = cascade("analyze and prove this", MockProvider(), Meter(), confidence_fn=bad_fn)
    assert res.response is not None            # got an answer, no exception
    assert res.model_used                       # a real tier answered


@pytest.mark.parametrize("body", [
    {}, {"messages": "not-a-list"}, {"messages": []}, {"messages": [{}]},
    {"messages": [{"role": "user", "content": None}]},
    {"messages": [{"content": 12345}]},
])
def test_gateway_survives_malformed_body(body):
    """Garbage request bodies must not crash the gateway (json + streaming paths)."""
    resp, status = handle_chat(body, MockProvider(), Meter())
    assert status in (200, 402)
    chunks = list(stream_chat(body, MockProvider(), Meter()))
    assert chunks[-1] == "data: [DONE]\n\n"


def test_summary_is_lock_snapshotted():
    """summary() must snapshot under the lock so it never tears mid-append. Bounded with
    max_history so the ledger stays small (snapshot O(1)) and the test can't hang."""
    import threading
    meter, prov = Meter(max_history=500), MockProvider()
    stop = threading.Event()

    def writer():
        while not stop.is_set():
            with meter.track("frugal-mock-cheap") as c:
                c.set(prov.complete("x", model="frugal-mock-cheap"))
    t = threading.Thread(target=writer)
    t.start()
    try:
        for _ in range(1000):
            meter.summary()          # must never raise (torn iteration)
    finally:
        stop.set()
        t.join(timeout=5)
