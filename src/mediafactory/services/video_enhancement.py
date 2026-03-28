"""
视频增强服务
"""

import asyncio
from pathlib import Path
from typing import Optional

from mediafactory.config import get_config
from mediafactory.pipeline import Pipeline
from mediafactory.pipeline.context import ProcessingContext, ProcessingResult
from mediafactory.logging import log_info, log_error, log_error_with_context
from mediafactory.core.progress_protocol import ProgressCallback, NO_OP_PROGRESS
from mediafactory.api.error_handler import sanitize_error


class VideoEnhancementService:
    """
    视频增强服务

    提供超分辨率、降噪、时序平滑等功能，委托给 Pipeline 执行。
    """

    def __init__(self):
        self.config = get_config()
        self._cancelled: bool = False

    def cancel(self):
        """取消当前任务"""
        self._cancelled = True

    async def enhance(
        self,
        video_path: str,
        scale: int = 2,
        model_type: str = "general",
        denoise: bool = False,
        temporal: bool = False,
        output_path: Optional[str] = None,
        progress: ProgressCallback = NO_OP_PROGRESS,
    ) -> ProcessingResult:
        """
        增强视频画质

        Args:
            video_path: 视频文件路径
            scale: 放大倍数（2 或 4）
            model_type: 模型类型（general 或 anime）
            denoise: 是否降噪
            temporal: 是否时序平滑
            output_path: 输出路径（可选）
            progress: 进度回调

        Returns:
            ProcessingResult: 处理结果
        """
        self._cancelled = False
        video_path = Path(video_path)

        if output_path is None:
            output_path = str(video_path.with_stem(f"{video_path.stem}_enhanced"))

        try:
            progress.update(0, "Starting video enhancement...")
            log_info(f"Starting video enhancement for: {video_path}")

            # 创建 Pipeline 上下文
            context = ProcessingContext(
                video_path=str(video_path),
                progress_callback=progress,
                config={
                    "scale": scale,
                    "model_type": model_type,
                    "denoise": denoise,
                    "temporal": temporal,
                    "output_path": output_path,
                },
            )

            # 创建并执行 Pipeline
            pipeline = Pipeline.create_enhance_only()

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, pipeline.execute, context)

            if self._cancelled:
                return ProcessingResult(
                    success=False,
                    error_message="Task cancelled",
                    error_type="CancelledError",
                )

            if not result.success:
                return ProcessingResult(
                    success=False,
                    error_message=result.error_message or "Pipeline execution failed",
                    error_type=result.error_type,
                )

            progress.update(100, "Video enhancement completed")
            log_info(f"Video enhanced: {result.output_path}")

            return ProcessingResult(
                success=True,
                output_path=result.output_path,
                metadata={
                    "video_path": str(video_path),
                    "scale": scale,
                    "denoise": denoise,
                    "temporal": temporal,
                },
            )

        except Exception as e:
            log_error_with_context(
                "Video enhancement failed",
                e,
                context={"video_path": str(video_path)},
            )
            return ProcessingResult(
                success=False,
                error_message=sanitize_error(e),
                error_type=type(e).__name__,
            )
