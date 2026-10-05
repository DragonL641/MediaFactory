"""视频增强引擎

提供视频画质增强功能，"""

import os
import shutil
import tempfile
import time
from dataclasses import dataclass

import cv2
import numpy as np

from mediafactory.core.exception_wrapper import wrap_exceptions
from mediafactory.core.progress_protocol import NO_OP_PROGRESS, ProgressCallback
from mediafactory.engine.deinterlace import pre_deinterlace
from mediafactory.engine.enhancement import (
    Denoiser,
    FaceRestoreManager,
    RealESRGANEnhancer,
    TemporalSmoother,
    TemporalSmootherConfig,
)
from mediafactory.engine.ffmpeg_runner import CancelledError, run_ffmpeg_cancellable
from mediafactory.exceptions import ProcessingError
from mediafactory.i18n import t
from mediafactory.logging import log_error, log_info, log_step

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

    # 人脸修复参数（老片增强 P0）
    face_restore: bool = False
    face_fidelity_weight: float = 0.7  # 官方默认保真度，不暴露 UI

    # 胶片颗粒（老片增强 P0）
    film_grain: bool = False

    # 设备配置
    device: str | None = None  # cuda, mps, cpu, None=auto
    half_precision: bool = True  # 默认启用半精度以提升性能

    # 处理参数
    tile_size: int = 512  # 默认启用分块处理以减少显存压力

    # 批处理参数
    batch_size: int = DEFAULT_BATCH_SIZE  # 批处理帧数


class VideoEnhancementEngine:
    """视频增强引擎"""

    def __init__(self, config: EnhancementConfig | None = None):
        """
        初始化视频增强引擎

        Args:
            config: 增强配置，如果为 None 则使用默认配置
        """
        self.config = config or EnhancementConfig()

        # 增强器实例（懒加载）
        self._sr_enhancer: RealESRGANEnhancer | None = None
        self._denoiser: Denoiser | None = None
        self._temporal_smoother: TemporalSmoother | None = None
        self._face_restorer: FaceRestoreManager | None = None

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

    def _get_denoiser(self) -> Denoiser | None:
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

    def _get_temporal_smoother(self) -> TemporalSmoother | None:
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

    def _get_face_restorer(self) -> FaceRestoreManager | None:
        """获取人脸修复器（懒加载）"""
        if not self.config.face_restore:
            return None
        if self._face_restorer is None:
            self._face_restorer = FaceRestoreManager(
                device=self.config.device,
                fidelity_weight=self.config.face_fidelity_weight,
            )
        return self._face_restorer

    def enhance(
        self,
        video_path: str,
        output_path: str | None = None,
        progress: ProgressCallback | None = None,
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
            output_path = os.path.join(
                video_dir, f"{video_basename}_enhanced{video_ext}"
            )
        output_path = os.path.abspath(output_path)

        # 守卫：输出与输入同路径会让 FFmpeg -y 边读边截断源文件（源片永久损毁）
        if output_path == video_path:
            raise ProcessingError(
                message="Output path must differ from the input video path",
                context={"video_path": video_path},
            )

        with wrap_exceptions(
            context={
                "video_path": video_path,
                "output_path": output_path,
                "config": self.config,
            },
            operation="video_enhancement",
        ):
            log_step(f"开始视频增强: {video_path}")
            log_info(
                f"配置: scale={self.config.scale}, model_type={self.config.model_type}"
            )

            # 阶段0: deinterlace 前置 (0-9%)
            progress.update(0, t("progress.checkingInterlace"))
            original_path = video_path  # 音轨等元数据始终从原始源取
            effective_path = pre_deinterlace(video_path, progress)
            _deint_dir: str | None = (
                os.path.dirname(effective_path)
                if effective_path != video_path
                else None
            )
            temp_video: str | None = None
            try:
                # 前置 pass 内取消已在 run_ffmpeg_cancellable 响应；此处兜底复查
                if progress.is_cancelled():
                    raise ProcessingError(
                        message=t("error.userCancelled"),
                        context={"stage": "pre_deinterlace"},
                    )
                video_path = effective_path
                if _deint_dir is not None:
                    log_info(f"使用去隔行中间产物: {video_path}")

                # 阶段1: 读取视频 (9-10%)
                progress.update(9, t("progress.readingVideo"))
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

                # 坏元数据守卫：frames/fps 读不到时，后续要么除零崩溃、要么
                # 写出空文件经兜底 copy 变"假成功"（产物不可播放）
                if total_frames <= 0 or fps <= 0:
                    cap.release()
                    raise ProcessingError(
                        message=(
                            f"Video metadata unreadable (frames={total_frames}, "
                            f"fps={fps}). The file may be corrupted or use an "
                            "unsupported container."
                        ),
                        context={"video_path": video_path},
                    )

                log_info(f"视频信息: {width}x{height}, {fps}fps, {total_frames}帧")

                # 阶段2: 准备输出 (10-11%)
                progress.update(10, t("progress.preparingOutput"))

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

                # 阶段3: 处理帧 (11-90%)
                progress.update(11, t("progress.loadingEnhancementModel"))

                try:
                    # 预加载增强器（try 内：加载抛错时 cap/out 由 finally 释放）
                    sr_enhancer = self._get_sr_enhancer()
                    self._get_denoiser()
                    temporal_smoother = self._get_temporal_smoother()
                    self._get_face_restorer()

                    log_info(f"设备信息: {sr_enhancer.get_device_info()}")
                    log_info(f"批处理大小: {self.config.batch_size}")
                    frame_idx = 0
                    batch_size = self.config.batch_size
                    # 帧缓冲区：存储 (原始帧, 增强后的帧)
                    frame_buffer: list[tuple[np.ndarray, np.ndarray]] = []

                    # 性能统计
                    frame_times: list[float] = []
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
                            self._process_and_write(frame_buffer, batch_size, out)

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
                        frame_progress = 11 + (frame_idx / total_frames) * 79
                        progress.update(
                            frame_progress,
                            t(
                                "progress.processingFrames",
                                current=frame_idx,
                                total=total_frames,
                            ),
                        )

                    # 处理缓冲区剩余帧
                    if frame_buffer and not progress.is_cancelled():
                        frame_start = time.time()
                        self._process_and_write(frame_buffer, len(frame_buffer), out)

                        frame_time = time.time() - frame_start
                        log_info(
                            f"Final batch ({len(frame_buffer)} frames): {frame_time:.2f}s"
                        )

                    # 刷新时序平滑器剩余帧
                    if temporal_smoother is not None and not progress.is_cancelled():
                        remaining_frames = temporal_smoother.flush()
                        for remaining_frame in remaining_frames:
                            out.write(remaining_frame)

                    # 输出总耗时
                    total_time = time.time() - process_start_time
                    avg_frame_time = (
                        total_time / total_frames if total_frames > 0 else 0
                    )
                    log_info(
                        f"处理完成: {total_frames}帧, 总耗时: {total_time:.1f}s, "
                        f"平均: {avg_frame_time:.2f}s/帧"
                    )

                finally:
                    cap.release()
                    out.release()

                if progress.is_cancelled():
                    raise ProcessingError(
                        message=t("error.userCancelled"),
                        context={"frame_processed": frame_idx},
                    )

                # 阶段4: 合并音频 (90-100%)——音轨从原始源取（deint 中间产物 -an 无音轨）
                progress.update(90, t("progress.mergingAudio"))
                try:
                    self._merge_audio(
                        original_path,
                        temp_video,
                        output_path,
                        film_grain=self.config.film_grain,
                        progress=progress,
                    )
                except CancelledError:
                    # 合并被用户取消：产物不落盘
                    if os.path.exists(output_path):
                        os.remove(output_path)
                    raise ProcessingError(
                        message=t("error.userCancelled"),
                        context={"stage": "merge"},
                    ) from None

                # 合并完成后取消复查：宁可丢弃成品也不让已取消任务产出文件
                if progress.is_cancelled():
                    if os.path.exists(output_path):
                        os.remove(output_path)
                    raise ProcessingError(
                        message=t("error.userCancelled"),
                        context={"stage": "post_merge"},
                    )

                progress.update(100, t("progress.videoEnhancementCompleted"))
                log_step(f"视频增强完成: {output_path}")

                return output_path
            finally:
                # 统一收口：任何失败/取消/成功路径都不留 GB 级半成品
                if temp_video is not None and os.path.exists(temp_video):
                    os.remove(temp_video)
                if _deint_dir is not None:
                    shutil.rmtree(_deint_dir, ignore_errors=True)

    def _process_and_write(
        self,
        frame_buffer: list[tuple[np.ndarray, np.ndarray]],
        batch_size: int,
        out: cv2.VideoWriter,
    ) -> None:
        """缓冲区批处理管线：去噪→超分→人脸修复→时序平滑写出（就地清空 buffer）。

        主循环与尾批共用（此前两处近逐行复制，P0 加人脸修复时被迫改两处）。
        """
        denoiser = self._denoiser
        sr_enhancer = self._sr_enhancer
        temporal_smoother = self._temporal_smoother
        face_restorer = self._face_restorer

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

        # 批量人脸修复（超分之后、时序平滑之前，spec §3.2）
        if face_restorer is not None:
            enhanced_frames, _faced = face_restorer.restore_batch(enhanced_frames)

        # 逐帧写入（时序平滑需要原始帧）
        for (orig, _), enhanced in zip(frame_buffer, enhanced_frames):
            if temporal_smoother is not None:
                output_frame = temporal_smoother.add_frame(orig, enhanced)
                if output_frame is not None:
                    out.write(output_frame)
            else:
                out.write(enhanced)
        frame_buffer.clear()

    def _build_merge_cmd(
        self, source_video: str, temp_video: str, output_path: str, film_grain: bool
    ) -> tuple[list[str], int]:
        """构造音视频合成命令。

        grain 开：视频重编码加噪点滤镜（加在修干净的成品上，spec §3.3）。
        返回 (完整命令, 超时秒数)——重编码长视频，超时放宽到 3600s。
        """
        from imageio_ffmpeg import get_ffmpeg_exe

        ffmpeg_exe = get_ffmpeg_exe()
        inputs = ["-i", temp_video, "-i", source_video]
        base = [
            "-map",
            "0:v:0",  # 使用第一个输入的视频
            "-map",
            "1:a:0?",  # 使用第二个输入的音频（如果存在）
            "-c:a",
            "aac",  # 音频编码为 AAC
            "-y",  # 覆盖输出
            "-loglevel",
            "error",
        ]
        if film_grain:
            video_opts = [
                "-vf",
                "noise=alls=7:allf=t",
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-crf",
                "18",
            ]
            timeout = 3600
        else:
            video_opts = ["-c:v", "copy"]  # 视频直接复制
            timeout = 300
        cmd = [ffmpeg_exe] + inputs + video_opts + base + [output_path]
        return cmd, timeout

    def _merge_audio(
        self,
        source_video: str,
        temp_video: str,
        output_path: str,
        film_grain: bool = False,
        progress: ProgressCallback | None = None,
    ) -> None:
        """
        合并音频到输出视频（film_grain 开时顺带完成重编码加噪点）

        Args:
            source_video: 源视频路径（包含原始音频）
            temp_video: 临时视频路径（增强后的视频，无音频）
            output_path: 输出视频路径
            film_grain: 是否加胶片颗粒（触发视频重编码）
            progress: 进度句柄（FFmpeg 长阻塞段内响应取消）
        """
        try:
            from imageio_ffmpeg import get_ffmpeg_exe

            get_ffmpeg_exe()
        except ImportError as e:
            raise ProcessingError(
                message="imageio-ffmpeg 未安装",
                context={"suggestion": "pip install imageio-ffmpeg"},
            ) from e

        cmd, timeout = self._build_merge_cmd(
            source_video, temp_video, output_path, film_grain
        )

        result = run_ffmpeg_cancellable(cmd, progress=progress, timeout=timeout)
        if result.returncode != 0 and film_grain:
            # grain 重编码失败：降级为无 grain 合并（音轨仍从源取），非裸 copy
            log_error(f"Film grain 重编码失败，降级为无 grain 合并: {result.stderr}")
            plain_cmd, plain_timeout = self._build_merge_cmd(
                source_video, temp_video, output_path, film_grain=False
            )
            plain = run_ffmpeg_cancellable(
                plain_cmd, progress=progress, timeout=plain_timeout
            )
            if plain.returncode != 0:
                log_error(f"FFmpeg 音频合并失败: {plain.stderr}")
                self._copy_without_audio(temp_video, output_path)
            return
        if result.returncode != 0:
            log_error(f"FFmpeg 音频合并失败: {result.stderr}")
            self._copy_without_audio(temp_video, output_path)

    @staticmethod
    def _copy_without_audio(temp_video: str, output_path: str) -> None:
        """最后兜底：直接复制增强后的视频（丢音轨，任务仍成功）"""
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

        if self._face_restorer is not None:
            self._face_restorer.cleanup()
            self._face_restorer = None

        log_info("视频增强引擎资源已清理")


__all__ = [
    "VideoEnhancementEngine",
    "EnhancementConfig",
]
