"""增强器基础接口 - 定义所有增强器的统一接口"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import numpy as np
import torch

from mediafactory.logging import log_info


# 像素归一化常量（供所有增强器使用）
PIXEL_NORMALIZATION_FACTOR = 255.0
PIXEL_DENORMALIZATION_FACTOR = 255.0


class BaseEnhancer(ABC):
    """
    增强器抽象基类

    所有增强器 (超分、去噪、人脸修复等) 都应继承此类并实现相应方法。
    """

    # 增强器类型标识
    enhancer_type: str = "base"

    # 默认配置
    DEFAULT_CONFIG: Dict[str, Any] = {}

    def __init__(
        self, device: Optional[str] = None, half_precision: bool = False, **kwargs
    ):
        """
        初始化增强器

        Args:
            device: 计算设备 ('cuda', 'mps', 'cpu', None 为自动检测)
            half_precision: 是否使用半精度 (FP16)
            **kwargs: 额外配置参数
        """
        self.device = self._detect_device(device)
        self.half_precision = half_precision and self.device == "cuda"
        self.config = {**self.DEFAULT_CONFIG, **kwargs}
        self._model = None
        self._is_loaded = False

    def _detect_device(self, device: Optional[str]) -> str:
        """检测并返回最佳计算设备"""
        if device:
            if device == "cuda" and torch.cuda.is_available():
                return "cuda"
            elif (
                device == "mps"
                and hasattr(torch.backends, "mps")
                and torch.backends.mps.is_available()
            ):
                return "mps"
            elif device == "cpu":
                return "cpu"

        # 自动检测
        if torch.cuda.is_available():
            return "cuda"
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
        return "cpu"

    @abstractmethod
    def load_model(self) -> None:
        """
        加载模型

        子类必须实现此方法来加载具体的模型。
        加载完成后应设置 self._model 和 self._is_loaded = True
        """
        pass

    @abstractmethod
    def enhance_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        增强单帧图像

        Args:
            frame: BGR 格式的图像帧 (OpenCV 格式)

        Returns:
            增强后的 BGR 图像
        """
        pass

    def enhance_batch(
        self, frames: List[np.ndarray], batch_size: Optional[int] = None
    ) -> List[np.ndarray]:
        """
        批量增强帧

        默认实现为逐帧处理。子类可以重写此方法以实现真正的批量推理。

        Args:
            frames: BGR 格式的图像帧列表
            batch_size: 批处理大小

        Returns:
            增强后的图像列表
        """
        return [self.enhance_frame(frame) for frame in frames]

    def unload_model(self) -> None:
        """
        卸载模型以释放显存

        子类可以重写此方法来实现自定义的卸载逻辑。
        """
        self._model = None
        self._is_loaded = False

        if self.device == "cuda":
            torch.cuda.empty_cache()

    def is_loaded(self) -> bool:
        """检查模型是否已加载"""
        return self._is_loaded

    def get_device_info(self) -> str:
        """获取设备信息字符串"""
        info = f"Device: {self.device.upper()}"

        if self.device == "cuda":
            info += f" ({torch.cuda.get_device_name(0)})"
            if self.half_precision:
                info += " [FP16]"
        elif self.device == "mps":
            info += " (Apple Silicon)"

        return info

    def get_memory_usage(self) -> Optional[Dict[str, float]]:
        """
        获取显存使用情况 (仅 CUDA)

        Returns:
            包含显存信息的字典，或 None (非 CUDA 设备)
        """
        if self.device != "cuda":
            return None

        return {
            "allocated": torch.cuda.memory_allocated() / 1024**3,  # GB
            "reserved": torch.cuda.memory_reserved() / 1024**3,  # GB
            "max_allocated": torch.cuda.max_memory_allocated() / 1024**3,  # GB
        }

    def __enter__(self):
        """上下文管理器入口"""
        if not self.is_loaded():
            self.load_model()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.unload_model()
        return False
