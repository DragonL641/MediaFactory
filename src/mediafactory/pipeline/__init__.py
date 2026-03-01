"""流水线处理包。

提供基于流水线的架构，用于视频字幕生成。
每个处理步骤都作为独立阶段实现，可以单独使用或与其他阶段组合。

架构：
    ProcessingContext (数据流)
        ↓
    ProcessingStage (抽象基类)
        ↓
    具体阶段 (音频、转录、翻译、SRT)
        ↓
    Pipeline (编排)

示例：
    # 创建默认流水线
    pipeline = Pipeline.create_default()

    # 或创建自定义流水线
    pipeline = Pipeline([
        AudioExtractionStage(audio_engine),
        TranscriptionStage(recognition_engine, model),
        TranslationStage(translation_engine),
        SRTGenerationStage(srt_engine),
    ])

    # 执行
    context = ProcessingContext(video_path="video.mp4", tgt_lang="zh")
    result = pipeline.execute(context)
"""

from .context import ProcessingContext, ProcessingResult
from .stage import ProcessingStage
from .pipeline import Pipeline
from .stages import (
    AudioExtractionStage,
    TranscriptionStage,
    TranslationStage,
    SRTGenerationStage,
)

__all__ = [
    # Context
    "ProcessingContext",
    "ProcessingResult",
    # Base classes
    "ProcessingStage",
    "Pipeline",
    # Concrete stages
    "AudioExtractionStage",
    "TranscriptionStage",
    "TranslationStage",
    "SRTGenerationStage",
]
