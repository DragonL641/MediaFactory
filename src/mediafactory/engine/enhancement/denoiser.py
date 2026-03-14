"""去噪增强器 - 基于 NAFNet 的图像去噪"""

import cv2
import numpy as np
import torch
from typing import List, Optional

from .base_enhancer import BaseEnhancer, PIXEL_NORMALIZATION_FACTOR, PIXEL_DENORMALIZATION_FACTOR
from mediafactory.logging import log_info


class Denoiser(BaseEnhancer):
    """
    图像去噪增强器

    基于 NAFNet (Nonlinear Activation Free Network) 实现高质量去噪。
    特别适合老视频中的噪点、压缩伪影等问题。
    """

    enhancer_type = "denoise"

    # 默认配置
    DEFAULT_CONFIG = {
        "strength": 1.0,  # 去噪强度 [0, 1]
        "model_name": "NAFNet-GoPro-width64",
    }

    def __init__(
        self,
        strength: float = 1.0,
        model_name: str = "NAFNet-GoPro-width64",
        device: Optional[str] = None,
        half_precision: bool = False,
        **kwargs
    ):
        """
        初始化去噪器

        Args:
            strength: 去噪强度 [0, 1]，1.0 为全强度
            model_name: 使用的 NAFNet 模型名称
            device: 计算设备
            half_precision: 是否使用半精度
        """
        super().__init__(
            device=device,
            half_precision=half_precision,
            strength=strength,
            model_name=model_name,
            **kwargs
        )

        self.strength = max(0.0, min(1.0, strength))
        self.model_name = model_name

    def load_model(self) -> None:
        """加载 NAFNet 模型"""
        try:
            from spandrel import ModelLoader, ImageModelDescriptor
        except ImportError as e:
            raise ImportError(
                "请安装依赖: pip install spandrel\n"
                "或运行: pip install -e '.[ml]'"
            ) from e

        # 获取模型路径（使用统一注册表）
        from mediafactory.models.model_registry import get_model_local_path

        model_path = get_model_local_path(self.model_name)

        if model_path is None or not model_path.exists():
            raise FileNotFoundError(
                f"去噪模型未下载: {self.model_name}\n"
                "请在 Models 页面下载相应的去噪模型"
            )

        # 加载模型
        loader = ModelLoader()
        self._model = loader.load_from_file(str(model_path))

        # 验证是图像模型
        if not isinstance(self._model, ImageModelDescriptor):
            raise RuntimeError(f"加载的模型不是有效的图像模型: {type(self._model)}")

        # 移动到设备
        self._model.to(self.device)
        self._model.eval()

        # 半精度
        if self.half_precision:
            self._model.half()
        else:
            self._model.float()

        self._is_loaded = True
        log_info(f"NAFNet 去噪模型加载成功: {self.model_name}")
        log_info(f"设备: {self.device}, 去噪强度: {self.strength}")

    def enhance_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        对单帧图像进行去噪

        Args:
            frame: BGR 格式的图像帧

        Returns:
            去噪后的 BGR 图像
        """
        if not self._is_loaded:
            self.load_model()

        # BGR -> RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # 转为 tensor: HWC -> 1CHW, 归一化到 [0, 1]
        tensor = torch.from_numpy(rgb_frame).float() / PIXEL_NORMALIZATION_FACTOR
        tensor = tensor.permute(2, 0, 1).unsqueeze(0)  # HWC -> 1CHW
        tensor = tensor.to(self.device)

        if self.half_precision:
            tensor = tensor.half()

        # 推理
        with torch.no_grad():
            output = self._model(tensor)

        # 如果是半精度，转回 float32
        if output.dtype == torch.float16:
            output = output.float()

        # 混合原始图像和去噪结果 (根据强度)
        if self.strength < 1.0:
            output = tensor * (1 - self.strength) + output * self.strength

        # 1CHW -> HWC, 反归一化
        output = output.squeeze(0).permute(1, 2, 0).cpu().numpy()
        output = np.clip(output * PIXEL_DENORMALIZATION_FACTOR, 0, 255).astype(np.uint8)

        # RGB -> BGR
        output = cv2.cvtColor(output, cv2.COLOR_RGB2BGR)

        return output

    def enhance_batch(
        self,
        frames: List[np.ndarray],
        batch_size: Optional[int] = None
    ) -> List[np.ndarray]:
        """
        批量去噪

        Args:
            frames: BGR 格式的图像帧列表
            batch_size: 批处理大小

        Returns:
            去噪后的图像列表
        """
        if not self._is_loaded:
            self.load_model()

        if not frames:
            return []

        if batch_size is None:
            batch_size = 4

        # 检查帧尺寸是否一致
        first_shape = frames[0].shape[:2]
        if not all(f.shape[:2] == first_shape for f in frames):
            return [self.enhance_frame(frame) for frame in frames]

        # 批量处理
        results = []
        height, width = first_shape

        for i in range(0, len(frames), batch_size):
            actual_batch = frames[i:i + batch_size]
            actual_size = len(actual_batch)

            # 准备批量 tensor
            batch_tensor = torch.zeros(
                actual_size, 3, height, width,
                dtype=torch.float16 if self.half_precision else torch.float32,
                device=self.device
            )

            for j, frame in enumerate(actual_batch):
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                batch_tensor[j] = torch.from_numpy(rgb_frame).float().permute(2, 0, 1) / PIXEL_NORMALIZATION_FACTOR

            # 批量推理
            with torch.no_grad():
                output = self._model(batch_tensor)

            if output.dtype == torch.float16:
                output = output.float()

            # 混合
            if self.strength < 1.0:
                output = batch_tensor * (1 - self.strength) + output * self.strength

            # 转换结果
            for j in range(actual_size):
                out_frame = output[j].permute(1, 2, 0).cpu().numpy()
                out_frame = np.clip(out_frame * PIXEL_DENORMALIZATION_FACTOR, 0, 255).astype(np.uint8)
                out_frame = cv2.cvtColor(out_frame, cv2.COLOR_RGB2BGR)
                results.append(out_frame)

        return results
