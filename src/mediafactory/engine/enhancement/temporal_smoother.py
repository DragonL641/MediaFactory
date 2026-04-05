"""时序平滑器

使用光流对齐和加权混合实现视频帧间的时序平滑，
减少增强后的闪烁和不一致性。
"""

from collections import deque
from dataclasses import dataclass
from typing import Deque, List, Optional, Tuple

import cv2
import numpy as np


@dataclass
class TemporalSmootherConfig:
    """时序平滑器配置"""

    # 窗口大小（必须是奇数，默认3：前一帧、当前帧、后一帧）
    window_size: int = 3
    # 混合强度（0.0-1.0，越大平滑效果越强）
    strength: float = 0.5
    # 光流计算分辨率缩放因子（0.25 表示使用 1/4 分辨率计算光流，减少 93.75% 计算量）
    flow_resolution_scale: float = 0.25
    # 光流金字塔尺度
    flow_pyramid_scale: float = 0.5
    # 光流金字塔层数
    flow_levels: int = 3
    # 光流窗口大小
    flow_winsize: int = 15
    # 光流迭代次数
    flow_iterations: int = 3
    # 光流多项式展开邻域大小
    flow_poly_n: int = 5
    # 光流多项式扩展标准差
    flow_poly_sigma: float = 1.2


class TemporalSmoother:
    """时序平滑器

    使用稠密光流进行帧对齐，然后进行高斯加权混合。
    支持延迟处理以获取前后帧信息。
    """

    def __init__(self, config: Optional[TemporalSmootherConfig] = None):
        """
        初始化时序平滑器

        Args:
            config: 平滑器配置，如果为 None 则使用默认配置
        """
        self.config = config or TemporalSmootherConfig()
        self._validate_config()

        # 帧缓冲区：存储 (原始帧, 增强帧, 低分辨率灰度帧)
        self._buffer: Deque[Tuple[np.ndarray, np.ndarray, np.ndarray]] = deque(
            maxlen=self.config.window_size
        )
        # 延迟输出的帧队列
        self._pending_frames: Deque[np.ndarray] = deque()

        # 高斯权重（预计算）
        self._weights = self._compute_gaussian_weights()

    def _validate_config(self) -> None:
        """验证配置参数"""
        if self.config.window_size < 3:
            raise ValueError("窗口大小必须至少为3")
        if self.config.window_size % 2 == 0:
            raise ValueError("窗口大小必须是奇数")
        if not 0.0 <= self.config.strength <= 1.0:
            raise ValueError("混合强度必须在0.0到1.0之间")

    def _compute_gaussian_weights(self) -> np.ndarray:
        """计算高斯权重"""
        window_size = self.config.window_size
        center = window_size // 2

        # 创建高斯权重
        weights = np.zeros(window_size, dtype=np.float32)
        sigma = center / 2.0 if center > 0 else 1.0

        for i in range(window_size):
            weights[i] = np.exp(-((i - center) ** 2) / (2 * sigma**2))

        # 归一化
        weights /= weights.sum()
        return weights

    def _compute_optical_flow(
        self,
        prev_gray: np.ndarray,
        curr_gray: np.ndarray,
    ) -> np.ndarray:
        """
        计算两帧之间的稠密光流

        Args:
            prev_gray: 前一帧灰度图
            curr_gray: 当前帧灰度图

        Returns:
            光流场 (H, W, 2)
        """
        flow = cv2.calcOpticalFlowFarneback(
            prev_gray,
            curr_gray,
            None,
            pyr_scale=self.config.flow_pyramid_scale,
            levels=self.config.flow_levels,
            winsize=self.config.flow_winsize,
            iterations=self.config.flow_iterations,
            poly_n=self.config.flow_poly_n,
            poly_sigma=self.config.flow_poly_sigma,
            flags=0,
        )
        return flow

    def _warp_frame(
        self,
        frame: np.ndarray,
        flow: np.ndarray,
    ) -> np.ndarray:
        """
        使用光流对帧进行变形

        Args:
            frame: 输入帧（增强后的高分辨率帧）
            flow: 光流场（基于原始帧计算）

        Returns:
            变形后的帧
        """
        h, w = frame.shape[:2]
        flow_h, flow_w = flow.shape[:2]

        # 检测尺寸不匹配并缩放光流场
        # 当启用超分辨率增强时，光流基于原始帧计算，但需要对增强后的高分辨率帧进行变形
        if flow_h != h or flow_w != w:
            scale_y = h / flow_h
            scale_x = w / flow_w
            # 缩放光流向量的幅度（光流值表示像素位移，需要按比例缩放）
            flow = flow * np.array([scale_x, scale_y], dtype=np.float32)
            # 缩放光流场的分辨率以匹配目标帧
            flow = cv2.resize(flow, (w, h), interpolation=cv2.INTER_LINEAR)

        # 创建坐标网格
        y, x = np.mgrid[0:h, 0:w].astype(np.float32)

        # 应用光流
        new_x = x + flow[..., 0]
        new_y = y + flow[..., 1]

        # 边界处理
        new_x = np.clip(new_x, 0, w - 1)
        new_y = np.clip(new_y, 0, h - 1)

        # 使用双线性插值进行重采样
        if len(frame.shape) == 3:
            # 彩色图像，逐通道处理
            result = np.zeros_like(frame)
            for c in range(frame.shape[2]):
                result[..., c] = cv2.remap(
                    frame[..., c],
                    new_x,
                    new_y,
                    cv2.INTER_LINEAR,
                    borderMode=cv2.BORDER_REPLICATE,
                )
        else:
            # 灰度图像
            result = cv2.remap(
                frame,
                new_x,
                new_y,
                cv2.INTER_LINEAR,
                borderMode=cv2.BORDER_REPLICATE,
            )

        return result

    def _blend_frames(
        self,
        frames: List[np.ndarray],
    ) -> np.ndarray:
        """
        使用高斯权重混合多帧

        Args:
            frames: 帧列表（已对齐到目标帧）

        Returns:
            混合后的帧
        """
        if len(frames) == 1:
            return frames[0]

        # 获取权重
        n = len(frames)
        center = n // 2

        # 从预计算的权重中提取对应部分
        if n == self.config.window_size:
            weights = self._weights
        else:
            # 动态计算权重（处理边界情况）
            weights = np.zeros(n, dtype=np.float32)
            sigma = center / 2.0 if center > 0 else 1.0
            for i in range(n):
                weights[i] = np.exp(-((i - center) ** 2) / (2 * sigma**2))
            weights /= weights.sum()

        # 根据混合强度调整权重
        # strength=0 时只有中心帧，strength=1 时完全混合
        adjusted_weights = np.copy(weights)
        adjusted_weights[center] += (1 - adjusted_weights[center]) * (
            1 - self.config.strength
        )
        # 重新归一化
        adjusted_weights /= adjusted_weights.sum()

        # 加权混合
        result = np.zeros_like(frames[0], dtype=np.float32)
        for frame, weight in zip(frames, adjusted_weights):
            result += frame.astype(np.float32) * weight

        return np.clip(result, 0, 255).astype(np.uint8)

    def add_frame(
        self,
        original_frame: np.ndarray,
        enhanced_frame: np.ndarray,
    ) -> Optional[np.ndarray]:
        """
        添加一帧并尝试输出平滑后的帧

        由于时序平滑需要前后帧信息，输出会有延迟。
        当缓冲区未满时返回 None。

        Args:
            original_frame: 原始帧（用于计算光流）
            enhanced_frame: 增强后的帧（用于混合）

        Returns:
            平滑后的帧，如果缓冲区未满则返回 None
        """
        # 转换为灰度图用于光流计算
        if len(original_frame.shape) == 3:
            gray = cv2.cvtColor(original_frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = original_frame.copy()

        # 缩小到低分辨率用于光流计算（大幅减少计算量）
        if self.config.flow_resolution_scale < 1.0:
            flow_gray = cv2.resize(
                gray,
                None,
                fx=self.config.flow_resolution_scale,
                fy=self.config.flow_resolution_scale,
                interpolation=cv2.INTER_AREA,
            )
        else:
            flow_gray = gray

        # 添加到缓冲区
        self._buffer.append(
            (
                original_frame.copy(),
                enhanced_frame.copy(),
                flow_gray,
            )
        )

        # 缓冲区未满，延迟输出
        half_window = self.config.window_size // 2
        if len(self._buffer) < self.config.window_size:
            return None

        # 缓冲区已满，处理中间帧
        return self._process_center_frame()

    def _process_center_frame(self) -> np.ndarray:
        """处理缓冲区中间的帧"""
        half_window = self.config.window_size // 2

        # 获取所有帧
        frames = list(self._buffer)
        center_idx = half_window

        # 获取中心帧的增强结果
        _, center_enhanced, center_gray = frames[center_idx]

        # 如果混合强度为0，直接返回中心帧
        if self.config.strength <= 0:
            return center_enhanced

        # 对齐所有帧到中心帧
        aligned_frames: List[np.ndarray] = []

        for i, (_, enhanced, gray) in enumerate(frames):
            if i == center_idx:
                # 中心帧不需要对齐
                aligned_frames.append(enhanced)
            else:
                # 计算从当前帧到中心帧的光流
                if i < center_idx:
                    # 前向光流：从前一帧到后一帧
                    flow = self._compute_optical_flow(gray, center_gray)
                else:
                    # 后向光流：从后一帧到前一帧
                    flow = self._compute_optical_flow(gray, center_gray)

                # 使用光流对齐增强帧
                aligned = self._warp_frame(enhanced, flow)
                aligned_frames.append(aligned)

        # 混合对齐后的帧
        result = self._blend_frames(aligned_frames)

        # 移除最旧的帧（滑动窗口）
        self._buffer.popleft()

        return result

    def flush(self) -> List[np.ndarray]:
        """
        刷新缓冲区，返回所有剩余的帧

        在处理完所有帧后调用，以获取最后几帧的结果。

        Returns:
            剩余帧的平滑结果列表
        """
        results: List[np.ndarray] = []

        while len(self._buffer) > 0:
            if len(self._buffer) == 1:
                # 最后一帧，直接输出
                _, enhanced, _ = self._buffer.popleft()
                results.append(enhanced)
            elif len(self._buffer) == 2:
                # 剩余两帧，简单平均
                frames = list(self._buffer)
                result = cv2.addWeighted(
                    frames[0][1],
                    0.5,
                    frames[1][1],
                    0.5,
                    0,
                )
                results.append(result)
                self._buffer.clear()
            else:
                # 处理中间帧
                result = self._process_center_frame()
                results.append(result)

        return results

    def reset(self) -> None:
        """重置平滑器状态"""
        self._buffer.clear()
        self._pending_frames.clear()

    @property
    def delay(self) -> int:
        """输出延迟（帧数）"""
        return self.config.window_size // 2

    @property
    def buffer_size(self) -> int:
        """当前缓冲区大小"""
        return len(self._buffer)


def smooth_video_frames(
    frames: List[np.ndarray],
    original_frames: Optional[List[np.ndarray]] = None,
    strength: float = 0.5,
    window_size: int = 3,
) -> List[np.ndarray]:
    """
    对视频帧序列进行时序平滑的便捷函数

    Args:
        frames: 增强后的帧列表
        original_frames: 原始帧列表（用于光流计算），如果为 None 则使用 frames
        strength: 混合强度
        window_size: 窗口大小

    Returns:
        平滑后的帧列表
    """
    if original_frames is None:
        original_frames = frames

    if len(frames) != len(original_frames):
        raise ValueError("帧列表长度不匹配")

    config = TemporalSmootherConfig(
        window_size=window_size,
        strength=strength,
    )
    smoother = TemporalSmoother(config)

    results: List[np.ndarray] = []

    for original, enhanced in zip(original_frames, frames):
        result = smoother.add_frame(original, enhanced)
        if result is not None:
            results.append(result)

    # 刷新剩余帧
    results.extend(smoother.flush())

    return results


__all__ = [
    "TemporalSmoother",
    "TemporalSmootherConfig",
    "smooth_video_frames",
]
