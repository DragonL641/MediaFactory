"""Pytest configuration and fixtures for MediaFactory tests.

Test Structure:
- tests/unit/          - 单元测试（全 mock，CI 运行）
- tests/integration/   - 集成测试（需要真实资源，本地按需运行）
- tests/helpers/       - 共享 mock 工具
- tests/data/          - 测试数据
- tests/resources/     - 测试资源
"""

import sys
from pathlib import Path
import pytest

# Add src directory to Python path for testing
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


def pytest_configure(config):
    """Configure pytest settings."""
    config.addinivalue_line("markers", "unit: Fast tests with all dependencies mocked")
    config.addinivalue_line("markers", "integration: Tests requiring real resources")
    config.addinivalue_line("markers", "slow: Tests taking more than 5 seconds")
    config.addinivalue_line("markers", "requires_ml: Tests requiring ML model files")
    config.addinivalue_line("markers", "requires_network: Tests making real network calls")


# ========== Singleton Reset Fixtures ==========


@pytest.fixture(autouse=True)
def reset_singletons():
    """自动重置所有单例实例，确保测试隔离。"""
    yield

    try:
        from mediafactory.config import reset_config_manager
        reset_config_manager()
    except ImportError:
        pass

    try:
        from mediafactory.models.local_models import reset_local_model_manager
        reset_local_model_manager()
    except ImportError:
        pass

    try:
        from mediafactory.resource_manager import reset_resource_manager
        reset_resource_manager()
    except ImportError:
        pass


# ========== Temporary Directory Fixtures ==========


@pytest.fixture
def temp_output_dir(tmp_path: Path) -> Path:
    """Provide a temporary output directory for each test."""
    output_dir = tmp_path / "output"
    output_dir.mkdir(exist_ok=True)
    return output_dir
