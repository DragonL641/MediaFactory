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

    @staticmethod
    def get_video_duration(video_path: str) -> float | None:
        """探测媒体时长（转录进度跟踪依赖），失败返回 None。

        imageio-ffmpeg 只捆绑 ffmpeg 不带 ffprobe，故解析 `ffmpeg -i`
        stderr 里的 Duration 行（ffmpeg 无输出文件时本就以 1 退出）。
        """
        try:
            import re
            import subprocess

            import imageio_ffmpeg

            result = subprocess.run(
                [imageio_ffmpeg.get_ffmpeg_exe(), "-i", video_path],
                capture_output=True,
                text=True,
                check=False,
            )
            m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", result.stderr)
            if m:
                h, mn, s = (float(g) for g in m.groups())
                return h * 3600 + mn * 60 + s
        except Exception:  # noqa: BLE001 — 探测失败静默降级，进度退化为不确定模式
            pass
        return None
