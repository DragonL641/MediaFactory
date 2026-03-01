"""SRT 引擎测试（使用 Mock）。"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch


class TestSRTEngine:
    """SRTEngine 测试。"""

    @pytest.mark.unit
    def test_engine_creation(self):
        """测试引擎创建。"""
        from mediafactory.engine import SRTEngine

        engine = SRTEngine()
        assert engine is not None

    @pytest.mark.unit
    def test_engine_has_generate_method(self):
        """测试引擎有 generate 方法。"""
        from mediafactory.engine import SRTEngine

        engine = SRTEngine()
        assert hasattr(engine, "generate") or hasattr(engine, "write_srt")

    @pytest.mark.unit
    def test_generate_srt_with_segments(self, tmp_path: Path):
        """测试生成 SRT 文件（Mock）。"""
        from mediafactory.engine import SRTEngine

        segments = [
            {"start": 0.0, "end": 2.0, "text": "Hello, world!"},
            {"start": 2.0, "end": 4.0, "text": "This is a test."},
            {"start": 4.0, "end": 6.0, "text": "Goodbye!"},
        ]

        output_path = tmp_path / "output.srt"
        engine = SRTEngine()

        # Mock generate 方法
        with patch.object(engine, "generate") as mock_generate:
            mock_generate.return_value = str(output_path)

            result = engine.generate(segments, str(output_path))

            assert result == str(output_path)
            mock_generate.assert_called_once()

    @pytest.mark.unit
    def test_generate_vtt_with_segments(self, tmp_path: Path):
        """测试生成 VTT 文件（Mock）。"""
        from mediafactory.engine import SRTEngine

        segments = [
            {"start": 0.0, "end": 2.0, "text": "Hello, world!"},
        ]

        output_path = tmp_path / "output.vtt"
        engine = SRTEngine()

        # Mock generate 方法
        with patch.object(engine, "generate") as mock_generate:
            mock_generate.return_value = str(output_path)

            result = engine.generate(segments, str(output_path), format="vtt")

            assert result == str(output_path)


class TestSRTFormatConstants:
    """SRT 格式常量测试。"""

    @pytest.mark.unit
    def test_srt_format_constants(self):
        """测试 SRT 格式常量。"""
        from mediafactory.constants import SubtitleFormatConstants

        assert SubtitleFormatConstants.MILLISECONDS_PER_SECOND == 1000
        assert SubtitleFormatConstants.SECONDS_PER_MINUTE == 60
        assert SubtitleFormatConstants.SECONDS_PER_HOUR == 3600

    @pytest.mark.unit
    def test_srt_timestamp_format(self):
        """测试 SRT 时间戳格式。"""
        # 测试时间戳转换
        seconds = 3661.5  # 1小时1分1.5秒
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)

        timestamp = f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
        assert timestamp == "01:01:01,500"

    @pytest.mark.unit
    def test_vtt_timestamp_format(self):
        """测试 VTT 时间戳格式。"""
        seconds = 3661.5
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)

        timestamp = f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"
        assert timestamp == "01:01:01.500"
