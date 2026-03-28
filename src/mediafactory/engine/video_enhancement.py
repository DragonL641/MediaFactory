"""视频增强引擎

提供视频画质增强功能，"""

import os
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Callable, Tuple

import cv2
import numpy as np

from mediafactory.core.progress_protocol import ProgressCallback, NO_OP_PROGRESS
from mediafactory.core.exception_wrapper import wrap_exceptions
from mediafactory.exceptions import ProcessingError
from mediafactory.logging import log_info, log_error, log_step
from mediafactory.engine.enhancement import (
    RealESRGANEnhancer,
    Denoiser,
    TemporalSmoother,
    TemporalSmootherConfig,
)
from mediafactory.i18n import t


# 批处理默认大小
DEFAULT_BATCH_SIZE = 4


@dataclass
class EnhancementConfig:
    """视频增强配置"""
    # 超分辨率参数
    scale: int = 4  # 2 或 4
    model_type: str = "general"  # general 或 anime

    # 去噪参数
    denoise: bool = False
    denoise_strength: float = 1.0

    # 时序平滑参数
    temporal: bool = False
    temporal_strength: float = 0.5

    # 设备配置
    device: Optional[str] = None  # cuda, mps, cpu, None=auto
    half_precision: bool = True  # 默认启用半精度以提升性能

    # 处理参数
    tile_size: int = 512  # 默认启用分块处理以减少显存压力

    # 批处理参数
    batch_size: int = DEFAULT_BATCH_SIZE  # 批处理帧数


class VideoEnhancementEngine:
    """视频增强引擎"""

    def __init__(self, config: Optional[EnhancementConfig] = None):
        """
        初始化视频增强引擎

        Args:
            config: 增强配置，如果为 None 则使用默认配置
        """
        self.config = config or EnhancementConfig()

        # 增强器实例（懒加载）
        self._sr_enhancer: Optional[RealESRGANEnhancer] = None
        self._denoiser: Optional[Denoiser] = None
        self._temporal_smoother: Optional[TemporalSmoother] = None

    def _get_sr_enhancer(self) -> RealESRGANEnhancer:
        """获取超分辨率增强器（懒加载）"""
        if self._sr_enhancer is None:
            self._sr_enhancer = RealESRGANEnhancer(
                scale=self.config.scale,
                model_type=self.config.model_type,
                device=self.config.device,
                half_precision=self.config.half_precision,
                tile=self.config.tile_size,
            )
        return self._sr_enhancer

    def _get_denoiser(self) -> Optional[Denoiser]:
        """获取去噪器（懒加载）"""
        if not self.config.denoise:
            return None
        if self._denoiser is None:
            self._denoiser = Denoiser(
                strength=self.config.denoise_strength,
                device=self.config.device,
                half_precision=self.config.half_precision,
            )
        return self._denoiser

    def _get_temporal_smoother(self) -> Optional[TemporalSmoother]:
        """获取时序平滑器（懒加载）"""
        if not self.config.temporal:
            return None
        if self._temporal_smoother is None:
            config = TemporalSmootherConfig(
                window_size=3,
                strength=self.config.temporal_strength,
            )
            self._temporal_smoother = TemporalSmoother(config)
        return self._temporal_smoother

    def enhance(
        self,
        video_path: str,
        output_path: Optional[str] = None,
        progress: Optional[ProgressCallback] = None,
    ) -> str:
        """
        增强视频

        Args:
            video_path: 输入视频路径
            output_path: 输出视频路径，如果为 None 则自动生成
            progress: 进度回调

        Returns:
            输出视频路径
        """
        if progress is None:
            progress = NO_OP_PROGRESS

        # 验证输入
        video_path = os.path.abspath(video_path)
        if not os.path.exists(video_path):
            raise ProcessingError(
                message=t("error.videoFileNotExist", path=video_path),
                context={"video_path": video_path},
            )

        # 生成输出路径
        if output_path is None:
            video_dir, video_name = os.path.split(video_path)
            video_basename, video_ext = os.path.splitext(video_name)
            output_path = os.path.join(video_dir, f"{video_basename}_enhanced{video_ext}")
        output_path = os.path.abspath(output_path)

        with wrap_exceptions(
            context={
                "video_path": video_path,
                "output_path": output_path,
                "config": self.config,
            },
            operation="video_enhancement",
        ):
            log_step(f"开始视频增强: {video_path}")
            log_info(f"配置: scale={self.config.scale}, model_type={self.config.model_type}")

            # 阶段1: 读取视频 (0-5%)
            progress.update(0, t("progress.readingVideo"))
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise ProcessingError(
                    message=t("error.cannotOpenVideo", path=video_path),
                    context={"video_path": video_path},
                )

            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

            log_info(f"视频信息: {width}x{height}, {fps}fps, {total_frames}帧")

            # 阶段2: 准备输出 (5-10%)
            progress.update(5, t("progress.preparingOutput"))

            # 计算输出尺寸
            out_width = width * self.config.scale
            out_height = height * self.config.scale

            # 创建临时输出文件（不含音频）
            temp_dir = tempfile.gettempdir()
            temp_video = os.path.join(temp_dir, f"enhanced_{os.getpid()}.mp4")

            # 使用 OpenCV VideoWriter
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            out = cv2.VideoWriter(temp_video, fourcc, fps, (out_width, out_height))
            if not out.isOpened():
                cap.release()
                raise ProcessingError(
                    message=t("error.cannotCreateOutputVideo", path=temp_video),
                    context={"temp_video": temp_video},
                )

            # 阶段3: 处理帧 (10-90%)
            progress.update(10, t("progress.loadingEnhancementModel"))

            # 预加载增强器
            sr_enhancer = self._get_sr_enhancer()
            denoiser = self._get_denoiser()
            temporal_smoother = self._get_temporal_smoother()

            log_info(f"设备信息: {sr_enhancer.get_device_info()}")
            log_info(f"批处理大小: {self.config.batch_size}")

            try:
                frame_idx = 0
                batch_size = self.config.batch_size
                # 帧缓冲区：存储 (原始帧, 增强后的帧)
                frame_buffer: List[Tuple[np.ndarray, np.ndarray]] = []

                # 性能统计
                frame_times: List[float] = []
                process_start_time = time.time()

                while True:
                    ret, frame = cap.read()
                    if not ret:
                        break

                    # 检查取消
                    if progress.is_cancelled():
                        log_info("用户取消视频增强")
                        break

                    frame_buffer.append((frame.copy(), None))

                    # 缓冲区满时批量处理
                    if len(frame_buffer) >= batch_size:
                        frame_start = time.time()

                        # 批量去噪
                        if denoiser is not None:
                            frames_to_denoise = [f[0] for f in frame_buffer]
                            denoised_frames = denoiser.enhance_batch(
                                frames_to_denoise, batch_size=batch_size
                            )
                        else:
                            denoised_frames = [f[0] for f in frame_buffer]

                        # 批量超分辨率
                        enhanced_frames = sr_enhancer.enhance_batch(
                            denoised_frames, batch_size=batch_size
                        )

                        # 更新缓冲区中的增强帧
                        for i, enhanced in enumerate(enhanced_frames):
                            frame_buffer[i] = (frame_buffer[i][0], enhanced)

                        # 逐帧写入（时序平滑需要原始帧）
                        for orig, enhanced in frame_buffer:
                            if temporal_smoother is not None:
                                output_frame = temporal_smoother.add_frame(orig, enhanced)
                                if output_frame is not None:
                                    out.write(output_frame)
                            else:
                                out.write(enhanced)

                        frame_buffer.clear()

                        # 性能日志
                        frame_time = time.time() - frame_start
                        frame_times.append(frame_time)
                        if len(frame_times) >= 10:
                            avg_time = sum(frame_times[-10:]) / 10
                            remaining_frames = total_frames - frame_idx - batch_size
                            eta_seconds = remaining_frames * avg_time / batch_size
                            eta_minutes = eta_seconds / 60
                            log_info(
                                f"Frame {frame_idx + batch_size}/{total_frames}: "
                                f"{frame_time:.2f}s/batch, ETA: {eta_minutes:.1f}min"
                            )

                    # 更新进度
                    frame_idx += 1
                    frame_progress = 10 + (frame_idx / total_frames) * 80
                    progress.update(
                        frame_progress,
                        t("progress.processingFrames", current=frame_idx, total=total_frames),
                    )

                # 处理缓冲区剩余帧
                if frame_buffer and not progress.is_cancelled():
                    frame_start = time.time()

                    # 批量去噪
                    if denoiser is not None:
                        frames_to_denoise = [f[0] for f in frame_buffer]
                        denoised_frames = denoiser.enhance_batch(
                            frames_to_denoise, batch_size=len(frames_to_denoise)
                        )
                    else:
                        denoised_frames = [f[0] for f in frame_buffer]

                    # 批量超分辨率
                    enhanced_frames = sr_enhancer.enhance_batch(
                        denoised_frames, batch_size=len(denoised_frames)
                    )

                    # 更新缓冲区中的增强帧
                    for i, enhanced in enumerate(enhanced_frames):
                        frame_buffer[i] = (frame_buffer[i][0], enhanced)

                    # 逐帧写入
                    for orig, enhanced in frame_buffer:
                        if temporal_smoother is not None:
                            output_frame = temporal_smoother.add_frame(orig, enhanced)
                            if output_frame is not None:
                                out.write(output_frame)
                        else:
                            out.write(enhanced)

                    frame_time = time.time() - frame_start
                    log_info(f"Final batch ({len(frame_buffer)} frames): {frame_time:.2f}s")

                # 刷新时序平滑器剩余帧
                if temporal_smoother is not None and not progress.is_cancelled():
                    remaining_frames = temporal_smoother.flush()
                    for remaining_frame in remaining_frames:
                        out.write(remaining_frame)

                # 输出总耗时
                total_time = time.time() - process_start_time
                avg_frame_time = total_time / total_frames if total_frames > 0 else 0
                log_info(
                    f"处理完成: {total_frames}帧, 总耗时: {total_time:.1f}s, "
                    f"平均: {avg_frame_time:.2f}s/帧"
                )

            finally:
                cap.release()
                out.release()

            if progress.is_cancelled():
                # 清理临时文件
                if os.path.exists(temp_video):
                    os.remove(temp_video)
                raise ProcessingError(
                    message=t("error.userCancelled"),
                    context={"frame_processed": frame_idx},
                )

            # 阶段4: 合并音频 (90-100%)
            progress.update(90, t("progress.mergingAudio"))
            self._merge_audio(video_path, temp_video, output_path)

            # 清理临时文件
            if os.path.exists(temp_video):
                os.remove(temp_video)

            progress.update(100, t("progress.videoEnhancementCompleted"))
            log_step(f"视频增强完成: {output_path}")

            return output_path

    def _process_frame(
        self,
        frame: np.ndarray,
        sr_enhancer: RealESRGANEnhancer,
        denoiser: Optional[Denoiser],
    ) -> np.ndarray:
        """
        处理单帧

        Args:
            frame: 输入帧
            sr_enhancer: 超分辨率增强器
            denoiser: 去噪器

        Returns:
            增强后的帧
        """
        result = frame

        # 1. 去噪（在低分辨率下进行）
        if denoiser is not None:
            result = denoiser.enhance_frame(result)

        # 2. 超分辨率
        result = sr_enhancer.enhance_frame(result)

        return result

    def _merge_audio(
        self,
        source_video: str,
        temp_video: str,
        output_path: str,
    ) -> None:
        """
        合并音频到输出视频

        Args:
            source_video: 源视频路径（包含原始音频）
            temp_video: 临时视频路径（增强后的视频，无音频）
            output_path: 输出视频路径
        """
        try:
            from imageio_ffmpeg import get_ffmpeg_exe
            ffmpeg_exe = get_ffmpeg_exe()
        except ImportError:
            raise ProcessingError(
                message="imageio-ffmpeg 未安装",
                context={"suggestion": "pip install imageio-ffmpeg"},
            )

        # 使用 FFmpeg 合并音频
        cmd = [
            ffmpeg_exe,
            "-i", temp_video,           # 输入: 增强后的视频
            "-i", source_video,         # 输入: 原始视频（提取音频）
            "-c:v", "copy",             # 视频直接复制
            "-c:a", "aac",              # 音频编码为 AAC
            "-map", "0:v:0",            # 使用第一个输入的视频
            "-map", "1:a:0?",           # 使用第二个输入的音频（如果存在）
            "-y",                       # 覆盖输出
            "-loglevel", "error",
            output_path,
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5分钟超时
            )
            if result.returncode != 0:
                log_error(f"FFmpeg 音频合并失败: {result.stderr}")
                # 如果音频合并失败，直接复制视频
                import shutil
                shutil.copy(temp_video, output_path)
                log_info("已保存无音频的视频")
        except subprocess.TimeoutExpired:
            raise ProcessingError(
                message="FFmpeg 音频合并超时",
                context={"temp_video": temp_video, "output_path": output_path},
            )
        except Exception as e:
            log_error(f"音频合并失败: {e}")
            # 如果音频合并失败，直接复制视频
            import shutil
            shutil.copy(temp_video, output_path)
            log_info("已保存无音频的视频")

    def cleanup(self) -> None:
        """清理资源"""
        if self._sr_enhancer is not None:
            self._sr_enhancer.unload_model()
            self._sr_enhancer = None

        if self._denoiser is not None:
            self._denoiser.unload_model()
            self._denoiser = None

        if self._temporal_smoother is not None:
            self._temporal_smoother.reset()
            self._temporal_smoother = None

        log_info("视频增强引擎资源已清理")


def create_enhancement_engine(
    scale: int = 4,
    model_type: str = "general",
    denoise: bool = False,
    denoise_strength: float = 1.0,
    temporal: bool = False,
    temporal_strength: float = 0.5,
    device: Optional[str] = None,
) -> VideoEnhancementEngine:
    """
    创建视频增强引擎的便捷函数

    Args:
        scale: 放大倍数 (2/4)
        model_type: 模型类型 (general/anime)
        denoise: 是否启用去噪
        denoise_strength: 去噪强度 (0.0-1.0)
        temporal: 是否启用时序平滑
        temporal_strength: 时序平滑强度 (0.0-1.0)
        device: 计算设备

    Returns:
        VideoEnhancementEngine 实例
    """
    config = EnhancementConfig(
        scale=scale,
        model_type=model_type,
        denoise=denoise,
        denoise_strength=denoise_strength,
        temporal=temporal,
        temporal_strength=temporal_strength,
        device=device,
    )

    return VideoEnhancementEngine(config)


__all__ = [
    "VideoEnhancementEngine",
    "EnhancementConfig",
    "create_enhancement_engine",
]
