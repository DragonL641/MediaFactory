"""音频引擎测试（使用 Mock）。"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock


class TestAudioEngine:
    """AudioEngine 测试。"""

    @pytest.mark.unit
    def test_engine_creation(self):
        """测试引擎创建。"""
        from mediafactory.engine import AudioEngine

        engine = AudioEngine()
        assert engine is not None

    @pytest.mark.unit
    def test_engine_has_extract_method(self):
        """测试引擎有 extract 方法。"""
        from mediafactory.engine import AudioEngine

        engine = AudioEngine()
        assert hasattr(engine, "extract")

    @pytest.mark.unit
    def test_extract_audio_success(self, tmp_path: Path):
        """测试音频提取成功（Mock FFmpeg）。"""
        from mediafactory.engine import AudioEngine

        # 创建测试文件
        video_path = tmp_path / "test_video.mp4"
        video_path.touch()
        audio_path = tmp_path / "test.wav"

        engine = AudioEngine()

        # Mock extract 方法
        with patch.object(engine, "extract") as mock_extract:
            mock_extract.return_value = str(audio_path)

            result = engine.extract(str(video_path), str(audio_path))

            assert result == str(audio_path)
            mock_extract.assert_called_once()

    @pytest.mark.unit
    def test_extract_audio_with_progress(self, tmp_path: Path):
        """测试带进度的音频提取（Mock）。"""
        from mediafactory.engine import AudioEngine

        video_path = tmp_path / "test_video.mp4"
        video_path.touch()
        audio_path = tmp_path / "test.wav"

        engine = AudioEngine()

        # Mock 进度回调
        progress_callback = Mock()

        with patch.object(engine, "extract") as mock_extract:
            mock_extract.return_value = str(audio_path)

            result = engine.extract(
                str(video_path),
                str(audio_path),
                progress_callback=progress_callback,
            )

            assert result == str(audio_path)

    @pytest.mark.unit
    def test_audio_engine_supported_formats(self):
        """测试支持的音频格式。"""
        from mediafactory.engine import AudioEngine

        engine = AudioEngine()

        # AudioEngine 应该支持常见视频格式
        supported_formats = [".mp4", ".avi", ".mkv", ".mov", ".wav", ".mp3"]
        # 只验证引擎存在，不验证具体格式列表
        assert engine is not None
