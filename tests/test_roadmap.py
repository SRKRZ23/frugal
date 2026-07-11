import json

from frugal import Meter, MockProvider, cascade
from frugal.gateway import handle_chat, stream_chat
from frugal.route import make_logprob_confidence


def test_logprob_confidence_routes_and_is_free():
    conf = make_logprob_confidence()
    prov = MockProvider()

    # easy prompt: cheap model is confident -> stays cheap, ONE call (no extra probes)
    m1 = Meter()
    r1 = cascade("say hi", prov, m1, confidence_fn=conf)
    assert r1.model_used == "frugal-mock-cheap"
    assert len(m1.calls) == 1

    # hard prompt: cheap model's logprob is low -> escalates
    m2 = Meter()
    r2 = cascade("Analyze the architecture and prove the optimal refactor step by step",
                 prov, m2, confidence_fn=conf)
    assert r2.escalated is True
    # logprob signal adds NO extra calls beyond the ladder tiers tried
    assert len(m2.calls) == len(r2.tiers_tried)


def test_logprob_confidence_value_from_logprob():
    conf = make_logprob_confidence()
    prov = MockProvider()
    easy = prov.complete("hi", model="frugal-mock-cheap")
    hard = prov.complete("prove and analyze this complex architecture in depth", model="frugal-mock-cheap")
    assert conf(prov, easy, "hi") > conf(prov, hard, "prove ...")   # easy more confident


def test_streaming_gateway_reconstructs_answer():
    meter = Meter()
    body = {"messages": [{"role": "user", "content": "say hello"}]}
    chunks = list(stream_chat(body, MockProvider(), Meter()))
    assert chunks[-1] == "data: [DONE]\n\n"
    # reconstruct the streamed content
    text = ""
    for c in chunks:
        if c.startswith("data: ") and "[DONE]" not in c:
            delta = json.loads(c[6:])["choices"][0]["delta"]
            text += delta.get("content", "")
    # matches the non-streamed answer
    resp, _ = handle_chat(body, MockProvider(), meter)
    assert text.strip() == resp["choices"][0]["message"]["content"].strip()


def test_streaming_respects_budget_402():
    meter = Meter(budget_usd=1e-9)
    body = {"messages": [{"role": "user", "content": "expensive " * 40}]}
    chunks = list(stream_chat(body, MockProvider(), meter))
    assert any("budget_exceeded" in c for c in chunks)
    assert chunks[-1] == "data: [DONE]\n\n"
