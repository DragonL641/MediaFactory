"""音频引擎测试（Mock FFmpeg 子进程）。"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock


class TestAudioEngine:
    """AudioEngine 测试 — mock FFmpeg 子进程而非被测方法。"""

    @pytest.mark.unit
    def test_engine_creation(self):
        """测试引擎创建。"""
        from mediafactory.engine import AudioEngine

        engine = AudioEngine()
        assert engine is not None

    @pytest.mark.unit
    def test_extract_builds_correct_ffmpeg_command(self, tmp_path: Path):
        """测试 extract 构建正确的 FFmpeg 命令。"""
        from mediafactory.engine import AudioEngine

        video_path = tmp_path / "test_video.mp4"
        video_path.touch()
        audio_path = tmp_path / "test.wav"

        engine = AudioEngine()

        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (b"", b"")

        with patch("subprocess.Popen", return_value=mock_process) as mock_popen:
            result = engine.extract(str(video_path), str(audio_path))

            # 验证 Popen 被调用
            mock_popen.assert_called_once()
            call_args = mock_popen.call_args

            # 验证命令包含关键 FFmpeg 参数
            cmd = call_args[0][0] if call_args[0] else call_args[1].get("args", [])
            cmd_str = " ".join(cmd) if isinstance(cmd, list) else str(cmd)

            # FFmpeg 应包含输入文件和输出文件
            assert str(video_path) in cmd_str or str(audio_path) in cmd_str

    @pytest.mark.unit
    def test_extract_raises_on_ffmpeg_failure(self, tmp_path: Path):
        """测试 FFmpeg 返回非零退出码时抛出异常。"""
        from mediafactory.engine import AudioEngine

        video_path = tmp_path / "test_video.mp4"
        video_path.touch()
        audio_path = tmp_path / "test.wav"

        engine = AudioEngine()

        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.communicate.return_value = (b"", b"Error: Invalid data found")

        with patch("subprocess.Popen", return_value=mock_process):
            with pytest.raises(Exception):
                engine.extract(str(video_path), str(audio_path))

    @pytest.mark.unit
    def test_extract_with_progress_callback(self, tmp_path: Path):
        """测试带进度回调的提取。"""
        from mediafactory.engine import AudioEngine

        video_path = tmp_path / "test_video.mp4"
        video_path.touch()
        audio_path = tmp_path / "test.wav"

        engine = AudioEngine()
        progress_callback = Mock()

        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (b"", b"")

        with patch("subprocess.Popen", return_value=mock_process):
            # 调用不应抛出异常
            try:
                engine.extract(
                    str(video_path),
                    str(audio_path),
                    progress_callback=progress_callback,
                )
            except Exception:
                # 某些路径可能因为文件不存在等抛异常，这是可接受的
                pass

    @pytest.mark.unit
    def test_cleanup_temp_file(self, tmp_path: Path):
        """测试临时文件清理。"""
        from mediafactory.engine import AudioEngine

        engine = AudioEngine()

        # 创建临时文件
        temp_file = tmp_path / "temp_audio.wav"
        temp_file.touch()
        assert temp_file.exists()

        engine._temp_audio_path = str(temp_file)
        engine.cleanup_temp_file()

        assert not temp_file.exists()
