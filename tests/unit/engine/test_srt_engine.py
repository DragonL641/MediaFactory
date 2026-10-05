"""SRT 引擎测试（使用 Mock）。"""

import pytest


class TestSRTEngine:
    """SRTEngine 测试。"""

    @pytest.mark.unit
    def test_engine_creation(self):
        """测试引擎创建。"""
        from mediafactory.engine import SRTEngine

        engine = SRTEngine()
        assert engine is not None

    @pytest.mark.unit
    def test_srt_timestamp_formatting(self):
        """测试 SRT 时间戳格式化。（来自 test_engine_robustness）"""
        from mediafactory.engine.srt import SRTEngine

        engine = SRTEngine()
        assert engine._format_timestamp(0) == "00:00:00,000"
        assert engine._format_timestamp(3661.5) == "01:01:01,500"
        assert engine._format_timestamp(59.999) == "00:00:59,999"

    @pytest.mark.unit
    def test_format_timestamp_method(self):
        """测试时间戳格式化方法的详细场景。（来自 test_process_video）"""
        from mediafactory.engine import SRTEngine

        engine = SRTEngine()
        # Test basic formatting
        assert engine._format_timestamp(0) == "00:00:00,000"
        assert engine._format_timestamp(1) == "00:00:01,000"
        assert engine._format_timestamp(60) == "00:01:00,000"
        assert engine._format_timestamp(3600) == "01:00:00,000"

        # Test with fractional seconds
        assert engine._format_timestamp(1.5) == "00:00:01,500"
        assert engine._format_timestamp(61.25) == "00:01:01,250"


class TestSRTFormatConstants:
    """SRT 格式常量测试。"""

    @pytest.mark.unit
    def test_srt_format_constants(self):
        """测试 SRT 格式常量。"""
        from mediafactory.engine.srt import SubtitleFormatConstants

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
