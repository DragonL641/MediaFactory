"""流水线编排模块"""

from typing import List
from .context import ProcessingContext, ProcessingResult
from .stage import ProcessingStage
from ..exceptions import MediaFactoryError, OperationCancelledError, ProcessingError
from ..logging import log_error, log_warning

# 各 stage 的相对权重（在包含它的 Pipeline 内归一化为 0-100 连续区间）
STAGE_WEIGHTS = {
    "model_loading": 5.0,
    "audio_extraction": 10.0,
    "transcription": 40.0,
    "postprocess": 10.0,
    "translation": 25.0,
    "srt_generation": 5.0,
}


class _StageProgress:
    """把 stage 内 0-100 进度线性映射到该 stage 在全局的区间。"""

    def __init__(self, callback, start: float, end: float):
        self._callback = callback
        self._start = start
        self._end = end

    def set_stage(self, stage: str) -> None:
        self._callback.set_stage(stage)

    def update(self, progress: float, message: str = "") -> None:
        mapped = self._start + (progress / 100.0) * (self._end - self._start)
        self._callback.update(mapped, message)

    def is_cancelled(self) -> bool:
        return self._callback.is_cancelled()


class Pipeline:
    """处理阶段编排器，按顺序执行各阶段"""

    def __init__(self, stages: List[ProcessingStage]):
        self.stages = stages

    def _compute_ranges(self) -> dict:
        """按本 pipeline 的 stage 组合把权重归一化为 0-100 的连续区间。"""
        total = sum(STAGE_WEIGHTS.get(stage.name, 1.0) for stage in self.stages)
        ranges = {}
        cursor = 0.0
        for stage in self.stages:
            weight = STAGE_WEIGHTS.get(stage.name, 1.0)
            ranges[stage.name] = (cursor, cursor + weight / total * 100.0)
            cursor += weight / total * 100.0
        return ranges

    def execute(self, context: ProcessingContext) -> ProcessingResult:
        """执行所有阶段"""
        ranges = self._compute_ranges()
        # 记住原始回调：每个 stage 基于它新建映射器，避免逐层叠加映射
        original_callback = context.progress_callback
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

                # 每个 stage 获得映射到全局区间的进度视图
                if original_callback:
                    start, end = ranges[stage.name]
                    context.progress_callback = _StageProgress(
                        original_callback, start, end
                    )

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
            # 恢复原始回调，去除最后一个 stage 留下的映射包装
            context.progress_callback = original_callback
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
