"""
视频增强服务
"""

import asyncio
import functools
from pathlib import Path
from typing import Optional

from mediafactory.config import get_config
from mediafactory.pipeline.context import ProcessingResult
from mediafactory.logging import log_info, log_error_with_context
from mediafactory.core.progress_protocol import ProgressCallback, NO_OP_PROGRESS
from mediafactory.core.error_utils import sanitize_error


class VideoEnhancementService:
    """
    视频增强服务

    提供超分辨率、降噪、时序平滑等功能，直接调用增强引擎执行。
    """

    def __init__(self):
        self.config = get_config()

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
        video_path = Path(video_path)

        if output_path is None:
            output_path = str(video_path.with_stem(f"{video_path.stem}_enhanced"))

        try:
            progress.update(0, "Starting video enhancement...")
            log_info(f"Starting video enhancement for: {video_path}")

            # 延迟导入以避免启动时加载 ML 依赖
            from mediafactory.engine.video_enhancement import (
                VideoEnhancementEngine,
                EnhancementConfig,
            )

            # 组装引擎
            enhancement_config = EnhancementConfig(
                scale=scale,
                model_type=model_type,
                denoise=denoise,
                temporal=temporal,
            )
            engine = VideoEnhancementEngine(enhancement_config)

            # 在线程池中直接调用引擎
            loop = asyncio.get_running_loop()
            result_output = await loop.run_in_executor(
                None,
                functools.partial(
                    engine.enhance, str(video_path), output_path, progress=progress
                ),
            )

            progress.update(100, "Video enhancement completed")
            log_info(f"Video enhanced: {result_output}")

            return ProcessingResult(
                success=True,
                output_path=result_output,
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
