"""配置测试的共享 fixture"""

import pytest
from pathlib import Path


@pytest.fixture
def tmp_config_file(tmp_path):
    """提供临时配置文件路径，测试结束后自动清理"""
    return tmp_path / "test_config.toml"
