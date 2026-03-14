"""人脸修复增强器 - 基于 CodeFormer 的人脸修复"""

import cv2
import numpy as np
import torch
from typing import List, Optional, Tuple
from dataclasses import dataclass

from .base_enhancer import BaseEnhancer, PIXEL_NORMALIZATION_FACTOR, PIXEL_DENORMALIZATION_FACTOR
from mediafactory.logging import log_info, log_warning


@dataclass
class FaceInfo:
    """人脸信息"""
    bbox: List[int]  # [x1, y1, x2, y2]
    score: float
    landmarks: Optional[np.ndarray] = None


class FaceEnhancer(BaseEnhancer):
    """
    人脸修复增强器

    基于 CodeFormer 实现高质量人脸修复。
    自动检测人脸并仅对检测到的人脸区域进行修复。
    """

    enhancer_type = "face_restore"

    # 默认配置
    DEFAULT_CONFIG = {
        "fidelity": 0.5,  # 保真度 [0, 1]，越高越接近原图
        "upscale": 2,     # 人脸放大倍数
        "detection_threshold": 0.5,  # 人脸检测阈值
        "only_center_face": False,   # 仅处理中心人脸
        "model_name": "CodeFormer",
        "detection_model": "RetinaFace-R50",
    }

    def __init__(
        self,
        fidelity: float = 0.5,
        upscale: int = 2,
        detection_threshold: float = 0.5,
        only_center_face: bool = False,
        model_name: str = "CodeFormer",
        detection_model: str = "RetinaFace-R50",
        device: Optional[str] = None,
        half_precision: bool = False,
        **kwargs
    ):
        """
        初始化人脸修复器

        Args:
            fidelity: 保真度 [0, 1]，0 为最强修复，1 为保持原图
            upscale: 人脸放大倍数
            detection_threshold: 人脸检测阈值
            only_center_face: 仅处理最靠近中心的人脸
            model_name: CodeFormer 模型名称
            detection_model: 人脸检测模型名称
            device: 计算设备
            half_precision: 是否使用半精度
        """
        super().__init__(
            device=device,
            half_precision=half_precision,
            fidelity=fidelity,
            upscale=upscale,
            detection_threshold=detection_threshold,
            only_center_face=only_center_face,
            model_name=model_name,
            detection_model=detection_model,
            **kwargs
        )

        self.fidelity = max(0.0, min(1.0, fidelity))
        self.upscale = upscale
        self.detection_threshold = detection_threshold
        self.only_center_face = only_center_face
        self.model_name = model_name
        self.detection_model = detection_model

        # 人脸检测器
        self._face_detector = None

    def load_model(self) -> None:
        """加载 CodeFormer 模型和人脸检测器"""
        try:
            import facexlib
            from facexlib.detection import RetinaFace
        except ImportError as e:
            raise ImportError(
                "请安装依赖: pip install facexlib\n"
                "或运行: pip install -e '.[ml]'"
            ) from e

        # 加载人脸检测器（使用统一注册表）
        from mediafactory.models.model_registry import get_model_local_path

        detection_path = get_model_local_path(self.detection_model)

        if detection_path is None or not detection_path.exists():
            raise FileNotFoundError(
                f"人脸检测模型未下载: {self.detection_model}\n"
                "请在 Models 页面下载相应的人脸检测模型"
            )

        self._face_detector = RetinaFace(
            network_name="resnet50",
            device=self.device,
            model_path=str(detection_path)
        )

        # 加载 CodeFormer 模型
        try:
            from spandrel import ModelLoader, ImageModelDescriptor
        except ImportError as e:
            raise ImportError(
                "请安装依赖: pip install spandrel\n"
                "或运行: pip install -e '.[ml]'"
            ) from e

        model_path = get_model_local_path(self.model_name)

        if model_path is None or not model_path.exists():
            raise FileNotFoundError(
                f"CodeFormer 模型未下载: {self.model_name}\n"
                "请在 Models 页面下载相应的 CodeFormer 模型"
            )

        loader = ModelLoader()
        self._model = loader.load_from_file(str(model_path))

        if not isinstance(self._model, ImageModelDescriptor):
            raise RuntimeError(f"加载的模型不是有效的图像模型: {type(self._model)}")

        self._model.to(self.device)
        self._model.eval()

        if self.half_precision:
            self._model.half()
        else:
            self._model.float()

        self._is_loaded = True
        log_info(f"CodeFormer 人脸修复模型加载成功: {self.model_name}")
        log_info(f"设备: {self.device}, 保真度: {self.fidelity}")

    def detect_faces(self, frame: np.ndarray) -> List[FaceInfo]:
        """
        检测图像中的人脸

        Args:
            frame: BGR 格式的图像

        Returns:
            人脸信息列表
        """
        if not self._is_loaded:
            self.load_model()

        # 转为 RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # 检测人脸
        faces = self._face_detector.detect(
            rgb_frame,
            threshold=self.detection_threshold
        )

        if faces is None or len(faces) == 0:
            return []

        # 转换格式
        result = []
        for face in faces:
            x1, y1, x2, y2 = face[:4].astype(int)
            score = float(face[4])

            # 获取关键点 (如果有)
            landmarks = None
            if len(face) > 5:
                landmarks = face[5:].reshape(-1, 2)

            result.append(FaceInfo(
                bbox=[x1, y1, x2, y2],
                score=score,
                landmarks=landmarks
            ))

        # 如果只处理中心人脸
        if self.only_center_face and result:
            h, w = frame.shape[:2]
            center_x, center_y = w // 2, h // 2

            # 找到最靠近中心的人脸
            min_dist = float('inf')
            center_face = None
            for face in result:
                x1, y1, x2, y2 = face.bbox
                face_center_x = (x1 + x2) // 2
                face_center_y = (y1 + y2) // 2
                dist = ((face_center_x - center_x) ** 2 + (face_center_y - center_y) ** 2) ** 0.5
                if dist < min_dist:
                    min_dist = dist
                    center_face = face

            result = [center_face] if center_face else []

        return result

    def enhance_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        修复单帧图像中的人脸

        Args:
            frame: BGR 格式的图像帧

        Returns:
            修复后的 BGR 图像
        """
        if not self._is_loaded:
            self.load_model()

        # 检测人脸
        faces = self.detect_faces(frame)

        if not faces:
            return frame

        # 复制帧以避免修改原图
        result = frame.copy()

        # 处理每个人脸
        for face in faces:
            x1, y1, x2, y2 = face.bbox

            # 扩展边界框
            h, w = frame.shape[:2]
            face_w = x2 - x1
            face_h = y2 - y1
            pad = int(max(face_w, face_h) * 0.2)

            x1 = max(0, x1 - pad)
            y1 = max(0, y1 - pad)
            x2 = min(w, x2 + pad)
            y2 = min(h, y2 + pad)

            # 提取人脸区域
            face_region = frame[y1:y2, x1:x2]
            if face_region.size == 0:
                continue

            # 修复人脸
            restored = self._restore_face(face_region)

            # 混合回原图 (根据保真度)
            if restored is not None:
                restored = cv2.resize(restored, (x2 - x1, y2 - y1))
                mask = self._create_blend_mask(restored.shape[:2])
                result[y1:y2, x1:x2] = (
                    result[y1:y2, x1:x2] * (1 - mask) +
                    restored * mask
                ).astype(np.uint8)

        return result

    def _restore_face(self, face_region: np.ndarray) -> Optional[np.ndarray]:
        """
        修复人脸区域

        Args:
            face_region: 人脸区域图像

        Returns:
            修复后的人脸区域
        """
        try:
            # BGR -> RGB
            rgb_face = cv2.cvtColor(face_region, cv2.COLOR_BGR2RGB)

            # 转为 tensor
            tensor = torch.from_numpy(rgb_face).float() / PIXEL_NORMALIZATION_FACTOR
            tensor = tensor.permute(2, 0, 1).unsqueeze(0)  # HWC -> 1CHW
            tensor = tensor.to(self.device)

            if self.half_precision:
                tensor = tensor.half()

            # 推理
            with torch.no_grad():
                output = self._model(tensor)

            if output.dtype == torch.float16:
                output = output.float()

            # 混合原图和修复结果
            if self.fidelity > 0:
                output = tensor * self.fidelity + output * (1 - self.fidelity)

            # 转回 numpy
            output = output.squeeze(0).permute(1, 2, 0).cpu().numpy()
            output = np.clip(output * PIXEL_DENORMALIZATION_FACTOR, 0, 255).astype(np.uint8)

            # RGB -> BGR
            output = cv2.cvtColor(output, cv2.COLOR_RGB2BGR)

            return output

        except Exception as e:
            log_warning(f"人脸修复失败: {e}")
            return None

    def _create_blend_mask(self, shape: Tuple[int, int]) -> np.ndarray:
        """
        创建混合蒙版 (边缘羽化)

        Args:
            shape: (height, width)

        Returns:
            混合蒙版 [0, 1]
        """
        h, w = shape
        mask = np.ones((h, w, 1), dtype=np.float32)

        # 边缘羽化宽度
        feather = min(h, w) // 8

        # 创建羽化效果
        for i in range(feather):
            alpha = i / feather
            mask[i, :] = alpha
            mask[h - i - 1, :] = alpha
            mask[:, i] = np.minimum(mask[:, i], alpha)
            mask[:, w - i - 1] = np.minimum(mask[:, w - i - 1], alpha)

        return mask

    def enhance_batch(
        self,
        frames: List[np.ndarray],
        batch_size: Optional[int] = None
    ) -> List[np.ndarray]:
        """
        批量人脸修复 (逐帧处理，因为每帧人脸位置不同)

        Args:
            frames: BGR 格式的图像帧列表
            batch_size: 忽略，人脸修复需要逐帧处理

        Returns:
            修复后的图像列表
        """
        return [self.enhance_frame(frame) for frame in frames]

    def unload_model(self) -> None:
        """卸载模型"""
        super().unload_model()
        self._face_detector = None
