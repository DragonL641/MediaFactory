"""CodeFormer 人脸修复（facexlib 检测/解析 + vendored 网络；不引入 basicsr）"""

import numpy as np
import torch

from mediafactory.exceptions import ProcessingError
from mediafactory.logging import log_info, log_warning


def _weight_path(model_id: str):
    from mediafactory.models.model_registry import get_model_local_path

    path = get_model_local_path(model_id)
    if path is None:
        raise ProcessingError(message=f"Face restoration model missing: {model_id}")
    return path


def _load_net(path, device: str):
    """加载 CodeFormer 主网络（vendored，S-Lab 权重）"""
    from mediafactory.engine.enhancement.codeformer_arch import CodeFormer

    net = CodeFormer(dim_embd=512, n_head=8, codebook_size=1024).to(device)
    ckpt = torch.load(path, map_location="cpu", weights_only=True)
    net.load_state_dict(ckpt["params_ema"])
    net.eval()
    return net


def _build_helper(device: str, weights_dir: str):
    """构建 facexlib 人脸检测/对齐/回贴助手"""
    from facexlib.utils.face_restoration_helper import FaceRestoreHelper

    return FaceRestoreHelper(
        upscale_factor=1,
        face_size=512,
        use_parse=True,
        device=device,
        model_rootpath=weights_dir,
    )


class FaceRestoreManager:
    """逐帧人脸修复；无脸帧原样通过。

    MPS 初始化或推理失败 → 整链回退 CPU 重建一次（仅一次），再失败抛 ProcessingError。
    """

    def __init__(self, device: str | None = None, fidelity_weight: float = 0.7):
        self._requested = device or self._auto_device()
        self._fidelity = fidelity_weight
        self.device = self._requested
        self.faces_found = 0
        self._batches_with_faces = 0  # 日志节流：每 25 个含脸批打一条摘要
        try:
            self._init_chain()
        except RuntimeError as e:
            log_warning(f"face_restore 初始化在 {self.device} 上失败，回退 CPU: {e}")
            self.device = "cpu"
            try:
                self._init_chain()
            except RuntimeError as e2:
                raise ProcessingError(
                    message=f"Face restoration failed on CPU fallback: {e2}"
                ) from e2

    @staticmethod
    def _auto_device() -> str:
        if torch.cuda.is_available():
            return "cuda"
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
        return "cpu"

    def _init_chain(self) -> None:
        from mediafactory.models.model_registry import get_enhancement_models_dir

        self._net = _load_net(_weight_path("CodeFormer"), self.device)
        self._helper = _build_helper(self.device, str(get_enhancement_models_dir()))

    def restore_batch(self, frames: list[np.ndarray]) -> tuple[list[np.ndarray], int]:
        """批量修复。返回 (修复后帧列表, 含脸帧数)。BGR uint8 进出。"""
        try:
            return self._restore_batch_inner(frames)
        except RuntimeError as e:
            if self.device == "cpu":
                raise ProcessingError(message=f"Face restoration failed: {e}") from e
            log_warning(f"face_restore 在 {self.device} 上失败，回退 CPU: {e}")
            self.device = "cpu"
            try:
                self._init_chain()
            except RuntimeError as e2:
                raise ProcessingError(
                    message=f"Face restoration failed on CPU fallback: {e2}"
                ) from e2
            return self._restore_batch_inner(frames)

    def _restore_batch_inner(self, frames: list[np.ndarray]) -> tuple[list[np.ndarray], int]:
        out: list[np.ndarray] = []
        faced = 0
        for frame in frames:
            self._helper.clean_all()
            self._helper.read_image(frame)
            self._helper.get_face_landmarks_5(only_center_face=False, resize=640)
            self._helper.align_warp_face()
            if not self._helper.cropped_faces:
                out.append(frame)
                continue
            faced += 1
            for face in self._helper.cropped_faces:
                face_t = self._to_tensor(face).to(self.device)
                with torch.no_grad():
                    restored, _, _ = self._net(face_t, w=self._fidelity)
                self._helper.restored_faces.append(self._from_tensor(restored))
            self._helper.get_inverse_affine()
            out.append(self._helper.paste_faces_to_input_image())
        self.faces_found += faced
        if faced:
            self._batches_with_faces += 1
            if self._batches_with_faces % 25 == 1:
                log_info(
                    f"face_restore: 已修复 {self.faces_found} 帧含脸"
                    f"（第 {self._batches_with_faces} 个含脸批）"
                )
        return out, faced

    @staticmethod
    def _to_tensor(face_bgr: np.ndarray) -> torch.Tensor:
        t = ((face_bgr[:, :, ::-1] / 255.0 - 0.5) / 0.5).transpose(2, 0, 1)
        return torch.from_numpy(t.astype(np.float32))[None]

    @staticmethod
    def _from_tensor(restored: torch.Tensor) -> np.ndarray:
        arr = restored[0].squeeze(0).permute(1, 2, 0).clamp(-1, 1).cpu().numpy()
        return ((arr + 1) / 2 * 255).astype(np.uint8)[:, :, ::-1]

    def cleanup(self) -> None:
        self._net = None
        self._helper = None
