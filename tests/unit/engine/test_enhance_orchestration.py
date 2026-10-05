"""enhance() 编排契约：合成视频 + 全 mock 模型件，锁三开关组合行为"""

import os

import cv2
import numpy as np
import pytest

pytestmark = [pytest.mark.unit]


@pytest.fixture
def tiny_video(tmp_path):
    path = str(tmp_path / "tiny.mp4")
    w = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"mp4v"), 5, (64, 48))
    for i in range(10):
        w.write(np.full((48, 64, 3), i * 20, dtype=np.uint8))
    w.release()
    return path


@pytest.fixture
def fake_enhancers(monkeypatch):
    """SR/脸修复为恒等假件，记录调用；去噪/平滑默认关闭不触达"""
    import mediafactory.engine.video_enhancement as ve

    calls = {"sr": 0, "face": 0}

    class FakeBatch:
        def __init__(self, *a, **k):
            pass

        def enhance_batch(self, frames, batch_size=4):
            calls["sr"] += 1
            return [f.copy() for f in frames]

        def get_device_info(self):
            return "Device: FAKE"

        def unload_model(self):
            pass

    class FakeFace:
        instances = []

        def __init__(self, device=None, fidelity_weight=0.7):
            self.device = device or "cpu"
            FakeFace.instances.append(self)

        def restore_batch(self, frames):
            calls["face"] += 1
            return [f.copy() for f in frames], 0

        def cleanup(self):
            pass

    monkeypatch.setattr(ve, "RealESRGANEnhancer", FakeBatch)
    monkeypatch.setattr(ve, "FaceRestoreManager", FakeFace)
    return calls


class TestEnhanceOrchestration:
    def test_off_pipeline_runs(self, tiny_video, fake_enhancers, tmp_path):
        from mediafactory.engine.video_enhancement import (
            EnhancementConfig,
            VideoEnhancementEngine,
        )

        out = str(tmp_path / "out.mp4")
        engine = VideoEnhancementEngine(EnhancementConfig(scale=2))
        result = engine.enhance(tiny_video, out)
        assert result == out
        assert fake_enhancers["sr"] >= 1
        assert fake_enhancers["face"] == 0
        assert os.path.exists(out)

    def test_face_restore_invoked_when_on(self, tiny_video, fake_enhancers, tmp_path):
        from mediafactory.engine.video_enhancement import (
            EnhancementConfig,
            VideoEnhancementEngine,
        )

        engine = VideoEnhancementEngine(EnhancementConfig(scale=2, face_restore=True))
        engine.enhance(tiny_video, str(tmp_path / "out2.mp4"))
        assert fake_enhancers["face"] >= 1

    def test_cancel_after_prepass_cleans_temp(self, tiny_video, tmp_path, monkeypatch):
        """Review Focus #4：前置 pass 完成时已取消 → 不进帧管线，临时目录清理。"""
        import mediafactory.engine.video_enhancement as ve
        from mediafactory.engine.video_enhancement import (
            EnhancementConfig,
            VideoEnhancementEngine,
        )
        from mediafactory.exceptions import ProcessingError

        class CancelledProgress:
            def update(self, p, m): ...

            def is_cancelled(self):
                return True

        fake_dir = tmp_path / ".mf_deint_1"
        fake_dir.mkdir()
        (fake_dir / "deinterlaced.mp4").write_bytes(b"x")
        monkeypatch.setattr(
            ve,
            "pre_deinterlace",
            lambda p, progress=None: str(fake_dir / "deinterlaced.mp4"),
        )

        engine = VideoEnhancementEngine(EnhancementConfig(scale=2))
        with pytest.raises(ProcessingError):
            engine.enhance(
                tiny_video, str(tmp_path / "out.mp4"), progress=CancelledProgress()
            )
        assert not fake_dir.exists()
