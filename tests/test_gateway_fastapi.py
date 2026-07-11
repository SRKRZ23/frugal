"""Gateway under real FastAPI — TestClient, concurrency, streaming, budget, malformed."""
import threading

import pytest

pytest.importorskip("fastapi")
from starlette.testclient import TestClient  # noqa: E402

from frugal.gateway import create_app  # noqa: E402


def _client(budget=None):
    return TestClient(create_app(budget_usd=budget))


def test_basic_completion_openai_shape():
    c = _client()
    r = c.post("/v1/chat/completions", json={"messages": [{"role": "user", "content": "say hi"}]})
    assert r.status_code == 200
    body = r.json()
    assert body["choices"][0]["message"]["role"] == "assistant"
    assert body["frugal"]["spent_usd"] > 0


def test_streaming_sse():
    c = _client()
    with c.stream("POST", "/v1/chat/completions",
                  json={"messages": [{"role": "user", "content": "say hi"}], "stream": True}) as r:
        assert r.status_code == 200
        data = "".join(r.iter_text())
    assert data.strip().endswith("data: [DONE]")
    assert '"delta"' in data


def test_malformed_bodies_never_500():
    c = _client()
    for body in [{}, {"messages": "x"}, {"messages": [{}]},
                 {"messages": [{"role": "user", "content": None}]}, {"messages": [{"content": 9}]}]:
        r = c.post("/v1/chat/completions", json=body)
        assert r.status_code in (200, 402), (body, r.status_code)


def test_concurrent_requests_budget_bounded():
    app_client = _client(budget=0.002)
    errors, statuses = [], []
    lock = threading.Lock()

    def worker():
        for _ in range(25):
            try:
                r = app_client.post("/v1/chat/completions",
                                    json={"messages": [{"role": "user", "content": "analyze and prove this deeply"}]})
                with lock:
                    statuses.append(r.status_code)
            except Exception as e:  # noqa: BLE001
                with lock:
                    errors.append(repr(e))

    ts = [threading.Thread(target=worker) for _ in range(16)]
    [t.start() for t in ts]
    [t.join() for t in ts]

    assert not errors, errors[:3]
    assert all(s in (200, 402) for s in statuses)         # never a 500
    summary = app_client.get("/frugal/summary").json()
    # budget respected within bounded overshoot (post-hoc metering under concurrency)
    assert summary["total_cost_usd"] <= 0.002 + 0.02
