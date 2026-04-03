"""识别引擎测试（使用 Mock Whisper 模型）。"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock


class TestRecognitionEngine:
    """RecognitionEngine 测试（Mock Whisper）。"""

    @pytest.mark.unit
    def test_engine_creation(self):
        """测试引擎创建。"""
        from mediafactory.engine import RecognitionEngine

        engine = RecognitionEngine()
        assert engine is not None

    @pytest.mark.unit
    def test_engine_has_transcribe_method(self):
        """测试引擎有 transcribe 方法。"""
        from mediafactory.engine import RecognitionEngine

        engine = RecognitionEngine()
        assert hasattr(engine, "transcribe")

    @pytest.mark.unit
    def test_transcribe_returns_result(self, tmp_path: Path):
        """测试转录返回结果（Mock）。"""
        from mediafactory.engine import RecognitionEngine

        # 创建测试音频文件
        audio_path = tmp_path / "test.wav"
        audio_path.touch()

        engine = RecognitionEngine()

        # Mock transcribe 方法
        with patch.object(engine, "transcribe") as mock_transcribe:
            mock_transcribe.return_value = {
                "segments": [
                    {"start": 0.0, "end": 2.0, "text": "Hello, world!"},
                    {"start": 2.0, "end": 4.0, "text": "This is a test."},
                ],
                "language": "en",
            }

            result = engine.transcribe(str(audio_path))

            assert result["language"] == "en"
            assert len(result["segments"]) == 2
            assert result["segments"][0]["text"] == "Hello, world!"

    @pytest.mark.unit
    def test_detect_language_with_mock(self, tmp_path: Path):
        """测试语言检测（Mock）。"""
        from mediafactory.engine import RecognitionEngine

        audio_path = tmp_path / "test.wav"
        audio_path.touch()

        engine = RecognitionEngine()

        # Mock detect_language_only 方法
        with patch.object(engine, "detect_language_only") as mock_detect:
            mock_detect.return_value = {
                "language": "ja",
                "language_probability": 0.92,
            }

            # 创建 Mock 模型
            mock_model = Mock()

            result = engine.detect_language_only(mock_model, str(audio_path))

            assert result["language"] == "ja"
            assert result["language_probability"] > 0.9
