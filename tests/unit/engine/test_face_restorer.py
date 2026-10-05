"""FaceRestoreManager 编排契约：无脸通过、有脸计数、MPS→CPU 回退"""

from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest
import torch

pytestmark = [pytest.mark.unit]


@pytest.fixture
def seams(monkeypatch):
    """mock 模块级缝：_weight_path / _load_net / _build_helper"""
    import mediafactory.engine.enhancement.face_restorer as fr

    monkeypatch.setattr(fr, "_weight_path", lambda mid: Path(f"/tmp/{mid}.pth"))
    net = MagicMock()
    net.side_effect = lambda t, w=0.7: (t, torch.zeros(1, 512, 1024), torch.zeros(1, 256, 16, 16))
    monkeypatch.setattr(fr, "_load_net", lambda path, device: net)
    helper = MagicMock()
    helper.cropped_faces = []
    helper.restored_faces = []
    helper.paste_faces_to_input_image.return_value = np.full((4, 4, 3), 7, np.uint8)
    monkeypatch.setattr(fr, "_build_helper", lambda device, wdir: helper)
    return fr, net, helper


class TestFaceRestoreManager:
    def test_no_face_frames_pass_through(self, seams):
        fr, net, helper = seams
        mgr = fr.FaceRestoreManager(device="cpu")
        frames = [np.zeros((4, 4, 3), np.uint8), np.ones((4, 4, 3), np.uint8)]
        out, faced = mgr.restore_batch(frames)
        assert faced == 0
        assert out[0] is frames[0]  # 原样返回

    def test_faces_restored_and_counted(self, seams):
        fr, net, helper = seams
        helper.cropped_faces = [np.zeros((512, 512, 3), np.uint8)]
        mgr = fr.FaceRestoreManager(device="cpu")
        out, faced = mgr.restore_batch([np.zeros((4, 4, 3), np.uint8)])
        assert faced == 1
        assert net.call_count == 1
        assert len(helper.restored_faces) == 1
        assert out[0].shape == (4, 4, 3)

    def test_face_fidelity_weight_forwarded(self, seams):
        fr, net, helper = seams
        helper.cropped_faces = [np.zeros((512, 512, 3), np.uint8)]
        mgr = fr.FaceRestoreManager(device="cpu", fidelity_weight=0.4)
        mgr.restore_batch([np.zeros((4, 4, 3), np.uint8)])
        kwargs = net.call_args[1]
        assert kwargs["w"] == 0.4

    def test_mps_failure_falls_back_to_cpu(self, seams, monkeypatch):
        """契约：mps 初始化 RuntimeError → 整链以 cpu 重建一次。"""
        fr, net, helper = seams
        calls = []

        def flaky_load(path, device):
            calls.append(device)
            if device == "mps":
                raise RuntimeError("MPS op not implemented")
            return MagicMock()

        monkeypatch.setattr(fr, "_load_net", flaky_load)
        mgr = fr.FaceRestoreManager(device="mps")
        assert calls == ["mps", "cpu"]
        assert mgr.device == "cpu"

    def test_second_failure_raises_processing_error(self, seams, monkeypatch):
        """契约：回退 CPU 后仍失败 → ProcessingError（不无限重试）。"""
        from mediafactory.exceptions import ProcessingError

        fr, net, helper = seams

        def always_fail(path, device):
            raise RuntimeError("boom")

        monkeypatch.setattr(fr, "_load_net", always_fail)
        with pytest.raises(ProcessingError):
            fr.FaceRestoreManager(device="mps")

    def test_logging_throttled_for_long_videos(self, seams, monkeypatch):
        """契约：无脸批静默；有脸批每 25 批仅打一次（长片防日志洪泛）。"""
        import mediafactory.engine.enhancement.face_restorer as fr

        logs: list[str] = []
        monkeypatch.setattr(fr, "log_info", lambda m, **k: logs.append(m))
        helper = seams[2]
        helper.cropped_faces = [np.zeros((512, 512, 3), np.uint8)]

        mgr = fr.FaceRestoreManager(device="cpu")
        for _ in range(60):
            mgr.restore_batch([np.zeros((4, 4, 3), np.uint8)])

        # 60 个含脸批 → 第 1 批 + 第 26 批 + 第 51 批 = 3 条
        assert len(logs) == 3

    def test_no_face_batch_is_silent(self, seams, monkeypatch):
        import mediafactory.engine.enhancement.face_restorer as fr

        logs: list[str] = []
        monkeypatch.setattr(fr, "log_info", lambda m, **k: logs.append(m))

        mgr = fr.FaceRestoreManager(device="cpu")
        for _ in range(40):
            mgr.restore_batch([np.zeros((4, 4, 3), np.uint8)])

        assert logs == []  # 全程无脸 → 零日志

    def test_runtime_failure_mid_batch_falls_back(self, seams):
        """契约：mps 推理中途 RuntimeError → 重建后整批重跑。"""
        fr, net, helper = seams
        calls = []
        real_side_effect = net.side_effect

        def flaky_forward(t, w=0.7):
            if mgr.device == "mps" and calls.count("forward") == 0:
                calls.append("forward")
                raise RuntimeError("MPS runtime boom")
            return real_side_effect(t, w=w)

        net.side_effect = flaky_forward
        helper.cropped_faces = [np.zeros((512, 512, 3), np.uint8)]
        mgr = fr.FaceRestoreManager(device="mps")
        frames = [np.zeros((4, 4, 3), np.uint8)]
        out, faced = mgr.restore_batch(frames)
        assert mgr.device == "cpu"
        assert faced == 1  # 回退 CPU 后重跑成功
        assert out[0].shape == (4, 4, 3)
