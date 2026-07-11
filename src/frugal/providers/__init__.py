"""Providers: one tiny protocol, many backends. MockProvider is always available
and offline; the rest are lazy so importing `frugal` never needs their SDKs.
"""
from .base import LLMResponse, Provider, count_tokens
from .mock import MockProvider, TIER_MODELS, prompt_complexity

__all__ = [
    "LLMResponse",
    "Provider",
    "count_tokens",
    "MockProvider",
    "TIER_MODELS",
    "prompt_complexity",
    "get_openai",
    "get_ollama",
]


def get_openai(*args, **kwargs):
    """Lazy factory so `frugal[openai]` stays optional."""
    from .openai_provider import OpenAIProvider

    return OpenAIProvider(*args, **kwargs)


def get_ollama(*args, **kwargs):
    from .ollama_provider import OllamaProvider

    return OllamaProvider(*args, **kwargs)
