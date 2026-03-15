"""Whisper model loading and device selection utilities - using Faster Whisper.

This module provides Whisper model loading with a fixed Large V3 model.
ML dependencies (torch, faster_whisper) are lazily loaded.
"""

import warnings
from pathlib import Path
from typing import Optional

from .model_registry import WHISPER_MODEL_ID, get_whisper_model_info
from .model_download import get_models_dir, is_model_complete
from ..logging import log_error, log_info, log_warning
from ..exceptions import ProcessingError


# Valid computing devices for Faster Whisper
# - cpu: Always available, uses int8 quantization
# - cuda: NVIDIA GPU, uses float16 for best performance
# - mps: Apple Silicon GPU (NOT supported - falls back to CPU)
VALID_DEVICES = ("cpu", "cuda", "mps")


def _ensure_ml_dependencies():
    """Ensure ML dependencies are installed.

    Raises:
        ProcessingError: If ML dependencies are not installed
    """
    try:
        import torch  # noqa: F401
        from faster_whisper import WhisperModel  # noqa: F401
    except ImportError as e:
        raise ProcessingError(
            message="ML dependencies not installed. Please run the setup wizard to install PyTorch and faster-whisper.",
            context={
                "missing_dependencies": ["torch", "faster-whisper"],
                "suggestion": "The setup wizard will start automatically when launching the application",
            },
        ) from e


def select_device() -> str:
    """Select the best computing device with CUDA compatibility check.

    Faster Whisper supports:
    - "cuda": NVIDIA GPU (recommended)
    - "cpu": CPU (universal)

    Note: Faster Whisper does not directly support MPS (Apple Silicon GPU),
    it will automatically fall back to CPU.

    This function checks for CUDA compatibility issues (e.g., GPU architecture
    not supported by current PyTorch version) and automatically falls back to
    CPU if such issues are detected.

    Returns:
        Computing device string ("cuda" or "cpu")

    Raises:
        ProcessingError: If torch is not installed
    """
    try:
        import torch
    except ImportError as e:
        raise ProcessingError(
            message="PyTorch not installed. Please run the setup wizard to install ML dependencies.",
            context={"missing_dependency": "torch"},
        ) from e

    # Capture CUDA compatibility warnings
    with warnings.catch_warnings(record=True) as caught_warnings:
        warnings.simplefilter("always")
        cuda_available = torch.cuda.is_available()

        # Check for compatibility warnings (e.g., sm_120 not compatible)
        for w in caught_warnings:
            warning_msg = str(w.message)
            if "CUDA capability" in warning_msg or "not compatible" in warning_msg:
                log_warning(f"CUDA compatibility issue detected: {warning_msg}")
                log_warning("Falling back to CPU for stability")
                return "cpu"

    if cuda_available:
        return "cuda"
    return "cpu"


def check_cuda_compatibility() -> bool:
    """Check if CUDA is truly available and compatible.

    This performs a more thorough check than torch.cuda.is_available() by
    verifying the GPU architecture is supported by the current PyTorch version.

    Returns:
        True if CUDA is available and compatible, False otherwise
    """
    try:
        import torch

        if not torch.cuda.is_available():
            return False

        # Get device capability
        device_capability = torch.cuda.get_device_capability()
        major, minor = device_capability

        # Check supported architectures
        supported_archs = getattr(torch.cuda, "get_arch_list", lambda: [])()
        current_arch = f"sm_{major}{minor}"

        if current_arch not in supported_archs:
            log_warning(
                f"GPU architecture {current_arch} not supported. "
                f"Supported: {supported_archs}"
            )
            return False

        return True
    except Exception as e:
        log_warning(f"CUDA compatibility check failed: {e}")
        return False


def get_compute_type(device: str) -> str:
    """Get the best compute type for a device.

    Args:
        device: Computing device ("cuda" or "cpu")

    Returns:
        Compute type string
    """
    if device == "cuda":
        return "float16"  # GPU uses float16 for best performance
    return "int8"  # CPU uses int8 for quantization speedup


def load_model(
    device: Optional[str] = None,
    compute_type: Optional[str] = None,
):
    """Load the Faster Whisper Large V3 model.

    The model is fixed to Large V3 - no model size selection needed.

    Args:
        device: Computing device ("cuda" or "cpu"), auto-selected if None
        compute_type: Compute type ("int8", "int8_float16", "float16", "float32"),
                    auto-selected based on device if None

    Returns:
        Faster Whisper model instance

    Raises:
        ProcessingError: If faster_whisper is not installed or model not found
    """
    # Lazily load WhisperModel
    try:
        from faster_whisper import WhisperModel
    except ImportError as e:
        raise ProcessingError(
            message="faster-whisper not installed. Please run the setup wizard to install ML dependencies.",
            context={"missing_dependency": "faster-whisper"},
        ) from e

    # Always use Large V3 (fixed model)
    model_id = WHISPER_MODEL_ID

    if device is None:
        device = select_device()

    if compute_type is None:
        compute_type = get_compute_type(device)

    model_info = get_whisper_model_info()

    # 计算模型绝对路径
    models_dir = get_models_dir()
    model_path = models_dir / model_id

    # 检查模型是否存在且完整
    if not model_path.exists():
        log_error(f"Whisper model not found: {model_path}")
        raise ProcessingError(
            message=f"Whisper model not found: {model_info.display_name}",
            context={
                "model_id": model_id,
                "expected_path": str(model_path),
                "suggestion": f"Please download the model using: python scripts/utils/download_model.py {model_id}",
            },
        )

    if not is_model_complete(model_id):
        log_error(f"Whisper model incomplete: {model_path}")
        raise ProcessingError(
            message=f"Whisper model incomplete: {model_info.display_name}",
            context={
                "model_id": model_id,
                "model_path": str(model_path),
                "suggestion": "The model download may have been interrupted. Please re-download the model.",
            },
        )

    log_info(
        f"Loading Whisper model: {model_info.display_name} from {model_path} ({device}, {compute_type})"
    )

    # 传递绝对路径给 WhisperModel
    model = WhisperModel(
        model_size_or_path=str(model_path),
        device=device,
        compute_type=compute_type,
    )

    return model


def get_fixed_model_id() -> str:
    """Get the fixed Whisper model ID.

    Returns:
        The fixed model ID ("large-v3")
    """
    return WHISPER_MODEL_ID


def get_fixed_model_display_name() -> str:
    """Get the fixed Whisper model display name.

    Returns:
        The fixed model display name
    """
    return get_whisper_model_info().display_name
