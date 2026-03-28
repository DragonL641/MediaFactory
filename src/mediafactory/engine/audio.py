"""音频提取引擎

配置：采样率 48000Hz，立体声，滤波器（高通200Hz，低通3000Hz）
"""

import os
import sys
import time
import threading
import subprocess
from typing import Optional
from pathlib import Path
from ..constants import THREAD_JOIN_TIMEOUT
from ..utils.time_estimator import TimeEstimator
from ..core.progress_protocol import ProgressCallback, NO_OP_PROGRESS
from ..logging import log_debug, log_error, log_step
from ..exceptions import ProcessingError
from ..core.exception_wrapper import wrap_exceptions, convert_exception
from ..i18n import t

# 音频参数
DEFAULT_HIGHPASS_FREQ = 200
DEFAULT_LOWPASS_FREQ = 3000
DEFAULT_VOLUME = 1.0
DEFAULT_AUDIO_SAMPLE_RATE = 48000
DEFAULT_AUDIO_CHANNELS = 2

# 支持的输出格式及其编码器配置
OUTPUT_FORMAT_CONFIG = {
    "wav": {"ext": ".wav", "codec": "pcm_s16le", "extra_args": []},
    "mp3": {"ext": ".mp3", "codec": "libmp3lame", "extra_args": ["-q:a", "2"]},
    "flac": {"ext": ".flac", "codec": "flac", "extra_args": []},
    "aac": {"ext": ".aac", "codec": "aac", "extra_args": ["-b:a", "192k"]},
}

# 危险字符 (注意: 不包含反斜杠，因为它是 Windows 路径分隔符)
DANGEROUS_CHARS = set(";|&`$()<>[]{}!*?~'\"")


def validate_video_path(video_path: str) -> None:
    """验证视频路径安全性"""
    if not video_path:
        raise ProcessingError(
            message=t("error.videoPathEmpty"), context={"video_path": video_path}
        )

    path_chars = set(video_path)
    if path_chars & DANGEROUS_CHARS:
        dangerous = "".join(sorted(path_chars & DANGEROUS_CHARS))
        raise ProcessingError(
            message=f"Video path contains dangerous characters: {dangerous!r}",
            context={"video_path": video_path, "dangerous_chars": dangerous},
        )

    try:
        resolved = Path(video_path).resolve()
    except Exception as e:
        raise ProcessingError(
            message=f"Invalid video path: {video_path}",
            context={"video_path": video_path, "error": str(e)},
        )

    if not resolved.exists():
        raise ProcessingError(
            message=t("error.videoFileNotFound", path=video_path),
            context={"video_path": video_path, "resolved_path": str(resolved)},
        )

    if not resolved.is_file():
        raise ProcessingError(
            message=f"Path is not a file: {video_path}",
            context={"video_path": video_path, "resolved_path": str(resolved)},
        )


def _find_ffmpeg_executable() -> str:
    """获取 FFmpeg 可执行文件路径（使用 imageio-ffmpeg）"""
    try:
        from imageio_ffmpeg import get_ffmpeg_exe

        ffmpeg_path = get_ffmpeg_exe()
        if Path(ffmpeg_path).exists():
            log_debug(f"Using bundled FFmpeg from imageio-ffmpeg: {ffmpeg_path}")
            return ffmpeg_path
    except ImportError as e:
        raise ProcessingError(
            message="imageio-ffmpeg package is not installed",
            context={"import_error": str(e)},
        )
    except Exception as e:
        raise ProcessingError(
            message=f"Failed to locate FFmpeg executable: {e}",
            context={"exception": str(e)},
        )

    raise ProcessingError(message="FFmpeg executable not found", context={})


class AudioEngine:
    """音频提取引擎"""

    def __init__(self):
        self._temp_audio_path: Optional[str] = None
        self._ffmpeg_executable: Optional[str] = None

    def _get_ffmpeg_executable(self) -> str:
        """获取 FFmpeg 路径（缓存）"""
        if self._ffmpeg_executable is None:
            self._ffmpeg_executable = _find_ffmpeg_executable()
        return self._ffmpeg_executable

    def extract(
        self,
        video_path: str,
        progress: Optional[ProgressCallback] = None,
        output_path: Optional[str] = None,
        sample_rate: int = DEFAULT_AUDIO_SAMPLE_RATE,
        channels: int = DEFAULT_AUDIO_CHANNELS,
        filter_enabled: bool = True,
        highpass_freq: int = DEFAULT_HIGHPASS_FREQ,
        lowpass_freq: int = DEFAULT_LOWPASS_FREQ,
        volume: float = DEFAULT_VOLUME,
        output_format: str = "wav",
    ) -> str:
        """从视频提取音频

        Args:
            video_path: 输入视频文件路径
            progress: 进度回调
            output_path: 输出音频文件路径（可选，不指定则自动生成）
            sample_rate: 采样率 (Hz)
            channels: 声道数 (1=单声道, 2=立体声)
            filter_enabled: 是否启用音频滤波器
            highpass_freq: 高通滤波频率 (Hz)
            lowpass_freq: 低通滤波频率 (Hz)
            volume: 音量倍数
            output_format: 输出格式 (wav/mp3/flac/aac)

        Returns:
            输出音频文件路径
        """
        if progress is None:
            progress = NO_OP_PROGRESS

        validate_video_path(video_path)
        video_path = os.path.abspath(video_path)

        # 获取输出格式配置
        format_config = OUTPUT_FORMAT_CONFIG.get(
            output_format, OUTPUT_FORMAT_CONFIG["wav"]
        )

        # 生成音频文件路径（支持自定义输出路径）
        if output_path:
            audio_path = os.path.abspath(output_path)
        else:
            video_dir, video_filename = os.path.split(video_path)
            video_basename = os.path.splitext(video_filename)[0]
            audio_filename = f"{video_basename}{format_config['ext']}"
            audio_path = os.path.abspath(os.path.join(video_dir, audio_filename))
        self._temp_audio_path = audio_path

        # 估算处理时间
        file_size = os.path.getsize(video_path)
        estimated_time = min(
            TimeEstimator.estimate_ffmpeg_extraction_time(file_size), 30.0
        )

        completion_event = threading.Event()
        monitor_thread = None

        try:
            with wrap_exceptions(
                context={
                    "video_path": video_path,
                    "audio_path": audio_path,
                    "file_size": file_size,
                    "sample_rate": sample_rate,
                    "channels": channels,
                    "filter_enabled": filter_enabled,
                    "output_format": output_format,
                },
                operation="audio_extraction",
            ):
                log_step("Extracting audio from video...")

                ffmpeg_executable = self._get_ffmpeg_executable()
                cmd = [
                    ffmpeg_executable,
                    "-i",
                    video_path,
                    "-ar",
                    str(sample_rate),
                    "-ac",
                    str(channels),
                    "-acodec",
                    format_config["codec"],
                    *format_config["extra_args"],
                    "-y",
                    "-loglevel",
                    "error",
                    "-copyts",
                ]

                if filter_enabled:
                    cmd.extend(
                        [
                            "-af",
                            f"highpass=f={highpass_freq},lowpass=f={lowpass_freq},volume={volume}",
                        ]
                    )

                cmd.append(audio_path)

                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True,
                )

                monitor_thread = threading.Thread(
                    target=self._monitor_subprocess,
                    args=(process, progress, estimated_time, completion_event),
                    daemon=True,
                )
                monitor_thread.start()

                _, stderr = process.communicate()
                if process.returncode != 0:
                    error_details = stderr.strip() if stderr else "Unknown error"
                    raise ProcessingError(
                        message=f"ffmpeg extraction failed with exit code {process.returncode}: {error_details}",
                        context={
                            "video_path": video_path,
                            "audio_path": audio_path,
                            "exit_code": process.returncode,
                            "error_details": error_details,
                        },
                    )

        except ProcessingError:
            log_error("Audio extraction failed")
            self.cleanup_temp_file()
            raise
        except Exception as e:
            log_error(f"Audio extraction failed: {e}")
            self.cleanup_temp_file()
            raise convert_exception(
                e, context={"video_path": video_path, "audio_path": audio_path}
            ) from e
        finally:
            completion_event.set()
            if monitor_thread:
                monitor_thread.join(timeout=THREAD_JOIN_TIMEOUT)
            progress.update(100.0, t("progress.completed"))

        return audio_path

    def cleanup_temp_file(self) -> None:
        """清理临时音频文件"""
        if self._temp_audio_path and os.path.exists(self._temp_audio_path):
            try:
                os.remove(self._temp_audio_path)
                log_debug(f"Cleaned up temporary audio file: {self._temp_audio_path}")
            except Exception as e:
                log_error(
                    f"Failed to cleanup temporary audio file {self._temp_audio_path}: {e}"
                )
            finally:
                self._temp_audio_path = None

    def _monitor_subprocess(
        self,
        process,
        progress: ProgressCallback,
        estimated_time: float,
        completion_event: threading.Event,
    ):
        """监控子进程进度"""
        start_time = time.time()
        while process.poll() is None and not completion_event.is_set():
            if progress.is_cancelled():
                process.terminate()
                process.wait()
                break

            elapsed = time.time() - start_time
            if estimated_time > 0:
                progress_value = min((elapsed / estimated_time) * 100, 99.0)
                progress.update(progress_value, t("progress.extractingAudio"))
            else:
                progress.update(50.0, t("progress.extractingAudio"))

            if completion_event.wait(0.5):
                break
        progress.update(100.0, t("progress.completed"))
