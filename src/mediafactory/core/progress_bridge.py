"""GUI Progress Bridge for MediaFactory.

This module provides the GUIProgressBridge class that bridges the GUI observer
callbacks to the ProgressCallback protocol, enabling proper progress tracking
from pipeline stages through to the GUI layer.

Architecture:
    GUI Layer (gui_observers) → GUIProgressBridge → ProcessingContext → Pipeline Stages
"""

from typing import Dict, Any, Optional, Callable
from ..core.progress_protocol import ProgressCallback, NO_OP_PROGRESS


class GUIProgressBridge(ProgressCallback):
    """Bridges GUI observer callbacks to ProgressCallback protocol.

    This bridge handles:
    1. Mapping stage names to GUI callback keys (transcription → recognition_progress_func)
    2. Mapping stage-level progress (0-100%) to batch-level progress (0-100%)
    3. Combining progress across multiple files in batch processing

    Usage:
        bridge = GUIProgressBridge(
            gui_observers=gui_observers,
            current_file_index=1,
            total_files=3
        )
        ctx.progress_callback = bridge
    """

    # Standard keys for GUI observer callbacks
    AUDIO_PROGRESS = "audio_progress_func"
    RECOGNITION_PROGRESS = "recognition_progress_func"
    TRANSLATION_PROGRESS = "translation_progress_func"
    CANCELLED = "cancelled"

    # Map stage names to GUI observer callback keys
    STAGE_CALLBACK_MAP = {
        "model_loading": "recognition_progress_func",
        "audio_extraction": "audio_progress_func",
        "transcription": "recognition_progress_func",
        "translation": "translation_progress_func",
        "srt_generation": "translation_progress_func",
    }

    # Progress ranges for each stage within a single file (0-100)
    STAGE_RANGES = {
        "model_loading": (0.0, 10.0),  # 0-10%
        "audio_extraction": (10.0, 20.0),  # 10-20%
        "transcription": (20.0, 70.0),  # 20-70% (main work)
        "translation": (70.0, 95.0),  # 70-95%
        "srt_generation": (95.0, 100.0),  # 95-100%
    }

    def __init__(
        self,
        gui_observers: Optional[Dict[str, Any]] = None,
        current_file_index: int = 1,
        total_files: int = 1,
        on_stage_change: Optional[Callable[[str], None]] = None,
        stage_callback_map: Optional[Dict[str, str]] = None,
        stage_ranges: Optional[Dict[str, tuple]] = None,
        progress_key: Optional[str] = None,
        operation_name: str = "",
    ):
        """Initialize the GUI progress bridge.

        Args:
            gui_observers: Dictionary of GUI observer callbacks
            current_file_index: Current file index (1-based)
            total_files: Total number of files to process
            on_stage_change: Optional callback when stage changes
            stage_callback_map: Custom stage name to callback key mapping
            stage_ranges: Custom stage progress ranges
            progress_key: Key for progress callback (for simple adapter mode)
            operation_name: Operation name for auto-detecting progress_key
        """
        self._gui_observers = gui_observers or {}
        self._current_file_index = current_file_index
        self._total_files = total_files
        self._on_stage_change = on_stage_change

        # Use provided configs or defaults
        self._stage_callback_map = stage_callback_map or self.STAGE_CALLBACK_MAP
        self._stage_ranges = stage_ranges or self.STAGE_RANGES

        # Simple adapter mode (backward compatibility)
        self._progress_key = progress_key or self._auto_detect_key(operation_name)

        # Current stage tracking
        self._current_stage: str = "model_loading"
        self._current_stage_progress: float = 0.0

    def _auto_detect_key(self, operation_name: str) -> Optional[str]:
        """Auto-detect progress key based on operation name."""
        operation_lower = operation_name.lower()
        if "audio" in operation_lower:
            return self.AUDIO_PROGRESS
        elif "识别" in operation_name or "recognition" in operation_lower:
            return self.RECOGNITION_PROGRESS
        elif "翻译" in operation_name or "translation" in operation_lower:
            return self.TRANSLATION_PROGRESS
        return None

    def set_stage(self, stage: str) -> None:
        """Set the current processing stage.

        Args:
            stage: Stage name (e.g., "transcription", "translation")
        """
        if stage in self._stage_ranges:
            self._current_stage = stage
            self._current_stage_progress = 0.0
            if self._on_stage_change:
                try:
                    self._on_stage_change(stage)
                except Exception:
                    pass  # Ignore callback errors

    def _get_stage_range(self, stage: str) -> tuple[float, float]:
        """Get the progress range for a stage.

        Args:
            stage: Stage name

        Returns:
            Tuple of (start_percent, end_percent)
        """
        return self._stage_ranges.get(stage, (0.0, 100.0))

    def _map_stage_to_batch_progress(
        self,
        stage: str,
        stage_progress: float,
    ) -> float:
        """Map stage progress to overall batch progress.

        Args:
            stage: Current stage name
            stage_progress: Progress within the stage (0-100)

        Returns:
            Overall batch progress (0-100)
        """
        stage_start, stage_end = self._get_stage_range(stage)

        # Calculate file-level progress
        # Map stage_progress (0-100) to stage range (stage_start to stage_end)
        file_progress = stage_start + (stage_progress / 100.0) * (
            stage_end - stage_start
        )

        # Calculate batch-level progress
        # Each file contributes (100 / total_files) percent to overall progress
        completed_files = self._current_file_index - 1
        batch_progress = (completed_files / self._total_files) * 100.0 + (
            file_progress / self._total_files
        )

        return batch_progress

    def _get_callback_for_stage(self, stage: str) -> Optional[Callable]:
        """Get the appropriate GUI callback for a stage.

        Args:
            stage: Stage name

        Returns:
            Callback function or None
        """
        # First try stage-based mapping
        callback_key = self._stage_callback_map.get(stage)
        if callback_key and callback_key in self._gui_observers:
            callback = self._gui_observers[callback_key]
            if callable(callback):
                return callback

        # Fallback to simple adapter mode
        if self._progress_key and self._progress_key in self._gui_observers:
            callback = self._gui_observers[self._progress_key]
            if callable(callback):
                return callback

        return None

    def update(self, progress: float, message: str = "") -> None:
        """Update progress.

        This method is called by pipeline stages to report progress.
        It maps the stage progress to batch progress and calls the GUI.

        Args:
            progress: Progress value (0-100) from the current stage
            message: Optional progress message
        """
        # Store stage progress
        self._current_stage_progress = progress

        # Get the appropriate callback for the current stage
        callback = self._get_callback_for_stage(self._current_stage)

        if callback:
            try:
                # Check if we should map to batch progress or use simple mode
                if self._total_files > 1 or self._current_stage in self._stage_ranges:
                    batch_progress = self._map_stage_to_batch_progress(
                        self._current_stage,
                        progress,
                    )
                    callback(batch_progress, message)
                else:
                    # Simple mode - direct pass-through
                    callback(progress, message)
            except Exception:
                # Silently handle GUI update errors
                pass

    def is_cancelled(self) -> bool:
        """Check if the operation should be cancelled.

        Returns:
            True if cancellation was requested
        """
        if self.CANCELLED in self._gui_observers:
            try:
                callback = self._gui_observers[self.CANCELLED]
                if callable(callback):
                    return callback()
            except Exception:
                pass
        return False

    def set_file_index(self, index: int) -> None:
        """Update the current file index.

        Args:
            index: New current file index (1-based)
        """
        self._current_file_index = index

    def get_current_stage(self) -> str:
        """Get the current processing stage.

        Returns:
            Current stage name
        """
        return self._current_stage


# =============================================================================
# Factory Functions
# =============================================================================


def create_gui_progress_bridge(
    gui_observers: Optional[Dict[str, Any]] = None,
    current_file_index: int = 1,
    total_files: int = 1,
    on_stage_change: Optional[Callable[[str], None]] = None,
) -> ProgressCallback:
    """Create a GUI progress bridge.

    Factory function that creates a GUIProgressBridge or returns NO_OP_PROGRESS.

    Args:
        gui_observers: Dictionary of GUI observer callbacks
        current_file_index: Current file index (1-based)
        total_files: Total number of files to process
        on_stage_change: Optional callback when stage changes

    Returns:
        GUIProgressBridge instance or NO_OP_PROGRESS
    """
    if not gui_observers:
        return NO_OP_PROGRESS

    return GUIProgressBridge(
        gui_observers=gui_observers,
        current_file_index=current_file_index,
        total_files=total_files,
        on_stage_change=on_stage_change,
    )


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "GUIProgressBridge",
    "create_gui_progress_bridge",
]
