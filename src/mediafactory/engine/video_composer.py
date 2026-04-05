"""视频合成引擎。

支持将字幕嵌入视频（软字幕/硬字幕）。
软字幕：字幕作为独立轨道嵌入视频，用户可切换显示。
硬字幕：字幕直接烧录到视频画面上。
"""

import os
import subprocess
from pathlib import Path
from typing import Optional, List, Literal

from ..logging import log_info, log_error, log_debug
from ..exceptions import ProcessingError
from ..core.exception_wrapper import wrap_exceptions, convert_exception
from ..i18n import t


class VideoComposer:
    """视频合成引擎，支持字幕嵌入。"""

    # 支持软字幕的视频格式
    SOFT_SUBTITLE_FORMATS = {".mp4", ".mov", ".mkv", ".m4v"}
    # 不支持软字幕的格式（需要硬字幕）
    HARD_SUBTITLE_ONLY_FORMATS = {".webm"}

    def __init__(self):
        """初始化视频合成引擎。"""
        self._ffmpeg_exe = self._get_ffmpeg_executable()

    def _get_ffmpeg_timeout(self, timeout_type: str) -> int:
        """从配置获取 FFmpeg 超时时间"""
        try:
            from ..config import get_config

            config = get_config()
            if timeout_type == "hard":
                return config.ffmpeg.hard_subtitle_timeout
            elif timeout_type == "multi":
                return config.ffmpeg.multi_subtitle_timeout
            else:
                return config.ffmpeg.soft_subtitle_timeout
        except Exception:
            # 配置不可用时回退到默认值
            defaults = {"hard": 1800, "multi": 300, "soft": 300}
            return defaults.get(timeout_type, 300)

    def _get_ffmpeg_executable(self) -> str:
        """获取 FFmpeg 可执行文件路径。

        优先使用 imageio-ffmpeg，其次使用系统 FFmpeg。

        Returns:
            FFmpeg 可执行文件路径

        Raises:
            ProcessingError: 如果找不到 FFmpeg
        """
        try:
            import imageio_ffmpeg

            return imageio_ffmpeg.get_ffmpeg_exe()
        except ImportError:
            pass

        # 尝试系统 FFmpeg
        import shutil

        ffmpeg_path = shutil.which("ffmpeg")
        if ffmpeg_path:
            return ffmpeg_path

        raise ProcessingError(
            message=t("error.ffmpegNotFound"),
            context={"missing_dependency": "ffmpeg"},
        )

    def embed_soft_subtitle(
        self,
        video_path: str,
        subtitle_path: str,
        output_path: str,
        language: str = "und",
        title: Optional[str] = None,
    ) -> str:
        """嵌入软字幕到视频。

        软字幕作为独立轨道嵌入视频，用户可以在播放器中切换显示。
        视频和音频流会被直接复制（无需重编码），处理速度快。

        Args:
            video_path: 输入视频文件路径
            subtitle_path: 字幕文件路径（支持 .srt, .ass, .ssa）
            output_path: 输出视频文件路径
            language: 字幕语言代码（如 "chi", "eng", "jpn"）
            title: 字幕轨道标题（可选）

        Returns:
            输出视频文件路径

        Raises:
            ProcessingError: 如果嵌入失败或格式不支持
        """
        ext = Path(output_path).suffix.lower()

        # 检查格式是否支持软字幕
        if ext in self.HARD_SUBTITLE_ONLY_FORMATS:
            raise ProcessingError(
                message=t("error.softSubtitleNotSupported", format=ext),
                context={"video_path": video_path, "format": ext},
            )

        # 确定字幕编码器
        if ext in [".mp4", ".mov", ".m4v"]:
            subtitle_codec = "mov_text"
        elif ext == ".mkv":
            # MKV 支持原始字幕格式
            sub_ext = Path(subtitle_path).suffix.lower()
            subtitle_codec = (
                sub_ext[1:] if sub_ext in [".srt", ".ass", ".ssa"] else "srt"
            )
        else:
            subtitle_codec = "mov_text"

        log_info(f"[VideoComposer] 嵌入软字幕: {subtitle_path} -> {video_path}")
        log_debug(f"  字幕编码器: {subtitle_codec}, 语言: {language}")

        cmd = [
            self._ffmpeg_exe,
            "-i",
            video_path,
            "-i",
            subtitle_path,
            "-c:v",
            "copy",  # 视频流直接复制
            "-c:a",
            "copy",  # 音频流直接复制
            "-c:s",
            subtitle_codec,  # 字幕编码器
            f"-metadata:s:s:0",
            f"language={language}",
        ]

        if title:
            cmd.extend(["-metadata:s:s:0", f"title={title}"])

        cmd.extend(["-y", output_path])  # 覆盖输出

        try:
            with wrap_exceptions(
                context={
                    "video_path": video_path,
                    "subtitle_path": subtitle_path,
                    "output_path": output_path,
                },
                operation="embed_soft_subtitle",
            ):
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self._get_ffmpeg_timeout("soft"),
                )

                if result.returncode != 0:
                    error_msg = (
                        result.stderr.strip() if result.stderr else "Unknown error"
                    )
                    log_error(f"[VideoComposer] FFmpeg 错误: {error_msg}")
                    raise ProcessingError(
                        message=t(
                            "error.softSubtitleEmbedFailed", error=error_msg[:200]
                        ),
                        context={
                            "video_path": video_path,
                            "subtitle_path": subtitle_path,
                            "ffmpeg_error": error_msg,
                        },
                    )

                log_info(f"[VideoComposer] 软字幕嵌入完成: {output_path}")
                return output_path

        except subprocess.TimeoutExpired:
            raise ProcessingError(
                message=t("error.softSubtitleTimeout"),
                context={"video_path": video_path, "timeout": 300},
            )
        except ProcessingError:
            raise
        except Exception as e:
            raise convert_exception(
                e,
                context={"video_path": video_path, "subtitle_path": subtitle_path},
            ) from e

    def burn_subtitle(
        self,
        video_path: str,
        subtitle_path: str,
        output_path: str,
        force_style: Optional[str] = None,
    ) -> str:
        """烧录硬字幕到视频。

        硬字幕直接渲染到视频画面上，所有播放器都能显示。
        需要对视频进行重编码，处理时间较长。

        Args:
            video_path: 输入视频文件路径
            subtitle_path: 字幕文件路径（支持 .srt, .ass, .ssa）
            output_path: 输出视频文件路径
            force_style: ASS 样式参数（可选，如 "FontSize=24,PrimaryColour=&HFFFFFF"）

        Returns:
            输出视频文件路径

        Raises:
            ProcessingError: 如果烧录失败
        """
        log_info(f"[VideoComposer] 烧录硬字幕: {subtitle_path} -> {video_path}")

        # 转义字幕路径（Windows 需要特殊处理）
        subtitle_path_escaped = subtitle_path.replace("\\", "/").replace(":", "\\:")

        # 构建字幕滤镜
        sub_ext = Path(subtitle_path).suffix.lower()
        if sub_ext == ".ass":
            filter_str = f"ass='{subtitle_path_escaped}'"
        else:
            filter_str = f"subtitles='{subtitle_path_escaped}'"

        if force_style:
            filter_str += f":force_style='{force_style}'"

        cmd = [
            self._ffmpeg_exe,
            "-i",
            video_path,
            "-vf",
            filter_str,
            "-c:a",
            "copy",  # 音频流直接复制
            "-y",
            output_path,
        ]

        try:
            with wrap_exceptions(
                context={
                    "video_path": video_path,
                    "subtitle_path": subtitle_path,
                    "output_path": output_path,
                },
                operation="burn_subtitle",
            ):
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self._get_ffmpeg_timeout("hard"),  # 重编码较慢
                )

                if result.returncode != 0:
                    error_msg = (
                        result.stderr.strip() if result.stderr else "Unknown error"
                    )
                    log_error(f"[VideoComposer] FFmpeg 错误: {error_msg}")
                    raise ProcessingError(
                        message=t(
                            "error.hardSubtitleBurnFailed", error=error_msg[:200]
                        ),
                        context={
                            "video_path": video_path,
                            "subtitle_path": subtitle_path,
                            "ffmpeg_error": error_msg,
                        },
                    )

                log_info(f"[VideoComposer] 硬字幕烧录完成: {output_path}")
                return output_path

        except subprocess.TimeoutExpired:
            raise ProcessingError(
                message=t("error.hardSubtitleTimeout"),
                context={"video_path": video_path, "timeout": 1800},
            )
        except ProcessingError:
            raise
        except Exception as e:
            raise convert_exception(
                e,
                context={"video_path": video_path, "subtitle_path": subtitle_path},
            ) from e

    def embed_multiple_subtitles(
        self,
        video_path: str,
        subtitle_tracks: List[dict],
        output_path: str,
    ) -> str:
        """嵌入多个软字幕轨道。

        Args:
            video_path: 输入视频文件路径
            subtitle_tracks: 字幕轨道列表，每个轨道包含:
                - path: 字幕文件路径
                - language: 语言代码（如 "chi", "eng"）
                - title: 轨道标题（可选）
            output_path: 输出视频文件路径

        Returns:
            输出视频文件路径

        Raises:
            ProcessingError: 如果嵌入失败
        """
        if not subtitle_tracks:
            raise ProcessingError(
                message=t("error.atLeastOneSubtitleRequired"),
                context={"video_path": video_path},
            )

        ext = Path(output_path).suffix.lower()

        if ext in self.HARD_SUBTITLE_ONLY_FORMATS:
            raise ProcessingError(
                message=t("error.formatNotSupportSoftSubtitle", format=ext),
                context={"video_path": video_path, "format": ext},
            )

        # 确定字幕编码器
        if ext in [".mp4", ".mov", ".m4v"]:
            subtitle_codec = "mov_text"
        elif ext == ".mkv":
            subtitle_codec = "srt"
        else:
            subtitle_codec = "mov_text"

        log_info(f"[VideoComposer] 嵌入 {len(subtitle_tracks)} 个字幕轨道")

        # 构建 FFmpeg 命令
        cmd = [self._ffmpeg_exe, "-i", video_path]

        # 添加每个字幕输入
        for track in subtitle_tracks:
            cmd.extend(["-i", track["path"]])

        # 映射流
        cmd.extend(["-map", "0:v", "-map", "0:a"])
        for i in range(len(subtitle_tracks)):
            cmd.extend(["-map", f"{i + 1}:s"])

        # 编码设置
        cmd.extend(["-c:v", "copy", "-c:a", "copy", "-c:s", subtitle_codec])

        # 添加元数据
        for i, track in enumerate(subtitle_tracks):
            lang = track.get("language", "und")
            cmd.extend([f"-metadata:s:s:{i}", f"language={lang}"])
            if track.get("title"):
                cmd.extend([f"-metadata:s:s:{i}", f"title={track['title']}"])

        cmd.extend(["-y", output_path])

        try:
            with wrap_exceptions(
                context={
                    "video_path": video_path,
                    "subtitle_tracks": subtitle_tracks,
                    "output_path": output_path,
                },
                operation="embed_multiple_subtitles",
            ):
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self._get_ffmpeg_timeout("multi"),
                )

                if result.returncode != 0:
                    error_msg = (
                        result.stderr.strip() if result.stderr else "Unknown error"
                    )
                    log_error(f"[VideoComposer] FFmpeg 错误: {error_msg}")
                    raise ProcessingError(
                        message=t(
                            "error.multiSubtitleEmbedFailed", error=error_msg[:200]
                        ),
                        context={"ffmpeg_error": error_msg},
                    )

                log_info(f"[VideoComposer] 多字幕嵌入完成: {output_path}")
                return output_path

        except subprocess.TimeoutExpired:
            raise ProcessingError(
                message=t("error.multiSubtitleTimeout"),
                context={"video_path": video_path},
            )
        except ProcessingError:
            raise
        except Exception as e:
            raise convert_exception(e, context={"video_path": video_path}) from e

    def supports_soft_subtitle(self, video_path: str) -> bool:
        """检查视频格式是否支持软字幕。

        Args:
            video_path: 视频文件路径

        Returns:
            True 如果支持软字幕
        """
        ext = Path(video_path).suffix.lower()
        return ext in self.SOFT_SUBTITLE_FORMATS
