"""Real-ESRGAN 增强器 - 超分辨率增强"""

import cv2
import numpy as np
import torch
from typing import List, Optional, Tuple

from .base_enhancer import BaseEnhancer, PIXEL_NORMALIZATION_FACTOR, PIXEL_DENORMALIZATION_FACTOR
from mediafactory.logging import log_info

# 分块处理常量（此类特有）
DEFAULT_TILE_PAD = 10
DEFAULT_PRE_PAD = 10


class RealESRGANEnhancer(BaseEnhancer):
    """
    Real-ESRGAN 超分辨率增强器

    基于 spandrel 库加载和推理 Real-ESRGAN 模型。
    """

    enhancer_type = "super_resolution"

    # 默认配置
    DEFAULT_CONFIG = {
        "scale": 4,
        "model_type": "general",
        "tile": 0,
        "tile_pad": DEFAULT_TILE_PAD,
        "pre_pad": DEFAULT_PRE_PAD,
    }

    # 默认批处理大小
    DEFAULT_BATCH_SIZE = 4

    def __init__(
        self,
        scale: int = 4,
        model_type: str = "general",
        device: Optional[str] = None,
        half_precision: bool = False,
        tile: int = 0,
        tile_pad: int = DEFAULT_TILE_PAD,
        pre_pad: int = DEFAULT_PRE_PAD,
        **kwargs
    ):
        """
        初始化 Real-ESRGAN 增强器

        Args:
            scale: 放大倍数 (2 或 4)
            model_type: 模型类型 ('general' 或 'anime')
            device: 计算设备
            half_precision: 是否使用半精度
            tile: 分块大小，0 表示不分块
            tile_pad: 分块填充
            pre_pad: 预填充
        """
        super().__init__(
            device=device,
            half_precision=half_precision,
            scale=scale,
            model_type=model_type,
            tile=tile,
            tile_pad=tile_pad,
            pre_pad=pre_pad,
            **kwargs
        )

        self.scale = scale
        self.model_type = model_type
        self.tile = tile
        self.tile_pad = tile_pad
        self.pre_pad = pre_pad

        # Tensor 缓存
        self._input_tensor_cache: Optional[torch.Tensor] = None
        self._cached_frame_shape: Optional[Tuple[int, int]] = None

    def load_model(self) -> None:
        """加载 Real-ESRGAN 模型"""
        try:
            from spandrel import ModelLoader, ImageModelDescriptor
        except ImportError as e:
            raise ImportError(
                "请安装依赖: pip install spandrel\n"
                "或运行: pip install -e '.[ml]'"
            ) from e

        # 获取模型路径（使用统一注册表）
        from mediafactory.models.model_registry import (
            get_enhancement_model_by_scale_and_type,
            get_model_local_path,
        )

        model_id = get_enhancement_model_by_scale_and_type(self.scale, self.model_type)
        if model_id is None:
            raise FileNotFoundError(
                f"未找到匹配的模型: scale={self.scale}, type={self.model_type}"
            )
        model_path = get_model_local_path(model_id)

        if model_path is None or not model_path.exists():
            raise FileNotFoundError(
                f"模型未下载: scale={self.scale}, model_type={self.model_type}\n"
                "请在 Models 页面下载相应的增强模型"
            )

        # 加载模型
        loader = ModelLoader()
        self._model = loader.load_from_file(str(model_path))

        # 验证是图像模型
        if not isinstance(self._model, ImageModelDescriptor):
            raise RuntimeError(f"加载的模型不是有效的图像超分辨率模型: {type(self._model)}")

        # 移动到设备
        self._model.to(self.device)
        self._model.evaluation_mode()

        # 半精度
        if self.half_precision:
            self._model.half()
        else:
            self._model.float()

        self._is_loaded = True
        log_info(f"Real-ESRGAN 模型加载成功: scale={self.scale}, type={self.model_type}")
        log_info(f"设备: {self.device}, 半精度: {self.half_precision}")

    def _get_or_create_input_tensor(self, frame: np.ndarray) -> torch.Tensor:
        """获取或创建输入 tensor，使用缓存以减少内存分配"""
        height, width = frame.shape[:2]

        # 检查是否需要重新分配
        if (self._cached_frame_shape != (height, width) or
            self._input_tensor_cache is None):
            # 重新分配缓存
            self._input_tensor_cache = torch.empty(
                1, 3, height, width,
                dtype=torch.float16 if self.half_precision else torch.float32,
                device=self.device
            )
            self._cached_frame_shape = (height, width)

        # BGR -> RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # 直接写入缓存 tensor
        self._input_tensor_cache[0, 0] = torch.from_numpy(rgb_frame[:, :, 0]) / PIXEL_NORMALIZATION_FACTOR
        self._input_tensor_cache[0, 1] = torch.from_numpy(rgb_frame[:, :, 1]) / PIXEL_NORMALIZATION_FACTOR
        self._input_tensor_cache[0, 2] = torch.from_numpy(rgb_frame[:, :, 2]) / PIXEL_NORMALIZATION_FACTOR

        return self._input_tensor_cache

    def enhance_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        增强单帧图像

        Args:
            frame: BGR 格式的图像帧

        Returns:
            增强后的 BGR 图像
        """
        if not self._is_loaded:
            self.load_model()

        # 使用缓存的 tensor
        tensor = self._get_or_create_input_tensor(frame)

        # 推理
        with torch.no_grad():
            if self.tile > 0:
                output = self._tile_process(tensor)
            else:
                output = self._model(tensor)

        # 移除 batch 维度: 1CHW -> CHW
        output = output.squeeze(0)

        # 如果是半精度，转回 float32
        if output.dtype == torch.float16:
            output = output.float()

        # CHW -> HWC, 反归一化到 [0, 255], 转为 uint8
        output = output.permute(1, 2, 0).cpu().numpy()
        output = np.clip(output * PIXEL_DENORMALIZATION_FACTOR, 0, 255).astype(np.uint8)

        # RGB -> BGR
        output = cv2.cvtColor(output, cv2.COLOR_RGB2BGR)

        return output

    def _tile_process(self, tensor: torch.Tensor) -> torch.Tensor:
        """分块处理大图像"""
        _, C, H, W = tensor.shape
        tile_size = self.tile
        tile_pad = self.tile_pad

        if H <= tile_size and W <= tile_size:
            return self._model(tensor)

        out_H = H * self.scale
        out_W = W * self.scale
        output = torch.zeros(1, C, out_H, out_W, dtype=tensor.dtype, device=self.device)

        tiles_y = (H - 1) // (tile_size - tile_pad) + 1
        tiles_x = (W - 1) // (tile_size - tile_pad) + 1

        for y in range(tiles_y):
            for x in range(tiles_x):
                y_start = y * (tile_size - tile_pad)
                x_start = x * (tile_size - tile_pad)
                y_end = min(y_start + tile_size, H)
                x_end = min(x_start + tile_size, W)

                tile = tensor[:, :, y_start:y_end, x_start:x_end]
                tile_output = self._model(tile)

                out_y_start = y_start * self.scale
                out_x_start = x_start * self.scale
                out_y_end = y_end * self.scale
                out_x_end = x_end * self.scale

                pad_y = min(tile_pad, y_start) if y > 0 else 0
                pad_x = min(tile_pad, x_start) if x > 0 else 0
                pad_y_end = min(tile_pad, H - y_end) if y < tiles_y - 1 else 0
                pad_x_end = min(tile_pad, W - x_end) if x < tiles_x - 1 else 0

                in_y_start = pad_y * self.scale
                in_x_start = pad_x * self.scale
                in_y_end = tile_output.shape[2] - pad_y_end * self.scale
                in_x_end = tile_output.shape[3] - pad_x_end * self.scale

                out_y_start_valid = out_y_start + pad_y * self.scale
                out_x_start_valid = out_x_start + pad_x * self.scale

                output[:, :, out_y_start_valid:out_y_end, out_x_start_valid:out_x_end] = \
                    tile_output[:, :, in_y_start:in_y_end, in_x_start:in_x_end]

        return output

    def enhance_batch(
        self,
        frames: List[np.ndarray],
        batch_size: Optional[int] = None
    ) -> List[np.ndarray]:
        """
        批量增强帧 - 实现真正的批量推理

        Args:
            frames: BGR 格式的图像帧列表
            batch_size: 批处理大小

        Returns:
            增强后的图像列表
        """
        if not self._is_loaded:
            self.load_model()

        if not frames:
            return []

        if batch_size is None:
            batch_size = self.DEFAULT_BATCH_SIZE

        # 如果帧数较少或使用分块处理，退回到逐帧处理
        if len(frames) < batch_size or self.tile > 0:
            return [self.enhance_frame(frame) for frame in frames]

        # 检查所有帧是否具有相同尺寸
        first_shape = frames[0].shape[:2]
        if not all(f.shape[:2] == first_shape for f in frames):
            return [self.enhance_frame(frame) for frame in frames]

        # 真正的批量处理
        results = []
        height, width = first_shape

        # 预分配批量 tensor
        batch_tensor = torch.empty(
            batch_size, 3, height, width,
            dtype=torch.float16 if self.half_precision else torch.float32,
            device=self.device
        )

        for i in range(0, len(frames), batch_size):
            actual_batch_size = min(batch_size, len(frames) - i)
            batch_frames = frames[i:i + actual_batch_size]

            # 准备批量输入
            for j, frame in enumerate(batch_frames):
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                batch_tensor[j, 0] = torch.from_numpy(rgb_frame[:, :, 0]) / PIXEL_NORMALIZATION_FACTOR
                batch_tensor[j, 1] = torch.from_numpy(rgb_frame[:, :, 1]) / PIXEL_NORMALIZATION_FACTOR
                batch_tensor[j, 2] = torch.from_numpy(rgb_frame[:, :, 2]) / PIXEL_NORMALIZATION_FACTOR

            # 只取实际批量大小
            input_tensor = batch_tensor[:actual_batch_size]

            # 批量推理
            with torch.no_grad():
                output = self._model(input_tensor)

            # 处理输出
            if output.dtype == torch.float16:
                output = output.float()

            for j in range(actual_batch_size):
                out_frame = output[j].permute(1, 2, 0).cpu().numpy()
                out_frame = np.clip(out_frame * PIXEL_DENORMALIZATION_FACTOR, 0, 255).astype(np.uint8)
                out_frame = cv2.cvtColor(out_frame, cv2.COLOR_RGB2BGR)
                results.append(out_frame)

        return results

    def unload_model(self) -> None:
        """卸载模型"""
        super().unload_model()
        self._input_tensor_cache = None
        self._cached_frame_shape = None

    def clear_cache(self) -> None:
        """清理 tensor 缓存"""
        self._input_tensor_cache = None
        self._cached_frame_shape = None

        if self.device == "cuda":
            torch.cuda.empty_cache()
