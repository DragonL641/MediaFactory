"""TimeEstimator.get_video_duration 回归测试。

背景：L11 死代码清扫（15cce61）误删了该方法，但 recognition.py:106
一直在调用——转录类任务（语音转文字/字幕生成）运行时直接崩溃。
"""

import wave
from pathlib import Path

import pytest

from mediafactory.utils.time_estimator import TimeEstimator

pytestmark = pytest.mark.unit


@pytest.fixture
def wav_file(tmp_path: Path) -> Path:
    """1 秒静音 WAV（纯标准库生成，ffprobe 可直接读时长）。"""
    p = tmp_path / "probe.wav"
    with wave.open(str(p), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(16000)
        f.writeframes(b"\x00\x00" * 16000)
    return p


def test_returns_positive_duration_for_real_media(wav_file: Path):
    duration = TimeEstimator.get_video_duration(str(wav_file))
    assert duration is not None
    assert 0.9 <= duration <= 1.1


def test_returns_none_for_missing_file():
    assert TimeEstimator.get_video_duration("/nonexistent/no_audio.wav") is None
