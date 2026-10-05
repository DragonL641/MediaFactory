"""Spike：验证 facexlib + CodeFormer 最小推理链（用后即弃）。

用法: uv run python scripts/debug/spike_face_restore.py <含人脸的图片路径> [--cpu]
产出: MPS/CPU 可用性结论 + 实测权重文件大小 + FaceRestoreHelper 0.3.0 调用序列。

结论（2026-10-05，Apple Silicon）:
- MPS 全链可用（检测→CodeFormer 修复→paste 回贴），CPU 亦可用
- 3 脸冷启动: MPS ~8.0s / CPU ~11.1s（含检测+解析+warp）
- facexlib 0.3.0 序列: clean_all→read_image→get_face_landmarks_5→
  align_warp_face→[net(face, w) 三元组→restored_faces.append]→
  get_inverse_affine→paste_faces_to_input_image()
"""

import inspect
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import torch

WEIGHTS_DIR = Path("data/models/enhancement")
HF_MIRROR = "https://hf-mirror.com"
CODEFORMER_REPO = "ziixzz/codeformer-v0.1.0.pth"
CODEFORMER_FILE = "codeformer-v0.1.0.pth"
FACEDETECT_REPO = "leonelhs/facexlib"
FACEDETECT_FILE = "detection_Resnet50_Final.pth"
FACEPARSE_REPO = "leonelhs/facexlib"
FACEPARSE_FILE = "parsing_parsenet.pth"


def ensure_weights() -> dict[str, Path]:
    """缺失权重经 GET 流式下载到 data/models/enhancement/（与注册表落点一致）。"""
    from mediafactory.models.model_download import _download_file_via_get

    WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)
    wanted = {
        "codeformer": (CODEFORMER_REPO, CODEFORMER_FILE),
        "detect": (FACEDETECT_REPO, FACEDETECT_FILE),
        "parse": (FACEPARSE_REPO, FACEPARSE_FILE),
    }
    out = {}
    for key, (repo, fname) in wanted.items():
        target = WEIGHTS_DIR / fname
        if not target.exists():
            for attempt in range(5):  # 镜像间歇性 SSL 重置，逐文件重试
                try:
                    _download_file_via_get(
                        repo_id=repo, filename=fname, local_path=target,
                        endpoint=HF_MIRROR,
                    )
                    break
                except Exception as e:
                    if attempt == 4:
                        raise
                    print(f"{key}: attempt {attempt + 1} failed ({type(e).__name__}), retrying...")
                    time.sleep(3)
        print(f"{key}: {target} {target.stat().st_size / 1024 / 1024:.0f}MiB")
        out[key] = target
    return out


def main() -> None:
    img_path = Path(sys.argv[1] if len(sys.argv) > 1 else "")
    force_cpu = "--cpu" in sys.argv
    weights = ensure_weights()

    from facexlib.utils.face_restoration_helper import FaceRestoreHelper

    print("--- FaceRestoreHelper 调用签名（Task 9 按此实现）---")
    for m in ("read_image", "get_face_landmarks_5", "align_warp_face",
              "paste_faces_to_input_image", "clean_all"):
        print(m, inspect.signature(getattr(FaceRestoreHelper, m)))

    device = "cpu"
    if not force_cpu and torch.backends.mps.is_available():
        device = "mps"
    print(f"device={device}")

    from mediafactory.engine.enhancement.codeformer_arch import CodeFormer  # noqa: E402

    net = CodeFormer(dim_embd=512, codebook_size=1024, n_head=8).to(device)
    ckpt = torch.load(weights["codeformer"], map_location="cpu", weights_only=True)
    net.load_state_dict(ckpt["params_ema"])
    net.eval()

    helper = FaceRestoreHelper(
        upscale_factor=1, face_size=512, use_parse=True, device=device,
        model_rootpath=str(WEIGHTS_DIR),
    )
    img = cv2.imread(str(img_path))
    assert img is not None, f"cannot read {img_path}"
    helper.clean_all()
    helper.read_image(img)
    helper.get_face_landmarks_5(only_center_face=False, resize=640)
    helper.align_warp_face()
    t0 = time.time()
    for i, face in enumerate(helper.cropped_faces):
        face_t = torch.from_numpy(
            ((face[:, :, ::-1] / 255.0 - 0.5) / 0.5).transpose(2, 0, 1).astype(np.float32)
        )[None].to(device)
        with torch.no_grad():
            restored, _, _ = net(face_t, w=0.7)
        restored = restored[0].squeeze(0).permute(1, 2, 0).clamp(-1, 1).cpu().numpy()
        restored = ((restored + 1) / 2 * 255).astype(np.uint8)[:, :, ::-1]
        print(f"face {i}: in {face.shape} -> out {restored.shape}")
        helper.restored_faces.append(restored)
    helper.get_inverse_affine()
    restored_img = helper.paste_faces_to_input_image()
    print(f"faces={len(helper.cropped_faces)} elapsed={time.time() - t0:.2f}s "
          f"out={None if restored_img is None else restored_img.shape}")
    helper.clean_all()


if __name__ == "__main__":
    main()
