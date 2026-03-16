"""流水线编排模块"""

from typing import List
from .context import ProcessingContext, ProcessingResult
from .stage import ProcessingStage
from ..exceptions import MediaFactoryError, OperationCancelledError, ProcessingError


class Pipeline:
    """处理阶段编排器，按顺序执行各阶段"""

    def __init__(self, stages: List[ProcessingStage]):
        self.stages = stages

    def execute(self, context: ProcessingContext) -> ProcessingResult:
        """执行所有阶段"""
        try:
            for stage in self.stages:
                # 检查取消
                if context.is_cancelled():
                    return ProcessingResult.from_exception(
                        OperationCancelledError(
                            message="Operation cancelled by user",
                            context={"stage": getattr(stage, "name", "unknown")},
                        ),
                        context,
                    )

                # 检查是否需要执行
                if not stage.should_execute(context):
                    stage._log("Skipping (result already exists)", "info")
                    continue

                # 执行阶段
                try:
                    stage._log("Starting...", "info")
                    context = stage.execute(context)
                except Exception as stage_error:
                    handled_error = stage.on_error(context, stage_error)

                    if handled_error is None:
                        stage._log("Error handled gracefully by stage", "info")
                    elif (
                        hasattr(handled_error, "severity")
                        and handled_error.severity == "warning"
                    ):
                        stage._log(
                            f"Stage completed with warning: {handled_error.message}",
                            "warning",
                        )
                    else:
                        raise handled_error

                # 验证结果
                if not stage.validate(context):
                    return ProcessingResult(
                        success=False,
                        error_message=f"Stage '{stage.name}' validation failed",
                        error_type="ValidationError",
                        context=context,
                    )

                stage._log("Completed successfully", "success")

            return ProcessingResult(
                success=True,
                output_path=context.output_path,
                context=context,
            )

        except OperationCancelledError as e:
            return ProcessingResult.from_exception(e, context)

        except MediaFactoryError as e:
            return ProcessingResult.from_exception(e, context)

        except Exception as e:
            wrapped = ProcessingError(
                message=f"Pipeline execution failed: {str(e)}",
                context={
                    "stage": getattr(context, "_current_stage", "unknown"),
                    "video_path": context.video_path,
                    "original_exception": type(e).__name__,
                },
            )
            return ProcessingResult.from_exception(wrapped, context)

        finally:
            # 无论成功还是失败，都清理上下文中的大对象
            if hasattr(context, "cleanup"):
                try:
                    context.cleanup()
                except Exception as cleanup_error:
                    # 清理失败不应该影响主流程
                    from ..logging import log_warning
                    log_warning(f"Context cleanup failed: {cleanup_error}")

    @classmethod
    def create_default(
        cls,
        audio_engine,
        recognition_engine,
        translation_engine,
        srt_engine,
    ) -> "Pipeline":
        """创建默认流水线（包含所有阶段）"""
        from .stages import (
            ModelLoadingStage,
            AudioExtractionStage,
            TranscriptionStage,
            TranslationStage,
            SRTGenerationStage,
            ModelCleanupStage,
        )

        return cls(
            [
                ModelLoadingStage(),
                AudioExtractionStage(audio_engine),
                TranscriptionStage(recognition_engine),
                TranslationStage(translation_engine),
                SRTGenerationStage(srt_engine),
                ModelCleanupStage(),
            ]
        )

    @classmethod
    def create_audio_only(cls, audio_engine) -> "Pipeline":
        """创建仅提取音频的流水线"""
        from .stages import AudioExtractionStage

        return cls([AudioExtractionStage(audio_engine)])

    @classmethod
    def create_with_model(
        cls,
        audio_engine,
        recognition_engine,
        translation_engine,
        srt_engine,
        whisper_model: str = "small",
        whisper_device: str = "cpu",
    ) -> "Pipeline":
        """创建带预加载模型的流水线（用于批处理）"""
        from .stages import (
            AudioExtractionStage,
            TranscriptionStage,
            TranslationStage,
            SRTGenerationStage,
        )

        return cls(
            [
                AudioExtractionStage(audio_engine),
                TranscriptionStage(recognition_engine),
                TranslationStage(translation_engine),
                SRTGenerationStage(srt_engine),
            ]
        )

    @classmethod
    def create_transcription_only(
        cls,
        audio_engine,
        recognition_engine,
        srt_engine,
    ) -> "Pipeline":
        """创建仅转录的流水线（不翻译）"""
        from .stages import (
            ModelLoadingStage,
            AudioExtractionStage,
            TranscriptionStage,
            SRTGenerationStage,
            ModelCleanupStage,
        )

        return cls(
            [
                ModelLoadingStage(),
                AudioExtractionStage(audio_engine),
                TranscriptionStage(recognition_engine),
                SRTGenerationStage(srt_engine),
                ModelCleanupStage(),
            ]
        )

    @classmethod
    def create_translation_only(
        cls,
        translation_engine,
        srt_engine,
    ) -> "Pipeline":
        """创建仅翻译的流水线"""
        from .stages import TranslationStage, SRTGenerationStage

        return cls(
            [
                TranslationStage(translation_engine),
                SRTGenerationStage(srt_engine),
            ]
        )

    def add_stage(self, stage: ProcessingStage) -> "Pipeline":
        """添加阶段到末尾"""
        self.stages.append(stage)
        return self

    def insert_stage(self, index: int, stage: ProcessingStage) -> "Pipeline":
        """在指定位置插入阶段"""
        self.stages.insert(index, stage)
        return self

    def remove_stage(self, stage_name: str) -> "Pipeline":
        """按名称移除阶段"""
        self.stages = [s for s in self.stages if s.name != stage_name]
        return self
