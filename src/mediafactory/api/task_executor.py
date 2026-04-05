"""
任务执行器

桥接 API 层和现有 Service 层，
"""

import asyncio
import logging
from typing import Any, Callable, Coroutine, Dict, Optional

from mediafactory.api.schemas import AudioConfig, EnhancementConfig, SubtitleConfig, TaskConfig, TaskType
from mediafactory.core.progress_protocol import ProgressCallback
from mediafactory.core.tool import CancellationToken
from mediafactory.exceptions import ConfigurationError

logger = logging.getLogger(__name__)


def _check_readiness(requirement: str, message: str):
    """检查前置条件，不满足时抛出 ConfigurationError"""
    from mediafactory.services.models import ModelStatusService

    readiness = ModelStatusService().get_readiness()

    if requirement == "whisper" and not readiness["whisper_ready"]:
        raise ConfigurationError(message)
    elif requirement == "translation_local" and not readiness["translation_ready"]:
        raise ConfigurationError(message)
    elif requirement == "enhancement" and not readiness["enhancement_ready"]:
        raise ConfigurationError(message)


# API 层使用标准 logging，通过 InterceptHandler 自动重定向到 loguru
# 详见 mediafactory.logging.loguru_logger.setup_logging_intercept


class SimpleProgressAdapter(ProgressCallback):
    """简单的进度回调适配器，委托 CancellationToken 实现取消检查"""

    def __init__(self, callback: Callable[[float, str, str], None], cancel_token: CancellationToken):
        self._callback = callback
        self._cancel_token = cancel_token
        self._current_stage: str = ""

    def set_stage(self, stage: str) -> None:
        """设置当前处理阶段"""
        self._current_stage = stage

    def update(self, progress: float, message: str = "") -> None:
        if not self.is_cancelled():
            self._callback(progress, message, self._current_stage)

    def is_cancelled(self) -> bool:
        return self._cancel_token.is_cancelled()

    def cancel(self):
        self._cancel_token.cancel()


def _run_async(coro: Coroutine) -> Any:
    """在独立事件循环中运行异步协程"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _make_result(result) -> Dict[str, Any]:
    """统一构造任务执行结果"""
    return {
        "output_path": getattr(result, "output_path", None),
        "success": result.success,
        "error": result.error_message if not result.success else None,
    }


# =============================================================================
# 异步执行函数
# =============================================================================


async def _execute_subtitle_async(config: TaskConfig, progress: ProgressCallback) -> Dict[str, Any]:
    from mediafactory.services.subtitle import SubtitleService

    sub = config.subtitle_config or SubtitleConfig()
    service = SubtitleService()
    result = await service.generate_subtitle(
        video_path=config.input_path,
        source_lang=config.source_lang,
        target_lang=config.target_lang,
        use_llm=config.use_llm,
        llm_preset=config.llm_preset,
        output_format=sub.output_format,
        bilingual=sub.bilingual,
        bilingual_layout=sub.bilingual_layout,
        style_preset=sub.style_preset,
        progress=progress,
    )
    return _make_result(result)


async def _execute_audio_async(config: TaskConfig, progress: ProgressCallback) -> Dict[str, Any]:
    from mediafactory.services.audio import AudioService

    audio = config.audio_config or AudioConfig()
    service = AudioService()
    result = await service.extract_audio(
        video_path=config.input_path,
        output_path=config.output_path,
        progress=progress,
        sample_rate=audio.sample_rate,
        channels=audio.channels,
        filter_enabled=audio.filter_enabled,
        highpass_freq=audio.highpass_freq,
        lowpass_freq=audio.lowpass_freq,
        volume=audio.volume,
        output_format=audio.output_format,
    )
    return _make_result(result)


async def _execute_transcribe_async(config: TaskConfig, progress: ProgressCallback) -> Dict[str, Any]:
    from mediafactory.services.transcription import TranscriptionService

    sub = config.subtitle_config or SubtitleConfig()
    service = TranscriptionService()
    result = await service.transcribe(
        audio_path=config.input_path,
        language=config.source_lang,
        progress=progress,
        output_format=sub.output_format,
    )
    return _make_result(result)


async def _execute_translate_async(config: TaskConfig, progress: ProgressCallback) -> Dict[str, Any]:
    from mediafactory.services.translation import TranslationService

    service = TranslationService()

    if config.input_path.endswith((".srt", ".ass", ".vtt")):
        result = await service.translate_srt(
            srt_path=config.input_path,
            target_lang=config.target_lang,
            use_llm=config.use_llm,
            llm_preset=config.llm_preset,
            output_format=config.output_format,
            progress=progress,
        )
    elif config.input_text:
        result = await service.translate_text(
            text=config.input_text,
            target_lang=config.target_lang,
            use_llm=config.use_llm,
            llm_preset=config.llm_preset,
            progress=progress,
        )
    else:
        raise ValueError("Translation task requires either input_path (SRT file) or input_text")

    return _make_result(result)


async def _execute_enhance_async(config: TaskConfig, progress: ProgressCallback) -> Dict[str, Any]:
    from mediafactory.services.video_enhancement import VideoEnhancementService

    enh = config.enhancement_config or EnhancementConfig()
    service = VideoEnhancementService()
    result = await service.enhance(
        video_path=config.input_path,
        scale=enh.scale,
        model_type=enh.model,
        denoise=enh.denoise,
        temporal=enh.temporal,
        output_path=config.output_path,
        progress=progress,
    )
    return _make_result(result)


# =============================================================================
# 同步入口函数（供 task_manager 调用）
# =============================================================================


def _create_executor(
    async_fn: Callable,
    readiness_check: Optional[Callable[[TaskConfig], None]] = None,
    task_name: str = "",
):
    """创建同步任务执行器（通用模板）。

    Args:
        async_fn: 异步执行函数，签名为 (config, progress_adapter) -> Dict
        readiness_check: 可选的前置条件检查函数，签名为 (config) -> None
        task_name: 任务名称，用于日志
    """

    def executor(
        config: TaskConfig,
        progress_callback: Callable[[float, str, str], None],
        cancel_token: CancellationToken,
    ) -> Dict[str, Any]:
        if readiness_check:
            readiness_check(config)
        adapter = SimpleProgressAdapter(progress_callback, cancel_token)
        try:
            return _run_async(async_fn(config, adapter))
        except Exception as e:
            logger.exception(f"{task_name} task failed: {e}")
            raise

    return executor


# 前置条件检查函数
def _check_whisper(_config: TaskConfig):
    _check_readiness("whisper", "Whisper model not downloaded. Please go to Settings to download a Whisper model.")


def _check_translation(config: TaskConfig):
    if not config.use_llm:
        _check_readiness(
            "translation_local",
            "Translation model not downloaded. Please go to Settings to download a translation model.",
        )


def _check_enhancement(_config: TaskConfig):
    _check_readiness(
        "enhancement",
        "Enhancement models not fully downloaded. Please go to Settings to download all enhancement models.",
    )


# 任务类型到执行器的映射
TASK_EXECUTORS = {
    TaskType.SUBTITLE: _create_executor(_execute_subtitle_async, _check_whisper, "Subtitle"),
    TaskType.AUDIO: _create_executor(_execute_audio_async, task_name="Audio"),
    TaskType.TRANSCRIBE: _create_executor(_execute_transcribe_async, _check_whisper, "Transcribe"),
    TaskType.TRANSLATE: _create_executor(_execute_translate_async, _check_translation, "Translate"),
    TaskType.ENHANCE: _create_executor(_execute_enhance_async, _check_enhancement, "Enhance"),
}


def get_executor(task_type: TaskType):
    """获取任务执行器"""
    return TASK_EXECUTORS.get(task_type)
