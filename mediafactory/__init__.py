"""MediaFactory - Professional multimedia processing platform.

Formerly known as VideoDub. Provides subtitle generation, audio extraction,
speech-to-text transcription, and translation capabilities.
"""

# Version is dynamically loaded from pyproject.toml (single source of truth)
from ._version import __version__

__author__ = "Dragon"
__email__ = "fldx123456@163.com"

# Configuration system (new - Pydantic v2 + TOML)
from .config import (
    AppConfig,
    AppConfigManager,
    get_config,
    get_config_manager,
    save_config,
    update_config,
)
from .core import (
    CancellationToken,
)
from .engine import (
    AudioEngine,
    RecognitionEngine,
    SRTEngine,
    TranslationEngine,
)

# Pipeline and Engine (new simplified architecture)
from .pipeline import (
    Pipeline,
    ProcessingContext,
    ProcessingResult,
)

__all__ = [
    # Version
    "__version__",
    # Configuration system
    "get_config_manager",
    "get_config",
    "save_config",
    "update_config",
    "AppConfigManager",
    "AppConfig",
    # Core framework
    "CancellationToken",
    # Pipeline and Engine (simplified architecture)
    "Pipeline",
    "ProcessingContext",
    "ProcessingResult",
    "AudioEngine",
    "RecognitionEngine",
    "TranslationEngine",
    "SRTEngine",
    # Server entry point
    "launch_server",
]


def launch_server():
    """启动 MediaFactory API 服务器

    这是推荐的应用启动方式，支持：
    - from mediafactory import launch_server; launch_server()
    - python -m mediafactory
    - mediafactory (命令行)
    """
    from mediafactory.api.main import start_server

    start_server()
