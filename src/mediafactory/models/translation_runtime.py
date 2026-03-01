"""Translation model loading runtime utilities.

This module provides translation model loading using the unified model registry.
Models are automatically selected based on available system memory.
All models use MADLAD400 architecture with 400+ language support.
"""

from typing import Any, Optional

from .local_models import local_model_manager
from .model_registry import (
    get_all_translation_models,
    get_translation_model_info,
    select_best_translation_model,
)
from ..logging import log_debug, log_error, log_info, log_success, log_warning


def get_translation_model(
    src_lang: str,
    tgt_lang: str,
    device: str = "cpu",
) -> Optional[Any]:
    """Load a translation model based on language and available resources.

    Automatically selects the best available model from downloaded models
    based on current system memory.

    Args:
        src_lang: Source language code (e.g., "zh", "en", "ja")
        tgt_lang: Target language code (e.g., "zh", "en")
        device: Device to load model on (default: "cpu")

    Returns:
        Model callable object or None if loading fails
    """
    # Get downloaded translation models
    downloaded_models = local_model_manager.get_downloaded_translation_models()

    if not downloaded_models:
        log_error(
            "No translation models downloaded. "
            "Please download at least one model from the Local Models tab."
        )
        return None

    # Select best model based on available memory
    best_model_id = select_best_translation_model(downloaded_models)

    if best_model_id is None:
        log_warning(
            "Available memory insufficient for any downloaded model. "
            "Consider closing other applications or using LLM API translation."
        )
        # Fall back to smallest downloaded model
        all_models = get_all_translation_models()
        for model_info in all_models:
            if model_info.model_id in downloaded_models:
                best_model_id = model_info.model_id
                log_warning(
                    f"Falling back to smallest model: {model_info.display_name}"
                )
                break

    if best_model_id is None:
        log_error("Could not select any translation model")
        return None

    model_info = get_translation_model_info(best_model_id)
    log_info(f"Selected translation model: {model_info.display_name}")

    log_debug(
        f"[TranslationRuntime] Loading model with src_lang={src_lang}, tgt_lang={tgt_lang}, device={device}"
    )

    try:
        model_obj, _ = local_model_manager.get_model_with_fallback(
            best_model_id,
            device=device,
            src_lang=src_lang,
            tgt_lang=tgt_lang,
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


def get_translation_model_by_id(
    model_id: str,
    src_lang: str,
    tgt_lang: str,
    device: str = "cpu",
) -> Optional[Any]:
    """Load a specific translation model by ID.

    Use this when you want to load a specific model rather than
    auto-selecting based on memory.

    Args:
        model_id: HuggingFace 模型 ID（如 "google/madlad400-3b-mt"）
        src_lang: Source language code
        tgt_lang: Target language code
        device: Device to load model on

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
