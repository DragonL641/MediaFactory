"""媒体任务执行器（统一任务入口）。

按 TaskType 分发：组装 ProcessingContext、选择 Pipeline 工厂或直调引擎，
返回 ProcessingResult。

错误通道约定（拉直）：
- Pipeline.execute 内部已把异常统一转为失败的 ProcessingResult，此处原样透传；
- 直调引擎的路径不捕获异常，由 TaskManager 统一捕获并标记 FAILED；
- 本模块不做结果重包装（旧 service 层的重包会丢失 error_context）。

进度约定：本模块不发送任何进度里程碑，进度由 stage 层（里程碑）与
引擎层（内部值）负责；全局区间映射由 Pipeline 的 _StageProgress 完成。
"""

import asyncio
import functools
from pathlib import Path
from typing import Callable, Optional

from mediafactory.api.schemas import (
    AudioConfig,
    EnhancementConfig,
    SubtitleConfig,
    TaskConfig,
    TaskType,
)
from mediafactory.config import get_config
from mediafactory.core.progress_protocol import ProgressCallback
from mediafactory.engine.audio import AudioEngine
from mediafactory.engine.recognition import RecognitionEngine
from mediafactory.engine.srt import SRTEngine
from mediafactory.engine.translation import TranslationEngine
from mediafactory.exceptions import ConfigurationError
from mediafactory.llm import initialize_llm_backend
from mediafactory.logging import log_error
from mediafactory.pipeline import Pipeline
from mediafactory.pipeline.context import ProcessingContext, ProcessingResult

# ==================== 引擎缓存（懒加载，进程内复用） ====================

_audio_engine: Optional[AudioEngine] = None
_recognition_engine: Optional[RecognitionEngine] = None
_srt_engine: Optional[SRTEngine] = None
_local_translation_engine: Optional[TranslationEngine] = None


def _get_audio_engine() -> AudioEngine:
    global _audio_engine
    if _audio_engine is None:
        _audio_engine = AudioEngine()
    return _audio_engine


def _get_recognition_engine() -> RecognitionEngine:
    global _recognition_engine
    if _recognition_engine is None:
        _recognition_engine = RecognitionEngine()
    return _recognition_engine


def _get_srt_engine() -> SRTEngine:
    global _srt_engine
    if _srt_engine is None:
        _srt_engine = SRTEngine()
    return _srt_engine


def _get_local_translation_engine() -> TranslationEngine:
    global _local_translation_engine
    if _local_translation_engine is None:
        _local_translation_engine = TranslationEngine()
    return _local_translation_engine


# ==================== 前置条件 ====================

_READINESS_KEYS = {
    "whisper": "whisper_ready",
    "translation_local": "translation_ready",
    "enhancement": "enhancement_ready",
}

_READINESS_MESSAGES = {
    "whisper": "Whisper model not downloaded. Please go to Settings to download a Whisper model.",
    "translation_local": "Translation model not downloaded. Please go to Settings to download a translation model.",
    "enhancement": "Enhancement models not fully downloaded. Please go to Settings to download all enhancement models.",
}

_readiness_service = None


def _require_ready(key: str) -> None:
    """任务前置条件检查，不满足时抛 ConfigurationError。"""
    global _readiness_service
    from mediafactory.services.models import ModelStatusService

    if _readiness_service is None:
        _readiness_service = ModelStatusService()
    readiness = _readiness_service.get_readiness()
    if not readiness[_READINESS_KEYS[key]]:
        raise ConfigurationError(message=_READINESS_MESSAGES[key])


def _select_translation_engine(config: TaskConfig) -> TranslationEngine:
    """按任务配置选择翻译引擎：LLM 优先，初始化失败回退本地。"""
    if config.use_llm:
        backend = initialize_llm_backend(get_config(), preset=config.llm_preset)
        if backend and backend.is_available:
            return TranslationEngine(llm_backend=backend, use_llm_backend=True)
        log_error("LLM backend initialization failed, falling back to local model")
    return _get_local_translation_engine()


# ==================== 任务执行函数 ====================


async def run_subtitle(
    config: TaskConfig, progress: ProgressCallback
) -> ProcessingResult:
    """字幕生成：音频提取 → 转录 → 后处理 → 翻译 → 字幕文件（6 stage Pipeline）"""
    _require_ready("whisper")
    sub = config.subtitle_config or SubtitleConfig()

    context = ProcessingContext(
        video_path=config.input_path,
        src_lang=config.source_lang,
        tgt_lang=config.target_lang,
        progress_callback=progress,
        bilingual=sub.bilingual,
        bilingual_layout=sub.bilingual_layout,
        style_preset=sub.style_preset,
        output_format=sub.output_format,
        requested_output_path=config.output_path,
    )
    pipeline = Pipeline.create_default(
        _get_audio_engine(),
        _get_recognition_engine(),
        _select_translation_engine(config),
        _get_srt_engine(),
    )
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, pipeline.execute, context)


async def run_audio(config: TaskConfig, progress: ProgressCallback) -> ProcessingResult:
    """音频提取：直调 AudioEngine（单动作流程不走 Pipeline）"""
    audio = config.audio_config or AudioConfig()
    loop = asyncio.get_running_loop()
    audio_path = await loop.run_in_executor(
        None,
        functools.partial(
            _get_audio_engine().extract,
            config.input_path,
            progress=progress,
            output_path=config.output_path,
            sample_rate=audio.sample_rate,
            channels=audio.channels,
            filter_enabled=audio.filter_enabled,
            highpass_freq=audio.highpass_freq,
            lowpass_freq=audio.lowpass_freq,
            volume=audio.volume,
            output_format=audio.output_format,
        ),
    )
    return ProcessingResult(success=True, output_path=audio_path)


async def run_transcribe(
    config: TaskConfig, progress: ProgressCallback
) -> ProcessingResult:
    """独立转录：模型加载 → 转录 → 后处理 → 字幕（4 stage Pipeline）"""
    _require_ready("whisper")
    sub = config.subtitle_config or SubtitleConfig()
    context = ProcessingContext(
        audio_path=config.input_path,
        src_lang=config.source_lang if config.source_lang != "auto" else None,
        progress_callback=progress,
        output_format=sub.output_format,
    )
    pipeline = Pipeline.create_transcribe_standalone(
        _get_recognition_engine(), _get_srt_engine()
    )
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, pipeline.execute, context)


async def run_translate(
    config: TaskConfig, progress: ProgressCallback
) -> ProcessingResult:
    """翻译：SRT/ASS/VTT 文件走 Pipeline，纯文本直调翻译引擎"""
    if not config.use_llm:
        _require_ready("translation_local")

    if config.input_path.lower().endswith((".srt", ".ass", ".vtt")):
        return await _translate_file(config, progress)
    if config.input_text:
        return await _translate_text(config, progress)
    raise ValueError(
        "Translation task requires either input_path (SRT file) or input_text"
    )


async def _translate_file(
    config: TaskConfig, progress: ProgressCallback
) -> ProcessingResult:
    srt_path = Path(config.input_path)
    srt_engine = _get_srt_engine()
    segments = srt_engine.parse(str(srt_path))

    if not segments:
        return ProcessingResult(
            success=False,
            error_message="No segments found in SRT file",
            error_type="ValidationError",
        )

    ext_map = {"srt": ".srt", "ass": ".ass", "vtt": ".vtt", "txt": ".txt"}
    ext = ext_map.get(config.output_format, ".srt")
    output_path = config.output_path or str(
        srt_path.with_suffix(f".{config.target_lang}{ext}")
    )

    context = ProcessingContext(
        src_lang="auto",
        tgt_lang=config.target_lang,
        progress_callback=progress,
        output_format=config.output_format,
        requested_output_path=output_path,
    )
    context.transcription_result = {"segments": segments}

    pipeline = Pipeline.create_translation_only(
        _select_translation_engine(config), srt_engine
    )
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, pipeline.execute, context)


async def _translate_text(
    config: TaskConfig, progress: ProgressCallback
) -> ProcessingResult:
    text = config.input_text
    target_lang = config.target_lang
    loop = asyncio.get_running_loop()

    if config.use_llm:
        backend = initialize_llm_backend(get_config(), preset=config.llm_preset)
        if backend and backend.is_available:
            try:
                from mediafactory.llm import TranslationRequest

                request = TranslationRequest(
                    text=text, src_lang="auto", tgt_lang=target_lang
                )
                result = await loop.run_in_executor(None, backend.translate, request)
                if result.success:
                    translated = result.translated_text
                else:
                    raise Exception(result.error_message or "LLM translation failed")
            except Exception as e:
                translated = await _translate_text_locally(text, target_lang, e)
        else:
            log_error("LLM backend unavailable, falling back to local model")
            translated = await _translate_text_locally(text, target_lang, None)
    else:
        translated = await _translate_text_locally(text, target_lang, None)

    return ProcessingResult(
        success=True,
        metadata={
            "original_text": text,
            "translated_text": translated,
            "target_lang": target_lang,
        },
    )


async def _translate_text_locally(
    text: str, target_lang: str, llm_error: Optional[Exception]
) -> str:
    """本地引擎翻译单条文本（segments 包装协议）；LLM 失败时记录回退原因。"""
    from mediafactory.logging import log_info

    if llm_error is not None:
        log_info(
            f"LLM text translation failed: {llm_error}, falling back to local model"
        )
    loop = asyncio.get_running_loop()
    wrapped = {"segments": [{"text": text}]}
    result = await loop.run_in_executor(
        None, _get_local_translation_engine().translate, wrapped, "auto", target_lang
    )
    return result["segments"][0]["text"]


async def run_enhance(
    config: TaskConfig, progress: ProgressCallback
) -> ProcessingResult:
    """视频增强：直调 VideoEnhancementEngine（单动作流程不走 Pipeline）"""
    _require_ready("enhancement")
    # 延迟导入以避免启动时加载 ML 依赖
    from mediafactory.engine.video_enhancement import (
        EnhancementConfig as EngineEnhancementConfig,
        VideoEnhancementEngine,
    )

    enh = config.enhancement_config or EnhancementConfig()
    engine_config = EngineEnhancementConfig(
        scale=enh.scale,
        model_type=enh.model,
        denoise=enh.denoise,
        temporal=enh.temporal,
    )
    src = Path(config.input_path)
    output_path = config.output_path or str(src.with_stem(f"{src.stem}_enhanced"))
    engine = VideoEnhancementEngine(engine_config)
    loop = asyncio.get_running_loop()
    result_path = await loop.run_in_executor(
        None,
        functools.partial(
            engine.enhance, config.input_path, output_path, progress=progress
        ),
    )
    return ProcessingResult(
        success=True,
        output_path=result_path,
        metadata={
            "video_path": config.input_path,
            "scale": enh.scale,
            "denoise": enh.denoise,
            "temporal": enh.temporal,
        },
    )


# ==================== 注册表 ====================

RUNNERS: dict[TaskType, Callable] = {
    TaskType.SUBTITLE: run_subtitle,
    TaskType.AUDIO: run_audio,
    TaskType.TRANSCRIBE: run_transcribe,
    TaskType.TRANSLATE: run_translate,
    TaskType.ENHANCE: run_enhance,
}
