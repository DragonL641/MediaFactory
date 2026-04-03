"""引擎层测试 fixtures。"""

import pytest
from pathlib import Path
from unittest.mock import Mock


@pytest.fixture
def sample_audio_path(tmp_path: Path) -> Path:
    """提供示例音频文件路径。"""
    audio_path = tmp_path / "sample.wav"
    audio_path.touch()
    return audio_path


@pytest.fixture
def sample_video_path(tmp_path: Path) -> Path:
    """提供示例视频文件路径。"""
    video_path = tmp_path / "sample.mp4"
    video_path.touch()
    return video_path


@pytest.fixture
def sample_segments():
    """提供示例字幕片段。"""
    return [
        {"start": 0.0, "end": 5.0, "text": "Hello, world!"},
        {"start": 5.0, "end": 10.0, "text": "This is a test."},
        {"start": 10.0, "end": 15.0, "text": "Goodbye!"},
    ]


@pytest.fixture
def mock_progress_callback():
    """提供 Mock 进度回调。"""
    callback = Mock()
    return callback
