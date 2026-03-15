"""Unified model registry for MediaFactory.

This module provides a centralized registry for ALL models:
- Whisper models (speech recognition)
- Translation models (MADLAD400)
- Enhancement models (Real-ESRGAN, NAFNet, CodeFormer)

Supports memory-aware selection and license tracking for commercial use compliance.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil

from ..logging import log_info, log_warning


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
    SUPER_RESOLUTION = "super_resolution"  # Real-ESRGAN
    DENOISE = "denoise"  # NAFNet
    FACE_RESTORE = "face_restore"  # CodeFormer, RetinaFace


class DownloadMode(Enum):
    """Download mode enumeration."""

    REPO = "repo"  # Download entire HuggingFace repository (snapshot_download)
    FILE = "file"  # Download single file (hf_hub_download)


class LicenseType(Enum):
    """Model license type enumeration."""

    APACHE_2_0 = "apache_2_0"  # Commercial use allowed
    MIT = "mit"  # Commercial use allowed


@dataclass
class ModelInfo:
    """Unified model information.

    Attributes:
        huggingface_id: HuggingFace model ID (also serves as unique identifier)
        display_name: Human-readable display name
        model_type: Type of model (WHISPER, TRANSLATION, SUPER_RESOLUTION, etc.)
        model_size_mb: Model file size in megabytes
        runtime_memory_mb: Estimated runtime memory usage in megabytes (CPU)
        license: Model license type
        language_support: Description of language support
        precision: Model precision (fp32, fp16, q4k, q8k)
        
        # Download configuration
        download_mode: REPO for full repository, FILE for single file
        huggingface_repo: HuggingFace repository ID (required for download)
        huggingface_filename: Filename for single file download (optional)
        local_filename: Local filename after download (optional, defaults to huggingface_filename)
        
        # Optional fields
        recommended_system_mb: Recommended system RAM in MB (0 = auto-calculate)
        requires_prompt: Whether the model requires special prompt formatting
        description: Brief model description
        gguf_file: GGUF filename for quantized models (optional)
        runtime_vram_mb: Estimated runtime VRAM usage for GPU (0 if not applicable)
        recommended_vram_mb: Recommended VRAM for GPU (0 if not applicable)
        metadata: Additional model-specific metadata
    """

    huggingface_id: str  # 唯一标识，同时也是注册表的键
    display_name: str
    model_type: ModelType
    model_size_mb: int  # 统一使用 MB
    runtime_memory_mb: int
    license: LicenseType
    
    # 下载配置
    download_mode: DownloadMode = DownloadMode.REPO
    huggingface_repo: str = ""  # 默认与 huggingface_id 相同
    huggingface_filename: Optional[str] = None  # 单文件下载时的文件名
    local_filename: Optional[str] = None  # 本地保存的文件名
    
    # 可选字段
    language_support: str = ""
    precision: str = ""
    recommended_system_mb: int = 0  # 0 means auto-calculate
    requires_prompt: bool = False
    description: str = ""
    gguf_file: Optional[str] = None  # GGUF filename for quantized models
    runtime_vram_mb: int = 0  # GPU runtime VRAM
    recommended_vram_mb: int = 0  # Recommended VRAM
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Calculate defaults and validate."""
        # 默认 huggingface_repo 与 huggingface_id 相同
        if not self.huggingface_repo:
            self.huggingface_repo = self.huggingface_id
        
        # 默认 local_filename 与 huggingface_filename 相同
        if self.huggingface_filename and not self.local_filename:
            self.local_filename = self.huggingface_filename
        
        # Calculate recommended system memory if not manually set
        if self.recommended_system_mb == 0 and self.runtime_memory_mb > 0:
            # Formula: runtime_memory × 4, rounded up to nearest tier
            self.recommended_system_mb = get_memory_tier(self.runtime_memory_mb / 1024 * 4) * 1024

    def __hash__(self):
        return hash(self.huggingface_id)
    
    # 兼容属性（GB 单位）
    @property
    def model_size_gb(self) -> float:
        return self.model_size_mb / 1024
    
    @property
    def runtime_memory_gb(self) -> float:
        return self.runtime_memory_mb / 1024
    
    @property
    def recommended_system_gb(self) -> int:
        return self.recommended_system_mb // 1024 if self.recommended_system_mb else 0


# Unified model registry
# 键直接使用 huggingface_id，与 HuggingFace 一致
MODEL_REGISTRY: dict[str, ModelInfo] = {
    # ========== Whisper Models ==========
    "Systran/faster-whisper-large-v3": ModelInfo(
        huggingface_id="Systran/faster-whisper-large-v3",
        display_name="Whisper Large V3",
        model_type=ModelType.WHISPER,
        model_size_mb=3072,  # 3 GB
        runtime_memory_mb=10240,  # 10 GB
        recommended_system_mb=16384,  # 16 GB
        license=LicenseType.MIT,
        language_support="99+ languages",
        precision="float16",
        description="Best quality for transcription",
    ),
    # ========== Translation Models ==========
    # M2M100 (Apache 2.0 许可证，轻量级)
    "facebook/m2m100_418M": ModelInfo(
        huggingface_id="facebook/m2m100_418M",
        display_name="M2M100-418M (轻量级)",
        model_type=ModelType.TRANSLATION,
        model_size_mb=1940,  # ~1.9 GB
        runtime_memory_mb=4096,  # 4 GB
        runtime_vram_mb=2048,  # 2 GB VRAM
        recommended_system_mb=8192,  # 8 GB
        recommended_vram_mb=4096,  # 4 GB VRAM
        license=LicenseType.APACHE_2_0,
        language_support="100 languages",
        precision="fp16",
        requires_prompt=False,
        description="轻量级多语言翻译，适合低显存设备",
    ),
    # MADLAD400 (Apache 2.0 许可证，支持商用)
    # 使用 safetensors 格式（HuggingFace 上的 GGUF 文件缺少必要元数据）
    "google/madlad400-3b-mt": ModelInfo(
        huggingface_id="google/madlad400-3b-mt",
        display_name="MADLAD400-3B",
        model_type=ModelType.TRANSLATION,
        model_size_mb=12000,  # ~11.7 GB (safetensors)
        runtime_memory_mb=8192,  # 8 GB
        runtime_vram_mb=6144,  # 6 GB VRAM
        recommended_system_mb=16384,  # 16 GB
        recommended_vram_mb=8192,  # 8 GB VRAM
        license=LicenseType.APACHE_2_0,
        language_support="400+ languages",
        precision="fp16",
        requires_prompt=False,
        description="All-language translation",
    ),
    "google/madlad400-7b-mt-bt": ModelInfo(
        huggingface_id="google/madlad400-7b-mt-bt",
        display_name="MADLAD400-7B",
        model_type=ModelType.TRANSLATION,
        model_size_mb=30000,  # ~30 GB (safetensors)
        runtime_memory_mb=16384,  # 16 GB
        runtime_vram_mb=12288,  # 12 GB VRAM
        recommended_system_mb=32768,  # 32 GB
        recommended_vram_mb=16384,  # 16 GB VRAM
        license=LicenseType.APACHE_2_0,
        language_support="400+ languages",
        precision="fp16",
        requires_prompt=False,
        description="High-quality translation",
    ),
    # ========== Enhancement Models: Super Resolution (Real-ESRGAN) ==========
    "RealESRGAN_x4plus": ModelInfo(
        huggingface_id="RealESRGAN_x4plus",
        display_name="Real-ESRGAN x4 (General)",
        model_type=ModelType.SUPER_RESOLUTION,
        model_size_mb=67,
        runtime_memory_mb=512,
        license=LicenseType.MIT,
        download_mode=DownloadMode.FILE,
        huggingface_repo="lllyasviel/Annotators",
        huggingface_filename="RealESRGAN_x4plus.pth",
        description="4x upscaling for most videos",
        metadata={"scale": 4, "type": "general"},
    ),
    "RealESRGAN_x2plus": ModelInfo(
        huggingface_id="RealESRGAN_x2plus",
        display_name="Real-ESRGAN x2 (General)",
        model_type=ModelType.SUPER_RESOLUTION,
        model_size_mb=64,  # 实际大小
        runtime_memory_mb=512,
        license=LicenseType.MIT,
        download_mode=DownloadMode.FILE,
        huggingface_repo="nateraw/real-esrgan",
        huggingface_filename="RealESRGAN_x2plus.pth",
        description="2x upscaling, faster processing",
        metadata={"scale": 2, "type": "general"},
    ),
    "RealESRGAN_x4plus_anime_6B": ModelInfo(
        huggingface_id="RealESRGAN_x4plus_anime_6B",
        display_name="Real-ESRGAN x4 (Anime)",
        model_type=ModelType.SUPER_RESOLUTION,
        model_size_mb=18,
        runtime_memory_mb=256,
        license=LicenseType.MIT,
        download_mode=DownloadMode.FILE,
        huggingface_repo="Runware/upscaler",
        huggingface_filename="RealESRGAN_x4plus_anime_6B.pth",
        description="4x upscaling for anime",
        metadata={"scale": 4, "type": "anime"},
    ),
    # ========== Enhancement Models: Denoise (NAFNet) ==========
    "NAFNet-GoPro-width64": ModelInfo(
        huggingface_id="NAFNet-GoPro-width64",
        display_name="NAFNet Denoiser (GoPro)",
        model_type=ModelType.DENOISE,
        model_size_mb=260,  # 实际大小
        runtime_memory_mb=512,
        license=LicenseType.MIT,
        download_mode=DownloadMode.FILE,
        huggingface_repo="nyanko7/nafnet-models",
        huggingface_filename="NAFNet-GoPro-width64.pth",
        description="Denoise for old/compressed videos",
        metadata={"type": "denoise"},
    ),
    # ========== Enhancement Models: Face Restore (CodeFormer) ==========
    "CodeFormer": ModelInfo(
        huggingface_id="CodeFormer",
        display_name="CodeFormer",
        model_type=ModelType.FACE_RESTORE,
        model_size_mb=360,  # 实际大小
        runtime_memory_mb=1024,
        license=LicenseType.MIT,
        download_mode=DownloadMode.FILE,
        huggingface_repo="alexgenovese/facerestore",
        huggingface_filename="codeformer-v0.1.0.pth",
        local_filename="codeformer.pth",
        description="Restore blurry faces",
        metadata={"type": "face_restore"},
    ),
    "RetinaFace-R50": ModelInfo(
        huggingface_id="RetinaFace-R50",
        display_name="RetinaFace R50",
        model_type=ModelType.FACE_RESTORE,
        model_size_mb=105,
        runtime_memory_mb=512,
        license=LicenseType.MIT,
        download_mode=DownloadMode.FILE,
        huggingface_repo="licyk/sd-upscaler-models",
        huggingface_filename="GFPGAN/detection_Resnet50_Final.pth",
        local_filename="Resnet50_Final.pth",
        description="Detect face positions",
        metadata={"type": "face_detection"},
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


# ==================== Enhancement Model Functions ====================

def get_all_enhancement_models() -> List[ModelInfo]:
    """获取所有增强模型。

    Returns:
        List of enhancement ModelInfo objects
    """
    enhancement_types = {ModelType.SUPER_RESOLUTION, ModelType.DENOISE, ModelType.FACE_RESTORE}
    return [
        info for info in MODEL_REGISTRY.values()
        if info.model_type in enhancement_types
    ]


def get_enhancement_models_by_type(model_type: ModelType) -> List[ModelInfo]:
    """按类型获取增强模型。

    Args:
        model_type: 模型类型 (SUPER_RESOLUTION, DENOISE, FACE_RESTORE)

    Returns:
        List of ModelInfo objects of the specified type
    """
    return [
        info for info in MODEL_REGISTRY.values()
        if info.model_type == model_type
    ]


def get_enhancement_model_by_scale_and_type(
    scale: int,
    model_subtype: str = "general"
) -> Optional[str]:
    """根据放大倍数和类型获取超分辨率模型名称。

    Args:
        scale: 放大倍数 (2 或 4)
        model_subtype: 模型类型 ('general' 或 'anime')

    Returns:
        模型 ID
    """
    for model_id, info in MODEL_REGISTRY.items():
        if info.model_type == ModelType.SUPER_RESOLUTION:
            if (info.metadata.get("scale") == scale and
                info.metadata.get("type") == model_subtype):
                return model_id
    return None


def is_enhancement_model(model_id: str) -> bool:
    """检查是否是增强模型。

    Args:
        model_id: 模型 ID

    Returns:
        True if the model is an enhancement model
    """
    info = MODEL_REGISTRY.get(model_id)
    if info is None:
        return False
    return info.model_type in {ModelType.SUPER_RESOLUTION, ModelType.DENOISE, ModelType.FACE_RESTORE}


# ==================== Model Storage Paths ====================

def get_models_base_dir() -> Path:
    """获取模型存储基础目录。"""
    from ..config import get_app_root_dir
    return get_app_root_dir() / "models"


def get_enhancement_models_dir() -> Path:
    """获取增强模型存储目录。"""
    return get_models_base_dir() / "enhancement"


def get_model_local_path(model_id: str) -> Optional[Path]:
    """获取模型的本地存储路径。

    Args:
        model_id: 模型 ID

    Returns:
        模型本地路径，如果模型不存在返回 None
    """
    info = MODEL_REGISTRY.get(model_id)
    if info is None:
        return None
    
    if info.download_mode == DownloadMode.FILE:
        # 单文件模型存储在 enhancement 目录
        filename = info.local_filename or info.huggingface_filename
        if filename:
            path = get_enhancement_models_dir() / filename
            return path if path.exists() else None
    else:
        # 仓库模型存储在以 huggingface_id 命名的目录
        path = get_models_base_dir() / model_id
        return path if path.exists() else None
    
    return None


def is_model_downloaded(model_id: str) -> bool:
    """检查模型是否已下载。

    Args:
        model_id: 模型 ID

    Returns:
        True if the model is downloaded
    """
    return get_model_local_path(model_id) is not None


def is_model_complete(model_id: str) -> bool:
    """检查模型是否完整下载（校验文件大小）。

    Args:
        model_id: 模型 ID

    Returns:
        True if the model is completely downloaded
    """
    info = MODEL_REGISTRY.get(model_id)
    if info is None:
        return False
    
    path = get_model_local_path(model_id)
    if path is None:
        return False
    
    if info.download_mode == DownloadMode.FILE:
        # 单文件模型：校验文件大小（允许 5% 容差）
        if not path.is_file():
            return False
        actual_size = path.stat().st_size
        expected_size = info.model_size_mb * 1024 * 1024
        tolerance = expected_size * 0.05
        return abs(actual_size - expected_size) <= tolerance or actual_size > expected_size * 0.9
    else:
        # 仓库模型：检查 config.json 和模型文件
        if not path.is_dir():
            return False
        config_file = path / "config.json"
        if not config_file.exists():
            return False
        
        # 检查模型文件
        model_files = list(path.glob("*.bin")) + list(path.glob("*.safetensors")) + list(path.glob("*.gguf"))
        if not model_files:
            return False
        
        # 检查文件大小（至少 1MB）
        for model_file in model_files:
            if model_file.stat().st_size >= 1_000_000:
                return True
        
        return False


def get_all_model_statuses() -> Dict[str, bool]:
    """获取所有模型的下载状态。

    Returns:
        {model_id: is_downloaded} 字典
    """
    return {model_id: is_model_downloaded(model_id) for model_id in MODEL_REGISTRY}


# Backward compatibility alias
ENHANCEMENT_MODEL_REGISTRY = {
    model_id: info for model_id, info in MODEL_REGISTRY.items()
    if is_enhancement_model(model_id)
}
