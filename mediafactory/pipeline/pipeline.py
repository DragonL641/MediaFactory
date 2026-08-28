"""流水线编排模块"""

from typing import List
from .context import ProcessingContext, ProcessingResult
from .stage import ProcessingStage
from ..exceptions import MediaFactoryError, OperationCancelledError, ProcessingError
from ..logging import log_error, log_warning


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

                # 执行阶段（异常直接上抛，由外层统一转为结果）
                stage._log("Starting...", "info")
                context = stage.execute(context)

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
            log_error(f"Pipeline failed at stage '{context.get_stage()}': {e.message}")
            return ProcessingResult.from_exception(e, context)

        except Exception as e:
            log_error(f"Pipeline failed at stage '{context.get_stage()}': {e}")
            wrapped = ProcessingError(
                message=f"Pipeline execution failed: {str(e)}",
                context={
                    "stage": getattr(context, "_current_stage_name", "unknown"),
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
            PostProcessStage,
            TranslationStage,
            SRTGenerationStage,
        )

        return cls(
            [
                ModelLoadingStage(),
                AudioExtractionStage(audio_engine),
                TranscriptionStage(recognition_engine),
                PostProcessStage(),
                TranslationStage(translation_engine),
                SRTGenerationStage(srt_engine),
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

    @classmethod
    def create_transcribe_standalone(
        cls,
        recognition_engine,
        srt_engine,
    ) -> "Pipeline":
        """创建独立转录流水线（音频已存在，仅转录+生成字幕）"""
        from .stages import (
            ModelLoadingStage,
            TranscriptionStage,
            PostProcessStage,
            SRTGenerationStage,
        )

        return cls(
            [
                ModelLoadingStage(),
                TranscriptionStage(recognition_engine),
                PostProcessStage(),
                SRTGenerationStage(srt_engine),
            ]
        )
