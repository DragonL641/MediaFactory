"""_merge_audio 命令构造契约（不实跑 FFmpeg）"""

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
