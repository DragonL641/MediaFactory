"""Memory detection utilities for MediaFactory model selection.

This module provides memory detection and model recommendation utilities
for both installation wizard and runtime model selection.
"""

from dataclasses import dataclass
from typing import Optional

from .model_registry import (
    MEMORY_TIERS,
    get_available_memory_gb,
    get_best_translation_model_for_installation,
    get_memory_tier,
    get_recommended_translation_models,
    get_system_total_memory_gb,
    select_best_translation_model,
)

import psutil


@dataclass
class MemoryInfo:
    """System memory information container."""

    total_gb: int
    available_gb: float
    used_percent: float
    memory_tier: int

    @classmethod
    def from_system(cls) -> "MemoryInfo":
        """Create MemoryInfo from current system state.

        Returns:
            MemoryInfo instance with current system memory data
        """
        mem = psutil.virtual_memory()
        total_gb = int(mem.total / (1024**3))
        available_gb = mem.available / (1024**3)
        used_percent = mem.percent
        memory_tier = get_memory_tier(total_gb)

        return cls(
            total_gb=total_gb,
            available_gb=available_gb,
            used_percent=used_percent,
            memory_tier=memory_tier,
        )

    def can_run_model(self, runtime_memory_gb: float) -> bool:
        """Check if system can run a model with given runtime memory.

        Args:
            runtime_memory_gb: Required runtime memory in GB

        Returns:
            True if available memory is sufficient
        """
        return self.available_gb >= runtime_memory_gb

    def get_memory_status_text(self) -> str:
        """Get a human-readable memory status text.

        Returns:
            Memory status string for display
        """
        return f"{self.total_gb}GB RAM | {self.available_gb:.1f}GB available"


@dataclass
class ModelRecommendation:
    """Model recommendation result."""

    model_id: str
    display_name: str
    runtime_memory_gb: float
    recommended_system_gb: int
    can_run: bool
    is_downloaded: bool
    is_recommended: bool


def get_memory_info() -> MemoryInfo:
    """Get current system memory information.

    Returns:
        MemoryInfo instance with current system state
    """
    return MemoryInfo.from_system()


def get_translation_model_recommendations(
    downloaded_models: Optional[list[str]] = None,
) -> list[ModelRecommendation]:
    """Get model recommendations for the translation model selection UI.

    Args:
        downloaded_models: List of already downloaded model IDs

    Returns:
        List of ModelRecommendation objects for all translation models
    """
    from .model_registry import MODEL_REGISTRY, ModelType, get_all_translation_models

    if downloaded_models is None:
        downloaded_models = []

    memory_info = get_memory_info()
    best_model = get_best_translation_model_for_installation()
    all_models = get_all_translation_models()

    recommendations = []
    for model_info in all_models:
        can_run = memory_info.can_run_model(model_info.runtime_memory_gb)
        is_downloaded = model_info.huggingface_id in downloaded_models
        is_recommended = model_info.huggingface_id == best_model

        recommendations.append(
            ModelRecommendation(
                model_id=model_info.huggingface_id,
                display_name=model_info.display_name,
                runtime_memory_gb=model_info.runtime_memory_gb,
                recommended_system_gb=model_info.recommended_system_gb,
                can_run=can_run,
                is_downloaded=is_downloaded,
                is_recommended=is_recommended,
            )
        )

    return recommendations


def get_runtime_model_selection(downloaded_models: list[str]) -> Optional[str]:
    """Select the best model at runtime based on available memory.

    This is a convenience wrapper around select_best_translation_model
    that logs the selection process.

    Args:
        downloaded_models: List of downloaded model IDs

    Returns:
        Selected model ID, or None if no suitable model
    """
    return select_best_translation_model(downloaded_models)


def format_memory_size(size_gb: float) -> str:
    """Format memory size for display.

    Args:
        size_gb: Size in gigabytes

    Returns:
        Formatted string (e.g., "3GB", "500MB")
    """
    if size_gb >= 1:
        return f"{size_gb:.1f}GB".replace(".0GB", "GB")
    else:
        mb = size_gb * 1024
        return f"{mb:.0f}MB"


def get_memory_tier_description(tier: int) -> str:
    """Get description for a memory tier.

    Args:
        tier: Memory tier value

    Returns:
        Human-readable tier description
    """
    descriptions = {
        8: "Entry-level system",
        16: "Mid-range system",
        32: "High-end system",
        64: "Workstation",
        128: "Server-class system",
    }
    return descriptions.get(tier, "Unknown tier")
