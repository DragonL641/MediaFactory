"""
音频提取服务
"""

import asyncio
import functools
from pathlib import Path
from typing import Optional

from mediafactory.config import get_config
from mediafactory.engine.audio import AudioEngine
from mediafactory.pipeline.context import ProcessingResult
from mediafactory.logging import log_info, log_error_with_context
from mediafactory.core.progress_protocol import ProgressCallback, NO_OP_PROGRESS
from mediafactory.core.error_utils import sanitize_error


class AudioService:
    """
    音频提取服务

    直接调用 AudioEngine 提取音频，统一进度报告。
    """

    def __init__(self):
        self.config = get_config()
        self._audio_engine: Optional[AudioEngine] = None

    @property
    def audio_engine(self) -> AudioEngine:
        if self._audio_engine is None:
            self._audio_engine = AudioEngine()
        return self._audio_engine

    async def extract_audio(
        self,
        video_path: str,
        output_path: Optional[str] = None,
        progress: ProgressCallback = NO_OP_PROGRESS,
        sample_rate: int = 48000,
        channels: int = 2,
        filter_enabled: bool = True,
        highpass_freq: int = 200,
        lowpass_freq: int = 3000,
        volume: float = 1.0,
        output_format: str = "wav",
    ) -> ProcessingResult:
        """
        从视频提取音频

        Args:
            video_path: 视频文件路径
            output_path: 音频输出路径（可选，不指定则自动生成）
            progress: 进度回调
            sample_rate: 采样率 (Hz)
            channels: 声道数
            filter_enabled: 是否启用音频滤波器
            highpass_freq: 高通滤波频率 (Hz)
            lowpass_freq: 低通滤波频率 (Hz)
            volume: 音量倍数
            output_format: 输出格式 (wav/mp3/flac/aac)

        Returns:
            ProcessingResult 包含输出路径或错误信息
        """
        try:
            progress.update(0, "Starting audio extraction...")
            video_path = Path(video_path)
            log_info(f"Starting audio extraction for: {video_path}")

            # 组装引擎参数（与原 AudioExtractionStage 传参一致）
            extract_kwargs = {
                "progress": progress,
                "output_path": output_path,
                "filter_enabled": filter_enabled,
                "volume": volume,
                "output_format": output_format,
            }
            # 仅在有值时传递，避免 None 覆盖 AudioEngine 默认值
            for key, value in (
                ("sample_rate", sample_rate),
                ("channels", channels),
                ("highpass_freq", highpass_freq),
                ("lowpass_freq", lowpass_freq),
            ):
                if value is not None:
                    extract_kwargs[key] = value

            # 在线程池中直接调用引擎
            loop = asyncio.get_running_loop()
            audio_path = await loop.run_in_executor(
                None,
                functools.partial(
                    self.audio_engine.extract, str(video_path), **extract_kwargs
                ),
            )

            progress.update(100, "Audio extraction completed")
            log_info(f"Audio extracted: {audio_path}")

            return ProcessingResult(
                success=True,
                output_path=audio_path,
                metadata={"video_path": str(video_path)},
            )

        except Exception as e:
            log_error_with_context(
                "Audio extraction failed",
                e,
                context={"video_path": str(video_path)},
            )
            return ProcessingResult(
                success=False,
                error_message=sanitize_error(e),
                error_type=type(e).__name__,
            )
