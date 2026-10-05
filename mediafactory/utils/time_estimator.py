"""Time estimation utilities for processing operations.

This module provides time estimation for FFmpeg audio extraction
and Whisper transcription operations.
"""


# =============================================================================
# 时间估算常量（从 constants.py 移入）
# =============================================================================


class TimeEstimationConstants:
    """时间估算常量。"""

    # FFmpeg 时间估算
    FFMPEG_BASE_TIME_PER_MB = 0.1  # 每MB基础处理时间（秒）
    FFMPEG_SAFETY_FACTOR = 3.0  # FFmpeg 时间估算安全系数


class TimeEstimator:
    """用于估算操作耗时的工具类。"""

    @staticmethod
    def estimate_ffmpeg_extraction_time(file_size_bytes: int) -> float:
        """根据文件大小估算 FFmpeg 提取时间。"""
        mb_size = file_size_bytes / (1024 * 1024)
        # 粗略估算：约 2-3 倍实时处理速度
        return (
            mb_size
            * TimeEstimationConstants.FFMPEG_BASE_TIME_PER_MB
            * TimeEstimationConstants.FFMPEG_SAFETY_FACTOR
        )
