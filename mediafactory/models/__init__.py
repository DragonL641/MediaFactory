"""MediaFactory model utilities subpackage.

This module provides model selection, loading, and management utilities.
All translation models use M2M100 architecture with 100+ language support.
"""

from .model_registry import (
    MODEL_REGISTRY,
    WHISPER_MODEL_ID,
    ModelInfo,
    ModelType,
    get_all_translation_models,
    get_display_name,
    get_model_info,
    get_whisper_model_info,
    # 增强模型相关函数（统一注册表）
    get_enhancement_model_by_scale_and_type,
    get_model_local_path,
    is_model_downloaded,
    is_model_complete,
    get_all_model_statuses,
)
from .model_download import (
    delete_model,
    download_model,
    get_models_dir,
)
from .whisper_runtime import load_model, select_device
from .translation_runtime import get_translation_model
from .local_models import LocalModelManager, local_model_manager

__all__ = [
    # Model Registry
    "MODEL_REGISTRY",
    "WHISPER_MODEL_ID",
    "ModelInfo",
    "ModelType",
    "get_all_translation_models",
    "get_display_name",
    "get_model_info",
    "get_whisper_model_info",
    # Model Download
    "delete_model",
    "download_model",
    "get_models_dir",
    # Whisper Runtime
    "load_model",
    "select_device",
    # Translation Runtime
    "get_translation_model",
    # Local Models
    "LocalModelManager",
    "local_model_manager",
    # 视频增强模型（统一注册表）
    "get_enhancement_model_by_scale_and_type",
    "get_model_local_path",
    "is_model_downloaded",
    "is_model_complete",
    "get_all_model_statuses",
]
