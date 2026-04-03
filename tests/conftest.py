"""Pytest configuration and fixtures for MediaFactory tests.

Test Structure:
- tests/engine/  - 引擎层测试（Mock）
- tests/llm/     - LLM 后端测试（Mock）
- tests/tools/   - 工具层测试（Mock）
- tests/data/    - 测试数据
- tests/resources/ - 测试资源（sample.mp4 用于 FFmpeg 测试）

For real model/API debugging, use scripts/debug/ scripts.
"""

import sys
from pathlib import Path
import pytest

# Add src directory to Python path for testing
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


def pytest_configure(config):
    """Configure pytest settings."""
    config.addinivalue_line("markers", "unit: mark test as unit test")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "slow: mark test as slow running")


# ========== Singleton Reset Fixtures ==========


@pytest.fixture(autouse=True)
def reset_singletons():
    """自动重置所有单例实例，确保测试隔离。

    此 fixture 会在每个测试前后自动执行，重置所有全局单例状态。
    """
    # 测试前不需要做任何事情
    yield

    # 测试后重置所有单例
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


# ========== Resource Path Fixtures ==========


@pytest.fixture(scope="session")
def resources_path() -> Path:
    """Provide the path to test resources directory."""
    return Path(__file__).parent / "resources"


@pytest.fixture(scope="session")
def sample_video_path(resources_path: Path) -> Path:
    """Provide a sample video path for FFmpeg testing.

    Note: The actual video file must be added manually to tests/resources/
    """
    return resources_path / "sample.mp4"


# ========== Temporary Directory Fixtures ==========


@pytest.fixture(scope="session")
def temp_directory(tmp_path_factory):
    """Provide a temporary directory for tests."""
    return tmp_path_factory.mktemp("mediafactory_test")


@pytest.fixture
def temp_output_dir(tmp_path: Path) -> Path:
    """Provide a temporary output directory for each test."""
    output_dir = tmp_path / "output"
    output_dir.mkdir(exist_ok=True)
    return output_dir
