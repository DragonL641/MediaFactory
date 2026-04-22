"""MediaFactory engine package."""

from .audio import AudioEngine
from .recognition import RecognitionEngine
from .translation import TranslationEngine
from .srt import SRTEngine
from .ass_engine import ASSEngine
from .video_composer import VideoComposer
from .postprocess import PostProcessEngine

# Lazy imports for video enhancement (requires torch)
VideoEnhancementEngine = None
EnhancementConfig = None


def __getattr__(name):
    """Lazy import for video enhancement that requires torch."""
    global VideoEnhancementEngine, EnhancementConfig

    if name in (
        "VideoEnhancementEngine",
        "EnhancementConfig",
    ):
        from .video_enhancement import (
            VideoEnhancementEngine as _VideoEnhancementEngine,
            EnhancementConfig as _EnhancementConfig,
        )

        VideoEnhancementEngine = _VideoEnhancementEngine
        EnhancementConfig = _EnhancementConfig

        if name == "VideoEnhancementEngine":
            return VideoEnhancementEngine
        elif name == "EnhancementConfig":
            return EnhancementConfig

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "AudioEngine",
    "RecognitionEngine",
    "TranslationEngine",
    "SRTEngine",
    "ASSEngine",
    "VideoComposer",
    "PostProcessEngine",
    # 视频增强
    "VideoEnhancementEngine",
    "EnhancementConfig",
]
