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

from .models.local_models import LocalModelManager, local_model_manager
from .batch import (
    BatchProcessor,
    BatchProcessingReport,
    FileProcessingResult,
    ProcessingStatus,
    process_batch,
)

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
    # Batch processing
    "BatchProcessor",
    "BatchProcessingReport",
    "FileProcessingResult",
    "ProcessingStatus",
    "process_batch",
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
    """启动 MediaFactory GUI 应用程序

    这是推荐的应用启动方式，支持：
    - from mediafactory import launch_gui; launch_gui()
    - python -m mediafactory
    - mediafactory (命令行)
    """
    from mediafactory.gui.flet import launch_gui as _launch

    _launch()
