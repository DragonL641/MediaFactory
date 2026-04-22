"""Memory detection utilities for MediaFactory model selection.

This module provides memory detection and model recommendation utilities
for both installation wizard and runtime model selection.
"""

from dataclasses import dataclass

from .model_registry import (
    get_available_memory_gb,
    get_memory_tier,
    get_system_total_memory_gb,
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
