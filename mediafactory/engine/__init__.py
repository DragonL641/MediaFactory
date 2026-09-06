"""MediaFactory engine package."""

from .ass_engine import ASSEngine
from .audio import AudioEngine
from .postprocess import PostProcessEngine
from .recognition import RecognitionEngine
from .srt import SRTEngine
from .translation import TranslationEngine

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
            EnhancementConfig as _EnhancementConfig,
        )
        from .video_enhancement import (
            VideoEnhancementEngine as _VideoEnhancementEngine,
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
    "PostProcessEngine",
    # 视频增强
    "VideoEnhancementEngine",
    "EnhancementConfig",
]
