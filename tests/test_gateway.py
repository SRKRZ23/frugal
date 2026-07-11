from frugal import Meter, MockProvider
from frugal.gateway import handle_chat


def test_gateway_returns_openai_shape():
    meter = Meter()
    body = {"messages": [{"role": "user", "content": "say hi"}]}
    resp, status = handle_chat(body, MockProvider(), meter)
    assert status == 200
    assert resp["choices"][0]["message"]["role"] == "assistant"
    assert resp["frugal"]["spent_usd"] > 0


def test_gateway_402_on_budget():
    meter = Meter(budget_usd=1e-9)
    body = {"messages": [{"role": "user", "content": "expensive " * 40}]}
    resp, status = handle_chat(body, MockProvider(), meter)
    assert status == 402
    assert resp["error"]["type"] == "budget_exceeded"
