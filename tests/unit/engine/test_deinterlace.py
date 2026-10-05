"""deinterlace 解析/判定/命令构造契约（ffmpeg 实跑归冒烟）"""

import pytest

pytestmark = [pytest.mark.unit]

IDET_PROGRESSIVE = (
    "[Parsed_idet_0 @ 0x7f] Multi frame detection: TFF: 0 BFF: 0 Progressive: 250 Undetermined: 0 | "
    "Multi frame detection: TFF: 0 BFF: 0 Progressive: 250 Undetermined: 0"
)
IDET_INTERLACED = (
    "[Parsed_idet_0 @ 0x7f] Multi frame detection: TFF: 1520 BFF: 96 Progressive: 384 Undetermined: 0"
)
IDET_UNRELIABLE = (
    "[Parsed_idet_0 @ 0x7f] Multi frame detection: TFF: 0 BFF: 0 Progressive: 10 Undetermined: 990"
)


class TestParseIdetOutput:
    def test_progressive_source(self):
        from mediafactory.engine.deinterlace import parse_idet_output

        v = parse_idet_output(IDET_PROGRESSIVE)
        assert v.interlaced is False
        assert v.reliable is True
        assert v.progressive == 250

    def test_interlaced_source_over_threshold(self):
        from mediafactory.engine.deinterlace import parse_idet_output

        v = parse_idet_output(IDET_INTERLACED)
        # (1520+96)/2000 = 80.8% >= 5%
        assert v.interlaced is True
        assert v.reliable is True

    def test_high_undetermined_is_not_reliable(self):
        from mediafactory.engine.deinterlace import parse_idet_output

        v = parse_idet_output(IDET_UNRELIABLE)
        assert v.reliable is False
        assert v.interlaced is False

    def test_empty_output_not_reliable(self):
        from mediafactory.engine.deinterlace import parse_idet_output

        v = parse_idet_output("")
        assert v.reliable is False
        assert v.interlaced is False

    def test_uses_last_multi_frame_line(self):
        from mediafactory.engine.deinterlace import parse_idet_output

        v = parse_idet_output(IDET_PROGRESSIVE + "\n" + IDET_INTERLACED)
        assert v.tff == 1520


class TestBuildBwdifCmd:
    def test_cmd_drops_audio_and_encodes_h264(self):
        from mediafactory.engine.deinterlace import build_bwdif_cmd

        cmd = build_bwdif_cmd("in.mp4", "out.mp4")
        assert "bwdif" in cmd
        assert "-an" in cmd  # 中间产物只喂帧管线，音频在最终合成时从源取
        assert cmd[-1] == "out.mp4"

    def test_uses_imageio_ffmpeg_binary(self):
        from imageio_ffmpeg import get_ffmpeg_exe

        from mediafactory.engine.deinterlace import build_bwdif_cmd

        cmd = build_bwdif_cmd("in.mp4", "out.mp4")
        assert cmd[0] == get_ffmpeg_exe()  # imageio-ffmpeg 自带二进制


class TestPreDeinterlaceFallback:
    def test_detect_failure_returns_original_path(self, tmp_path, monkeypatch):
        """idet 检测异常 → 按非隔行降级返回原路径（spec §5）"""
        import mediafactory.engine.deinterlace as di

        video = str(tmp_path / "src.mp4")
        monkeypatch.setattr(
            di, "detect_interlaced", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
        )
        assert di.pre_deinterlace(video) == video

    def test_progressive_returns_original_path(self, tmp_path, monkeypatch):
        import mediafactory.engine.deinterlace as di
        from mediafactory.engine.deinterlace import DeinterlaceVerdict

        video = str(tmp_path / "src.mp4")
        monkeypatch.setattr(
            di,
            "detect_interlaced",
            lambda *a, **k: DeinterlaceVerdict(False, True, 0, 0, 250, 0),
        )
        assert di.pre_deinterlace(video) == video
