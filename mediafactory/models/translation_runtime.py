"""Translation model loading runtime utilities.

This module provides translation model loading using the unified model registry.
Models are automatically selected based on available system memory.
Uses M2M100 architecture with 100 language support.
"""

from typing import Any, Optional

from .local_models import local_model_manager
from .model_registry import (
    get_available_memory_for_device,
    get_required_memory_for_model,
    get_translation_model_info,
)
from ..logging import log_debug, log_error, log_info, log_success, log_warning


def get_translation_model(
    src_lang: str,
    tgt_lang: str,
    device: str = "cpu",
    progress: Optional[Any] = None,
) -> Optional[Any]:
    """Load a translation model based on language and available resources.

    Checks if M2M100-1.2B is downloaded and has enough memory to run.
    Falls back to CPU if GPU memory is insufficient.

    Args:
        src_lang: Source language code (e.g., "zh", "en", "ja")
        tgt_lang: Target language code (e.g., "zh", "en")
        device: Device to load model on (default: "cpu")
        progress: Optional progress callback for reporting loading status

    Returns:
        Model callable object or None if loading fails
    """
    log_info(f"[TranslationRuntime] Starting model loading process...")
    log_info(
        f"[TranslationRuntime] Parameters: src_lang={src_lang}, tgt_lang={tgt_lang}, device={device}"
    )

    # The only supported translation model
    target_model_id = "facebook/m2m100_1.2B"

    # Check if the model is downloaded
    if not local_model_manager.is_model_available_locally(target_model_id):
        log_error(
            f"Translation model {target_model_id} is not downloaded. "
            "Please download it from the Local Models tab."
        )
        return None

    # Check available memory
    available_memory = get_available_memory_for_device(device)
    memory_type = "VRAM" if device == "cuda" else "RAM"
    required_memory = get_required_memory_for_model(target_model_id, device)
    log_info(
        f"[TranslationRuntime] Available {memory_type}: {available_memory:.1f} GB, required: {required_memory:.1f} GB"
    )

    actual_device = device

    # If GPU memory is insufficient, fallback to CPU
    if device == "cuda" and available_memory < required_memory:
        log_warning(
            f"[TranslationRuntime] GPU VRAM insufficient ({available_memory:.1f} GB < {required_memory:.1f} GB), "
            f"falling back to CPU..."
        )
        actual_device = "cpu"
        cpu_memory = get_available_memory_for_device("cpu")
        log_info(f"[TranslationRuntime] Available RAM: {cpu_memory:.1f} GB")

    # Log the final selection
    model_info = get_translation_model_info(target_model_id)
    log_info(
        f"[TranslationRuntime] Selected model: {model_info.display_name}, "
        f"device: {actual_device}"
    )
    log_info(
        f"[TranslationRuntime] Model size: {model_info.model_size_mb / 1024:.1f} GB, "
        f"Precision: {model_info.precision}"
    )

    log_debug(
        f"[TranslationRuntime] Loading model with src_lang={src_lang}, tgt_lang={tgt_lang}, device={actual_device}"
    )
    log_debug(
        f"[TranslationRuntime] progress callback: {progress is not None}, type: {type(progress).__name__ if progress else 'N/A'}"
    )

    try:
        log_info(
            f"[TranslationRuntime] Calling local_model_manager.get_model_with_fallback()..."
        )
        log_debug(
            f"[TranslationRuntime] Passing progress to get_model_with_fallback: {progress is not None}"
        )
        model_obj, _ = local_model_manager.get_model_with_fallback(
            target_model_id,
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
