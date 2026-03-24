"""Time estimation utilities for processing operations.

This module provides time estimation for FFmpeg audio extraction
and Whisper transcription operations.
"""

from typing import Optional


# =============================================================================
# 时间估算常量（从 constants.py 移入）
# =============================================================================


class TimeEstimationConstants:
    """时间估算常量。"""

    # FFmpeg 时间估算
    FFMPEG_BASE_TIME_PER_MB = 0.1  # 每MB基础处理时间（秒）
    FFMPEG_SAFETY_FACTOR = 3.0  # FFmpeg 时间估算安全系数

    # Whisper 转录时间因子（固定使用 Large V3）
    WHISPER_LARGE_V3_FACTOR = 4.2  # Large V3 模型时间因子
    WHISPER_BEAM_SIZE_ADDITIONAL_FACTOR = 0.05  # 每 beam 增加 5% 时间
    WHISPER_WORD_TIMESTAMP_FACTOR = 1.3  # 词级时间戳增加 30% 时间


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
    def estimate_whisper_transcription_time(
        audio_duration: float,
        beam_size: int = 5,
        has_word_timestamps: bool = False,
    ) -> float:
        """估算 Whisper 转写时间。

        Args:
            audio_duration: 音频时长（秒）
            beam_size: beam search 大小（影响处理速度）
            has_word_timestamps: 是否启用词级时间戳（会增加处理时间）

        Returns:
            估算的转写时间（秒）
        """
        # 固定使用 Large V3 的时间因子
        factor = TimeEstimationConstants.WHISPER_LARGE_V3_FACTOR

        # beam_size 影响：每个额外的 beam 增加约 5% 处理时间
        beam_factor = 1.0 + (beam_size - 1) * (
            TimeEstimationConstants.WHISPER_BEAM_SIZE_ADDITIONAL_FACTOR
        )

        # 词级时间戳影响：增加约 30% 处理时间
        word_timestamp_factor = (
            TimeEstimationConstants.WHISPER_WORD_TIMESTAMP_FACTOR
            if has_word_timestamps
            else 1.0
        )

        return audio_duration * factor * beam_factor * word_timestamp_factor

    @staticmethod
    def get_video_duration(video_path: str) -> Optional[float]:
        """使用 imageio-ffmpeg 获取实际视频时长。"""
        try:
            import subprocess
            import json
            import imageio_ffmpeg

            # Get ffprobe path (bundled with imageio-ffmpeg)
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            ffprobe_exe = ffmpeg_exe.replace("ffmpeg", "ffprobe")

            # Run ffprobe to get video info
            cmd = [
                ffprobe_exe,
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                video_path,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            probe = json.loads(result.stdout)

            # Try to get duration from streams first
            for stream in probe.get("streams", []):
                if "duration" in stream:
                    return float(stream["duration"])

            # Fallback to format duration
            if "format" in probe and "duration" in probe["format"]:
                return float(probe["format"]["duration"])
        except Exception as e:
            # 静默忽略获取视频时长失败的情况
            pass
        return None
