"""Unified model registry for MediaFactory.

This module provides a centralized registry for all models (Whisper and translation),
with memory-aware selection and license tracking for commercial use compliance.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import psutil

from ..logging import log_warning


# Memory tier definitions (GB)
MEMORY_TIERS = [8, 16, 32, 64, 128]


def get_memory_tier(value_gb: float) -> int:
    """Round memory value up to the nearest tier.

    Args:
        value_gb: Memory value in gigabytes

    Returns:
        Nearest memory tier (8, 16, 32, 64, or 128)
    """
    for tier in MEMORY_TIERS:
        if value_gb <= tier:
            return tier
    return MEMORY_TIERS[-1]


class ModelType(Enum):
    """Model type enumeration."""

    WHISPER = "whisper"
    TRANSLATION = "translation"


class LicenseType(Enum):
    """Model license type enumeration."""

    APACHE_2_0 = "apache_2_0"  # Commercial use allowed
    MIT = "mit"  # Commercial use allowed


@dataclass
class ModelInfo:
    """Unified model information.

    Attributes:
        model_id: Internal identifier (e.g., "whisper-large-v3", "madlad400-3b-q4k")
        huggingface_id: HuggingFace model ID for downloading
        display_name: Human-readable display name
        model_type: Type of model (WHISPER or TRANSLATION)
        model_size_gb: Model file size in gigabytes
        runtime_memory_gb: Estimated runtime memory usage in gigabytes (CPU)
        recommended_system_gb: Recommended system RAM (can be manually set)
        license: Model license type
        language_support: Description of language support
        precision: Model precision (fp32, fp16, q4k, q8k)
        requires_prompt: Whether the model requires special prompt formatting
        description: Brief model description
        gguf_file: GGUF filename for quantized models (optional)
        runtime_vram_gb: Estimated runtime VRAM usage for GPU (0 if not applicable)
        recommended_vram_gb: Recommended VRAM for GPU (0 if not applicable)
    """

    model_id: str
    huggingface_id: str
    display_name: str
    model_type: ModelType
    model_size_gb: float
    runtime_memory_gb: float
    license: LicenseType
    language_support: str
    precision: str
    recommended_system_gb: int = 0  # 0 means auto-calculate
    requires_prompt: bool = False
    description: str = ""
    gguf_file: Optional[str] = None  # GGUF filename for quantized models
    runtime_vram_gb: float = 0.0  # GPU runtime VRAM
    recommended_vram_gb: int = 0  # Recommended VRAM

    def __post_init__(self):
        """Calculate recommended system memory if not manually set."""
        if self.recommended_system_gb == 0:
            # Formula: runtime_memory × 4, rounded up to nearest tier
            self.recommended_system_gb = get_memory_tier(self.runtime_memory_gb * 4)


# Unified model registry
# Unified model registry
# 键直接使用 huggingface_id，与 HuggingFace 一致
MODEL_REGISTRY: dict[str, ModelInfo] = {
    # ========== Whisper Models ==========
    "Systran/faster-whisper-large-v3": ModelInfo(
        model_id="Systran/faster-whisper-large-v3",  # 与 huggingface_id 一致
        huggingface_id="Systran/faster-whisper-large-v3",
        display_name="Whisper Large V3",
        model_type=ModelType.WHISPER,
        model_size_gb=3.0,
        runtime_memory_gb=10.0,
        recommended_system_gb=16,  # Optimized for 16GB systems
        license=LicenseType.MIT,
        language_support="99+ languages",
        precision="float16",
        description="Best quality Whisper model for transcription",
    ),
    # ========== Translation Models ==========
    # 所有翻译模型使用 MADLAD400 (Apache 2.0 许可证，支持商用)
    # GGUF Q4K 量化版本：磁盘占用小、内存占用低、质量接近原版
    # 16GB 级别（CPU） / 8GB VRAM（GPU）
    "google/madlad400-3b-mt": ModelInfo(
        model_id="google/madlad400-3b-mt",  # 与 huggingface_id 一致
        huggingface_id="google/madlad400-3b-mt",
        gguf_file="madlad400-3b.Q4_K_M.gguf",
        display_name="MADLAD400-3B (Q4K GGUF)",
        model_type=ModelType.TRANSLATION,
        model_size_gb=2.0,
        runtime_memory_gb=4.0,
        runtime_vram_gb=3.0,
        recommended_system_gb=16,
        recommended_vram_gb=8,
        license=LicenseType.APACHE_2_0,
        language_support="400+ languages",
        precision="q4k",
        requires_prompt=False,
        description="量化版 MADLAD400，支持所有语言对翻译 (GGUF格式)",
    ),
    # 32GB 级别（CPU） / 12GB VRAM（GPU）
    "google/madlad400-7b-mt-bt": ModelInfo(
        model_id="google/madlad400-7b-mt-bt",  # 与 huggingface_id 一致
        huggingface_id="google/madlad400-7b-mt-bt",
        gguf_file="madlad400-7b.Q4_K_M.gguf",
        display_name="MADLAD400-7B (Q4K GGUF)",
        model_type=ModelType.TRANSLATION,
        model_size_gb=4.5,
        runtime_memory_gb=7.0,
        runtime_vram_gb=5.0,
        recommended_system_gb=32,
        recommended_vram_gb=12,
        license=LicenseType.APACHE_2_0,
        language_support="400+ languages",
        precision="q4k",
        requires_prompt=False,
        description="高质量量化版 MADLAD400 (GGUF格式)",
    ),
    # 64GB+ 级别（CPU） / 16GB+ VRAM（GPU）- 原生 FP16
    "google/madlad400-3b-mt-fp16": ModelInfo(
        model_id="google/madlad400-3b-mt-fp16",  # 与 huggingface_id 一致
        huggingface_id="google/madlad400-3b-mt",
        display_name="MADLAD400-3B (FP16 Native)",
        model_type=ModelType.TRANSLATION,
        model_size_gb=6.0,
        runtime_memory_gb=10.0,
        runtime_vram_gb=6.0,
        recommended_system_gb=64,
        recommended_vram_gb=16,
        license=LicenseType.APACHE_2_0,
        language_support="400+ languages",
        precision="fp16",
        requires_prompt=False,
        description="原生 FP16 版本，最高质量 MADLAD400 翻译",
    ),
}

# Fixed Whisper model ID (huggingface_id)
WHISPER_MODEL_ID = "Systran/faster-whisper-large-v3"


def get_system_total_memory_gb() -> int:
    """Get system total memory in gigabytes.

    Returns:
        Total system RAM in GB
    """
    return int(psutil.virtual_memory().total / (1024**3))


def get_available_memory_gb() -> float:
    """Get currently available memory in gigabytes.

    Returns:
        Available system RAM in GB
    """
    return psutil.virtual_memory().available / (1024**3)


def get_whisper_model_info() -> ModelInfo:
    """Get the fixed Whisper model information.

    Returns:
        ModelInfo for Whisper Large V3
    """
    return MODEL_REGISTRY[WHISPER_MODEL_ID]


def get_all_whisper_models() -> list[ModelInfo]:
    """Get all Whisper models in the registry.

    Returns:
        List of Whisper ModelInfo objects
    """
    return [
        info for info in MODEL_REGISTRY.values() if info.model_type == ModelType.WHISPER
    ]


def get_all_translation_models() -> list[ModelInfo]:
    """Get all translation models in the registry.

    Returns:
        List of translation ModelInfo objects, sorted by runtime memory
    """
    models = [
        info
        for info in MODEL_REGISTRY.values()
        if info.model_type == ModelType.TRANSLATION
    ]
    return sorted(models, key=lambda m: m.runtime_memory_gb)


def get_translation_model_info(huggingface_id: str) -> Optional[ModelInfo]:
    """Get translation model information by HuggingFace ID.

    Args:
        huggingface_id: HuggingFace 模型 ID（如 "google/madlad400-3b-mt"）

    Returns:
        ModelInfo if found and is a translation model, None otherwise
    """
    info = MODEL_REGISTRY.get(huggingface_id)
    if info and info.model_type == ModelType.TRANSLATION:
        return info
    return None


def get_model_info(huggingface_id: str) -> Optional[ModelInfo]:
    """Get model information by HuggingFace ID.

    Args:
        huggingface_id: HuggingFace 模型 ID（如 "Systran/faster-whisper-large-v3"）

    Returns:
        ModelInfo if found, None otherwise
    """
    return MODEL_REGISTRY.get(huggingface_id)


def get_recommended_translation_models() -> list[str]:
    """Get recommended translation models for installation based on system memory.

    Returns models whose recommended system memory is <= total system memory.

    Returns:
        List of huggingface_ids suitable for the current system
    """
    total_memory = get_system_total_memory_gb()

    suitable_models = [
        huggingface_id
        for huggingface_id, info in MODEL_REGISTRY.items()
        if info.model_type == ModelType.TRANSLATION
        and info.recommended_system_gb <= total_memory
    ]

    # 最低要求 16GB，否则推荐使用 LLM API
    return suitable_models or ["google/madlad400-3b-mt"]


def get_best_translation_model_for_installation() -> str:
    """Get the best translation model recommendation for installation.

    Based on system total memory, returns the largest suitable model.
    Minimum requirement: 16GB RAM

    Returns:
        HuggingFace ID of the best recommended model
    """
    total_memory = get_system_total_memory_gb()

    # 最低要求 16GB
    if total_memory < 16:
        log_warning("系统内存不足 16GB，建议使用 LLM API 翻译")
        return "google/madlad400-3b-mt"  # 仍然返回，但会有警告

    suitable_models = [
        (huggingface_id, info)
        for huggingface_id, info in MODEL_REGISTRY.items()
        if info.model_type == ModelType.TRANSLATION
        and info.recommended_system_gb <= total_memory
    ]

    if not suitable_models:
        return "google/madlad400-3b-mt"

    # Return the model with highest runtime memory (best quality)
    return max(suitable_models, key=lambda x: x[1].runtime_memory_gb)[0]


def select_best_translation_model(downloaded_models: list[str]) -> Optional[str]:
    """Select the best translation model at runtime from downloaded models.

    Based on currently available memory, selects the largest usable model.

    Args:
        downloaded_models: List of downloaded model IDs

    Returns:
        Model ID of the best available model, or None if no suitable model
    """
    if not downloaded_models:
        return None

    available_memory = get_available_memory_gb()

    # Filter downloaded models that fit in available memory
    suitable_models = [
        (model_id, MODEL_REGISTRY[model_id])
        for model_id in downloaded_models
        if model_id in MODEL_REGISTRY
        and MODEL_REGISTRY[model_id].model_type == ModelType.TRANSLATION
        and MODEL_REGISTRY[model_id].runtime_memory_gb <= available_memory
    ]

    if not suitable_models:
        return None

    # Return the model with highest runtime memory (best quality)
    return max(suitable_models, key=lambda x: x[1].runtime_memory_gb)[0]


def is_model_commercial_use_allowed(model_id: str) -> bool:
    """Check if a model allows commercial use.

    Args:
        model_id: Model identifier

    Returns:
        True if commercial use is allowed, False otherwise
    """
    info = MODEL_REGISTRY.get(model_id)
    if info is None:
        return False
    return info.license in (LicenseType.APACHE_2_0, LicenseType.MIT)


def get_display_name(huggingface_id: str) -> str:
    """获取模型的展示名称。

    Args:
        huggingface_id: HuggingFace 模型 ID（如 "Systran/faster-whisper-large-v3"）

    Returns:
        人类可读的展示名称，如果不在注册表中则返回 ID 的最后部分
    """
    info = MODEL_REGISTRY.get(huggingface_id)
    if info:
        return info.display_name
    # 不在注册表中，返回 ID 的最后部分
    return huggingface_id.split("/")[-1]
