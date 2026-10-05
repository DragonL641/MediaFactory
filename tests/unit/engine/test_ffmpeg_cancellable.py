"""可取消 FFmpeg 子进程运行器契约（stub 进程，不实跑 ffmpeg）

H1 假取消修复的核心件：阻塞段内轮询取消并 terminate。
"""

import subprocess
import time
from unittest.mock import patch

import pytest

pytestmark = [pytest.mark.unit]


class _FakePopen:
    """按脚本回放的假进程：始终活着直到被 terminate"""

    def __init__(self, script_alive_seconds: float = 60.0):
        self.created = time.monotonic()
        self.script_alive_seconds = script_alive_seconds
        self.terminated = False
        self.returncode = None

    def poll(self):
        if self.terminated:
            return self.returncode if self.returncode is not None else -15
        if time.monotonic() - self.created >= self.script_alive_seconds:
            return 0
        return None

    def terminate(self):
        self.terminated = True
        self.returncode = -15

    def kill(self):
        self.terminated = True
        self.returncode = -9

    def wait(self, timeout=None):
        deadline = time.monotonic() + (
            timeout if timeout else self.script_alive_seconds
        )
        while time.monotonic() < deadline:
            if self.poll() is not None:
                return self.poll()
            time.sleep(0.01)
        raise subprocess.TimeoutExpired(cmd="fake", timeout=timeout)

    def communicate(self, timeout=None):
        code = self.wait(timeout=timeout)
        if self.returncode is None:
            self.returncode = code
        return (b"", b"")


class _CancelledProgress:
    """第 N 次轮询后报告取消的假进度句柄"""

    def __init__(self, cancel_after: int = 3):
        self.polls = 0
        self._cancel_after = cancel_after

    def update(self, p, m): ...

    def is_cancelled(self):
        self.polls += 1
        return self.polls >= self._cancel_after


class TestRunFfmpegCancellable:
    def test_terminates_on_cancel(self):
        from mediafactory.engine.ffmpeg_runner import (
            CancelledError,
            run_ffmpeg_cancellable,
        )

        proc = _FakePopen(script_alive_seconds=60.0)
        progress = _CancelledProgress(cancel_after=3)
        with patch("subprocess.Popen", return_value=proc):
            with pytest.raises(CancelledError):
                run_ffmpeg_cancellable(["ffmpeg", "-i", "a", "b"], progress=progress)
        assert proc.terminated is True

    def test_completes_normally(self):
        from mediafactory.engine.ffmpeg_runner import run_ffmpeg_cancellable

        proc = _FakePopen(script_alive_seconds=0.05)  # 很快自然结束
        with patch("subprocess.Popen", return_value=proc):
            ret = run_ffmpeg_cancellable(["ffmpeg", "-i", "a", "b"], progress=None)
        assert ret.returncode == 0
        assert not proc.terminated

    def test_nonzero_exit_returns_result(self):
        from mediafactory.engine.ffmpeg_runner import run_ffmpeg_cancellable

        proc = _FakePopen(script_alive_seconds=0.05)
        proc.returncode_after = None
        with patch("subprocess.Popen", return_value=proc):
            # 让自然结束时返回非零
            orig_poll = proc.poll

            def poll_nonzero():
                code = orig_poll()
                return code if code is None else 1

            proc.poll = poll_nonzero
            ret = run_ffmpeg_cancellable(["ffmpeg"], progress=None)
        assert ret.returncode == 1
