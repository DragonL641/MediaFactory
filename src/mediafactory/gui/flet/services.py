"""
服务适配器

将现有引擎与 Flet GUI 连接，提供统一的异步接口。
"""

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

import flet as ft

from mediafactory.config import get_config
from mediafactory.engine.audio import AudioEngine
from mediafactory.engine.recognition import RecognitionEngine
from mediafactory.engine.translation import TranslationEngine
from mediafactory.engine.srt import SRTEngine
from mediafactory.logging import log_info, log_error, log_error_with_context, log_debug
from mediafactory.core.progress_protocol import ProgressCallback


@dataclass
class ProcessingProgress:
    """处理进度"""

    stage: str
    progress: float  # 0-100
    message: str
    file_index: int = 0
    total_files: int = 1


@dataclass
class ProcessingResult:
    """处理结果"""

    success: bool
    output_path: Optional[str] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    error_context: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class _SimpleProgressAdapter(ProgressCallback):
    """
    简化的进度适配器

    直接调用回调函数，不使用队列和轮询。
    适用于 Flet 0.80+ 的 page.run_task() 模式。
    """

    def __init__(
        self,
        callback: Callable[[float, str], None],
        is_cancelled_func: Optional[Callable[[], bool]] = None,
    ):
        self._callback = callback
        self._is_cancelled_func = is_cancelled_func

    def update(self, progress: float, message: str = "") -> None:
        """更新进度"""
        try:
            self._callback(progress, message)
        except Exception as e:
            log_debug(f"[ProgressAdapter] update failed: {e}")

    def is_cancelled(self) -> bool:
        """检查是否已取消"""
        if self._is_cancelled_func:
            return self._is_cancelled_func()
        return False


class SubtitleService:
    """
    字幕生成服务

    委托给 Pipeline 进行字幕生成，统一工作流和进度报告。
    """

    def __init__(self):
        self.config = get_config()
        self._audio_engine: Optional[AudioEngine] = None
        self._recognition_engine: Optional[RecognitionEngine] = None
        self._local_translation_engine: Optional[TranslationEngine] = None
        self._llm_translation_engine: Optional[TranslationEngine] = None
        self._srt_engine: Optional[SRTEngine] = None

        self._cancelled: bool = False

    @property
    def audio_engine(self) -> AudioEngine:
        if self._audio_engine is None:
            self._audio_engine = AudioEngine()
        return self._audio_engine

    @property
    def recognition_engine(self) -> RecognitionEngine:
        if self._recognition_engine is None:
            self._recognition_engine = RecognitionEngine()
        return self._recognition_engine

    @property
    def srt_engine(self) -> SRTEngine:
        if self._srt_engine is None:
            self._srt_engine = SRTEngine()
        return self._srt_engine

    def _get_translation_engine(
        self, use_llm: bool, llm_preset: str = "openai"
    ) -> TranslationEngine:
        """根据配置获取翻译引擎"""
        # 自动检测最佳设备
        from mediafactory.models.whisper_runtime import select_device
        device = select_device()  # 返回 "cuda" 或 "cpu"
        log_info(f"[SubtitleService] Detected device for translation engine: {device}")

        if use_llm:
            if self._llm_translation_engine is None:
                # 创建 LLM 翻译引擎
                from mediafactory.llm import initialize_llm_backend

                llm_backend = initialize_llm_backend(self.config, preset=llm_preset)
                if llm_backend is None:
                    log_error(
                        "LLM backend initialization failed, falling back to local"
                    )
                    # 回退到本地模型
                    return self._get_translation_engine(use_llm=False)
                self._llm_translation_engine = TranslationEngine(
                    use_llm_backend=True,
                    llm_backend=llm_backend,
                    device=device,
                )
            return self._llm_translation_engine
        else:
            if self._local_translation_engine is None:
                log_info(f"[SubtitleService] Creating local translation engine with device={device}")
                self._local_translation_engine = TranslationEngine(
                    use_local_models_only=False,
                    device=device,
                )
            return self._local_translation_engine

    def cancel(self) -> None:
        """取消处理"""
        self._cancelled = True

    def reset(self) -> None:
        """重置状态"""
        self._cancelled = False

    def _is_cancelled(self) -> bool:
        """检查是否已取消（供适配器使用）"""
        return self._cancelled

    async def generate_subtitles(
        self,
        video_path: str,
        page: ft.Page,
        output_path: Optional[str] = None,
        source_language: str = "auto",
        target_language: str = "zh",
        use_llm: bool = False,
        llm_preset: str = "openai",
        auto_translate: bool = True,
        output_format_type: str = "srt",
        bilingual: bool = False,
        bilingual_layout: str = "translate_on_top",
        style_preset: str = "default",
        progress_callback: Optional[Callable[[ProcessingProgress], None]] = None,
    ) -> ProcessingResult:
        """
        生成字幕

        委托给 Pipeline 执行完整的字幕生成流程。

        Args:
            video_path: 视频文件路径
            output_path: 输出路径（可选）
            source_language: 源语言
            target_language: 目标语言
            use_llm: 是否使用 LLM 翻译
            llm_preset: LLM 预设名称
            auto_translate: 是否自动翻译
            output_format_type: 输出格式（srt, ass 或 txt）
            bilingual: 是否生成双语字幕
            bilingual_layout: 双语布局
            style_preset: ASS样式预设
            progress_callback: 进度回调

        Returns:
            ProcessingResult: 处理结果
        """
        from mediafactory.pipeline.pipeline import Pipeline
        from mediafactory.pipeline.context import (
            ProcessingContext as PipelineContext,
            ProcessingResult as PipelineResult,
        )

        self.reset()
        video_path = Path(video_path)
        video_dir = video_path.parent
        video_name = video_path.stem

        # 确定输出路径
        if output_path is None:
            output_path = video_dir / f"{video_name}.{target_language}.srt"
        else:
            output_path = Path(output_path)

        progress_adapter: Optional[ProgressCallback] = None
        try:
            # 创建进度适配器
            if progress_callback:
                progress_adapter = _SimpleProgressAdapter(
                    callback=progress_callback,
                    is_cancelled_func=self._is_cancelled,
                )
            else:
                from mediafactory.core.progress_protocol import NO_OP_PROGRESS

                progress_adapter = NO_OP_PROGRESS

            # 根据配置获取翻译引擎
            log_info(f"[SubtitleService] Getting translation engine (use_llm={use_llm}, llm_preset={llm_preset})")
            translation_engine = self._get_translation_engine(use_llm, llm_preset)
            log_info(f"[SubtitleService] Translation engine ready")

            # 选择合适的 Pipeline 类型
            if auto_translate:
                pipeline = Pipeline.create_default(
                    audio_engine=self.audio_engine,
                    recognition_engine=self.recognition_engine,
                    translation_engine=translation_engine,
                    srt_engine=self.srt_engine,
                )
            else:
                pipeline = Pipeline.create_transcription_only(
                    audio_engine=self.audio_engine,
                    recognition_engine=self.recognition_engine,
                    srt_engine=self.srt_engine,
                )

            # 创建处理上下文
            context = PipelineContext(
                video_path=str(video_path),
                src_lang=None if source_language == "auto" else source_language,
                tgt_lang=target_language,
                output_path=str(output_path),
                progress_callback=progress_adapter,
                config={
                    "output_path": str(output_path),
                    "output_format_type": output_format_type,
                },
                bilingual=bilingual,
                bilingual_layout=bilingual_layout,
                style_preset=style_preset,
            )

            # 在线程池中执行 Pipeline（Pipeline 是同步的）
            # Pipeline 各阶段会通过 progress_callback 报告真实进度
            # 添加超时保护（5分钟），防止 CUDA 操作阻塞导致 UI 卡住
            loop = asyncio.get_event_loop()
            try:
                result: PipelineResult = await asyncio.wait_for(
                    loop.run_in_executor(None, pipeline.execute, context),
                    timeout=300.0  # 5分钟超时
                )
            except asyncio.TimeoutError:
                log_error_with_context(
                    "Subtitle generation timed out",
                    TimeoutError("Operation exceeded 5 minute limit"),
                    {"video_path": str(video_path)}
                )
                return ProcessingResult(
                    success=False,
                    error="Subtitle generation timeout (exceeded 5-minute limit). The video file may be too large or GPU incompatible."
                )

            # 里程碑进度：完成
            if result.success:
                progress_adapter.update(100, "Subtitle generation completed!")
            else:
                progress_adapter.update(
                    -1, f"Failed: {result.error_message}"
                )

            # 转换 PipelineResult 到 ProcessingResult
            return ProcessingResult(
                success=result.success,
                output_path=result.output_path,
                error=result.error_message if not result.success else None,
                error_type=result.error_type if not result.success else None,
                error_context=result.error_context if not result.success else None,
                metadata={
                    "source_language": source_language,
                    "target_language": target_language,
                    "use_llm": use_llm,
                    "auto_translate": auto_translate,
                },
            )

        except Exception as e:
            log_error_with_context(
                "Subtitle generation failed", e, {"video_path": str(video_path)}
            )
            return ProcessingResult(success=False, error=str(e))
        finally:
            pass  # 进度适配器无需清理

    def cleanup(self) -> None:
        """清理服务持有的所有资源

        实现 ResourceCleanupProtocol 接口。
        在应用退出或服务不再使用时调用。
        """
        import gc

        from mediafactory.logging import log_debug
        log_info("[SubtitleService] Starting cleanup...")

        # 清理翻译引擎
        if self._local_translation_engine is not None:
            if hasattr(self._local_translation_engine, "cleanup"):
                log_debug("[SubtitleService] Cleaning up local translation engine")
                self._local_translation_engine.cleanup()
            self._local_translation_engine = None

        if self._llm_translation_engine is not None:
            if hasattr(self._llm_translation_engine, "cleanup"):
                log_debug("[SubtitleService] Cleaning up LLM translation engine")
                self._llm_translation_engine.cleanup()
            self._llm_translation_engine = None

        # 清理其他引擎
        self._audio_engine = None
        self._recognition_engine = None
        self._srt_engine = None

        gc.collect()
        log_info("[SubtitleService] Cleanup completed")


class AudioService:
    """音频提取服务"""

    def __init__(self):
        self._engine: Optional[AudioEngine] = None
        self._cancelled: bool = False

    @property
    def engine(self) -> AudioEngine:
        if self._engine is None:
            self._engine = AudioEngine()
        return self._engine

    def cancel(self) -> None:
        self._cancelled = True

    def reset(self) -> None:
        self._cancelled = False

    async def extract_audio(
        self,
        video_path: str,
        page: ft.Page,
        output_path: Optional[str] = None,
        output_format: str = "wav",
        sample_rate: int = 48000,
        channels: int = 2,
        filter_enabled: bool = True,
        highpass_freq: int = 200,
        lowpass_freq: int = 3000,
        volume: float = 1.0,
        progress_callback: Optional[Callable[[ProcessingProgress], None]] = None,
    ) -> ProcessingResult:
        """提取音频

        Args:
            video_path: 输入视频文件路径
            output_path: 输出音频文件路径（可选）
            output_format: 输出格式 (wav/mp3/flac)
            sample_rate: 采样率 (Hz)
            channels: 声道数 (1=单声道, 2=立体声)
            filter_enabled: 是否启用音频滤波器
            highpass_freq: 高通滤波频率 (Hz)
            lowpass_freq: 低通滤波频率 (Hz)
            volume: 音量倍数
            progress_callback: 进度回调
        """
        self.reset()

        progress_adapter: Optional[ProgressCallback] = None
        try:
            video_path = Path(video_path)
            video_dir = video_path.parent
            video_name = video_path.stem

            if output_path is None:
                output_path = video_dir / f"{video_name}.wav"
            else:
                output_path = Path(output_path)

            # 创建进度适配器
            if progress_callback:
                progress_adapter = _SimpleProgressAdapter(
                    callback=progress_callback,
                    is_cancelled_func=lambda: self._cancelled,
                )
            else:
                from mediafactory.core.progress_protocol import NO_OP_PROGRESS

                progress_adapter = NO_OP_PROGRESS

            progress_adapter.update(0, f"Extracting audio from {video_name}...")

            loop = asyncio.get_event_loop()

            def extract():
                return self.engine.extract(
                    str(video_path),
                    progress=progress_adapter,
                    output_format=output_format,
                    sample_rate=sample_rate,
                    channels=channels,
                    filter_enabled=filter_enabled,
                    highpass_freq=highpass_freq,
                    lowpass_freq=lowpass_freq,
                    volume=volume,
                )

            audio_path = await loop.run_in_executor(None, extract)

            progress_adapter.update(100, f"Completed: {Path(audio_path).name}")

            return ProcessingResult(
                success=True,
                output_path=audio_path,
            )

        except Exception as e:
            log_error_with_context(
                "Audio extraction failed", e, {"video_path": str(video_path)}
            )
            return ProcessingResult(success=False, error=str(e))
        finally:
            pass  # 进度适配器无需清理


class TranscriptionService:
    """语音转录服务"""

    def __init__(self):
        self._engine: Optional[RecognitionEngine] = None
        self._cancelled: bool = False
        self._model_context: Optional[Any] = None
        self._whisper_model: Optional[Any] = None

    @property
    def engine(self) -> RecognitionEngine:
        if self._engine is None:
            self._engine = RecognitionEngine()
        return self._engine

    def cancel(self) -> None:
        self._cancelled = True

    def reset(self) -> None:
        self._cancelled = False

    def _ensure_model_loaded(self) -> Any:
        """确保模型已加载"""
        if self._whisper_model is None:
            from mediafactory.resource_manager import whisper_model
            from mediafactory.models.whisper_runtime import select_device
            from mediafactory.models.model_registry import WHISPER_MODEL_ID

            device = select_device()
            # 模型路径由 whisper_model 内部处理
            self._model_context = whisper_model(WHISPER_MODEL_ID, device)
            self._whisper_model = self._model_context.__enter__()
        return self._whisper_model

    def cleanup(self) -> None:
        """清理模型资源"""
        if self._model_context is not None:
            try:
                self._model_context.__exit__(None, None, None)
            except Exception:
                pass
            finally:
                self._model_context = None
                self._whisper_model = None

    async def transcribe(
        self,
        audio_path: str,
        page: ft.Page,
        language: str = "auto",
        output_path: Optional[str] = None,
        output_format_type: str = "srt",
        bilingual: bool = False,
        bilingual_layout: str = "translate_on_top",
        style_preset: str = "default",
        progress_callback: Optional[Callable[[ProcessingProgress], None]] = None,
    ) -> ProcessingResult:
        """转录音频

        Args:
            audio_path: 音频文件路径
            language: 源语言
            output_path: 输出路径（可选）
            output_format_type: 输出格式（srt, ass 或 txt）
            bilingual: 是否双语
            bilingual_layout: 双语布局
            style_preset: ASS样式预设
            progress_callback: 进度回调
        """
        self.reset()

        progress_adapter: Optional[ProgressCallback] = None
        try:
            audio_path_obj = Path(audio_path)
            audio_dir = audio_path_obj.parent
            audio_name = audio_path_obj.stem

            # 如果未指定输出路径，自动生成默认路径
            if output_path is None:
                if output_format_type == "txt":
                    file_extension = "txt"
                elif output_format_type == "ass":
                    file_extension = "ass"
                else:
                    file_extension = "srt"
                output_path = str(audio_dir / f"{audio_name}.{file_extension}")

            # 创建进度适配器
            if progress_callback:
                progress_adapter = _SimpleProgressAdapter(
                    callback=progress_callback,
                    is_cancelled_func=lambda: self._cancelled,
                )
            else:
                from mediafactory.core.progress_protocol import NO_OP_PROGRESS

                progress_adapter = NO_OP_PROGRESS

            progress_adapter.update(0, f"Loading model...")

            loop = asyncio.get_event_loop()

            # 在 executor 中加载模型和执行转录
            def transcribe_with_model():
                model = self._ensure_model_loaded()
                return self.engine.transcribe(
                    model=model,
                    audio_path=str(audio_path_obj),
                    src_lang=None if language == "auto" else language,
                    progress=progress_adapter,
                )

            progress_adapter.update(10, f"Transcribing {audio_name}...")
            result = await loop.run_in_executor(None, transcribe_with_model)

            # 从结果中提取 segments
            segments = result.get("segments", [])

            # 如果指定了输出路径，生成输出文件
            if output_path:
                if output_format_type == "txt":
                    srt_engine = SRTEngine()
                    srt_engine.generate_text_to_path(output_path, segments)
                elif output_format_type == "ass":
                    from mediafactory.engine.ass_engine import ASSEngine

                    ass_engine = ASSEngine()
                    ass_engine.generate_to_path(
                        output_path,
                        segments,
                        style_preset=style_preset,
                        bilingual=bilingual,
                        layout=bilingual_layout,
                    )
                else:  # srt
                    srt_engine = SRTEngine()
                    srt_engine.generate_to_path(
                        output_path,
                        segments,
                        bilingual=bilingual,
                        layout=bilingual_layout,
                    )

            progress_adapter.update(100, f"Completed: {len(segments)} segments")

            return ProcessingResult(
                success=True,
                output_path=output_path,
                metadata={"segments": segments, "segments_count": len(segments)},
            )

        except Exception as e:
            log_error_with_context(
                "Transcription failed", e, {"audio_path": str(audio_path)}
            )
            return ProcessingResult(success=False, error=str(e))
        finally:
            pass  # 进度适配器无需清理


class TranslationService:
    """翻译服务"""

    def __init__(self):
        self._engine: Optional[TranslationEngine] = None
        self._cancelled: bool = False
        self._use_llm: bool = False

    def _get_engine(self, use_llm: bool) -> TranslationEngine:
        """获取翻译引擎，根据 use_llm 参数决定使用哪种翻译方式"""
        # 如果引擎不存在或 use_llm 设置改变，重新创建引擎
        if self._engine is None or self._use_llm != use_llm:
            self._use_llm = use_llm
            self._engine = TranslationEngine(use_llm_backend=use_llm)
        return self._engine

    def cancel(self) -> None:
        self._cancelled = True

    def reset(self) -> None:
        self._cancelled = False

    async def translate(
        self,
        text: str,
        page: ft.Page,
        source_language: str = "auto",
        target_language: str = "zh",
        use_llm: bool = False,
        progress_callback: Optional[Callable[[ProcessingProgress], None]] = None,
    ) -> ProcessingResult:
        """翻译文本"""
        self.reset()

        try:
            # 创建进度适配器
            progress_adapter: ProgressCallback
            if progress_callback:
                progress_adapter = _SimpleProgressAdapter(
                    callback=progress_callback,
                    is_cancelled_func=lambda: self._cancelled,
                )
            else:
                from mediafactory.core.progress_protocol import NO_OP_PROGRESS

                progress_adapter = NO_OP_PROGRESS

            progress_adapter.update(0, "Translating...")

            loop = asyncio.get_event_loop()

            def translate():
                engine = self._get_engine(use_llm)
                # 将文本转换为 TranslationEngine 期望的格式
                result = {"segments": [{"text": text}]}
                translated_result = engine.translate(
                    result=result,
                    src_lang=source_language if source_language != "auto" else None,
                    tgt_lang=target_language,
                    progress=progress_adapter,
                )
                # 从翻译结果中提取翻译后的文本
                segments = translated_result.get("segments", [])
                return segments[0].get("text", "") if segments else ""

            translated = await loop.run_in_executor(None, translate)

            progress_adapter.update(100, "Translation completed")

            return ProcessingResult(success=True, metadata={"translated": translated})

        except Exception as e:
            log_error_with_context("Translation failed", e, {})
            return ProcessingResult(success=False, error=str(e))

    async def translate_srt(
        self,
        srt_path: str,
        page: ft.Page,
        target_lang: str = "zh",
        use_llm: bool = False,
        output_path: Optional[str] = None,
        progress_callback: Optional[Callable[[ProcessingProgress], None]] = None,
    ) -> ProcessingResult:
        """翻译 SRT 字幕文件（源语言自动检测）"""
        self.reset()

        progress_adapter: Optional[ProgressCallback] = None
        try:
            from mediafactory.engine.srt import SRTEngine

            srt_path_obj = Path(srt_path)
            srt_name = srt_path_obj.stem

            if output_path is None:
                output_path = srt_path_obj.parent / f"{srt_name}.{target_lang}.srt"
            else:
                output_path = Path(output_path)

            # 创建进度适配器
            if progress_callback:
                progress_adapter = _SimpleProgressAdapter(
                    callback=progress_callback,
                    is_cancelled_func=lambda: self._cancelled,
                )
            else:
                from mediafactory.core.progress_protocol import NO_OP_PROGRESS

                progress_adapter = NO_OP_PROGRESS

            # 里程碑进度：开始解析
            progress_adapter.update(5, f"Parsing {srt_name}...")

            loop = asyncio.get_event_loop()

            # 用于在翻译期间模拟平滑进度的标志和进度值
            translation_running = True
            current_progress = 5.0

            def smooth_progress_task():
                """在后台线程中模拟平滑进度增长"""
                import time

                nonlocal current_progress
                # 进度增长配置
                stages_config = [
                    (5, 15, 0.5, f"Parsing {srt_name}..."),
                    (15, 25, 0.3, "Detecting source language..."),
                    (25, 85, 0.1, "Translating subtitles..."),  # 翻译阶段较长
                    (85, 90, 0.2, "Preparing output..."),
                ]
                stage_idx = 0

                while translation_running and stage_idx < len(stages_config):
                    start, end, speed, msg = stages_config[stage_idx]
                    if current_progress < start:
                        current_progress = start

                    while translation_running and current_progress < end:
                        time.sleep(0.5)
                        if not translation_running:
                            break
                        current_progress = min(current_progress + speed, end)
                        try:
                            progress_adapter.update(current_progress, msg)
                        except Exception:
                            pass

                    stage_idx += 1

                # 保持在90%直到完成
                while translation_running and current_progress < 90:
                    time.sleep(0.5)
                    if not translation_running:
                        break
                    current_progress = min(current_progress + 0.3, 90)
                    try:
                        progress_adapter.update(current_progress, "Finalizing...")
                    except Exception:
                        pass

            # 启动平滑进度任务
            smooth_progress_future = loop.run_in_executor(None, smooth_progress_task)

            try:

                def translate():
                    # 使用 SRTEngine 解析 SRT 文件
                    srt_engine = SRTEngine()
                    segments = srt_engine.parse(str(srt_path_obj))

                    # 检测双语字幕，不支持翻译
                    if srt_engine.detect_bilingual(segments):
                        raise ValueError(
                            "Bilingual subtitles detected. Translation of bilingual subtitles is not currently supported.\n\n"
                            "Please use a single-language subtitle file for translation."
                        )

                    if not segments:
                        return []

                    # 构建翻译引擎期望的格式
                    result = {"segments": segments}

                    # 获取翻译引擎并翻译（源语言自动检测，传入 None）
                    engine = self._get_engine(use_llm)
                    translated_result = engine.translate(
                        result=result,
                        src_lang=None,  # 自动检测源语言
                        tgt_lang=target_lang,
                        progress=progress_adapter,
                    )

                    return translated_result.get("segments", [])

                translated_segments = await loop.run_in_executor(None, translate)

                # 里程碑进度：翻译完成，开始写入文件
                progress_adapter.update(90, "Writing output file...")

                # 写入输出文件
                def write_file():
                    srt_engine = SRTEngine()
                    srt_engine.generate_to_path(str(output_path), translated_segments)

                await loop.run_in_executor(None, write_file)

            finally:
                # 翻译完成，停止平滑进度
                translation_running = False
                try:
                    await asyncio.wait_for(smooth_progress_future, timeout=2.0)
                except asyncio.TimeoutError:
                    pass

            # 里程碑进度：完成
            progress_adapter.update(100, f"Completed: {output_path.name}")

            return ProcessingResult(
                success=True,
                output_path=str(output_path),
            )

        except Exception as e:
            log_error_with_context(
                "SRT translation failed", e, {"srt_path": str(srt_path)}
            )
            return ProcessingResult(success=False, error=str(e))
        finally:
            pass  # 进度适配器无需清理

    def cleanup(self) -> None:
        """清理服务持有的所有资源

        实现 ResourceCleanupProtocol 接口。
        在应用退出或服务不再使用时调用。
        """
        import gc

        from mediafactory.logging import log_debug, log_info

        log_info("[TranslationService] Starting cleanup...")

        # 清理翻译引擎
        if self._engine is not None:
            if hasattr(self._engine, "cleanup"):
                log_debug("[TranslationService] Cleaning up translation engine")
                self._engine.cleanup()
            self._engine = None

        gc.collect()
        log_info("[TranslationService] Cleanup completed")


class VideoEnhancementService:
    """视频增强服务"""

    def __init__(self):
        self._engine = None
        self._cancelled: bool = False

    @property
    def engine(self):
        """获取视频增强引擎（懒加载）"""
        if self._engine is None:
            from mediafactory.engine.video_enhancement import VideoEnhancementEngine

            self._engine = VideoEnhancementEngine()
        return self._engine

    def cancel(self) -> None:
        """取消处理"""
        self._cancelled = True

    def reset(self) -> None:
        """重置状态"""
        self._cancelled = False

    def _is_cancelled(self) -> bool:
        """检查是否已取消"""
        return self._cancelled

    async def enhance_video(
        self,
        video_path: str,
        page: ft.Page,
        output_path: Optional[str] = None,
        scale: int = 4,
        model_type: str = "general",
        denoise: bool = False,
        denoise_strength: float = 1.0,
        temporal: bool = False,
        temporal_strength: float = 0.5,
        progress_callback: Optional[Callable[[ProcessingProgress], None]] = None,
    ) -> ProcessingResult:
        """
        增强视频

        Args:
            video_path: 输入视频路径
            output_path: 输出视频路径（可选）
            scale: 放大倍数 (2/4)
            model_type: 模型类型 (general/anime)
            denoise: 是否启用去噪
            denoise_strength: 去噪强度 (0.0-1.0)
            temporal: 是否启用时序平滑
            temporal_strength: 时序平滑强度 (0.0-1.0)
            progress_callback: 进度回调

        Returns:
            ProcessingResult: 处理结果
        """
        self.reset()

        progress_adapter: Optional[ProgressCallback] = None
        try:
            from mediafactory.engine.video_enhancement import (
                VideoEnhancementEngine,
                EnhancementConfig,
            )

            # 创建进度适配器
            if progress_callback:
                progress_adapter = _SimpleProgressAdapter(
                    callback=progress_callback,
                    is_cancelled_func=self._is_cancelled,
                )
            else:
                from mediafactory.core.progress_protocol import NO_OP_PROGRESS

                progress_adapter = NO_OP_PROGRESS

            # 创建配置
            config = EnhancementConfig(
                scale=scale,
                model_type=model_type,
                denoise=denoise,
                denoise_strength=denoise_strength,
                temporal=temporal,
                temporal_strength=temporal_strength,
            )

            # 创建引擎
            engine = VideoEnhancementEngine(config)

            # 里程碑进度：开始
            progress_adapter.update(0, "Starting video enhancement...")

            loop = asyncio.get_event_loop()

            # 在线程池中执行增强
            def enhance():
                return engine.enhance(
                    video_path=video_path,
                    output_path=output_path,
                    progress=progress_adapter,
                )

            output = await loop.run_in_executor(None, enhance)

            # 里程碑进度：完成
            progress_adapter.update(100, "Video enhancement completed!")

            return ProcessingResult(
                success=True,
                output_path=output,
                metadata={
                    "scale": scale,
                    "model_type": model_type,
                    "denoise": denoise,
                    "temporal": temporal,
                },
            )

        except Exception as e:
            log_error_with_context(
                "Video enhancement failed", e, {"video_path": str(video_path)}
            )
            return ProcessingResult(success=False, error=str(e))
        finally:
            pass  # 进度适配器无需清理


# 服务单例
_subtitle_service: Optional[SubtitleService] = None
_audio_service: Optional[AudioService] = None
_transcription_service: Optional[TranscriptionService] = None
_translation_service: Optional[TranslationService] = None
_video_enhancement_service: Optional[VideoEnhancementService] = None


def get_subtitle_service() -> SubtitleService:
    """获取字幕服务单例"""
    global _subtitle_service
    if _subtitle_service is None:
        _subtitle_service = SubtitleService()
    return _subtitle_service


def get_audio_service() -> AudioService:
    """获取音频服务单例"""
    global _audio_service
    if _audio_service is None:
        _audio_service = AudioService()
    return _audio_service


def get_transcription_service() -> TranscriptionService:
    """获取转录服务单例"""
    global _transcription_service
    if _transcription_service is None:
        _transcription_service = TranscriptionService()
    return _transcription_service


def get_translation_service() -> TranslationService:
    """获取翻译服务单例"""
    global _translation_service
    if _translation_service is None:
        _translation_service = TranslationService()
    return _translation_service


def get_video_enhancement_service() -> VideoEnhancementService:
    """获取视频增强服务单例"""
    global _video_enhancement_service
    if _video_enhancement_service is None:
        _video_enhancement_service = VideoEnhancementService()
    return _video_enhancement_service


class ModelStatusService:
    """模型状态服务"""

    def __init__(self):
        self.config = get_config()

    def get_whisper_status(self):
        """获取 Whisper 模型状态（固定为 Large V3）"""
        from mediafactory.gui.flet.state import ModelStatus
        from mediafactory.models.model_registry import WHISPER_MODEL_ID

        # 使用文件系统检查模型是否真正可用，与 Settings 页签保持一致
        try:
            from mediafactory.models.local_models import local_model_manager

            downloaded = local_model_manager.is_model_available_locally(
                WHISPER_MODEL_ID
            )
        except Exception:
            downloaded = False

        return ModelStatus(
            model_type="whisper",
            name="Faster Whisper Large V3",
            loaded=downloaded,
            available=downloaded,
            enabled=True,
        )

    def refresh_model_status(self) -> None:
        """刷新模型状态（重新扫描本地模型）"""
        from mediafactory.config import get_config_manager

        # 触发配置管理器重新扫描模型
        config_manager = get_config_manager()
        config_manager.sync_models()

    def get_translation_model_statuses(self) -> List[Dict[str, Any]]:
        """获取三个档位的本地翻译模型状态"""
        from mediafactory.models.local_models import local_model_manager

        # 使用 huggingface_id
        models = [
            {
                "id": "google/madlad400-3b-mt",
                "name": "MADLAD400-3B Q4K",
                "tier": "Small",
                "memory": "3-4 GB",
            },
            {
                "id": "google/madlad400-7b-mt-bt",
                "name": "MADLAD400-7B Q4K",
                "tier": "Medium",
                "memory": "6-7 GB",
            },
            {
                "id": "google/madlad400-3b-mt-fp16",
                "name": "MADLAD400-3B FP16",
                "tier": "Large",
                "memory": "9-10 GB",
            },
        ]

        result = []
        for model in models:
            # 使用文件系统检查模型是否真正可用，与 Settings 页签保持一致
            try:
                downloaded = local_model_manager.is_model_available_locally(model["id"])
            except Exception:
                downloaded = False
            result.append(
                {
                    "id": model["id"],
                    "name": model["name"],
                    "tier": model["tier"],
                    "memory": model["memory"],
                    "downloaded": downloaded,
                }
            )

        return result

    def get_translation_status(self):
        """获取翻译模型状态（兼容旧接口）"""
        from mediafactory.gui.flet.state import ModelStatus
        from mediafactory.models.local_models import local_model_manager
        from mediafactory.models.model_registry import get_translation_model_info

        # 预定义的翻译模型列表
        translation_model_ids = [
            "google/madlad400-3b-mt",
            "google/madlad400-7b-mt-bt",
            "google/madlad400-3b-mt-fp16",
        ]

        try:
            # 使用文件系统检查获取真正可用的模型
            available_models = [
                model_id
                for model_id in translation_model_ids
                if local_model_manager.is_model_available_locally(model_id)
            ]

            if available_models:
                # 使用第一个已下载的模型
                translation_model = available_models[0]
                model_info = get_translation_model_info(translation_model)
                display_name = (
                    model_info.display_name if model_info else translation_model
                )
                loaded = True
                available = True
            else:
                display_name = "No model"
                loaded = False
                available = False
        except Exception:
            display_name = "No model"
            loaded = False
            available = False

        return ModelStatus(
            model_type="translation",
            name=f"Translation ({display_name})",
            loaded=loaded,
            available=available,
            enabled=True,
        )

    def get_llm_status(self):
        """获取 LLM 状态"""
        from mediafactory.gui.flet.state import ModelStatus

        llm_enabled = False
        llm_backend = "openai"
        llm_model = ""
        llm_available = False

        try:
            if hasattr(self.config, "llm"):
                llm_enabled = getattr(self.config.llm, "enabled", False)
                llm_backend = getattr(self.config.llm, "backend", "openai")

            # 获取当前配置的模型名称
            if hasattr(self.config, "openai_compatible"):
                preset = self.config.openai_compatible.current_preset
                preset_config = self.config.openai_compatible.get_preset_config(preset)
                llm_model = preset_config.model
                llm_backend = preset

            if llm_enabled:
                api_key = ""
                if hasattr(self.config, "openai_compatible"):
                    preset = self.config.openai_compatible.current_preset
                    preset_config = self.config.openai_compatible.get_preset_config(
                        preset
                    )
                    api_key = preset_config.api_key
                llm_available = bool(api_key)
        except Exception:
            llm_available = False

        return ModelStatus(
            model_type="llm",
            name=f"{llm_backend.title()}" + (f" ({llm_model})" if llm_model else ""),
            loaded=llm_available,
            available=llm_available,
            enabled=llm_enabled,
        )

    def get_llm_config(self) -> Dict[str, Any]:
        """获取 LLM 配置详情"""
        result = {
            "enabled": False,
            "preset": "openai",
            "base_url": "",
            "api_key": "",
            "model": "",
        }

        try:
            if hasattr(self.config, "llm"):
                result["enabled"] = getattr(self.config.llm, "enabled", False)

            if hasattr(self.config, "openai_compatible"):
                preset = self.config.openai_compatible.current_preset
                preset_config = self.config.openai_compatible.get_preset_config(preset)
                result["preset"] = preset
                result["base_url"] = preset_config.base_url
                result["api_key"] = preset_config.api_key
                result["model"] = preset_config.model
        except Exception:
            pass

        return result

    def test_llm_connection(self) -> Dict[str, Any]:
        """测试 LLM 连通性（同步方法）"""
        from mediafactory.llm import initialize_llm_backend

        llm_config = self.get_llm_config()

        if not llm_config["base_url"] or not llm_config["api_key"]:
            return {
                "success": False,
                "error": "API not configured",
                "message": "Please configure API Key",
            }

        try:
            backend = initialize_llm_backend(self.config, skip_availability_check=True)

            if backend is None:
                return {
                    "success": False,
                    "error": "Backend creation failed",
                    "message": "Failed to create LLM backend",
                }

            # 使用 test_connection() 方法（同步）
            return backend.test_connection()

        except Exception as ex:
            log_error(f"LLM connection test failed: {ex}")
            return {
                "success": False,
                "error": str(ex),
                "message": f"Connection failed: {str(ex)[:50]}",
            }

    def set_llm_enabled(self, enabled: bool) -> None:
        """设置 LLM 启用状态"""
        try:
            from mediafactory.config import update_config

            update_config(llm__enabled=enabled)
            log_info(f"LLM enabled: {enabled}")
        except Exception as e:
            log_error_with_context("Failed to set LLM enabled", e, {})

    def test_all_llm_connections(self) -> Dict[str, Dict[str, Any]]:
        """测试所有 LLM 预设的连通性（同步方法）"""
        from mediafactory.constants import BackendConfigMapping
        from mediafactory.llm import initialize_llm_backend

        results = {}

        for preset_id, preset_info in BackendConfigMapping.BASE_URL_PRESETS.items():
            if preset_id == "custom":
                continue

            # 获取该预设的配置
            preset_config = self.config.openai_compatible.get_preset_config(preset_id)

            if not preset_config.api_key:
                results[preset_id] = {
                    "success": False,
                    "message": "Not configured",
                }
                continue

            # 测试连通性
            try:
                backend = initialize_llm_backend(
                    self.config, preset=preset_id, skip_availability_check=True
                )

                if backend is None:
                    results[preset_id] = {
                        "success": False,
                        "message": "Failed to create backend",
                    }
                    continue

                # 使用 test_connection() 方法（同步）
                result = backend.test_connection()
                results[preset_id] = result

            except Exception as ex:
                log_error(f"LLM connection test failed for {preset_id}: {ex}")
                results[preset_id] = {
                    "success": False,
                    "message": f"Connection failed: {str(ex)[:50]}",
                }

        return results


# 模型状态服务单例
_model_status_service: Optional[ModelStatusService] = None


def get_model_status_service() -> ModelStatusService:
    """获取模型状态服务单例"""
    global _model_status_service
    if _model_status_service is None:
        _model_status_service = ModelStatusService()
    return _model_status_service
