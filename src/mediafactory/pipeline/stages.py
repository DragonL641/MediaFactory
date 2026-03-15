"""处理阶段实现模块"""

import os
from .stage import SkipableStage
from .context import ProcessingContext
from ..core.progress_protocol import NO_OP_PROGRESS
from ..utils.resources import get_language_name
from ..logging import log_step, log_info, log_warning, log_success, log_debug
from ..exceptions import ProcessingError
from ..core.exception_wrapper import convert_exception


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
        log_step("Audio Extraction")
        ctx.set_stage("audio_extraction")
        progress = ctx.progress_callback or NO_OP_PROGRESS
        progress.update(0.0, "Starting audio extraction...")

        ctx.audio_path = self.audio_engine.extract(ctx.video_path, progress=progress)

        log_success("Audio extraction completed")
        return ctx

    def validate(self, ctx: ProcessingContext) -> bool:
        """验证音频文件"""
        if not ctx.audio_path:
            self._log("Audio path not set", "error")
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
        log_step("Speech Recognition")
        ctx.set_stage("transcription")
        progress = ctx.progress_callback or NO_OP_PROGRESS
        progress.update(0.0, "Preparing transcription...")

        result = self.recognition_engine.transcribe(
            ctx.whisper_model_instance, ctx.audio_path, ctx.src_lang, progress
        )

        detected_lang = result.get("language", ctx.src_lang)
        ctx.detected_lang = detected_lang
        ctx.transcription_result = result

        log_info(f"Detected/selected language: {get_language_name(detected_lang)}")
        progress.update(100.0, "Audio transcription completed")
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
            self._log(
                f"Source and target languages are the same ({ctx.detected_lang}), skipping translation",
                "info",
            )
            ctx.translation_result = ctx.transcription_result
            return False
        return True

    def execute(self, ctx: ProcessingContext) -> ProcessingContext:
        """执行翻译"""
        log_step("Translation")
        ctx.set_stage("translation")
        progress = ctx.progress_callback or NO_OP_PROGRESS
        log_debug(f"[TranslationStage] progress_callback: {ctx.progress_callback is not None}, type: {type(progress).__name__}")
        progress.update(0.0, "Preparing translation...")

        src_lang = ctx.detected_lang or ctx.src_lang
        log_info(f"[TranslationStage] Source language: {src_lang}, Target language: {ctx.tgt_lang}")

        # 检查本地模型是否可用
        if not ctx.use_local_models_only:
            from ..models.local_models import local_model_manager

            log_info("[TranslationStage] Checking available local translation models...")
            downloaded_models = local_model_manager.get_downloaded_translation_models()
            log_info(f"[TranslationStage] Found {len(downloaded_models)} downloaded models: {downloaded_models}")

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
                            "Please run: python scripts/utils/download_model.py google/madlad400-3b-mt"
                        )
            elif not downloaded_models:
                log_warning(
                    f"No translation models found for "
                    f"{get_language_name(src_lang)} -> {get_language_name(ctx.tgt_lang)}."
                )
                log_info(
                    "Please run: python scripts/utils/download_model.py google/madlad400-3b-mt"
                )

        # 里程碑进度：开始语言检测
        progress.update(10, "Detecting source language...")

        result = self.translation_engine.translate(
            ctx.transcription_result,
            src_lang,
            ctx.tgt_lang,
            progress,
            detection_context="Pipeline Translation",
        )

        ctx.translation_result = result
        log_success("Translation completed")
        progress.update(100.0, "Translation completed")
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
        raise error


class SRTGenerationStage(SkipableStage):
    """字幕生成阶段（支持SRT/ASS/TXT格式）"""

    name = "srt_generation"

    def __init__(self, srt_engine, ass_engine=None):
        self.srt_engine = srt_engine
        self.ass_engine = ass_engine

    def execute(self, ctx: ProcessingContext) -> ProcessingContext:
        """生成字幕文件"""
        log_step("Final Stage")
        ctx.set_stage("srt_generation")
        progress = ctx.progress_callback or NO_OP_PROGRESS
        progress.update(0.0, "Preparing subtitle generation...")

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
            if output_format == "ass" and not output_path.endswith(".ass"):
                output_path = os.path.splitext(output_path)[0] + ".ass"
        else:
            video_dir = ctx.get_video_dir()
            video_name = ctx.get_video_name()
            if output_format == "ass":
                ext = ".ass"
            elif output_format == "txt":
                ext = ".txt"
            else:
                ext = ".srt"
            output_filename = f"{video_name}_{output_lang}{ext}"
            output_path = os.path.join(video_dir, output_filename)

        segments = result.get("segments", [])

        # 里程碑进度：开始生成文件
        progress.update(30, f"Generating {output_format.upper()} file...")

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

        # 里程碑进度：文件写入完成
        progress.update(80, "Finalizing...")

        log_success(f"Subtitle generated: {output_path}")
        progress.update(100.0, "Subtitle generation task completed!")
        return ctx

    def validate(self, ctx: ProcessingContext) -> bool:
        """验证输出文件"""
        if not ctx.output_path:
            self._log("Output path not set", "error")
            return False
        if not os.path.exists(ctx.output_path):
            self._log(f"Output file does not exist: {ctx.output_path}", "error")
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
        log_step("Initialization")
        ctx.set_stage("model_loading")
        progress = ctx.progress_callback or NO_OP_PROGRESS

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
            progress.update(0.0, f"Loading {ctx.whisper_model} model...")

            from ..resource_manager import whisper_model

            # 里程碑进度：开始加载
            progress.update(20, "Initializing model...")

            # 加载模型（模型路径由 whisper_model 内部处理）
            model_instance = whisper_model(ctx.whisper_model, ctx.whisper_device)
            ctx._model_context = model_instance
            ctx.whisper_model_instance = model_instance.__enter__()

            # 里程碑进度：模型加载中
            progress.update(60, "Loading model weights...")

            log_success(f"Faster Whisper model {ctx.whisper_model} loaded successfully")
            progress.update(
                100.0, f"Faster Whisper {ctx.whisper_model} loaded successfully"
            )
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
