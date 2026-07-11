"""Cluster / environment configuration.

Frugal itself runs anywhere (a laptop, a CI runner); the *models* live on your
cluster. Point Frugal at them with env vars — nothing is hard-coded to localhost:

    # cloud / frontier (any OpenAI-compatible endpoint: vLLM, OpenAI, Fireworks...)
    FRUGAL_CLOUD_BASE_URL   e.g. http://gpu-node-0.cluster:8000/v1
    FRUGAL_CLOUD_API_KEY    (any string if the endpoint ignores it)
    FRUGAL_CLOUD_MODEL      e.g. meta-llama/Llama-3.1-70B-Instruct

    # local / cheap (Ollama on a cluster node, or a small vLLM)
    FRUGAL_LOCAL_BASE_URL   e.g. http://cpu-node-3.cluster:11434   (Ollama)
    FRUGAL_LOCAL_MODEL      e.g. llama3

    # budgets
    FRUGAL_BUDGET_USD       e.g. 5.00

`providers_from_env()` builds the (local, cloud) pair from whatever is set and
falls back to the offline MockProvider when nothing is configured — so the same
code runs in CI (mock) and against the cluster (real) with no edits.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional, Tuple

from .providers import MockProvider
from .providers.base import Provider


@dataclass
class ClusterConfig:
    cloud_base_url: Optional[str] = None
    cloud_api_key: Optional[str] = None
    cloud_model: Optional[str] = None
    local_base_url: Optional[str] = None
    local_model: Optional[str] = None
    budget_usd: Optional[float] = None

    @classmethod
    def from_env(cls) -> "ClusterConfig":
        b = os.environ.get("FRUGAL_BUDGET_USD")
        return cls(
            cloud_base_url=os.environ.get("FRUGAL_CLOUD_BASE_URL"),
            cloud_api_key=os.environ.get("FRUGAL_CLOUD_API_KEY", "x"),
            cloud_model=os.environ.get("FRUGAL_CLOUD_MODEL"),
            local_base_url=os.environ.get("FRUGAL_LOCAL_BASE_URL"),
            local_model=os.environ.get("FRUGAL_LOCAL_MODEL", "llama3"),
            budget_usd=float(b) if b else None,
        )

    @property
    def has_cloud(self) -> bool:
        return bool(self.cloud_base_url and self.cloud_model)

    @property
    def has_local(self) -> bool:
        return bool(self.local_base_url)


def providers_from_env() -> Tuple[Provider, Optional[Provider], ClusterConfig]:
    """Return (local_provider, cloud_provider_or_None, config).

    Uses real cluster providers when configured; otherwise MockProvider so the
    exact same script runs offline. `cloud` may be None (local-only cluster)."""
    cfg = ClusterConfig.from_env()

    if cfg.has_local:
        from .providers import get_ollama

        local: Provider = get_ollama(model=cfg.local_model, host=cfg.local_base_url)
    else:
        local = MockProvider()

    cloud: Optional[Provider] = None
    if cfg.has_cloud:
        from .providers import get_openai

        cloud = get_openai(model=cfg.cloud_model, base_url=cfg.cloud_base_url, api_key=cfg.cloud_api_key)
    elif not cfg.has_local:
        cloud = MockProvider()  # full offline: both tiers mocked

    return local, cloud, cfg


def is_cluster_configured() -> bool:
    cfg = ClusterConfig.from_env()
    return cfg.has_cloud or cfg.has_local
