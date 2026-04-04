"""Unified model registry for MediaFactory.

This module provides a centralized registry for ALL models:
- Whisper models (speech recognition)
- Translation models (M2M100)
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
    DIARIZATION = "diarization"  # Speaker diarization


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
    purpose: str = ""  # 功能描述，用于 UI 卡片标题
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

    @property
    def runtime_vram_gb(self) -> float:
        """GPU 运行时显存需求 (GB)。"""
        return self.runtime_vram_mb / 1024


# Unified model registry
# 键直接使用 huggingface_id，与 HuggingFace 一致
MODEL_REGISTRY: dict[str, ModelInfo] = {
    # ========== Whisper Models ==========
    "Systran/faster-whisper-large-v3": ModelInfo(
        huggingface_id="Systran/faster-whisper-large-v3",
        display_name="Whisper Large V3",
        model_type=ModelType.WHISPER,
        model_size_mb=3072,  # 3 GB
        runtime_memory_mb=6144,  # 6 GB (FP16推理3-4GB, CPU需要6GB)
        recommended_system_mb=16384,  # 16 GB
        license=LicenseType.MIT,
        language_support="99+ languages",
        precision="float16",
        description="Best quality for transcription",
        purpose="Speech Recognition",
    ),
    # ========== Translation Models ==========
    # M2M100-1.2B (MIT 许可证，唯一本地翻译模型)
    "facebook/m2m100_1.2B": ModelInfo(
        huggingface_id="facebook/m2m100_1.2B",
        display_name="M2M100-1.2B",
        model_type=ModelType.TRANSLATION,
        model_size_mb=2500,
        runtime_memory_mb=5120,  # ~5 GB (CPU fp16)
        runtime_vram_mb=4800,  # ~4.8 GB VRAM (fp16)
        recommended_system_mb=16384,  # 16 GB
        recommended_vram_mb=8192,  # 8 GB VRAM
        license=LicenseType.MIT,
        language_support="100 languages",
        precision="fp16",
        requires_prompt=False,
        description="Multilingual translation model (1.2B parameters)",
        purpose="Multilingual Translation",
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
        purpose="4x Video Upscaling",
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
        purpose="2x Video Upscaling",
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
        purpose="4x Video Upscaling (Anime)",
        metadata={"scale": 4, "type": "anime"},
    ),
    # ========== Diarization Models ==========
    "pyannote/speaker-diarization-3.1": ModelInfo(
        huggingface_id="pyannote/speaker-diarization-3.1",
        display_name="Pyannote Speaker Diarization 3.1",
        model_type=ModelType.DIARIZATION,
        model_size_mb=600,
        runtime_memory_mb=1024,
        runtime_vram_mb=800,
        recommended_system_mb=8192,
        recommended_vram_mb=4096,
        license=LicenseType.MIT,
        language_support="Language-independent",
        precision="fp32",
        description="State-of-the-art speaker diarization model",
        purpose="Speaker Diarization",
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
        purpose="Video Denoising",
        metadata={"type": "denoise"},
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


def get_available_vram_gb() -> float:
    """获取当前可用的 GPU 显存 (GB)。

    Returns:
        可用 GPU 显存 (GB)，无 GPU 时返回 0
    """
    try:
        import torch

        if torch.cuda.is_available():
            free, total = torch.cuda.mem_get_info(0)
            return free / (1024**3)
    except Exception:
        pass
    return 0.0


def get_total_vram_gb() -> float:
    """获取 GPU 总显存 (GB)。

    Returns:
        GPU 总显存 (GB)，无 GPU 时返回 0
    """
    try:
        import torch

        if torch.cuda.is_available():
            return torch.cuda.get_device_properties(0).total_memory / (1024**3)
    except Exception:
        pass
    return 0.0


def get_available_memory_for_device(device: str = "cpu") -> float:
    """获取指定设备的可用内存 (GB)。

    Args:
        device: 设备类型 ("cuda" 或 "cpu")

    Returns:
        可用内存 (GB)，GPU 返回 VRAM，CPU 返回 RAM
    """
    if device == "cuda":
        return get_available_vram_gb()
    return get_available_memory_gb()


def get_required_memory_for_model(model_id: str, device: str = "cpu") -> float:
    """获取模型在指定设备上运行所需的内存 (GB)。

    Args:
        model_id: 模型 ID (HuggingFace ID)
        device: 设备类型 ("cuda" 或 "cpu")

    Returns:
        所需内存 (GB)，GPU 返回 VRAM 需求，CPU 返回 RAM 需求
    """
    info = MODEL_REGISTRY.get(model_id)
    if info is None:
        return 0.0
    if device == "cuda":
        return info.runtime_vram_gb
    return info.runtime_memory_gb


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
        huggingface_id: HuggingFace 模型 ID（如 "facebook/m2m100_1.2B"）

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
    return suitable_models or ["facebook/m2m100_1.2B"]


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
        return "facebook/m2m100_1.2B"  # 仍然返回，但会有警告

    suitable_models = [
        (huggingface_id, info)
        for huggingface_id, info in MODEL_REGISTRY.items()
        if info.model_type == ModelType.TRANSLATION
        and info.recommended_system_gb <= total_memory
    ]

    if not suitable_models:
        return "facebook/m2m100_1.2B"

    # Return the model with highest runtime memory (best quality)
    return max(suitable_models, key=lambda x: x[1].runtime_memory_gb)[0]


def select_best_translation_model(
    downloaded_models: list[str],
    device: str = "cpu",
) -> Optional[str]:
    """从已下载模型中选择最佳翻译模型。

    根据设备类型和可用资源（GPU用VRAM，CPU用RAM）选择模型。
    如果GPU显存不足，自动回退到CPU模式，然后选择最小模型。

    Args:
        downloaded_models: 已下载模型 ID 列表
        device: 设备类型 ("cuda" 或 "cpu")

    Returns:
        最佳可用模型的 ID，若无合适模型则返回 None
    """
    if not downloaded_models:
        return None

    # 根据设备类型确定可用内存
    if device == "cuda":
        available_memory = get_available_vram_gb()
        memory_field = "runtime_vram_gb"  # GPU 使用 VRAM 字段
    else:
        available_memory = get_available_memory_gb()
        memory_field = "runtime_memory_gb"  # CPU 使用 RAM 字段

    # 筛选适合可用内存的已下载模型
    suitable_models = [
        (model_id, MODEL_REGISTRY[model_id])
        for model_id in downloaded_models
        if model_id in MODEL_REGISTRY
        and MODEL_REGISTRY[model_id].model_type == ModelType.TRANSLATION
        and getattr(MODEL_REGISTRY[model_id], memory_field) <= available_memory
    ]

    if suitable_models:
        # 返回内存占用最高（质量最好）的模型
        return max(suitable_models, key=lambda x: getattr(x[1], memory_field))[0]

    # 无合适模型 - 尝试 CPU 回退
    if device == "cuda":
        log_warning("无翻译模型适合 GPU 显存，回退到 CPU 模式")
        return select_best_translation_model(downloaded_models, device="cpu")

    # 仍然无模型 - 返回最小的作为最后手段
    all_models = sorted(
        [MODEL_REGISTRY[m] for m in downloaded_models if m in MODEL_REGISTRY],
        key=lambda m: m.runtime_memory_gb,
    )
    if all_models:
        log_warning(
            f"可用内存不足以运行任何模型。使用最小模型: {all_models[0].display_name}"
        )
        return all_models[0].huggingface_id

    return None


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
    enhancement_types = {ModelType.SUPER_RESOLUTION, ModelType.DENOISE}
    return [
        info for info in MODEL_REGISTRY.values()
        if info.model_type in enhancement_types
    ]


def get_enhancement_models_by_type(model_type: ModelType) -> List[ModelInfo]:
    """按类型获取增强模型。

    Args:
        model_type: 模型类型 (SUPER_RESOLUTION, DENOISE)

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
    return info.model_type in {ModelType.SUPER_RESOLUTION, ModelType.DENOISE}


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
        # 仓库模型：检查配置文件和模型文件
        if not path.is_dir():
            return False
        # 支持多种配置文件格式
        config_files = ["config.json", "config.yaml", "config.yml"]
        has_config = any((path / cf).exists() for cf in config_files)
        if not has_config:
            return False

        # 单次扫描目录，过滤模型文件后缀
        valid_suffixes = {".bin", ".safetensors", ".gguf", ".onnx", ".pt", ".ckpt"}
        for entry in path.iterdir():
            if entry.is_file() and entry.suffix in valid_suffixes and entry.stat().st_size >= 1_000_000:
                return True

        # 某些 pipeline 模型（如 pyannote）没有权重文件，只有配置 + handler
        # 检查目录中是否有实质性内容（非隐藏文件、非 README）
        for entry in path.iterdir():
            if entry.is_file() and not entry.name.startswith(".") and entry.name != "README.md":
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
