"""Translation model loading runtime utilities.

This module provides translation model loading using the unified model registry.
Models are automatically selected based on available system memory.
All models use MADLAD400 architecture with 400+ language support.
"""

from typing import Any, Optional

from .local_models import local_model_manager
from .model_registry import (
    get_all_translation_models,
    get_available_memory_for_device,
    get_required_memory_for_model,
    get_translation_model_info,
    select_best_translation_model,
)
from ..logging import log_debug, log_error, log_info, log_success, log_warning


def get_translation_model(
    src_lang: str,
    tgt_lang: str,
    device: str = "cpu",
    progress: Optional[Any] = None,
) -> Optional[Any]:
    """Load a translation model based on language and available resources.

    Automatically selects the best available model from downloaded models
    based on current system memory. Supports device fallback when GPU
    memory is insufficient.

    Fallback chain:
    1. Try specified device (e.g., CUDA)
    2. If no suitable model for GPU VRAM, fallback to CPU
    3. If no suitable model for CPU RAM, force smallest model on CPU

    Args:
        src_lang: Source language code (e.g., "zh", "en", "ja")
        tgt_lang: Target language code (e.g., "zh", "en")
        device: Device to load model on (default: "cpu")
        progress: Optional progress callback for reporting loading status

    Returns:
        Model callable object or None if loading fails
    """
    log_info(f"[TranslationRuntime] Starting model loading process...")
    log_info(f"[TranslationRuntime] Parameters: src_lang={src_lang}, tgt_lang={tgt_lang}, device={device}")

    # Get downloaded translation models
    log_info("[TranslationRuntime] Checking downloaded translation models...")
    downloaded_models = local_model_manager.get_downloaded_translation_models()
    log_info(f"[TranslationRuntime] Found {len(downloaded_models)} downloaded models: {downloaded_models}")

    if not downloaded_models:
        log_error(
            "No translation models downloaded. "
            "Please download at least one model from the Local Models tab."
        )
        return None

    # Log available memory for the specified device
    available_memory = get_available_memory_for_device(device)
    memory_type = "VRAM" if device == "cuda" else "RAM"
    log_info(f"[TranslationRuntime] Available {memory_type}: {available_memory:.1f} GB")

    # Step 1: Try to select best model for the specified device
    log_info(f"[TranslationRuntime] Selecting best model for device={device}...")
    best_model_id = select_best_translation_model(downloaded_models, device=device)
    actual_device = device

    # Step 2: If GPU has no suitable model, fallback to CPU
    if best_model_id is None and device == "cuda":
        log_warning(
            f"[TranslationRuntime] No suitable model for GPU VRAM ({available_memory:.1f} GB), "
            f"falling back to CPU..."
        )
        actual_device = "cpu"
        cpu_memory = get_available_memory_for_device("cpu")
        log_info(f"[TranslationRuntime] Available RAM: {cpu_memory:.1f} GB")
        best_model_id = select_best_translation_model(downloaded_models, device="cpu")

    # Step 3: If CPU also has no suitable model, force smallest downloaded model
    if best_model_id is None:
        log_warning(
            "[TranslationRuntime] No suitable model for available RAM, "
            "forcing smallest downloaded model..."
        )
        all_models = get_all_translation_models()
        for model_info in all_models:
            if model_info.huggingface_id in downloaded_models:
                best_model_id = model_info.huggingface_id
                actual_device = "cpu"  # Force CPU for safety
                log_warning(
                    f"[TranslationRuntime] Forcing model: {model_info.display_name} "
                    f"(requires {model_info.runtime_memory_gb:.1f} GB RAM) on CPU"
                )
                break

    if best_model_id is None:
        log_error("[TranslationRuntime] Could not select any translation model")
        return None

    # Log the final selection
    model_info = get_translation_model_info(best_model_id)
    required_memory = get_required_memory_for_model(best_model_id, actual_device)
    log_info(
        f"[TranslationRuntime] Selected model: {model_info.display_name}, "
        f"device: {actual_device}, required memory: {required_memory:.1f} GB"
    )
    log_info(
        f"[TranslationRuntime] Model size: {model_info.model_size_mb / 1024:.1f} GB, "
        f"Precision: {model_info.precision}"
    )

    log_debug(
        f"[TranslationRuntime] Loading model with src_lang={src_lang}, tgt_lang={tgt_lang}, device={actual_device}"
    )
    log_debug(f"[TranslationRuntime] progress callback: {progress is not None}, type: {type(progress).__name__ if progress else 'N/A'}")

    try:
        log_info(f"[TranslationRuntime] Calling local_model_manager.get_model_with_fallback()...")
        log_debug(f"[TranslationRuntime] Passing progress to get_model_with_fallback: {progress is not None}")
        model_obj, _ = local_model_manager.get_model_with_fallback(
            best_model_id,
            device=actual_device,
            src_lang=src_lang,
            tgt_lang=tgt_lang,
            progress=progress,
        )
        if model_obj:
            log_success(
                f"Translation model {model_info.display_name} loaded successfully on {actual_device}"
            )
            return model_obj
        log_error(f"Failed to load translation model {model_info.display_name}")
    except Exception as e:
        log_error(f"Error loading model {model_info.display_name}: {e}")

    return None


def get_translation_model_by_id(
    model_id: str,
    src_lang: str,
    tgt_lang: str,
    device: str = "cpu",
    progress: Optional[Any] = None,
) -> Optional[Any]:
    """Load a specific translation model by ID.

    Use this when you want to load a specific model rather than
    auto-selecting based on memory.

    Args:
        model_id: HuggingFace 模型 ID（如 "google/madlad400-3b-mt"）
        src_lang: Source language code
        tgt_lang: Target language code
        device: Device to load model on
        progress: Optional progress callback for reporting loading status

    Returns:
        Model callable object or None if loading fails
    """
    model_info = get_translation_model_info(model_id)
    if model_info is None:
        log_error(f"Unknown model ID: {model_id}")
        return None

    log_info(f"Loading translation model: {model_info.display_name}")

    try:
        model_obj, _ = local_model_manager.get_model_with_fallback(
            model_id,
            device=device,
            src_lang=src_lang,
            tgt_lang=tgt_lang,
            progress=progress,
        )
        if model_obj:
            log_success(
                f"Translation model {model_info.display_name} loaded successfully"
            )
            return model_obj
        log_error(f"Failed to load translation model {model_info.display_name}")
    except Exception as e:
        log_error(f"Error loading model {model_info.display_name}: {e}")

    return None
