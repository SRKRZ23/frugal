"""OpenAI-compatible budget gateway. Point any OpenAI SDK at it (base_url) and it
transparently: meters every call, enforces a hard spend cap, and cascade-routes
cheap->frontier. The pure-python `handle_chat()` is offline-testable; `create_app()`
wraps it in FastAPI when the extra is installed.

    from frugal.gateway import handle_chat
    body = {"messages": [{"role": "user", "content": "hi"}]}
    resp, status = handle_chat(body, provider, meter)
"""
from typing import Optional, Tuple

from ..meter import BudgetExceeded, Meter
from ..providers.base import Provider
from ..providers.mock import MockProvider
from ..route import cascade


def _content_of(m) -> str:
    """Coerce a message's content to a string, tolerating None / numbers / non-dicts."""
    if not isinstance(m, dict):
        return ""
    c = m.get("content", "")
    if c is None:
        return ""
    return c if isinstance(c, str) else str(c)


def _last_user_message(body: dict) -> str:
    msgs = body.get("messages", [])
    if not isinstance(msgs, list) or not msgs:
        return ""
    for m in reversed(msgs):
        if isinstance(m, dict) and m.get("role") == "user":
            return _content_of(m)
    return _content_of(msgs[-1])


def handle_chat(
    body: dict,
    provider: Provider,
    meter: Meter,
    route: bool = True,
) -> Tuple[dict, int]:
    """Return (openai-shaped response, http_status). Never raises on budget —
    returns a 402 body instead, so it behaves like a real gateway."""
    prompt = _last_user_message(body)
    try:
        if route:
            result = cascade(prompt, provider, meter)
            text, model = result.text, result.model_used
        else:
            model = body.get("model", "frugal-mock-mid")
            with meter.track(model) as call:
                r = call.set(provider.complete(prompt, model=model))
            text = r.text
    except BudgetExceeded as e:
        return ({"error": {"type": "budget_exceeded", "message": str(e)}}, 402)

    return (
        {
            "object": "chat.completion",
            "model": model,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": text}, "finish_reason": "stop"}],
            "usage": {
                "prompt_tokens": meter.calls[-1].input_tokens if meter.calls else 0,
                "completion_tokens": meter.calls[-1].output_tokens if meter.calls else 0,
                "total_tokens": (meter.calls[-1].input_tokens + meter.calls[-1].output_tokens) if meter.calls else 0,
            },
            "frugal": {
                "spent_usd": round(meter.total_cost, 6),
                "budget_remaining_usd": (None if meter.budget_usd is None else round(meter.budget_usd - meter.total_cost, 6)),
            },
        },
        200,
    )


def stream_chat(body: dict, provider: Provider, meter: Meter, route: bool = True):
    """OpenAI-compatible streaming: route + meter the call, then yield the answer as
    `chat.completion.chunk` SSE lines. (We stream the routed answer — you can't stream a
    token then decide to escalate, so routing happens first, streaming second.)"""
    import json

    resp, status = handle_chat(body, provider, meter, route=route)
    model = resp.get("model", body.get("model", "frugal-mock-mid"))
    if status != 200:
        yield f"data: {json.dumps(resp)}\n\n"
        yield "data: [DONE]\n\n"
        return
    text = resp["choices"][0]["message"]["content"]

    def chunk(delta, finish=None):
        return "data: " + json.dumps({
            "object": "chat.completion.chunk", "model": model,
            "choices": [{"index": 0, "delta": delta, "finish_reason": finish}],
        }) + "\n\n"

    yield chunk({"role": "assistant"})
    for i, word in enumerate(text.split(" ")):
        yield chunk({"content": ("" if i == 0 else " ") + word})
    yield chunk({}, finish="stop")
    yield "data: [DONE]\n\n"


def create_app(provider: Optional[Provider] = None, budget_usd: Optional[float] = None):  # pragma: no cover - needs fastapi
    try:
        from fastapi import FastAPI, Request
        from fastapi.responses import JSONResponse, StreamingResponse
    except ImportError as e:
        raise ImportError("Install extras:  pip install 'frugal[gateway]'") from e

    provider = provider or MockProvider()
    meter = Meter(budget_usd=budget_usd)
    app = FastAPI(title="Frugal Gateway", version="0.1.0")

    @app.post("/v1/chat/completions")
    async def chat(request: Request):
        body = await request.json()
        if body.get("stream"):
            return StreamingResponse(stream_chat(body, provider, meter),
                                     media_type="text/event-stream")
        resp, status = handle_chat(body, provider, meter)
        return JSONResponse(resp, status_code=status)

    @app.get("/frugal/summary")
    async def summary():
        return meter.summary()

    return app
