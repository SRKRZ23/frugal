import os

from frugal.config import ClusterConfig, is_cluster_configured, providers_from_env
from frugal.providers import MockProvider


def test_offline_falls_back_to_mock(monkeypatch):
    for k in ("FRUGAL_CLOUD_BASE_URL", "FRUGAL_CLOUD_MODEL", "FRUGAL_LOCAL_BASE_URL"):
        monkeypatch.delenv(k, raising=False)
    local, cloud, cfg = providers_from_env()
    assert isinstance(local, MockProvider)
    assert isinstance(cloud, MockProvider)
    assert not is_cluster_configured()


def test_env_config_flags(monkeypatch):
    monkeypatch.setenv("FRUGAL_LOCAL_BASE_URL", "http://cpu-node:11434")
    monkeypatch.setenv("FRUGAL_CLOUD_BASE_URL", "http://gpu-node:8000/v1")
    monkeypatch.setenv("FRUGAL_CLOUD_MODEL", "big-model")
    cfg = ClusterConfig.from_env()
    assert cfg.has_local and cfg.has_cloud
    assert is_cluster_configured()
