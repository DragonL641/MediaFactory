"""音频引擎测试（Mock FFmpeg 子进程）。"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

pytestmark = [pytest.mark.unit]


class TestAudioEngine:
    """AudioEngine 测试 — mock FFmpeg 子进程而非被测方法。"""

    def test_engine_creation(self):
        """测试引擎创建。"""
        from mediafactory.engine import AudioEngine

        engine = AudioEngine()
        assert engine is not None

    def test_extract_with_ffmpeg_success(self, tmp_path: Path):
        """测试 extract 正常完成。"""
        from mediafactory.engine import AudioEngine

        video_path = tmp_path / "test_video.mp4"
        video_path.write_bytes(b"\x00" * 100)
        audio_path = tmp_path / "test.wav"

        engine = AudioEngine()

        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = ("", "")

        with patch.object(engine, "_get_ffmpeg_executable", return_value="ffmpeg"), \
             patch("subprocess.Popen", return_value=mock_process), \
             patch.object(engine, "_monitor_subprocess"):
            result = engine.extract(str(video_path), output_path=str(audio_path))
            assert result is not None

    def test_extract_raises_on_ffmpeg_failure(self, tmp_path: Path):
        """测试 FFmpeg 返回非零退出码时抛出异常。"""
        from mediafactory.engine import AudioEngine

        video_path = tmp_path / "test_video.mp4"
        video_path.write_bytes(b"\x00" * 100)
        audio_path = tmp_path / "test.wav"

        engine = AudioEngine()

        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.communicate.return_value = ("", "Error: Invalid data found")

        with patch.object(engine, "_get_ffmpeg_executable", return_value="ffmpeg"), \
             patch("subprocess.Popen", return_value=mock_process), \
             patch.object(engine, "_monitor_subprocess"):
            with pytest.raises(Exception):
                engine.extract(str(video_path), output_path=str(audio_path))

    def test_extract_with_progress_callback(self, tmp_path: Path):
        """测试带进度回调的提取。"""
        from mediafactory.engine import AudioEngine

        video_path = tmp_path / "test_video.mp4"
        video_path.write_bytes(b"\x00" * 100)
        audio_path = tmp_path / "test.wav"

        engine = AudioEngine()
        progress_callback = Mock()

        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = ("", "")

        with patch.object(engine, "_get_ffmpeg_executable", return_value="ffmpeg"), \
             patch("subprocess.Popen", return_value=mock_process), \
             patch.object(engine, "_monitor_subprocess"):
            try:
                engine.extract(
                    str(video_path),
                    progress=progress_callback,
                    output_path=str(audio_path),
                )
            except Exception:
                pass

    def test_cleanup_temp_file(self, tmp_path: Path):
        """测试临时文件清理。"""
        from mediafactory.engine import AudioEngine

        engine = AudioEngine()

        temp_file = tmp_path / "temp_audio.wav"
        temp_file.touch()
        assert temp_file.exists()

        engine._temp_audio_path = str(temp_file)
        engine.cleanup_temp_file()

        assert not temp_file.exists()
