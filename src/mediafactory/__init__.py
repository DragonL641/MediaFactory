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
    get_config_manager,
    get_config,
    save_config,
    update_config,
    AppConfigManager,
    AppConfig,
)

# Model management - lazy import to avoid requiring ML dependencies at startup
# These will be available after ML dependencies are installed via Setup Wizard
LocalModelManager = None
local_model_manager = None


def __getattr__(name):
    """Lazy import for model-related names that require ML dependencies."""
    global LocalModelManager, local_model_manager

    if name in ("LocalModelManager", "local_model_manager"):
        from .models.local_models import LocalModelManager as _LocalModelManager
        from .models.local_models import local_model_manager as _local_model_manager

        LocalModelManager = _LocalModelManager
        local_model_manager = _local_model_manager

        if name == "LocalModelManager":
            return LocalModelManager
        elif name == "local_model_manager":
            return local_model_manager

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# Core framework
from .core import (
    CancellationToken,
)

# Pipeline and Engine (new simplified architecture)
from .pipeline import (
    Pipeline,
    ProcessingContext,
    ProcessingResult,
)
from .engine import (
    AudioEngine,
    RecognitionEngine,
    TranslationEngine,
    SRTEngine,
)

__all__ = [
    # Configuration system
    "get_config_manager",
    "get_config",
    "save_config",
    "update_config",
    "AppConfigManager",
    "AppConfig",
    # Model management
    "LocalModelManager",
    "local_model_manager",
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
    # GUI entry point
    "launch_gui",
]


def launch_gui():
    """启动 MediaFactory API 服务器

    这是推荐的应用启动方式，支持：
    - from mediafactory import launch_gui; launch_gui()
    - python -m mediafactory
    - mediafactory (命令行)

    注意：GUI 功能已迁移到 Electron 前端。
    此函数现在启动 FastAPI 后端服务。
    """
    from mediafactory.api.main import start_server

    start_server()
