"""Frugal MCP server — lets an AI agent introspect its OWN spend and run guardrails.

Tools exposed:
  • get_cost_summary   -> total $, tokens, per-model breakdown (from a live Meter)
  • list_recent_calls  -> the last N calls with model/tokens/cost/latency
  • get_budget_status  -> budget, spent, remaining, over_budget flag
  • guard_prompt       -> PII redaction + prompt-injection check

The core (`FrugalMCP`) is framework-agnostic and fully testable offline via
`.call(tool, **kw)`. If the `mcp` package is installed, `.to_server()` wires the
same tools into a real Model Context Protocol server.
"""
from __future__ import annotations

from typing import Any, Dict

from ..meter import Meter
from .guard import guard_prompt


class FrugalMCP:
    def __init__(self, meter: Meter):
        self.meter = meter

    # --- tool implementations ------------------------------------------------
    def get_cost_summary(self) -> Dict[str, Any]:
        return self.meter.summary()

    def list_recent_calls(self, n: int = 10) -> Dict[str, Any]:
        calls = self.meter.calls[-n:]
        return {
            "calls": [
                {
                    "model": c.model,
                    "tier": c.tier,
                    "input_tokens": c.input_tokens,
                    "output_tokens": c.output_tokens,
                    "cost_usd": round(c.cost_usd, 6),
                    "latency_s": round(c.latency_s, 6),
                }
                for c in calls
            ]
        }

    def get_budget_status(self) -> Dict[str, Any]:
        b = self.meter.budget_usd
        spent = self.meter.total_cost
        return {
            "budget_usd": b,
            "spent_usd": round(spent, 6),
            "remaining_usd": None if b is None else round(b - spent, 6),
            "over_budget": bool(b is not None and spent > b),
        }

    def guard_prompt(self, text: str) -> Dict[str, Any]:
        return guard_prompt(text)

    # --- dispatch (offline-testable) -----------------------------------------
    _TOOLS = ("get_cost_summary", "list_recent_calls", "get_budget_status", "guard_prompt")

    def tools(self):
        return self._TOOLS

    def call(self, name: str, **kwargs) -> Dict[str, Any]:
        if name not in self._TOOLS:
            raise ValueError(f"unknown tool {name!r}; available: {self._TOOLS}")
        return getattr(self, name)(**kwargs)

    # --- optional real MCP server --------------------------------------------
    def to_server(self):  # pragma: no cover - requires `mcp` extra
        try:
            from mcp.server import Server
            from mcp.types import TextContent, Tool
        except ImportError as e:
            raise ImportError("Install extras:  pip install 'frugal[mcp]'") from e

        import json

        server = Server("frugal")

        @server.list_tools()
        async def _list():
            return [
                Tool(name="get_cost_summary", description="Total spend, tokens, per-model breakdown.", inputSchema={"type": "object", "properties": {}}),
                Tool(name="list_recent_calls", description="Last N LLM calls.", inputSchema={"type": "object", "properties": {"n": {"type": "integer"}}}),
                Tool(name="get_budget_status", description="Budget, spent, remaining.", inputSchema={"type": "object", "properties": {}}),
                Tool(name="guard_prompt", description="PII redaction + injection check.", inputSchema={"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}),
            ]

        @server.call_tool()
        async def _call(name: str, arguments: dict):
            result = self.call(name, **(arguments or {}))
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        return server
