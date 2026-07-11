"""Frugal — run AI agents cheap, local, and verified.

One drop-in stack that makes any LLM agent:
  • cheaper     -> frugal.meter (cost/token accounting) + frugal.route (cascade routing)
  • local       -> frugal.local (route local<->cloud, Ollama/vLLM/AMD adapters)
  • verifiable  -> frugal.eval (semantic asserts, drift) + frugal.rag (retrieval checks)
  • self-aware  -> frugal.mcp (an MCP server that reports the agent's own $/token spend)

Everything runs fully offline with the built-in MockProvider (no API keys needed),
so the whole toolkit is testable and demo-able out of the box.
"""

from .meter import Meter, count_tokens
from .route import cascade
from .providers import MockProvider, LLMResponse
from .cache import ResponseCache

__version__ = "0.1.0"
__all__ = ["Meter", "count_tokens", "cascade", "MockProvider", "LLMResponse",
           "ResponseCache", "__version__"]
