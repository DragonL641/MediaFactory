"""MediaFactory engine package."""

from .audio import AudioEngine
from .recognition import RecognitionEngine
from .translation import TranslationEngine
from .srt import SRTEngine
from .ass_engine import ASSEngine
from .video_composer import VideoComposer

# Lazy imports for video enhancement (requires torch)
VideoEnhancementEngine = None
EnhancementConfig = None
create_enhancement_engine = None


def __getattr__(name):
    """Lazy import for video enhancement that requires torch."""
    global VideoEnhancementEngine, EnhancementConfig, create_enhancement_engine

    if name in ("VideoEnhancementEngine", "EnhancementConfig", "create_enhancement_engine"):
        from .video_enhancement import (
            VideoEnhancementEngine as _VideoEnhancementEngine,
            EnhancementConfig as _EnhancementConfig,
            create_enhancement_engine as _create_enhancement_engine,
        )

        VideoEnhancementEngine = _VideoEnhancementEngine
        EnhancementConfig = _EnhancementConfig
        create_enhancement_engine = _create_enhancement_engine

        if name == "VideoEnhancementEngine":
            return VideoEnhancementEngine
        elif name == "EnhancementConfig":
            return EnhancementConfig
        elif name == "create_enhancement_engine":
            return create_enhancement_engine

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "AudioEngine",
    "RecognitionEngine",
    "TranslationEngine",
    "SRTEngine",
    "ASSEngine",
    "VideoComposer",
    # 视频增强
    "VideoEnhancementEngine",
    "EnhancementConfig",
    "create_enhancement_engine",
]
