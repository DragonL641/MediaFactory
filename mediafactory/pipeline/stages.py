"""处理阶段实现模块"""

import os
from .stage import SkipableStage
from .context import ProcessingContext
from ..utils.resources import get_language_name
from ..logging import log_step, log_info, log_warning, log_success
from ..exceptions import ProcessingError
from ..core.exception_wrapper import convert_exception
from ..i18n import t


class AudioExtractionStage(SkipableStage):
    """音频提取阶段"""

    name = "audio_extraction"

    def __init__(self, audio_engine):
        self.audio_engine = audio_engine

    def should_execute(self, ctx: ProcessingContext) -> bool:
        """音频文件已存在则跳过"""
        if ctx.audio_path and os.path.exists(ctx.audio_path):
            self._log(f"Audio already exists: {ctx.audio_path}", "info")
            return False
        return True

    def execute(self, ctx: ProcessingContext) -> ProcessingContext:
        """提取音频"""
        progress = self._begin(ctx, "Audio Extraction")
        progress.update(0.0, t("progress.audioExtractionStart"))

        # 从 ctx.config 读取额外参数（兼容 Pipeline 和直接调用）
        config = ctx.config or {}
        kwargs = {
            "progress": progress,
            "output_path": config.get("output_path"),
            "filter_enabled": config.get("filter_enabled", True),
            "volume": config.get("volume", 1.0),
            "output_format": config.get("output_format", "wav"),
        }
        # 仅在 config 中有值时传递，避免 None 覆盖 AudioEngine 默认值
        for key in ("sample_rate", "channels", "highpass_freq", "lowpass_freq"):
            if config.get(key) is not None:
                kwargs[key] = config[key]
        ctx.audio_path = self.audio_engine.extract(ctx.video_path, **kwargs)
        ctx.output_path = ctx.audio_path

        log_success("Audio extraction completed")
        return ctx

    def validate(self, ctx: ProcessingContext) -> bool:
        """验证音频文件"""
        if not ctx.audio_path:
            self._log(t("error.audioPathNotSet"), "error")
            return False
        if not os.path.exists(ctx.audio_path):
            self._log(f"Audio file does not exist: {ctx.audio_path}", "error")
            return False
        return True


class TranscriptionStage(SkipableStage):
    """语音转录阶段"""

    name = "transcription"

    def __init__(self, recognition_engine):
        self.recognition_engine = recognition_engine

    def should_execute(self, ctx: ProcessingContext) -> bool:
        """转录结果已存在则跳过"""
        return ctx.transcription_result is None

    def execute(self, ctx: ProcessingContext) -> ProcessingContext:
        """执行语音转录"""
        progress = self._begin(ctx, "Speech Recognition")
        progress.update(0.0, t("progress.transcriptionPrepare"))

        result = self.recognition_engine.transcribe(
            ctx.whisper_model_instance, ctx.audio_path, ctx.src_lang, progress
        )

        detected_lang = result.get("language", ctx.src_lang)
        ctx.detected_lang = detected_lang
        ctx.transcription_result = result

        log_info(f"Detected/selected language: {get_language_name(detected_lang)}")
        progress.update(100.0, t("progress.transcriptionCompleted"))
        return ctx

    def validate(self, ctx: ProcessingContext) -> bool:
        """验证转录结果"""
        if not ctx.transcription_result:
            self._log("Transcription result not set", "error")
            return False
        if "segments" not in ctx.transcription_result:
            self._log("Transcription result missing segments", "error")
            return False
        return True


class PostProcessStage(SkipableStage):
    """转录后处理阶段（智能断句）"""

    name = "postprocess"

    def __init__(self):
        pass

    def should_execute(self, ctx: ProcessingContext) -> bool:
        """有转录结果才执行"""
        return ctx.transcription_result is not None

    def execute(self, ctx: ProcessingContext) -> ProcessingContext:
        """执行后处理"""
        progress = self._begin(ctx, "Post-Processing")
        progress.update(0.0, "Post-processing...")

        # 延迟导入：避免启动时加载 ML 依赖（stable-ts、torch 等）
        from ..engine.postprocess import PostProcessEngine
        from ..config import get_config_manager

        engine = PostProcessEngine()

        # 从配置管理器读取 postprocess 配置
        config_manager = get_config_manager()
        pp_config = config_manager.config.postprocess

        # 从 ctx.config 读取运行时覆盖（任务级别配置）
        runtime_config = ctx.config or {}
        pp_runtime = runtime_config.get("postprocess", {})

        resegment_enabled = pp_runtime.get(
            "resegment_enabled", pp_config.resegment_enabled
        )

        segments = ctx.transcription_result.get("segments", [])
        original_count = len(segments)

        # 智能断句
        if resegment_enabled:
            progress.update(20.0, "Resegmenting...")
            segments = engine.resegment(
                segments,
                max_chars_cjk=pp_runtime.get("max_chars_cjk", pp_config.max_chars_cjk),
                max_chars_latin=pp_runtime.get(
                    "max_chars_latin", pp_config.max_chars_latin
                ),
                min_duration=pp_runtime.get("min_duration", pp_config.min_duration),
                max_duration=pp_runtime.get("max_duration", pp_config.max_duration),
                merge_gap_threshold=pp_runtime.get(
                    "merge_gap_threshold", pp_config.merge_gap_threshold
                ),
                language=ctx.detected_lang,
            )

        # 更新转录结果中的 segments
        ctx.transcription_result["segments"] = segments

        # 重新生成完整文本
        ctx.transcription_result["text"] = " ".join(
            seg.get("text", "").strip() for seg in segments
        )

        log_success(
            f"Post-processing complete: {original_count} -> {len(segments)} segments"
        )
        progress.update(100.0, "Post-processing completed")
        return ctx

    def validate(self, ctx: ProcessingContext) -> bool:
        """验证后处理结果"""
        if not ctx.transcription_result:
            self._log("Transcription result not set after post-processing", "error")
            return False
        return True


class TranslationStage(SkipableStage):
    """翻译阶段"""

    name = "translation"

    def __init__(self, translation_engine):
        self.translation_engine = translation_engine

    def should_execute(self, ctx: ProcessingContext) -> bool:
        """判断是否需要翻译"""
        if not ctx.transcription_result:
            return False
        if ctx.translation_result:
            self._log("Translation already exists", "info")
            return False
        if ctx.detected_lang == ctx.tgt_lang:
            if ctx.bilingual:
                raise ProcessingError(
                    message=f"双语字幕需要源语言和目标语言不同，"
                    f"但检测到的语言和目标语言都是 {ctx.tgt_lang}",
                    context={
                        "detected_lang": ctx.detected_lang,
                        "tgt_lang": ctx.tgt_lang,
                        "bilingual": True,
                    },
                )
            self._log(
                f"Source and target languages are the same ({ctx.detected_lang}), skipping translation",
                "info",
            )
            ctx.translation_result = ctx.transcription_result
            return False
        return True

    def execute(self, ctx: ProcessingContext) -> ProcessingContext:
        """执行翻译"""
        progress = self._begin(ctx, "Translation")
        progress.update(0.0, t("progress.translationPrepare"))

        src_lang = ctx.detected_lang or ctx.src_lang
        log_info(
            f"[TranslationStage] Source language: {src_lang}, Target language: {ctx.tgt_lang}"
        )

        # 检查本地模型是否可用
        if not ctx.use_local_models_only:
            from ..models.local_models import local_model_manager

            log_info(
                "[TranslationStage] Checking available local translation models..."
            )
            downloaded_models = local_model_manager.get_downloaded_translation_models()
            log_info(
                f"[TranslationStage] Found {len(downloaded_models)} downloaded models: {downloaded_models}"
            )

            # 如果用户指定了特定模型，检查是否可用
            if ctx.translation_model:
                if not local_model_manager.is_model_available_locally(
                    ctx.translation_model
                ):
                    log_warning(
                        f"Translation model ({ctx.translation_model}) not found locally."
                    )
                    if downloaded_models:
                        log_info(f"Available models: {', '.join(downloaded_models)}")
                    else:
                        log_info(
                            "Please run: python scripts/utils/download_model.py facebook/m2m100_1.2B"
                        )
            elif not downloaded_models:
                log_warning(
                    f"No translation models found for "
                    f"{get_language_name(src_lang)} -> {get_language_name(ctx.tgt_lang)}."
                )
                log_info(
                    "Please run: python scripts/utils/download_model.py facebook/m2m100_1.2B"
                )

        # 里程碑进度：开始语言检测
        progress.update(10, t("progress.detectingSourceLanguage"))

        result = self.translation_engine.translate(
            ctx.transcription_result,
            src_lang,
            ctx.tgt_lang,
            progress,
            detection_context="Pipeline Translation",
        )

        ctx.translation_result = result
        log_success("Translation completed")
        progress.update(100.0, t("progress.translationCompleted"))
        return ctx

    def validate(self, ctx: ProcessingContext) -> bool:
        """验证翻译结果"""
        if not ctx.translation_result:
            self._log("Translation result not set", "error")
            return False
        return True

    def on_error(self, ctx: ProcessingContext, error: Exception) -> Exception:
        """翻译失败时终止流水线"""
        from ..logging import log_error_with_context

        log_error_with_context(
            "Translation failed, terminating pipeline",
            error,
            context={
                "src_lang": getattr(ctx, "src_lang", "unknown"),
                "tgt_lang": getattr(ctx, "tgt_lang", "unknown"),
                "translation_mode": getattr(ctx, "translation_mode", "unknown"),
            },
        )
        return error


class SRTGenerationStage(SkipableStage):
    """字幕生成阶段（支持SRT/ASS/TXT格式）"""

    name = "srt_generation"

    # 格式到扩展名的映射
    _FORMAT_EXT = {"srt": ".srt", "ass": ".ass", "vtt": ".vtt", "txt": ".txt"}

    def __init__(self, srt_engine, ass_engine=None):
        self.srt_engine = srt_engine
        self.ass_engine = ass_engine

    def should_execute(self, ctx: ProcessingContext) -> bool:
        """没有翻译或转录结果则跳过"""
        if not ctx.translation_result and not ctx.transcription_result:
            self._log("No transcription or translation result available", "error")
            return False
        return True

    def execute(self, ctx: ProcessingContext) -> ProcessingContext:
        """生成字幕文件"""
        progress = self._begin(ctx, "Final Stage")
        progress.update(0.0, t("progress.subtitleGenerationPrepare"))

        # 优先使用翻译结果
        result = ctx.translation_result or ctx.transcription_result

        # 确定输出语言
        if ctx.translation_result:
            output_lang = ctx.tgt_lang
        else:
            output_lang = ctx.detected_lang or ctx.src_lang or ctx.tgt_lang

        # 获取输出格式配置
        output_format = "srt"
        if ctx.config:
            output_format = ctx.config.get("output_format_type", "srt")

        # 确定输出路径和文件扩展名
        if ctx.config and "output_path" in ctx.config:
            output_path = ctx.config["output_path"]
            # 如果配置了输出路径但格式是ASS，需要修改扩展名
            ext = self._FORMAT_EXT.get(output_format, ".srt")
            if not output_path.endswith(ext):
                output_path = os.path.splitext(output_path)[0] + ext
        else:
            video_dir = ctx.get_video_dir()
            video_name = ctx.get_video_name()
            ext = self._FORMAT_EXT.get(output_format, ".srt")
            output_filename = f"{video_name}_{output_lang}{ext}"
            output_path = os.path.join(video_dir, output_filename)

        segments = result.get("segments", [])

        # 里程碑进度：开始生成文件
        progress.update(
            30, t("progress.generatingSubtitleFile", format=output_format.upper())
        )

        # 根据格式生成输出
        if output_format == "txt":
            self.srt_engine.generate_text_to_path(output_path, segments)
        elif output_format == "ass":
            # 使用ASSEngine生成ASS格式字幕
            if self.ass_engine is None:
                from ..engine.ass_engine import ASSEngine

                self.ass_engine = ASSEngine()
            self.ass_engine.generate_to_path(
                output_path,
                segments,
                style_preset=ctx.style_preset,
                bilingual=ctx.bilingual,
                layout=ctx.bilingual_layout,
            )
        else:  # srt
            self.srt_engine.generate_to_path(
                output_path,
                segments,
                bilingual=ctx.bilingual,
                layout=ctx.bilingual_layout,
            )

        ctx.output_path = output_path

        # 翻译场景：额外生成源语言字幕文件
        has_translation = (
            ctx.translation_result is not None
            and ctx.transcription_result is not None
            and ctx.detected_lang
            and ctx.detected_lang != ctx.tgt_lang
        )
        if has_translation:
            src_lang = ctx.detected_lang
            source_segments = ctx.transcription_result.get("segments", [])
            if source_segments:
                video_dir = ctx.get_video_dir()
                video_name = ctx.get_video_name()
                source_filename = f"{video_name}_{src_lang}{ext}"
                source_path = os.path.join(video_dir, source_filename)

                if output_format == "txt":
                    self.srt_engine.generate_text_to_path(source_path, source_segments)
                elif output_format == "ass":
                    if self.ass_engine is None:
                        from ..engine.ass_engine import ASSEngine
                        self.ass_engine = ASSEngine()
                    self.ass_engine.generate_to_path(source_path, source_segments)
                else:
                    self.srt_engine.generate_to_path(source_path, source_segments)

                ctx.source_subtitle_path = source_path
                log_success(f"Source subtitle generated: {source_path}")

        # 里程碑进度：文件写入完成
        progress.update(80, t("progress.finalizing"))

        log_success(f"Subtitle generated: {output_path}")
        progress.update(100.0, t("progress.subtitleGenerationCompleted"))
        return ctx

    def validate(self, ctx: ProcessingContext) -> bool:
        """验证输出文件"""
        if not ctx.output_path:
            self._log("Output path not set", "error")
            return False
        if not os.path.exists(ctx.output_path):
            self._log(f"Output file does not exist: {ctx.output_path}", "error")
            return False
        if os.path.getsize(ctx.output_path) == 0:
            self._log(f"Output file is empty: {ctx.output_path}", "error")
            return False
        return True


class ModelLoadingStage(SkipableStage):
    """模型加载阶段"""

    name = "model_loading"

    def __init__(self):
        pass

    def should_execute(self, ctx: ProcessingContext) -> bool:
        """模型已加载则跳过"""
        return ctx.whisper_model_instance is None

    def execute(self, ctx: ProcessingContext) -> ProcessingContext:
        """加载 Whisper 模型"""
        progress = self._begin(ctx, "Initialization")

        from ..models.whisper_runtime import select_device
        from ..models.model_registry import WHISPER_MODEL_ID

        try:
            # 固定使用 Large V3 模型
            ctx.whisper_model = WHISPER_MODEL_ID

            # 自动选择最佳设备（除非已明确指定非 "auto"）
            if ctx.whisper_device == "auto":
                ctx.whisper_device = select_device()

            log_step(f"Whisper model: {ctx.whisper_model}")
            log_step(f"Device: {ctx.whisper_device}")
            progress.update(0.0, t("progress.loadingModel", model=ctx.whisper_model))

            from ..resource_manager import whisper_model

            # 里程碑进度：开始加载
            progress.update(20, t("progress.initializingModel"))

            # 加载模型（模型路径由 whisper_model 内部处理）
            model_instance = whisper_model(ctx.whisper_model, ctx.whisper_device)
            ctx._model_context = model_instance
            ctx.whisper_model_instance = model_instance.__enter__()

            # 里程碑进度：模型加载中
            progress.update(60, t("progress.loadingModelWeights"))

            log_success(f"Faster Whisper model {ctx.whisper_model} loaded successfully")
            progress.update(100.0, t("progress.modelLoaded", model=ctx.whisper_model))
            return ctx

        except Exception as e:
            if hasattr(ctx, "_model_context") and ctx._model_context is not None:
                try:
                    ctx._model_context.__exit__(None, None, None)
                except Exception:
                    pass
                finally:
                    ctx._model_context = None
                    ctx.whisper_model_instance = None
            raise

    def validate(self, ctx: ProcessingContext) -> bool:
        """验证模型加载"""
        return ctx.whisper_model_instance is not None


class ModelCleanupStage(SkipableStage):
    """模型清理阶段"""

    name = "model_cleanup"

    def __init__(self):
        pass

    def should_execute(self, ctx: ProcessingContext) -> bool:
        """有模型上下文则执行清理"""
        return hasattr(ctx, "_model_context") and ctx._model_context is not None

    def execute(self, ctx: ProcessingContext) -> ProcessingContext:
        """清理模型资源"""
        if hasattr(ctx, "_model_context") and ctx._model_context:
            try:
                ctx._model_context.__exit__(None, None, None)
            except Exception as e:
                self._log(f"Error during model cleanup: {e}", "warning")
                wrapped = convert_exception(
                    e, context={"stage": self.name, "operation": "model_cleanup"}
                )
                self._log(f"Cleanup error type: {type(wrapped).__name__}", "debug")
            finally:
                ctx._model_context = None
        return ctx


class VideoEnhancementStage(SkipableStage):
    """视频增强阶段（超分辨率、降噪、时序平滑）"""

    name = "video_enhancement"

    def execute(self, ctx: ProcessingContext) -> ProcessingContext:
        """执行视频增强"""
        progress = self._begin(ctx, "Video Enhancement")
        progress.update(0.0, t("progress.videoEnhancementStart"))

        # 延迟导入以避免启动时加载 ML 依赖
        from ..engine.video_enhancement import VideoEnhancementEngine, EnhancementConfig

        config = ctx.config or {}
        enhancement_config = EnhancementConfig(
            scale=config.get("scale", 2),
            model_type=config.get("model_type", "general"),
            denoise=config.get("denoise", False),
            temporal=config.get("temporal", False),
        )

        engine = VideoEnhancementEngine(enhancement_config)
        output_path = config.get("output_path") or ctx.output_path
        result = engine.enhance(ctx.video_path, output_path, progress=progress)

        ctx.output_path = result

        log_success(f"Video enhanced: {ctx.output_path}")
        progress.update(100.0, t("progress.videoEnhancementCompleted"))
        return ctx

    def validate(self, ctx: ProcessingContext) -> bool:
        """验证输出文件"""
        import os

        if not ctx.output_path:
            self._log("Output path not set", "error")
            return False
        if not os.path.exists(ctx.output_path):
            self._log(f"Output file does not exist: {ctx.output_path}", "error")
            return False
        return True
