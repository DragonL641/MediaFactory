"""可取消的 FFmpeg 子进程运行器。

FFmpeg 长阻塞段（idet/bwdif/合并重编码）的统一执行入口：小步轮询进度句柄，
用户取消时 terminate 进程并抛 CancelledError——取代裸 subprocess.run 的
"假取消"（状态先置 CANCELLED 但进程继续满载跑完并落盘产物）。
"""

import subprocess

from mediafactory.core.progress_protocol import ProgressCallback
from mediafactory.logging import log_info

_POLL_INTERVAL = 1.0  # 秒；取消响应粒度


class CancelledError(Exception):
    """FFmpeg 运行中被用户取消（进程已 terminate）"""


def run_ffmpeg_cancellable(
    cmd: list[str],
    progress: ProgressCallback | None = None,
    timeout: float = 3600.0,
) -> subprocess.CompletedProcess:
    """执行命令；progress 报告取消时 terminate 进程并抛 CancelledError。

    Returns:
        CompletedProcess（returncode/stdout/stderr；正常结束或非零退出均返回，
        调用方自行判定 returncode）
    """
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        errors="replace",  # Windows 控制台代码页 + 非 UTF-8 路径回显防解码崩溃
    )
    import time

    deadline = time.monotonic() + timeout
    while True:
        try:
            stdout, stderr = proc.communicate(timeout=_POLL_INTERVAL)
            return subprocess.CompletedProcess(cmd, proc.returncode, stdout, stderr)
        except subprocess.TimeoutExpired:
            if progress is not None and progress.is_cancelled():
                proc.terminate()
                try:
                    proc.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.communicate()
                log_info("FFmpeg 子进程已因用户取消而终止")
                raise CancelledError("cancelled during ffmpeg execution") from None
            if time.monotonic() > deadline:
                proc.kill()
                stdout, stderr = proc.communicate()
                return subprocess.CompletedProcess(cmd, proc.returncode, stdout, stderr)
