"""MediaFactory model utilities subpackage.

This module provides model selection, loading, and management utilities.
All translation models use MADLAD400 architecture with 400+ language support.
"""

from .model_registry import (
    MODEL_REGISTRY,
    WHISPER_MODEL_ID,
    LicenseType,
    ModelInfo,
    ModelType,
    get_all_translation_models,
    get_all_whisper_models,
    get_available_memory_for_device,
    get_available_memory_gb,
    get_available_vram_gb,
    get_best_translation_model_for_installation,
    get_display_name,
    get_model_info,
    get_recommended_translation_models,
    get_required_memory_for_model,
    get_system_total_memory_gb,
    get_total_vram_gb,
    get_translation_model_info,
    get_whisper_model_info,
    is_model_commercial_use_allowed,
    select_best_translation_model,
    # 增强模型相关函数（统一注册表）
    get_all_enhancement_models,
    get_enhancement_models_by_type,
    get_enhancement_model_by_scale_and_type,
    is_enhancement_model,
    get_enhancement_models_dir,
    get_model_local_path,
    is_model_downloaded,
    is_model_complete,
    get_all_model_statuses,
    ENHANCEMENT_MODEL_REGISTRY,
)
from .model_download import (
    delete_model,
    download_model,
    get_downloaded_size,
    get_model_total_size,
    get_models_dir,
)
from .memory_detection import (
    MemoryInfo,
    ModelRecommendation,
    format_memory_size,
    get_memory_info,
    get_memory_tier_description,
    get_runtime_model_selection,
    get_translation_model_recommendations,
)
from .whisper_runtime import get_compute_type, load_model, select_device
from .translation_runtime import get_translation_model
from .local_models import LocalModelManager, local_model_manager

__all__ = [
    # Model Registry
    "MODEL_REGISTRY",
    "WHISPER_MODEL_ID",
    "LicenseType",
    "ModelInfo",
    "ModelType",
    "get_all_translation_models",
    "get_all_whisper_models",
    "get_available_memory_for_device",
    "get_available_memory_gb",
    "get_available_vram_gb",
    "get_best_translation_model_for_installation",
    "get_display_name",
    "get_model_info",
    "get_recommended_translation_models",
    "get_required_memory_for_model",
    "get_system_total_memory_gb",
    "get_total_vram_gb",
    "get_translation_model_info",
    "get_whisper_model_info",
    "is_model_commercial_use_allowed",
    "select_best_translation_model",
    # Model Download
    "delete_model",
    "download_model",
    "get_downloaded_size",
    "get_model_total_size",
    "get_models_dir",
    # Memory Detection
    "MemoryInfo",
    "ModelRecommendation",
    "format_memory_size",
    "get_memory_info",
    "get_memory_tier_description",
    "get_runtime_model_selection",
    "get_translation_model_recommendations",
    # Whisper Runtime
    "get_compute_type",
    "load_model",
    "select_device",
    # Translation Runtime
    "get_translation_model",
    # Local Models
    "LocalModelManager",
    "local_model_manager",
    # 视频增强模型（统一注册表）
    "get_all_enhancement_models",
    "get_enhancement_models_by_type",
    "get_enhancement_model_by_scale_and_type",
    "is_enhancement_model",
    "get_enhancement_models_dir",
    "get_model_local_path",
    "is_model_downloaded",
    "is_model_complete",
    "get_all_model_statuses",
    "ENHANCEMENT_MODEL_REGISTRY",
]
