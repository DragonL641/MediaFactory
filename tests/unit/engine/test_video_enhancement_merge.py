"""_merge_audio 命令构造契约（不实跑 FFmpeg）"""

import subprocess
from unittest.mock import patch

import pytest

pytestmark = [pytest.mark.unit]


class TestBuildMergeCmd:
    def _engine(self):
        from mediafactory.engine.video_enhancement import VideoEnhancementEngine

        return VideoEnhancementEngine()

    def test_copy_mode_without_grain(self):
        cmd, timeout = self._engine()._build_merge_cmd(
            "src.mp4", "tmp.mp4", "out.mp4", film_grain=False
        )
        assert "-c:v" in cmd and cmd[cmd.index("-c:v") + 1] == "copy"
        assert "noise=" not in " ".join(cmd)
        assert timeout == 300

    def test_reencode_mode_with_grain(self):
        cmd, timeout = self._engine()._build_merge_cmd(
            "src.mp4", "tmp.mp4", "out.mp4", film_grain=True
        )
        joined = " ".join(cmd)
        assert "noise=alls=7:allf=t" in joined
        assert "libx264" in joined
        assert "-map" in cmd and "1:a:0?" in cmd  # 无音轨源可容忍
        assert timeout == 3600

    def test_output_path_is_last_arg(self):
        cmd, _ = self._engine()._build_merge_cmd(
            "src.mp4", "tmp.mp4", "out.mp4", film_grain=True
        )
        assert cmd[-1] == "out.mp4"


class TestMergeAudioFallback:
    def test_grain_failure_falls_back_to_plain_merge(self, tmp_path):
        """契约：grain 重编码失败 → 重试一次无 grain 合并（保音轨），非裸 copy。"""
        from mediafactory.engine.video_enhancement import VideoEnhancementEngine

        src = tmp_path / "src.mp4"
        src.write_bytes(b"SRC")
        tmpv = tmp_path / "tmp.mp4"
        tmpv.write_bytes(b"TMP")
        out = tmp_path / "out.mp4"

        calls: list[list[str]] = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            if "noise=" in " ".join(cmd):  # grain 重编码：失败
                return subprocess.CompletedProcess(cmd, 1, "", "encode boom")
            out.write_bytes(b"PLAIN_MERGE_OK")  # 无 grain 合并：成功
            return subprocess.CompletedProcess(cmd, 0, "", "")

        with patch("mediafactory.engine.video_enhancement.subprocess.run", fake_run):
            VideoEnhancementEngine()._merge_audio(str(src), str(tmpv), str(out), film_grain=True)

        assert len(calls) == 2
        assert "noise=" in " ".join(calls[0])
        assert "noise=" not in " ".join(calls[1])  # 第二次是无 grain 命令
        assert out.read_bytes() == b"PLAIN_MERGE_OK"  # 产物来自保音轨合并，非裸 copy
