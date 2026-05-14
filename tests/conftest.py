"""Pytest configuration for cpip testing."""

import pytest
import os
import tempfile
from pathlib import Path

@pytest.fixture
def mock_config(monkeypatch):
    """Provide a mock configuration for tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        home = Path(temp_dir)
        monkeypatch.setenv("CPIP_HOME", str(home))
        
        from client.config import CpipConfig, CloudConfig, RuntimeConfig, CacheConfig, AuthConfig
        
        yield CpipConfig(
            home=str(home),
            cloud=CloudConfig(api_url="http://testserver", ws_url="ws://testserver/ws"),
            runtime=RuntimeConfig(offline_mode=False, gpu_offload=False, import_hooks=True),
            cache=CacheConfig(max_size_mb=100),
            auth=AuthConfig(token="test_token", device_id="test_device")
        )

@pytest.fixture
def mock_cache_dir(mock_config):
    """Provide a temporary cache directory."""
    cache_dir = Path(mock_config.cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir
